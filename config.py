import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / 'instance'
INSTANCE_DIR.mkdir(exist_ok=True)


def _default_sqlite_path():
    if os.environ.get('DATABASE_URL'):
        return None
    if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RAILWAY_PUBLIC_DOMAIN'):
        return Path('/tmp/belhistory.db')
    return INSTANCE_DIR / 'belhistory.db'


DEFAULT_SQLITE_PATH = _default_sqlite_path() or INSTANCE_DIR / 'belhistory.db'
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

def _normalize_database_url(url):
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)

    if url.startswith('postgresql://') and 'sslmode=' not in url:
        if 'railway.internal' not in url and 'localhost' not in url and '127.0.0.1' not in url:
            separator = '&' if '?' in url else '?'
            url = f'{url}{separator}sslmode=require'

    return url


def _build_database_uri():
    if os.environ.get('FORCE_SQLITE') == '1':
        database_url = None
    else:
        database_url = os.environ.get('DATABASE_URL')

    if database_url:
        return _normalize_database_url(database_url)

    sqlite_path = _default_sqlite_path() or INSTANCE_DIR / 'belhistory.db'
    return f'sqlite:///{sqlite_path.as_posix()}'


def _engine_options():
    uri = _build_database_uri()
    options = {'pool_pre_ping': True}

    if uri.startswith('postgresql'):
        options['connect_args'] = {'connect_timeout': 5}

    return options


class Config:
    SECRET_KEY = _load_or_create_secret_key()
    SQLALCHEMY_DATABASE_URI = _build_database_uri()
    SQLALCHEMY_ENGINE_OPTIONS = _engine_options()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
