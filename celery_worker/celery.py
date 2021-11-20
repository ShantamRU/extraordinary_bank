from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
  'celery_worker',
  broker='amqp://admin:admin@rabbit:5672',
  include=['celery_worker.tasks'])

celery_app.conf.beat_schedule = {
  'fetch_currencies': {
    'task': 'fetch_currencies',
    'schedule': crontab(minute='0', hour='1'),
  }
}
