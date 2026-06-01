from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

ROLE_LABELS = {
    'admin': 'Администратор',
    'moderator': 'Модератор',
    'user': 'Пользователь',
}

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(10), default='user')
    profile_pic = db.Column(db.String(256), default='default_profile.png')
    
    progress = db.relationship('UserProgress', backref='user', lazy='dynamic')
    collection = db.relationship('Collection', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def has_role(self, *roles):
        return self.role in roles

    def is_admin(self):
        return self.has_role('admin')

    def is_moderator(self):
        return self.has_role('moderator')

    def is_staff(self):
        return self.has_role('admin', 'moderator')

    @property
    def role_label(self):
        return ROLE_LABELS.get(self.role, self.role.title())

    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    objects = db.relationship('HistoricalObject', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'

class Region(db.Model):
    __tablename__ = 'regions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    objects = db.relationship('HistoricalObject', backref='region', lazy='dynamic')

    def __repr__(self):
        return f'<Region {self.name}>'

class HistoricalObject(db.Model):
    __tablename__ = 'historical_objects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True, nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    region_id = db.Column(db.Integer, db.ForeignKey('regions.id'))
    period = db.Column(db.String(64))
    year = db.Column(db.Integer)
    image_url = db.Column(db.String(256))
    is_featured = db.Column(db.Boolean, default=False)
    collection_items = db.relationship('Collection', back_populates='historical_object', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<HistoricalObject {self.name}>'

class Hero(db.Model):
    __tablename__ = 'heroes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True, nullable=False)
    description = db.Column(db.Text)
    short_info = db.Column(db.String(256))
    image_url = db.Column(db.String(256))

    def __repr__(self):
        return f'<Hero {self.name}>'

class HistoricalEvent(db.Model):
    __tablename__ = 'historical_events'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(128), unique=True, nullable=False, index=True)
    year_label = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(256), nullable=False, index=True)
    kind = db.Column(db.String(128), nullable=False, index=True)
    summary = db.Column(db.Text, nullable=False)
    details = db.Column(db.Text, nullable=False)
    image_name = db.Column(db.String(512), nullable=False)

    def __repr__(self):
        return f'<HistoricalEvent {self.slug}>'

class NationalHoliday(db.Model):
    __tablename__ = 'national_holidays'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(128), unique=True, nullable=False, index=True)
    title = db.Column(db.String(256), nullable=False, index=True)
    date_label = db.Column(db.String(128), nullable=False)
    kind = db.Column(db.String(128), nullable=False, index=True)
    summary = db.Column(db.Text, nullable=False)
    details = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(256), nullable=False)

    def __repr__(self):
        return f'<NationalHoliday {self.slug}>'

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key=True)
    mode = db.Column(db.String(16), index=True, nullable=False, default='quiz')
    question = db.Column(db.String(256), nullable=False)
    answer = db.Column(db.String(128), nullable=False)
    option1 = db.Column(db.String(128))
    option2 = db.Column(db.String(128))
    option3 = db.Column(db.String(128))

    def __repr__(self):
        return f'<Quiz {self.id}>'

class UserProgress(db.Model):
    __tablename__ = 'user_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    object_id = db.Column(db.Integer, db.ForeignKey('historical_objects.id'))
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

class Collection(db.Model):
    __tablename__ = 'collections'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    object_id = db.Column(db.Integer, db.ForeignKey('historical_objects.id'))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    historical_object = db.relationship('HistoricalObject', back_populates='collection_items')

    @property
    def object(self):
        return self.historical_object
