import asyncio

from controller import Currency
from .celery import celery_app


@celery_app.task(bind=True, name='fetch_currencies')
def fetch_currencies(self):
    """
    Определяет валютный курс используя для этого реальный курс валют Ценрального Банка Российской Федерации.
    """
    asyncio.run(Currency.fetch_currencies(is_schedule_task=True))
