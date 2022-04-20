
from django.core.mail import send_mail
from config import settings

from logging import getLogger
logger = getLogger('django')

def send_email(subject, message, to_email, from_email=None, html_message=None):
    logger.info('Sending email to: ' + to_email)

    if not from_email:
        from_email = settings.DEFAULT_FROM_EMAIL

    send_mail(subject, message, from_email, (to_email,),
        html_message=html_message)