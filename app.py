import os
from flask import Flask
from models import db, User
from flask_login import LoginManager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max limit

db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import routes after app is created to avoid circular imports
# from routes import * # This causes circular import issues and type checking confusion

if __name__ == '__main__':
    # Import routes here to register them
    from routes import *
    
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    with app.app_context():
        db.create_all()
    
    app.run(debug=True)
