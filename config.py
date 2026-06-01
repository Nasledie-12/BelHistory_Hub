import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / 'instance'
INSTANCE_DIR.mkdir(exist_ok=True)
DEFAULT_SQLITE_PATH = INSTANCE_DIR / 'belhistory.db'
SECRET_KEY_PATH = INSTANCE_DIR / '.secret_key'


def _load_or_create_secret_key():
    env_secret = os.environ.get('SECRET_KEY')
    if env_secret:
        return env_secret

    if SECRET_KEY_PATH.exists():
        return SECRET_KEY_PATH.read_text(encoding='utf-8').strip()

    secret = secrets.token_urlsafe(32)
    SECRET_KEY_PATH.write_text(secret, encoding='utf-8')
    return secret

class Config:
    SECRET_KEY = _load_or_create_secret_key()
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
