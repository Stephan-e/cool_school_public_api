
from celery.task.schedules import crontab
from celery import  shared_task
from celery.utils.log import get_task_logger
import requests
import json
import os
import datetime
from config import settings


logger = get_task_logger(__name__)


@shared_task 
def send_notifiction():
    from school.models import Booking
    from school.enums import AttendanceStatus
    from school.utils.common import send_email
    
    bookings = Booking.objects.filter(attendance_status=AttendanceStatus.NONE, date = datetime.date.today())
    recipients = ['stephan@usersprojects.com','tony@usersprojects.com', 'ethan@usersprojects.com']
    message = []
    for booking in bookings: 
        if str(booking.session.teacher.email) not in recipients:
            recipients.append(str(booking.session.teacher.email))
        message.append( str(booking.session.teacher.first_name) + " " + str(booking.session.teacher.last_name) + ": " + str(booking.student.student_id) + " " + str(booking.student.first_name) + " " + str(booking.student.last_name) + " " + str(booking.session.description) + " " + str(booking.date))

    from django.core.mail import send_mail

    messageToStr='\n'.join(map(str, message))

    message = send_mail(
        "school Daily Attendance Reminder - " + str(datetime.date.today()),
        "The system has detected that the following student's attendance have not been marked: \n" + messageToStr ,
        "info@usersprojects.com",
        recipients,
    )

    return True

