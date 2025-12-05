from flask import render_template, redirect, url_for, request, flash, send_from_directory, jsonify, session, send_file
from werkzeug.utils import secure_filename
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import User, File, Folder, FileAttribute, FileVersion
from utils import convert_cad_to_stl
from translations import translations
import os
import uuid
from datetime import datetime

ALLOWED_EXTENSIONS = {
    'stp', 'step', 'igs', 'iges', 'brep', 'geo',  # Geometry
    'msh', 'stl', 'wrl', 'vrml', 'obj', 'ply', 'unv', 'vtk', 'med',  # Mesh
    'inp', 'bdf', 'nas', 'key', 'k', 'su2'  # Solver
}

@app.context_processor
def inject_get_text():
    def get_text(key):
        if current_user.is_authenticated:
            lang = current_user.language
        else:
            lang = session.get('language', 'zh')
        return translations.get(lang, translations['zh']).get(key, key)
    
    def get_theme():
        if current_user.is_authenticated:
            return current_user.theme
        return session.get('theme', 'dark')
        
    return dict(_=get_text, current_theme=get_theme())

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in ['en', 'zh']:
        if current_user.is_authenticated:
            current_user.language = lang
            db.session.commit()
        session['language'] = lang
    return redirect(request.referrer or url_for('index'))

@app.route('/set_theme/<theme>')
def set_theme(theme):
    if theme in ['light', 'dark']:
        if current_user.is_authenticated:
            current_user.theme = theme
            db.session.commit()
        session['theme'] = theme
    return redirect(request.referrer or url_for('index'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
            
        user = User(username=username, password=password) # In production, hash password!
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password: # In production, check hash!
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        username = request.form.get('username')
        new_password = request.form.get('new_password')
        current_password = request.form.get('current_password')
        
        # Update username
        if username and username != current_user.username:
            if User.query.filter_by(username=username).first():
                flash('Username already exists')
            else:
                current_user.username = username
                
        # Update password
        if new_password:
            if not current_password:
                flash('Please enter your current password to change it.')
            elif current_user.password != current_password:
                flash('Incorrect current password.')
            else:
                current_user.password = new_password
                flash('Password updated successfully')
            
        db.session.commit()
        if not new_password and (not username or username == current_user.username):
             pass # No changes
        elif not new_password:
             flash('Profile updated successfully')

        return redirect(url_for('profile'))
        
    return render_template('profile.html')

@app.route('/dashboard')
@app.route('/dashboard/<int:folder_id>')
@login_required
def dashboard(folder_id=None):
    current_folder = None
    if folder_id:
        current_folder = Folder.query.get_or_404(folder_id)
        # Check permission (owner or shared)
        if current_folder.user_id != current_user.id:
            # Check if shared
            if current_user not in current_folder.shared_with:
                flash('Permission denied')
                return redirect(url_for('dashboard'))
    
    if folder_id:
        subfolders = Folder.query.filter_by(parent_id=folder_id).all()
        my_files = File.query.filter_by(folder_id=folder_id).all()
        shared_files = []
        shared_folders = []
    else:
        subfolders = Folder.query.filter_by(user_id=current_user.id, parent_id=None).all()
        my_files = File.query.filter_by(user_id=current_user.id, folder_id=None).all()
        shared_files = current_user.shared_with_me
        shared_folders = current_user.shared_folders
    
    # Fetch all user folders for the "Move" functionality
    all_user_folders = Folder.query.filter_by(user_id=current_user.id).all()
        
    return render_template('dashboard.html', 
                         my_files=my_files, 
                         shared_files=shared_files, 
                         subfolders=subfolders, 
                         shared_folders=shared_folders,
                         current_folder=current_folder,
                         all_user_folders=all_user_folders)

@app.route('/create_folder', methods=['POST'])
@login_required
def create_folder():
    folder_name = request.form.get('folder_name')
    parent_id = request.form.get('parent_id')
    
    # Ensure parent_id is None if empty string
    if not parent_id:
        parent_id = None
    else:
        try:
            parent_id = int(parent_id)
        except ValueError:
            parent_id = None
    
    if not folder_name:
        flash('Folder name is required')
        return redirect(url_for('dashboard', folder_id=parent_id))
        
    if parent_id:
        parent_folder = Folder.query.get(parent_id)
        if not parent_folder or parent_folder.user_id != current_user.id:
            flash('Invalid parent folder')
            return redirect(url_for('dashboard'))
            
    new_folder = Folder(name=folder_name, user_id=current_user.id, parent_id=parent_id)
    db.session.add(new_folder)
    db.session.commit()
    flash('Folder created')
    return redirect(url_for('dashboard', folder_id=parent_id))

@app.route('/delete_folder/<int:folder_id>', methods=['POST'])
@login_required
def delete_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id:
        flash('Permission denied')
        return redirect(url_for('dashboard'))

    # Recursive deletion function
    def delete_folder_contents(current_folder):
        # Delete files in this folder
        for file in current_folder.files:
            # Delete from disk
            try:
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filepath)
                if os.path.exists(full_path):
                    os.remove(full_path)
                
                # Delete STL if exists
                stl_path = full_path + '.stl'
                if os.path.exists(stl_path):
                    os.remove(stl_path)
                    
                # Delete versions
                for version in file.versions:
                     # version.filepath is relative to UPLOAD_FOLDER
                     v_path = os.path.join(app.config['UPLOAD_FOLDER'], version.filepath)
                     if os.path.exists(v_path):
                         os.remove(v_path)
            except Exception as e:
                print(f"Error deleting file {file.id} from disk: {e}")
            
            # DB deletion will be handled by cascade if configured, but let's be explicit or rely on session.delete
            db.session.delete(file)
        
        # Recurse for subfolders
        for sub in current_folder.subfolders:
            delete_folder_contents(sub)
            db.session.delete(sub)

    delete_folder_contents(folder)
    parent_id = folder.parent_id
    db.session.delete(folder)
    db.session.commit()
    
    flash('Folder and all contents deleted')
    return redirect(url_for('dashboard', folder_id=parent_id))

@app.route('/api/search_users')
@login_required
def search_users():
    query = request.args.get('q', '')
    if len(query) < 1:
        return jsonify([])
    
    # Search users excluding current user
    users = User.query.filter(User.username.ilike(f'%{query}%'), User.id != current_user.id).limit(10).all()
    return jsonify([{'id': u.id, 'username': u.username} for u in users])

import re

def custom_secure_filename(filename):
    # Remove invalid characters for Windows/Linux: \ / : * ? " < > |
    return re.sub(r'[\\/*?:"<>|]', "", filename).strip()

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('dashboard'))
    file = request.files['file']
    folder_id = request.form.get('folder_id')
    if folder_id:
        folder_id = int(folder_id)
        # Verify folder ownership
        folder = Folder.query.get(folder_id)
        if not folder or folder.user_id != current_user.id:
            flash('Invalid folder')
            return redirect(url_for('dashboard'))
    else:
        folder_id = None

    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('dashboard', folder_id=folder_id))
        
    # Get fixed attributes
    part_name = request.form.get('part_name')
    part_number = request.form.get('part_number')
    mass = request.form.get('mass')
    material = request.form.get('material')
    surface_finish = request.form.get('surface_finish')
    supplier = request.form.get('supplier')
    unit_price = request.form.get('unit_price')
    material_code = request.form.get('material_code')
    
    # Validate required attributes
    if not all([part_name, part_number, mass, material, surface_finish, supplier, unit_price, material_code]):
        flash('All fixed attributes (Part Name, Part Number, Mass, Material, Finish, Supplier, Price, Code) are required.')
        return redirect(url_for('dashboard', folder_id=folder_id))

    if file and file.filename and allowed_file(file.filename):
        # Use original filename to get extension, but be careful
        original_filename = file.filename
        if '.' in original_filename:
            ext = original_filename.rsplit('.', 1)[1].lower()
        else:
            ext = ''
        
        # Construct new filename: PartName_PartNumber.ext
        # Use custom_secure_filename to allow Chinese characters
        safe_part_name = custom_secure_filename(part_name)
        safe_part_number = custom_secure_filename(part_number)
        new_filename = f"{safe_part_name}_{safe_part_number}.{ext}"
        
        # Ensure unique filename on disk to prevent overwrites
        # We use UUID for disk storage, so filename collision on disk is not an issue
        # But we store the display filename in DB
        unique_filename = f"{uuid.uuid4().hex}_{new_filename}"
        
        # User specific directory
        user_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id))
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
            
        filepath = os.path.join(user_dir, unique_filename)
        file.save(filepath)
        
        # Convert if necessary
        if ext in ['stp', 'step', 'igs', 'iges']:
            stl_filepath = filepath + '.stl'
            convert_cad_to_stl(filepath, stl_filepath)
        
        # Store relative path including user_id for easy retrieval but keep DB clean
        # Actually, let's store just the filename in DB and reconstruct path using user_id
        # But to keep backward compatibility with shared files logic (which might need full path if we change logic),
        # let's store the relative path from UPLOAD_FOLDER: "user_id/filename"
        db_filepath = f"{current_user.id}/{unique_filename}"
        
        new_file = File(
            filename=new_filename, 
            filepath=db_filepath, 
            user_id=current_user.id, 
            folder_id=folder_id,
            part_name=part_name,
            part_number=part_number,
            mass=mass,
            material=material,
            surface_finish=surface_finish,
            supplier=supplier,
            unit_price=unit_price,
            material_code=material_code
        )
        db.session.add(new_file)
        db.session.commit()
        flash('File uploaded successfully')
    else:
        flash('Allowed file types are: prt, stp, stl, igs')
    return redirect(url_for('dashboard', folder_id=folder_id))

@app.route('/move_file/<int:file_id>', methods=['POST'])
@login_required
def move_file(file_id):
    file = File.query.get_or_404(file_id)
    if file.user_id != current_user.id:
        flash('Permission denied')
        return redirect(url_for('dashboard'))
        
    target_folder_id = request.form.get('target_folder_id')
    
    if target_folder_id == 'root':
        file.folder_id = None
    else:
        try:
            target_folder_id = int(target_folder_id)
            target_folder = Folder.query.get(target_folder_id)
            if not target_folder or target_folder.user_id != current_user.id:
                flash('Invalid target folder')
                return redirect(url_for('dashboard'))
            file.folder_id = target_folder_id
        except ValueError:
            flash('Invalid target folder')
            return redirect(url_for('dashboard'))
            
    db.session.commit()
    flash('File moved successfully')
    return redirect(url_for('dashboard', folder_id=file.folder_id))

@app.route('/delete_file/<int:file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    file = File.query.get_or_404(file_id)
    if file.user_id != current_user.id:
        flash('Permission denied')
        return redirect(url_for('dashboard'))
    
    # Remove file from disk
    try:
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filepath)
        if os.path.exists(full_path):
            os.remove(full_path)
            
        # Remove potential converted STL file
        stl_path = full_path + '.stl'
        if os.path.exists(stl_path):
            os.remove(stl_path)

        # Remove versions from disk
        for version in file.versions:
            v_path = os.path.join(app.config['UPLOAD_FOLDER'], version.filepath)
            if os.path.exists(v_path):
                os.remove(v_path)
            
    except Exception as e:
        print(f"Error deleting file from disk: {e}")
        # Continue to delete from DB even if disk delete fails (or partial)
    
    folder_id = file.folder_id
    db.session.delete(file)
    db.session.commit()
    flash('File deleted successfully')
    return redirect(url_for('dashboard', folder_id=folder_id))

@app.route('/update_file_properties/<int:file_id>', methods=['POST'])
@login_required
def update_file_properties(file_id):
    file = File.query.get_or_404(file_id)
    if file.user_id != current_user.id:
        flash('Permission denied')
        return redirect(url_for('dashboard'))
    
    # Update fixed attributes
    part_name = request.form.get('part_name')
    part_number = request.form.get('part_number')
    mass = request.form.get('mass')
    material = request.form.get('material')
    surface_finish = request.form.get('surface_finish')
    supplier = request.form.get('supplier')
    unit_price = request.form.get('unit_price')
    material_code = request.form.get('material_code')
    
    if not all([part_name, part_number, mass, material, surface_finish, supplier, unit_price, material_code]):
        flash('All fixed attributes cannot be empty.')
        return redirect(url_for('view_file', file_id=file.id))

    file.part_name = part_name
    file.part_number = part_number
    file.mass = mass
    file.material = material
    file.surface_finish = surface_finish
    file.supplier = supplier
    file.unit_price = unit_price
    file.material_code = material_code
    
    # Update filename if Part Name or Part Number changed
    ext = file.filename.rsplit('.', 1)[1].lower()
    safe_part_name = custom_secure_filename(part_name)
    safe_part_number = custom_secure_filename(part_number)
    new_filename = f"{safe_part_name}_{safe_part_number}.{ext}"
    file.filename = new_filename
    
    # Update custom attributes
    # First, remove existing ones (simple approach)
    FileAttribute.query.filter_by(file_id=file.id).delete()
    
    # Add new ones
    custom_keys = request.form.getlist('custom_keys[]')
    custom_values = request.form.getlist('custom_values[]')
    
    for k, v in zip(custom_keys, custom_values):
        if k and v: # Only add if both key and value exist
            attr = FileAttribute(file_id=file.id, key=k, value=v)
            db.session.add(attr)
            
    db.session.commit()
    flash('Properties updated successfully')
    
    # Redirect back to viewer or dashboard
    return redirect(url_for('view_file', file_id=file.id))

@app.route('/upload_version/<int:file_id>', methods=['POST'])
@login_required
def upload_version(file_id):
    file = File.query.get_or_404(file_id)
    if file.user_id != current_user.id:
        flash('Permission denied')
        return redirect(url_for('dashboard'))
        
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('view_file', file_id=file.id))
        
    new_file_obj = request.files['file']
    if new_file_obj.filename == '':
        flash('No selected file')
        return redirect(url_for('view_file', file_id=file.id))
        
    if new_file_obj and allowed_file(new_file_obj.filename):
        # Archive current version
        old_version = FileVersion(
            file_id=file.id,
            filepath=file.filepath,
            filename=file.filename,
            upload_date=file.upload_date,
            version_number=file.version,
            uploader_id=file.user_id
        )
        db.session.add(old_version)
        
        # Save new file
        filename = custom_secure_filename(new_file_obj.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        user_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id))
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
            
        filepath = os.path.join(user_dir, unique_filename)
        new_file_obj.save(filepath)
        
        # Convert if necessary
        ext = filename.rsplit('.', 1)[1].lower()
        if ext in ['stp', 'step', 'igs', 'iges']:
            stl_filepath = filepath + '.stl'
            convert_cad_to_stl(filepath, stl_filepath)
            
        # Update File record
        db_filepath = f"{current_user.id}/{unique_filename}"
        file.filename = filename
        file.filepath = db_filepath
        file.upload_date = datetime.utcnow()
        file.version += 1
        
        db.session.commit()
        flash(f'Updated to version {file.version}')
    else:
        flash('Invalid file type')
        
    return redirect(url_for('view_file', file_id=file.id))

@app.route('/share/<int:file_id>', methods=['POST'])
@login_required
def share_file(file_id):
    file = File.query.get_or_404(file_id)
    if file.user_id != current_user.id:
        flash('Permission denied')
        return redirect(url_for('dashboard'))
        
    share_type = request.form.get('share_type')
    
    if share_type == 'public':
        file.is_public = True
        db.session.commit()
        flash('File is now public')
    else:
        file.is_public = False
        usernames = request.form.getlist('usernames[]')
        
        added_users = []
        for username in usernames:
            user_to_share = User.query.filter_by(username=username).first()
            if user_to_share and user_to_share not in file.shared_with:
                file.shared_with.append(user_to_share)
                added_users.append(username)
        
        db.session.commit()
        if added_users:
            flash(f'Shared with: {", ".join(added_users)}')
        else:
            flash('Updated sharing settings')
            
    return redirect(url_for('dashboard'))

@app.route('/share_folder/<int:folder_id>', methods=['POST'])
@login_required
def share_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    if folder.user_id != current_user.id:
        flash('Permission denied')
        return redirect(url_for('dashboard'))
        
    usernames = request.form.getlist('usernames[]')
    
    added_users = []
    for username in usernames:
        user_to_share = User.query.filter_by(username=username).first()
        if user_to_share and user_to_share not in folder.shared_with:
            folder.shared_with.append(user_to_share)
            added_users.append(username)
    
    db.session.commit()
    if added_users:
        flash(f'Folder shared with: {", ".join(added_users)}')
    else:
        flash('No new users added to share')
        
    return redirect(url_for('dashboard'))

@app.route('/public')
def public_gallery():
    files = File.query.filter_by(is_public=True).all()
    return render_template('public_gallery.html', files=files)

@app.route('/view/<int:file_id>')
@login_required
def view_file(file_id):
    file = File.query.get_or_404(file_id)
    # Check permissions
    if not file.is_public and file.user_id != current_user.id and current_user not in file.shared_with:
        flash('Permission denied')
        return redirect(url_for('dashboard'))
    
    # Determine view URL and extension
    ext = file.filename.rsplit('.', 1)[1].lower()
    
    # Construct full path
    # file.filepath is now "user_id/unique_filename"
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filepath)
    
    if ext in ['stp', 'step', 'igs', 'iges', 'prt', 'sldprt', 'sldasm', 'catpart', 'catproduct', 'dwg', 'dxf', 'ans', 'cdb', 'inp', 'key', 'k', 'hm', 'fem']:
        # Check if converted file exists
        converted_full_path = full_path + '.stl'
        converted_db_path = file.filepath + '.stl'
        
        if os.path.exists(converted_full_path):
            view_url = url_for('uploaded_file', filename=converted_db_path)
            view_ext = 'stl'
        else:
            # Try to convert on the fly if missing
            success = convert_cad_to_stl(full_path, converted_full_path)
            if success:
                view_url = url_for('uploaded_file', filename=converted_db_path)
                view_ext = 'stl'
            else:
                # If conversion fails, we can't view it in 3D, but maybe we can download it.
                # For now, let's just show the original and let the viewer handle the error (or show a message)
                # But viewer.html expects STL for 3D.
                # We will pass a flag or handle it in template.
                flash('Preview not available for this format. Please download to view.')
                view_url = url_for('uploaded_file', filename=file.filepath)
                view_ext = ext # This will likely trigger "not supported" in viewer.html logic if we had any
    else:
        view_url = url_for('uploaded_file', filename=file.filepath)
        view_ext = ext

    return render_template('viewer.html', file=file, view_url=view_url, view_ext=view_ext)

@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    # filename here will be "user_id/unique_filename"
    # We need to verify access
    
    # Check if it's a derived file (e.g. .stl from .stp)
    # The filename passed here might be "1/abc...xyz.stp.stl"
    
    # Clean the filename to find the DB entry
    # If it ends with .stl but the original was .stp, we need to find the .stp entry
    
    # Security check: ensure no directory traversal
    if '..' in filename or filename.startswith('/'):
        return "Invalid path", 400

    # Try to find exact match first
    file = File.query.filter_by(filepath=filename).first()
    
    if not file and filename.endswith('.stl'):
        # Try stripping .stl
        possible_original = filename[:-4]
        file = File.query.filter_by(filepath=possible_original).first()
        
    if file:
        if file.is_public or file.user_id == current_user.id or current_user in file.shared_with:
             return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    return "Permission Denied", 403

@app.route('/download/<int:file_id>')
@login_required
def download_file(file_id):
    file = File.query.get_or_404(file_id)
    
    # Check permissions
    if not file.is_public and file.user_id != current_user.id and current_user not in file.shared_with:
        flash('Permission denied')
        return redirect(url_for('dashboard'))
        
    # Construct full path
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filepath)
    
    if not os.path.exists(full_path):
        flash('File not found on server')
        return redirect(url_for('dashboard'))
        
    return send_file(full_path, as_attachment=True, download_name=file.filename)

@app.route('/download_version/<int:version_id>')
@login_required
def download_version(version_id):
    version = FileVersion.query.get_or_404(version_id)
    file = File.query.get(version.file_id)
    
    # Check permissions on the main file
    if not file.is_public and file.user_id != current_user.id and current_user not in file.shared_with:
        flash('Permission denied')
        return redirect(url_for('dashboard'))
        
    # Construct full path
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], version.filepath)
    
    if not os.path.exists(full_path):
        flash('File version not found on server')
        return redirect(url_for('view_file', file_id=file.id))
        
    return send_file(full_path, as_attachment=True, download_name=version.filename)
