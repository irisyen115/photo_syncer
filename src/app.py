from flask import Flask
from controllers.upload_controller import upload_bp
from controllers.sync_controller import sync_bp
from controllers.delete_controller import delete_bp
from controllers.photo_controller import photo_bp
from controllers.blacklist_controller import black_bp
from controllers.batch_controller import batch_bp
from controllers.album_controller import album_bp
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
import os
from datetime import timedelta
from config.config import Config

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=[f"{Config.SERVER_URL}"])
load_dotenv()

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = os.getenv("SECRET_KEY", "your-default-secret-key")
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
app.permanent_session_lifetime = timedelta(days=1)

# blueprint 掛載路由
app.register_blueprint(sync_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(delete_bp)
app.register_blueprint(photo_bp)
app.register_blueprint(black_bp)
app.register_blueprint(batch_bp)
app.register_blueprint(album_bp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
