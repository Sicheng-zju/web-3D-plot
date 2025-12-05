# 3D Model Manager & Viewer

A comprehensive web-based solution for managing, sharing, and viewing 3D engineering files. Designed for offline LAN deployment with a desktop-first full-screen experience.

## Features

### 📂 File Management
- **Hierarchical Storage**: Create folders and subfolders to organize your projects.
- **File Operations**: Upload, move, delete, and rename files easily.
- **Version Control**: Update models while keeping a history of previous versions.
- **Format Support**: Optimized for engineering formats (STL, STEP, IGES, OBJ, etc.).

### 🧊 3D Viewer
- **Interactive Viewing**: Rotate, pan, and zoom 3D models directly in the browser.
- **Visual Tools**:
  - Standard Views (Isometric, Front, Top, etc.)
  - Wireframe Mode
  - Opacity & Color Adjustment
  - Screenshot Capture
- **Properties Panel**: View and edit metadata (Part Number, Material, Mass, Supplier) and custom attributes.

### 🤝 Collaboration
- **Sharing System**:
  - **Private Share**: Share files or folders with specific users.
  - **Public Share**: Make files accessible to all users in the "Public Gallery".
- **Dashboard**: Distinct sections for "My Files" and "Shared with Me".

### 🛠 Technical Highlights
- **Offline Ready**: All dependencies (Bootstrap, Three.js) are bundled locally. No internet connection required.
- **Desktop-First UI**: Full-screen responsive layout designed for desktop productivity.
- **Bilingual**: Complete support for English and Chinese (Switchable in UI).

## Installation

1. **Clone or Download** the repository.
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the Application**:
   ```bash
   python app.py
   ```
4. **Access**: Open your browser and navigate to `http://127.0.0.1:5000`.

## Project Structure

- `app.py`: Main Flask application entry point.
- `models.py`: Database models (User, File, Folder, etc.).
- `translations.py`: Localization dictionary (EN/CN).
- `templates/`: HTML templates (Jinja2).
- `static/`:
  - `css/`: Custom styles and responsive layout rules.
  - `js/`: Viewer logic and dashboard scripts.
  - `vendor/`: Local copies of third-party libraries (Bootstrap, Three.js).
- `uploads/`: Default storage location for uploaded files.
- `instance/`: Contains the SQLite database (`db.sqlite3`) after first run.

## License

MIT License
