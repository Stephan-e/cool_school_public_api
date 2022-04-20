# from datetime import timedelta
# import os
# from logging import getLogger

# from celery.schedules import crontab

# logger = getLogger('django')

# if os.environ.get('SKIP_TASK_QUEUE') in ['True', 'true', True]:
#     logger.info('Task Queues Disabled')
#     CELERY_TASK_ALWAYS_EAGER = True
# else:
#     logger.info('Task Queues Enabled')

# CELERY_IMPORTS = ("wallet.models",)

# CELERY_ENABLE_UTC = True
# CELERY_TIMEZONE = "UTC"

# CELERY_TASK_CREATE_MISSING_QUEUES = True
# CELERY_WORKER_PREFETCH_MULTIPLIER = 150
# CELERY_BROKER_CONNECTION_TIMEOUT=10.0

# CELERY_TASK_SERIALIZER = 'msgpack'
# CELERY_ACCEPT_CONTENT = ['msgpack', 'json']

# project_id = os.environ.get('CELERY_ID', 'local')

# default_queue = '-'.join(('general', project_id))
# CELERY_TASK_DEFAULT_QUEUE = default_queue

# transaction_queue = '-'.join(('transaction', project_id))
# webhook_queue = '-'.join(('webhook', project_id))
# result_set_queue = '-'.join(('result-set', project_id))

# CELERY_TASK_ROUTES = {
#     'wallet.tasks.process_transfer_claims': {'queue': transaction_queue},
#     'wallet.tasks.process_webhook': {'queue': webhook_queue},
#     'wallet.tasks.process_result_set_page': {'queue': result_set_queue},
# }

# # RabbitMQ
# if os.environ.get('RABBITMQ_HOST'):
#     RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST')
# else:
#     RABBITMQ_HOST = 'rabbitmq'

# # RabbitMQ
# if os.environ.get('RABBITMQ_PORT'):
#     RABBITMQ_PORT = os.environ.get('RABBITMQ_PORT')
# else:
#     RABBITMQ_PORT = '5672'

# CELERY_BROKER_URL = 'amqp://{user}:{password}@{hostname}/{vhost}'.format(
#     user=os.environ.get('RABBITMQ_USER', 'guest'),
#     password=os.environ.get('RABBITMQ_PASSWORD', 'guest'),
#     hostname="%s:%s" % (RABBITMQ_HOST, RABBITMQ_PORT),
#     vhost=os.environ.get('RABBITMQ_ENV_RABBITMQ_DEFAULT_VHOST', '/'))

# CELERY_IGNORE_RESULT = True

# CELERY_BEAT_SCHEDULE = {
#     'daily_report': {
#         'task': 'wallet.tasks.daily_report',
#         'schedule': crontab(minute=55, hour='23'),
#         'args': ()
#     },
#     'daily_key_metric_report': {
#         'task': 'wallet.tasks.key_metric_report',
#         'schedule': crontab(minute=55, hour='23'),
#         'args': ()
#     },
#     'clear_requests': {
#         'task': 'wallet.tasks.clear_requests',
#         'schedule': timedelta(minutes=10),
#         'args': ()
#     },
#     'clear_webhook_tasks': {
#         'task': 'wallet.tasks.clear_webhook_tasks',
#         'schedule': timedelta(minutes=10),
#         'args': ()
#     },
# }

from celery.task.schedules import crontab
import datetime

CELERY_BROKER_URL = 'amqp://127.0.0.1'
CELERY_IMPORTS = ('school.tasks', )

CELERY_RESULT_BACKEND = 'amqp://127.0.0.1'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = 'Asia/Taipei'

CELERY_BEAT_SCHEDULE = {
    'send_notification': {
        'task': 'school.tasks.send_notifiction',
        # 'schedule': 20.0,
        'schedule': crontab(minute=30, hour='10'),
        'args': ()
    },
    'weekly_report': {
        'task': 'school.tasks.send_weekly_report',
        #'schedule': 21.0,
        'schedule': crontab(minute=1, hour='2', day_of_week=1),
        'args': ()
    },
    'monthly_report': {
        'task': 'school.tasks.send_monthly_report',
        #'schedule': 21.0,
        'schedule': crontab(minute=1, hour='2', day_of_month=1),
        'args': ()
    }
}

