from flask import Flask
from dotenv import load_dotenv
import os
from models.database import init_db
from controllers.webhook_controller import webhook_bp
from controllers.notify_controller import notify_bp
from controllers.album_controller import album_bp
from controllers.face_controller import face_bp
from utils.get_menu_items import create_rich_menu

load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
init_db(app)

app.register_blueprint(webhook_bp)
app.register_blueprint(notify_bp)
app.register_blueprint(album_bp)
app.register_blueprint(face_bp)


if __name__ == "__main__":
    create_rich_menu()
    app.run(host='0.0.0.0', port=5001)

