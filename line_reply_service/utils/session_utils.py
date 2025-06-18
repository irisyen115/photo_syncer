from cachetools import TTLCache
import secrets

user_sessions = TTLCache(maxsize=1000, ttl=1800)

def generate_token(length=32):
    return secrets.token_hex(length // 2)

def get_user_id_from_token(token):
    return user_sessions.get(token)
