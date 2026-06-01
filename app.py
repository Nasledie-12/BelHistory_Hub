import random
from pathlib import Path
from urllib.parse import urljoin, urlparse

from flask import Flask, abort, flash, redirect, render_template, request, send_from_directory, url_for
from flask_admin import Admin
from flask_admin import AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import SecureForm
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_migrate import Migrate
from sqlalchemy import inspect, or_, text
from wtforms import PasswordField, SelectField
from wtforms.validators import Length, Optional

from config import Config
from content_seed_data import HISTORICAL_EVENT_DATA, NATIONAL_HOLIDAY_DATA, QUIZ_LIBRARY
from models import (
    db,
    User,
    HistoricalObject,
    Category,
    Region,
    Hero,
    HistoricalEvent,
    NationalHoliday,
    Quiz,
    UserProgress,
    Collection,
    ROLE_LABELS,
)

app = Flask(__name__)
app.config.from_object(Config)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

db.init_app(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'
login.login_message = 'Войдите в аккаунт, чтобы продолжить.'
login.login_message_category = 'error'

class StaffAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_staff()

    def inaccessible_callback(self, name, **kwargs):
        flash('Панель управления доступна только сотрудникам платформы.')
        return redirect(url_for('login', next=request.url))


class StaffModelView(ModelView):
    allowed_roles = ('admin',)

    def is_accessible(self):
        return current_user.is_authenticated and current_user.has_role(*self.allowed_roles)

    def inaccessible_callback(self, name, **kwargs):
        flash('У вас нет прав для доступа к этому разделу.')
        return redirect(url_for('login', next=request.url))


class UserAdminView(StaffModelView):
    allowed_roles = ('admin',)
    can_view_details = True
    column_list = ('username', 'email', 'role', 'profile_pic')
    column_searchable_list = ('username', 'email', 'role')
    column_filters = ('role',)
    column_sortable_list = ('username', 'email', 'role')
    column_labels = {
        'username': 'Логин',
        'email': 'Email',
        'role': 'Роль',
        'profile_pic': 'Фото профиля',
        'password_hash': 'Пароль',
    }
    form_base_class = SecureForm
    form_columns = ('username', 'email', 'role', 'profile_pic', 'password')
    form_extra_fields = {
        'role': SelectField(
            'Роль',
            choices=[(role, label) for role, label in ROLE_LABELS.items()],
        ),
        'password': PasswordField(
            'Новый пароль',
            validators=[Optional(), Length(min=6, message='Пароль должен содержать минимум 6 символов.')],
        ),
    }

    def on_model_change(self, form, model, is_created):
        username = (model.username or '').strip()
        email = (model.email or '').strip().lower()
        password = (form.password.data or '').strip()

        if len(username) < 3:
            raise ValueError('Логин должен содержать минимум 3 символа.')
        if '@' not in email or '.' not in email:
            raise ValueError('Укажите корректный email.')

        existing_username = User.query.filter(User.username == username, User.id != model.id).first()
        if existing_username:
            raise ValueError('Пользователь с таким логином уже существует.')

        existing_email = User.query.filter(User.email == email, User.id != model.id).first()
        if existing_email:
            raise ValueError('Пользователь с таким email уже существует.')

        model.username = username
        model.email = email

        if password:
            model.set_password(password)
        elif is_created and not model.password_hash:
            raise ValueError('Укажите пароль для нового аккаунта.')

    def on_form_prefill(self, form, id):
        form.password.data = ''

    def delete_model(self, model):
        if model.id == current_user.id:
            raise ValueError('Нельзя удалить аккаунт, под которым вы сейчас вошли.')
        return super().delete_model(model)


class ContentAdminView(StaffModelView):
    allowed_roles = ('admin', 'moderator')


admin = Admin(
    app,
    name='Панель управления',
    index_view=StaffAdminIndexView(name='Главная'),
)
admin.add_view(
    UserAdminView(
        User,
        db.session,
        name='Пользователи',
        category='Администрирование',
    )
)
admin.add_view(ContentAdminView(HistoricalObject, db.session, name='Исторические объекты', category='Контент'))
admin.add_view(ContentAdminView(Category, db.session, name='Категории', category='Контент'))
admin.add_view(ContentAdminView(Region, db.session, name='Регионы', category='Контент'))
admin.add_view(ContentAdminView(Hero, db.session, name='Герои', category='Контент'))
admin.add_view(ContentAdminView(HistoricalEvent, db.session, name='События', category='Контент'))
admin.add_view(ContentAdminView(NationalHoliday, db.session, name='Праздники', category='Контент'))
admin.add_view(ContentAdminView(Quiz, db.session, name='Тесты', category='Контент'))

PLACE_CATEGORY_NAMES = (
    'Замки и дворцы',
    'Музеи',
    'Исторические места',
)

PLACE_OBJECT_NAMES = (
    'Софийский собор',
    'Собор Трех Святителей в Могилеве',
    'Собор святых Петра и Павла',
    'Часовня-усыпальница Паскевичей',
    'Костёл Святого Франциска Ксаверия',
)

EVENTS_PHOTO_DIR = Path(app.static_folder) / 'img' / 'historical_events'
LEGACY_EVENTS_PHOTO_DIR = Path(__file__).resolve().parent / 'photo' / 'historical_events'
PLACE_GALLERY_DIR = Path(__file__).resolve().parent / 'photo'


def resolve_historical_event_image_path(event):
    if event is None:
        return None

    candidate_names = []
    if event.image_name:
        image_basename = Path(event.image_name).name
        candidate_names.extend([image_basename, event.image_name])

    if event.slug:
        candidate_names.extend([
            f'{event.slug}.jpg',
            f'{event.slug}.jpeg',
            f'{event.slug}.png',
            f'{event.slug}.webp',
        ])

    seen_names = set()
    for directory in (EVENTS_PHOTO_DIR, LEGACY_EVENTS_PHOTO_DIR):
        if not directory.exists():
            continue
        for name in candidate_names:
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            candidate_path = directory / name
            if candidate_path.is_file():
                return candidate_path

    return None


def build_static_asset_url(filename):
    asset_path = Path(app.static_folder) / filename
    version = int(asset_path.stat().st_mtime) if asset_path.exists() else 0
    return url_for('static', filename=filename, v=version)


def build_historical_event_image_url(event):
    image_path = resolve_historical_event_image_path(event)
    if image_path is None:
        return ''

    version = int(image_path.stat().st_mtime) if image_path.exists() else 0

    try:
        relative_path = image_path.resolve().relative_to(Path(app.static_folder).resolve()).as_posix()
        return build_static_asset_url(relative_path)
    except ValueError:
        return url_for('historical_event_image', slug=event.slug, v=version)


def get_place_gallery_items():
    if not PLACE_GALLERY_DIR.exists():
        return []

    items = []
    for file_path in sorted(PLACE_GALLERY_DIR.iterdir(), key=lambda item: item.name.lower()):
        if not file_path.is_file() or file_path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
            continue
        items.append(
            {
                'name': file_path.name,
                'title': file_path.stem,
                'updated_at': int(file_path.stat().st_mtime),
            }
        )
    return items


def build_place_gallery_image_url(image_name, updated_at=0):
    return url_for('place_gallery_image', image_name=image_name, v=updated_at)


@app.context_processor
def inject_asset_helpers():
    return {
        'asset_url': build_static_asset_url,
        'historical_event_image_url': build_historical_event_image_url,
        'place_gallery_image_url': build_place_gallery_image_url,
    }


@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

def sync_historical_events_content():
    existing_events = HistoricalEvent.query.order_by(HistoricalEvent.id.asc()).all()
    existing_by_slug = {
        event.slug: event
        for event in existing_events
    }
    desired_slugs = set()

    for event_data in HISTORICAL_EVENT_DATA:
        desired_slugs.add(event_data['slug'])
        event = existing_by_slug.get(event_data['slug'])

        if not event:
            event = HistoricalEvent(slug=event_data['slug'])
            db.session.add(event)

        event.slug = event_data['slug']
        event.year_label = event_data['year_label']
        event.title = event_data['title']
        event.kind = event_data['kind']
        event.summary = event_data['summary']
        event.details = event_data['details']
        event.image_name = Path(event_data['image_name']).name

    stale_events = [
        event
        for event in HistoricalEvent.query.order_by(HistoricalEvent.id.asc()).all()
        if event.slug not in desired_slugs
    ]
    for event in stale_events:
        db.session.delete(event)


def sync_national_holidays_content():
    existing_holidays = NationalHoliday.query.order_by(NationalHoliday.id.asc()).all()
    existing_by_slug = {
        holiday.slug: holiday
        for holiday in existing_holidays
    }
    desired_slugs = set()

    for holiday_data in NATIONAL_HOLIDAY_DATA:
        desired_slugs.add(holiday_data['slug'])
        holiday = existing_by_slug.get(holiday_data['slug'])

        if not holiday:
            holiday = NationalHoliday(slug=holiday_data['slug'])
            db.session.add(holiday)

        holiday.slug = holiday_data['slug']
        holiday.title = holiday_data['title']
        holiday.date_label = holiday_data['date_label']
        holiday.kind = holiday_data['kind']
        holiday.summary = holiday_data['summary']
        holiday.details = holiday_data['details']
        holiday.image_path = holiday_data['image_path']

    stale_holidays = [
        holiday
        for holiday in NationalHoliday.query.order_by(NationalHoliday.id.asc()).all()
        if holiday.slug not in desired_slugs
    ]
    for holiday in stale_holidays:
        db.session.delete(holiday)


def ensure_database_ready():
    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)

        if inspector.has_table('quizzes'):
            quiz_columns = {column['name'] for column in inspector.get_columns('quizzes')}
            if 'mode' not in quiz_columns:
                with db.engine.begin() as connection:
                    connection.execute(text("ALTER TABLE quizzes ADD COLUMN mode VARCHAR(16)"))
                    connection.execute(text("UPDATE quizzes SET mode = 'quiz' WHERE mode IS NULL OR mode = ''"))

        sync_historical_events_content()
        sync_national_holidays_content()
        sync_learning_content()


def build_quiz_options(quiz):
    options = [option for option in (quiz.answer, quiz.option1, quiz.option2, quiz.option3) if option]
    random.Random(f'{quiz.id}-{quiz.mode}').shuffle(options)
    return options


def get_mode_quizzes(mode, include_options=False):
    quizzes = Quiz.query.filter_by(mode=mode).order_by(Quiz.id.asc()).all()
    if include_options:
        for quiz in quizzes:
            quiz.display_options = build_quiz_options(quiz)
    return quizzes


def get_completed_quiz_ids(user_id, quiz_ids):
    if not user_id or not quiz_ids:
        return []

    quiz_id_set = set(quiz_ids)
    completed_ids = {
        progress.object_id
        for progress in UserProgress.query.filter_by(user_id=user_id).all()
        if progress.object_id in quiz_id_set
    }
    return sorted(completed_ids)


def build_mode_progress(mode, user=None, quizzes=None):
    quizzes = quizzes if quizzes is not None else get_mode_quizzes(mode)
    quiz_ids = [quiz.id for quiz in quizzes]
    completed_ids = []

    if user and user.is_authenticated:
        completed_ids = get_completed_quiz_ids(user.id, quiz_ids)

    completed_count = len(completed_ids)
    total_questions = len(quizzes)
    progress_percent = int((completed_count / total_questions) * 100) if total_questions else 0

    return {
        'mode': mode,
        'total_questions': total_questions,
        'completed_count': completed_count,
        'progress_percent': progress_percent,
        'completed_ids': completed_ids,
    }


def build_learning_stats(user):
    stats = {}
    total_questions = 0
    total_completed = 0

    for mode in QUIZ_LIBRARY:
        mode_quizzes = get_mode_quizzes(mode)
        mode_stats = build_mode_progress(mode, user=user, quizzes=mode_quizzes)
        stats[mode] = mode_stats
        total_questions += mode_stats['total_questions']
        total_completed += mode_stats['completed_count']

    stats['overall'] = {
        'total_questions': total_questions,
        'completed_count': total_completed,
        'progress_percent': int((total_completed / total_questions) * 100) if total_questions else 0,
    }
    return stats


def sync_learning_content():
    existing_quizzes = Quiz.query.order_by(Quiz.id.asc()).all()
    existing_by_key = {
        ((quiz.mode or 'quiz'), quiz.question): quiz
        for quiz in existing_quizzes
    }
    desired_keys = set()

    for mode, questions in QUIZ_LIBRARY.items():
        for question_data in questions:
            key = (mode, question_data['question'])
            desired_keys.add(key)
            quiz = existing_by_key.get(key)

            if not quiz:
                quiz = Quiz(question=question_data['question'], mode=mode)
                db.session.add(quiz)

            quiz.mode = mode
            quiz.question = question_data['question']
            quiz.answer = question_data['answer']
            quiz.option1 = question_data['option1']
            quiz.option2 = question_data['option2']
            quiz.option3 = question_data['option3']

    db.session.flush()

    stale_quizzes = [
        quiz
        for quiz in Quiz.query.order_by(Quiz.id.asc()).all()
        if ((quiz.mode or 'quiz'), quiz.question) not in desired_keys
    ]
    stale_quiz_ids = [quiz.id for quiz in stale_quizzes]

    for quiz in stale_quizzes:
        db.session.delete(quiz)

    if stale_quiz_ids:
        UserProgress.query.filter(UserProgress.object_id.in_(stale_quiz_ids)).delete(synchronize_session=False)

    db.session.commit()


ensure_database_ready()

@login.user_loader
def load_user(user_id):
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        return None
    return db.session.get(User, user_id_int)


def parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def is_safe_redirect_url(target):
    if not target:
        return False
    current_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in ('http', 'https') and current_url.netloc == redirect_url.netloc


def is_place_object(historical_object):
    return bool(
        historical_object.name in PLACE_OBJECT_NAMES
        or (historical_object.category and historical_object.category.name in PLACE_CATEGORY_NAMES)
    )


def build_place_filter():
    return or_(
        Category.name.in_(PLACE_CATEGORY_NAMES),
        HistoricalObject.name.in_(PLACE_OBJECT_NAMES),
    )


def get_treasure_categories():
    return Category.query.filter(~Category.name.in_(PLACE_CATEGORY_NAMES)).order_by(Category.name.asc()).all()


def build_historical_object_query(keyword='', category_id=None, region_id=None, year_from=None, year_to=None, period=None, content_scope='all'):
    query = HistoricalObject.query.join(Category)

    if content_scope == 'places':
        query = query.filter(build_place_filter())
    elif content_scope == 'treasures':
        query = query.filter(~build_place_filter())

    if keyword:
        query = query.filter(
            or_(
                HistoricalObject.name.ilike(f'%{keyword}%'),
                HistoricalObject.description.ilike(f'%{keyword}%'),
                HistoricalObject.period.ilike(f'%{keyword}%'),
                Category.name.ilike(f'%{keyword}%'),
            )
        )
    if category_id is not None:
        query = query.filter(HistoricalObject.category_id == category_id)
    if region_id is not None:
        query = query.filter(HistoricalObject.region_id == region_id)
    if period:
        query = query.filter(HistoricalObject.period == period)
    if year_from is not None:
        query = query.filter(HistoricalObject.year.is_not(None), HistoricalObject.year >= year_from)
    if year_to is not None:
        query = query.filter(HistoricalObject.year.is_not(None), HistoricalObject.year <= year_to)

    return query


def build_places_overview():
    places = []
    regions = Region.query.order_by(Region.name.asc()).all()

    for region in regions:
        objects_count = build_historical_object_query(
            region_id=region.id,
            content_scope='places',
        ).count()
        places.append({
            'region': region,
            'objects_count': objects_count,
        })

    return places


def build_region_places(region_id=None, keyword=''):
    return build_historical_object_query(
        keyword=keyword,
        region_id=region_id,
        content_scope='places',
    ).order_by(
        HistoricalObject.is_featured.desc(),
        HistoricalObject.year.asc(),
        HistoricalObject.name.asc(),
    ).all()


def get_distinct_values(field):
    return [
        value
        for value, in db.session.query(field).filter(field.is_not(None)).distinct().order_by(field.asc()).all()
        if value
    ]

@app.route('/')
def index():
    featured_objects = build_historical_object_query(content_scope='treasures').filter(
        HistoricalObject.is_featured.is_(True)
    ).order_by(HistoricalObject.name.asc()).limit(3).all()
    places_highlights = build_historical_object_query(content_scope='places').order_by(
        HistoricalObject.is_featured.desc(),
        HistoricalObject.name.asc(),
    ).limit(3).all()
    heroes = Hero.query.order_by(Hero.name.asc()).limit(5).all()
    events_preview = HistoricalEvent.query.order_by(HistoricalEvent.id.asc()).limit(4).all()
    holidays_preview = NationalHoliday.query.order_by(NationalHoliday.id.asc()).limit(3).all()
    quizzes = get_mode_quizzes('quiz', include_options=True)[:3]
    categories = get_treasure_categories()
    regions = Region.query.all()
    return render_template(
        'index.html',
        featured_objects=featured_objects,
        places_highlights=places_highlights,
        events_preview=events_preview,
        holidays_preview=holidays_preview,
        heroes=heroes,
        quizzes=quizzes,
        categories=categories,
        regions=regions,
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        credential = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        remember = request.form.get('remember') == 'on'
        user = User.query.filter(
            or_(User.username == credential, User.email == credential)
        ).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash(f'Вы вошли как {user.role_label.lower()}.')
            if is_safe_redirect_url(next_page):
                return redirect(next_page)
            return redirect(url_for('index'))
        flash('Неверное имя пользователя или пароль')
    return render_template('login.html', mode='login')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        password_repeat = request.form.get('password_repeat') or ''

        if len(username) < 3:
            flash('Имя пользователя должно содержать минимум 3 символа.')
        elif '@' not in email or '.' not in email:
            flash('Укажите корректный email.')
        elif len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов.')
        elif password != password_repeat:
            flash('Пароли не совпадают.')
        elif User.query.filter_by(username=username).first():
            flash('Пользователь с таким логином уже существует.')
        elif User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует.')
        else:
            user = User(username=username, email=email, role='user')
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Аккаунт создан. Теперь можно войти.')
            return redirect(url_for('login'))

    return render_template('login.html', mode='register')

@app.route('/logout')
def logout():
    logout_user()
    flash('Вы вышли из аккаунта.')
    return redirect(url_for('index'))

@app.route('/search')
def search():
    keyword = request.args.get('keyword', '')
    category_id = parse_int(request.args.get('category_id'))
    region_id = parse_int(request.args.get('region_id'))
    year_from = parse_int(request.args.get('year_from'))
    year_to = parse_int(request.args.get('year_to'))

    return redirect(url_for(
        'treasures',
        keyword=keyword,
        category_id=category_id,
        region_id=region_id,
        year_from=year_from,
        year_to=year_to,
    ))


@app.route('/treasures')
def treasures():
    keyword = request.args.get('keyword', '')
    category_id = parse_int(request.args.get('category_id'))
    region_id = parse_int(request.args.get('region_id'))
    year_from = parse_int(request.args.get('year_from'))
    year_to = parse_int(request.args.get('year_to'))
    period = (request.args.get('period') or '').strip()

    results = build_historical_object_query(
        keyword=keyword,
        category_id=category_id,
        region_id=region_id,
        year_from=year_from,
        year_to=year_to,
        period=period,
        content_scope='treasures',
    ).order_by(HistoricalObject.is_featured.desc(), HistoricalObject.name.asc()).all()
    categories = get_treasure_categories()
    regions = Region.query.all()
    periods = get_distinct_values(HistoricalObject.period)

    return render_template(
        'search_results.html',
        results=results,
        keyword=keyword,
        categories=categories,
        regions=regions,
        selected_category_id=category_id,
        selected_region_id=region_id,
        year_from=year_from,
        year_to=year_to,
        periods=periods,
        selected_period=period,
    )


@app.route('/heroes')
def heroes_page():
    keyword = (request.args.get('keyword') or '').strip()
    heroes_query = Hero.query

    if keyword:
        heroes_query = heroes_query.filter(
            or_(
                Hero.name.ilike(f'%{keyword}%'),
                Hero.short_info.ilike(f'%{keyword}%'),
                Hero.description.ilike(f'%{keyword}%'),
            )
        )

    heroes = heroes_query.order_by(Hero.name.asc()).all()
    return render_template('heroes_page.html', heroes=heroes, keyword=keyword)


@app.route('/places')
def places_page():
    keyword = (request.args.get('keyword') or '').strip()
    places = build_places_overview()
    selected_region_id = parse_int(request.args.get('region_id'))
    selected_region = None
    region_objects = []

    if selected_region_id is not None:
        selected_region = Region.query.get_or_404(selected_region_id)
        region_objects = build_region_places(selected_region.id, keyword=keyword)
    elif keyword:
        region_objects = build_region_places(keyword=keyword)

    total_objects = sum(place['objects_count'] for place in places)
    populated_regions = sum(1 for place in places if place['objects_count'] > 0)

    return render_template(
        'places.html',
        places=places,
        selected_region=selected_region,
        region_objects=region_objects,
        total_objects=total_objects,
        populated_regions=populated_regions,
        total_regions=len(places),
        keyword=keyword,
        place_gallery_items=get_place_gallery_items(),
    )


@app.route('/historical-events')
def historical_events_page():
    keyword = (request.args.get('keyword') or '').strip()
    selected_kind = (request.args.get('kind') or '').strip()
    events_query = HistoricalEvent.query

    if keyword:
        events_query = events_query.filter(
            or_(
                HistoricalEvent.title.ilike(f'%{keyword}%'),
                HistoricalEvent.kind.ilike(f'%{keyword}%'),
                HistoricalEvent.summary.ilike(f'%{keyword}%'),
                HistoricalEvent.details.ilike(f'%{keyword}%'),
                HistoricalEvent.year_label.ilike(f'%{keyword}%'),
            )
        )
    if selected_kind:
        events_query = events_query.filter(HistoricalEvent.kind == selected_kind)

    events = events_query.order_by(HistoricalEvent.id.asc()).all()
    return render_template(
        'historical_events_page.html',
        events=events,
        events_count=len(events),
        total_events=HistoricalEvent.query.count(),
        event_kinds=get_distinct_values(HistoricalEvent.kind),
        selected_kind=selected_kind,
        keyword=keyword,
        featured_event_images=HistoricalEvent.query.order_by(HistoricalEvent.id.asc()).limit(4).all(),
    )


@app.route('/historical-events/media/<slug>')
def historical_event_image(slug):
    event = HistoricalEvent.query.filter_by(slug=slug).first()
    if event is None:
        abort(404)
    image_path = resolve_historical_event_image_path(event)
    if image_path is None:
        abort(404)
    return send_from_directory(image_path.parent, image_path.name)


@app.route('/places/gallery-media/<path:image_name>')
def place_gallery_image(image_name):
    image_path = (PLACE_GALLERY_DIR / Path(image_name).name).resolve()
    try:
        image_path.relative_to(PLACE_GALLERY_DIR.resolve())
    except ValueError:
        abort(404)

    if not image_path.is_file():
        abort(404)

    return send_from_directory(image_path.parent, image_path.name)


@app.route('/national-holidays')
def national_holidays_page():
    keyword = (request.args.get('keyword') or '').strip()
    selected_kind = (request.args.get('kind') or '').strip()
    holidays_query = NationalHoliday.query

    if keyword:
        holidays_query = holidays_query.filter(
            or_(
                NationalHoliday.title.ilike(f'%{keyword}%'),
                NationalHoliday.kind.ilike(f'%{keyword}%'),
                NationalHoliday.summary.ilike(f'%{keyword}%'),
                NationalHoliday.details.ilike(f'%{keyword}%'),
                NationalHoliday.date_label.ilike(f'%{keyword}%'),
            )
        )
    if selected_kind:
        holidays_query = holidays_query.filter(NationalHoliday.kind == selected_kind)

    holidays = holidays_query.order_by(NationalHoliday.id.asc()).all()
    return render_template(
        'national_holidays_page.html',
        holidays=holidays,
        holidays_count=len(holidays),
        total_holidays=NationalHoliday.query.count(),
        holiday_kinds=get_distinct_values(NationalHoliday.kind),
        selected_kind=selected_kind,
        keyword=keyword,
    )

@app.route('/help')
def help_page():
    return render_template('help_page.html')


@app.route('/quizzes')
def quizzes_page():
    keyword = (request.args.get('keyword') or '').strip()
    mode = request.args.get('mode', 'quiz')
    if mode not in QUIZ_LIBRARY:
        mode = 'quiz'
    quizzes = Quiz.query.filter_by(mode=mode)
    if keyword:
        quizzes = quizzes.filter(Quiz.question.ilike(f'%{keyword}%'))
    quizzes = quizzes.order_by(Quiz.id.asc()).all()
    for quiz in quizzes:
        quiz.display_options = build_quiz_options(quiz)
    mode_progress = build_mode_progress(mode, user=current_user, quizzes=quizzes)
    learning_stats = build_learning_stats(current_user)

    return render_template(
        'quizzes_page.html',
        quizzes=quizzes,
        completed_quizzes=mode_progress['completed_count'],
        progress_percent=mode_progress['progress_percent'],
        completed_quiz_ids=mode_progress['completed_ids'],
        quiz_mode=mode,
        learning_stats=learning_stats,
        keyword=keyword,
    )

@app.route('/object/<int:id>')
def object_detail(id):
    obj = HistoricalObject.query.get_or_404(id)
    is_place = is_place_object(obj)
    related_objects = HistoricalObject.query.filter(
        HistoricalObject.id != obj.id,
        HistoricalObject.region_id == obj.region_id,
    ).order_by(
        HistoricalObject.category_id != obj.category_id,
        HistoricalObject.is_featured.desc(),
        HistoricalObject.name.asc(),
    ).limit(3).all()
    return render_template(
        'object_detail.html',
        object=obj,
        object_kind_label='Место Беларуси' if is_place else 'Сокровище Беларуси',
        collection_label='Маршрут и посещение' if is_place else 'Историческая справка',
        parent_label='Места Беларуси' if is_place else 'Сокровища и артефакты',
        parent_url=url_for('places_page', region_id=obj.region_id) if is_place else url_for('treasures'),
        related_objects=related_objects,
    )

@app.route('/quiz', methods=['POST'])
def submit_quiz():
    quiz_id = parse_int(request.form.get('quiz_id'))
    answer = (request.form.get('answer') or '').strip()
    if quiz_id is None:
        return {"status": "error", "message": "Некорректный вопрос викторины."}, 400

    quiz = Quiz.query.get_or_404(quiz_id)
    is_correct = quiz.answer == answer

    if not current_user.is_authenticated:
        if is_correct:
            return {
                "status": "success",
                "message": "Правильно! Войдите в аккаунт, чтобы сохранить прогресс.",
                "quiz_id": quiz.id,
                "mode": quiz.mode,
                "completed": False,
            }
        return {
            "status": "error",
            "message": "Неправильно. Попробуйте еще раз.",
            "quiz_id": quiz.id,
            "mode": quiz.mode,
            "completed": False,
        }

    if is_correct:
        progress = UserProgress.query.filter_by(user_id=current_user.id, object_id=quiz.id).first()
        if not progress:
            new_progress = UserProgress(user_id=current_user.id, object_id=quiz.id)
            db.session.add(new_progress)
            db.session.commit()
        mode_progress = build_mode_progress(quiz.mode, user=current_user)
        return {
            "status": "success",
            "message": "Правильно!",
            "quiz_id": quiz.id,
            "mode": quiz.mode,
            "completed": True,
            "completed_quizzes": mode_progress['completed_count'],
            "progress_percent": mode_progress['progress_percent'],
        }

    mode_progress = build_mode_progress(quiz.mode, user=current_user)
    return {
        "status": "error",
        "message": "Неправильно. Попробуйте еще раз.",
        "quiz_id": quiz.id,
        "mode": quiz.mode,
        "completed": False,
        "completed_quizzes": mode_progress['completed_count'],
        "progress_percent": mode_progress['progress_percent'],
    }

@app.route('/profile')
@login_required
def profile():
    learning_stats = build_learning_stats(current_user)
    collection = Collection.query.filter_by(user_id=current_user.id).order_by(Collection.added_at.desc()).all()

    return render_template(
        'profile.html',
        progress_percent=learning_stats['overall']['progress_percent'],
        learning_stats=learning_stats,
        collection=collection,
        users_count=User.query.count() if current_user.is_admin() else None,
    )


@app.route('/profile/edit', methods=['POST'])
@login_required
def edit_profile():
    username = (request.form.get('username') or '').strip()
    email = (request.form.get('email') or '').strip().lower()
    current_password = request.form.get('current_password') or ''
    new_password = request.form.get('new_password') or ''
    password_repeat = request.form.get('password_repeat') or ''

    if len(username) < 3:
        flash('Имя пользователя должно содержать минимум 3 символа.')
        return redirect(url_for('profile'))

    if '@' not in email or '.' not in email:
        flash('Укажите корректный email.')
        return redirect(url_for('profile'))

    existing_username = User.query.filter(User.username == username, User.id != current_user.id).first()
    if existing_username:
        flash('Пользователь с таким логином уже существует.')
        return redirect(url_for('profile'))

    existing_email = User.query.filter(User.email == email, User.id != current_user.id).first()
    if existing_email:
        flash('Пользователь с таким email уже существует.')
        return redirect(url_for('profile'))

    if new_password or password_repeat or current_password:
        if not current_user.check_password(current_password):
            flash('Укажите текущий пароль, чтобы изменить его.')
            return redirect(url_for('profile'))
        if len(new_password) < 6:
            flash('Новый пароль должен содержать минимум 6 символов.')
            return redirect(url_for('profile'))
        if new_password != password_repeat:
            flash('Новые пароли не совпадают.')
            return redirect(url_for('profile'))
        current_user.set_password(new_password)

    current_user.username = username
    current_user.email = email
    db.session.commit()
    flash('Профиль обновлён.')
    return redirect(url_for('profile'))

@app.route('/add_to_collection/<int:id>', methods=['POST'])
def add_to_collection(id):
    if not current_user.is_authenticated:
        return {"status": "error", "message": "Войдите в аккаунт, чтобы сохранять материалы."}, 401

    historical_object = HistoricalObject.query.get_or_404(id)
    existing = Collection.query.filter_by(user_id=current_user.id, object_id=id).first()
    if not existing:
        new_item = Collection(user_id=current_user.id, object_id=historical_object.id)
        db.session.add(new_item)
        db.session.commit()
        return {"status": "success", "message": "Добавлено в коллекцию"}
    return {"status": "info", "message": "Уже в коллекции"}


@app.route('/remove_from_collection/<int:id>', methods=['POST'])
@login_required
def remove_from_collection(id):
    collection_item = Collection.query.filter_by(user_id=current_user.id, object_id=id).first_or_404()
    db.session.delete(collection_item)
    db.session.commit()
    flash('Материал удален из коллекции.')
    return redirect(url_for('profile'))

if __name__ == '__main__':
    app.run(debug=app.config.get('DEBUG', False))
