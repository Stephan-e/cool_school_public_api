from school.models import  *
from django.db.models import Count, Sum


def get_student_hours(instance):
    try:
        camp_hours = CampBooking.objects.filter(student=instance, attendance_status="attended").aggregate(Sum('session__duration'))
    
        if camp_hours['session__duration__sum'] == None:
            camp_hours = 0
        else:
            camp_hours = camp_hours['session__duration__sum']

    except CampBooking.DoesNotExist:
        camp_hours = 0

    try:
        hours = Booking.objects.filter(student=instance, attendance_status="attended").aggregate(Sum('session__duration'))
    
        if hours['session__duration__sum'] == None:
            hours = 0
        else:
            hours = hours['session__duration__sum']

    except Booking.DoesNotExist:
        hours = 0

    return hours + camp_hours


def get_client_hours(instance):

    try:
        hours_purchased = Payment.objects.filter(client=instance).aggregate(Sum('hours_purchased'))
    except Payment.DoesNotExist:
        hours_purchased = 0

    try:
        camp_attended = CampBooking.objects.filter(client=instance, attendance_status="attended").aggregate(Sum('session__duration'))
        camp_absent = CampBooking.objects.filter(client=instance, attendance_status="absent").aggregate(Sum('session__duration'))

        if camp_attended['session__duration__sum'] == None:
            camp_attended = 0
        else:
            camp_attended = camp_attended['session__duration__sum']

        if camp_absent['session__duration__sum'] == None:
            camp_absent = 0
        else:
            camp_absent = camp_absent['session__duration__sum']

    except CampBooking.DoesNotExist:
        camp_attended = 0
        camp_absent = 0


    try:
        attended = Booking.objects.filter(client=instance, attendance_status="attended").aggregate(Sum('session__duration'))
        absent = Booking.objects.filter(client=instance, attendance_status="absent").aggregate(Sum('session__duration'))

        if hours_purchased['hours_purchased__sum'] == None:
            hours_purchased = 0
        else:
            hours_purchased = hours_purchased['hours_purchased__sum']

        if attended['session__duration__sum'] == None:
            attended = 0
        else:
            attended = attended['session__duration__sum']

        if absent['session__duration__sum'] == None:
            absent = 0
        else:
            absent = absent['session__duration__sum']
        
    except Booking.DoesNotExist:
        attended = 0
        absent = 0

    return hours_purchased - attended - absent - camp_attended - camp_absent

def get_client_hours_penalty(instance):

    try:
        camp_absent = CampBooking.objects.filter(client=instance, attendance_status="absent").aggregate(Sum('session__duration'))

        if camp_absent['session__duration__sum'] == None:
            camp_absent = 0
        else:
            camp_absent = camp_absent['session__duration__sum']/2
            
    except CampBooking.DoesNotExist:
        camp_absent = 0

    try:
        absent = Booking.objects.filter(client=instance, attendance_status="absent").aggregate(Sum('session__duration'))

        if absent['session__duration__sum'] == None:
            absent = 0
        else:
            absent = absent['session__duration__sum']/2
        
    except Booking.DoesNotExist:
        attended = 0
        absent = 0

    return  absent + camp_absent