from flask import Blueprint, request, jsonify
from lib.google import (
    get_service,
    get_albums_with_cover_urls,
    authenticate
)
import logging
import requests
from config.config import Config

logging.basicConfig(filename="error.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

album_bp = Blueprint('album_bp', __name__)

@album_bp.route('/list_albums', methods=['POST'])
def get_albums():
    token = request.args.get('token')
    if not token:
        return jsonify({"error": "Token is required"}), 400
    creds = authenticate()
    if not creds:
        return jsonify({
        "error": "unauthorized",
        "message": "Google 憑證已過期或無效，請重新登入。"
    }), 401


    service = get_service(creds)
    if not service:
        return jsonify({"error": "Failed to create Google Photos service"}), 500

    try:
        albums = get_albums_with_cover_urls(service)
        if not albums:
            return jsonify({"message": "No albums found"}), 404
        album_titles = [album['title'] for album in albums if 'title' in album]
        cover_url = [album['cover_url'] for album in albums if 'cover_url' in album]
        if not album_titles:
            return jsonify({"message": "No album titles found"}), 404
        requests.post(f"{Config.SERVER_URL}/api/line/album", json={
            "album_titles": album_titles,
            "covers": cover_url,
            "token": token
        })
        return jsonify(album_titles), 200
    except Exception as e:
        logging.error(f"Error fetching albums: {e}")
        return jsonify({"error": str(e)}), 500