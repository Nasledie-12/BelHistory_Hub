import os


bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"
workers = 1
timeout = 120
accesslog = '-'
errorlog = '-'
capture_output = True


def post_worker_init(worker):
    from app import app, ensure_database_ready, logger

    with app.app_context():
        try:
            ensure_database_ready()
            logger.info('Database ready in worker %s', worker.pid)
        except Exception:
            logger.exception('Database init failed in worker %s', worker.pid)
