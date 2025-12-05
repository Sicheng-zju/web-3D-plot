from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# Association table for sharing files
shared_files = db.Table('shared_files',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('file_id', db.Integer, db.ForeignKey('file.id'), primary_key=True)
)

# Association table for sharing folders
shared_folders = db.Table('shared_folders',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('folder_id', db.Integer, db.ForeignKey('folder.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    language = db.Column(db.String(10), default='zh')
    theme = db.Column(db.String(10), default='dark')
    files = db.relationship('File', backref='owner', lazy=True)
    folders = db.relationship('Folder', backref='owner', lazy=True)
    shared_with_me = db.relationship('File', secondary=shared_files, backref=db.backref('shared_with', lazy='dynamic'))

class Folder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    subfolders = db.relationship('Folder', backref=db.backref('parent', remote_side=[id]), lazy=True)
    files = db.relationship('File', backref='folder', lazy=True)
    shared_with = db.relationship('User', secondary=shared_folders, backref=db.backref('shared_folders', lazy='dynamic'))

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    filepath = db.Column(db.String(200), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=True)
    is_public = db.Column(db.Boolean, default=False)
    version = db.Column(db.Integer, default=1)
    versions = db.relationship('FileVersion', backref='file', lazy=True, cascade="all, delete-orphan")

    # Fixed attributes
    mass = db.Column(db.String(50))
    material = db.Column(db.String(100))
    surface_finish = db.Column(db.String(100))
    supplier = db.Column(db.String(100))
    unit_price = db.Column(db.String(50))
    material_code = db.Column(db.String(100))
    part_number = db.Column(db.String(100))
    part_name = db.Column(db.String(100))
    
    # Custom attributes
    attributes = db.relationship('FileAttribute', backref='file', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<File {self.filename}>'

class FileAttribute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=False)
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(200), nullable=False)

class FileVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=False)
    filepath = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    version_number = db.Column(db.Integer, nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)


