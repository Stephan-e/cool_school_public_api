import uuid
import datetime
import uuid
import re
import requests
import json
import os

from enumfields import EnumField
from school.enums import *
from logging import getLogger


from django.db import models
from django.utils.timezone import utc
from django.template import Template
from django.template import Context
from django.contrib.auth.base_user import BaseUserManager
from rest_framework import exceptions
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.postgres.fields import JSONField, ArrayField
from django.utils.translation import ugettext_lazy as _
from django.utils.timezone import (
    utc, now
)
from django.db import models
from django.db.models import Count
from taggit.managers import TaggableManager


logger = getLogger('django')

class DateModel(models.Model):
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def __str__(self):
        return str(self.created)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class AbstractUser(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True)
    email = models.EmailField(_('email address'), null=True, unique=True)
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=now)
    objects = UserManager()
    all_objects = BaseUserManager()
    role = EnumField(
                Role, 
                max_length=50,
                default=Role.STUDENT)
    client = models.ForeignKey('school.Client', on_delete = models.CASCADE, related_name="user", blank=True, null=True)
    teacher = models.ForeignKey('school.Teacher', on_delete = models.CASCADE, related_name="user", blank=True, null=True)
    staff = models.ForeignKey('school.Staff', on_delete = models.CASCADE, related_name="user", blank=True, null=True)
    


    USERNAME_FIELD = 'email'

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('school')
        abstract = True

    def __str__(self):
        return self.email

    def get_full_name(self):
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        "Returns the short name for the user."
        return self.first_name


class User(AbstractUser, DateModel):
    class Meta(AbstractUser.Meta):
        swappable = 'AUTH_USER_MODEL'


class Student(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    first_name = models.CharField(max_length=50, db_index=True, blank=True)
    last_name = models.CharField(max_length=50, db_index=True, blank=True)
    birth_date = models.DateField(blank=True, null=True)
    medical_condition = models.CharField(max_length=100, db_index=True, blank=True, null=True)
    client = models.ForeignKey('school.Client', on_delete = models.CASCADE, related_name="student")
    language = models.CharField(max_length=200, db_index=True, blank=True)
    student_id = models.CharField(max_length=50, db_index=True, blank=True)
    status = EnumField(
                StudentStatus, 
                max_length=50,
                default=StudentStatus.ACTIVE)
    location = models.CharField(max_length=50, db_index=True, blank=True)
    tags = TaggableManager()
    @property
    def age(self):
        today=datetime.datetime.today()
        return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))


class Client(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    first_name = models.CharField(max_length=50, db_index=True, blank=True)
    last_name = models.CharField(max_length=50, db_index=True, blank=True)
    location = models.CharField(max_length=50, db_index=True, blank=True)
    language = models.CharField(max_length=50, db_index=True, blank=True)
    email = models.EmailField(_('email address'), null=True)
    phone = models.CharField(max_length=50, db_index=True, blank=True)
    payment_status = EnumField(
                PaymentStatus, 
                max_length=50,
                default=PaymentStatus.PENDING)
    status = EnumField(
                ClientStatus, 
                max_length=50,
                default=ClientStatus.ACTIVE)
    description = models.CharField(max_length=200, blank=True)
    tags = TaggableManager()
    @property
    def service_rate(self):
        try:
            payment = Payment.objects.filter(client=self, amount__gte=0, hours_purchased__gte=0).latest('date_purchased')
        except Payment.DoesNotExist:
            return 720
        if payment.hours_purchased > 0 and payment.amount >0:
            return payment.amount/payment.hours_purchased
        else:
            return 720


class Teacher(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    first_name = models.CharField(max_length=50, db_index=True, blank=True)
    last_name = models.CharField(max_length=50, db_index=True, blank=True)
    birth_date = models.DateField(blank=True, null=True)
    language = models.CharField(max_length=200, db_index=True, blank=True)
    email = models.EmailField(_('email address'), null=True)
    phone = models.CharField(max_length=50, db_index=True, blank=True)   
    location = models.CharField(max_length=50, db_index=True, blank=True)


class Staff(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    first_name = models.CharField(max_length=50, db_index=True, blank=True)
    last_name = models.CharField(max_length=50, db_index=True, blank=True)
    birth_date = models.DateField(blank=True, null=True)
    language = models.CharField(max_length=200, db_index=True, blank=True)
    email = models.EmailField(_('email address'), null=True)
    phone = models.CharField(max_length=50, db_index=True, blank=True)   
    location = models.CharField(max_length=50, db_index=True, blank=True)
    role = models.CharField(max_length=50, db_index=True, blank=True)   
 

class Payment(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    hours_purchased = models.DecimalField(max_digits=5, decimal_places=2)
    date_purchased = models.DateField(blank=True, null=True)
    method = models.CharField(max_length=50, db_index=True, blank=True)
    amount = models.IntegerField()
    client = models.ForeignKey('school.Client', on_delete = models.CASCADE, related_name="payment")


class Club(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    name = models.CharField(max_length=50, db_index=True, blank=True)
    description = models.CharField(max_length=200, blank=True, null=True)
    badges = models.ManyToManyField('school.Badge', blank=True)


class StudentClub(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    badges = models.ManyToManyField('school.Badge', blank=True)
    club = models.ForeignKey('school.Club', on_delete = models.CASCADE, related_name="club",null=True,blank=True)
    student = models.ForeignKey('school.Student', on_delete = models.CASCADE, related_name="clubs",null=True,blank=True)


class BookingManager(models.Manager):
    
    def create_booking(self, sessions, data):
        bookings = set()
        for session in range(sessions): 
            try: 
                booking = Booking.objects.get(
                    student=data.get('student'),
                    date = data.get('date') + session*datetime.timedelta(days=7)
                )
                logger.exception("booking exists" + str(booking.identifier))

            except Booking.DoesNotExist:
                
                booking = Booking.objects.create(
                    student=data.get('student'),
                    client=data.get('client'),
                    session = data.get('session'),
                    date = data.get('date') + session*datetime.timedelta(days=7),
                    )

                try: 
                    count = Session.objects.filter(
                            identifier = booking.session.identifier,
                            students__identifier= booking.student.identifier
                        ).count()
                    if count > 0: 
                        booking.session.student_amount = booking.session.student_amount + 1

                except Session.DoesNotExist:
                    raise exceptions.NotFound()
                
                booking.session.bookings.add(booking)
                booking.session.save()

        return booking

    def get_student_count(self, session):
        return session.bookings.values('student__identifier').distinct().count()
    

class Booking(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    student = models.ForeignKey('school.Student' , related_name="bookings")
    client = models.ForeignKey('school.Client',blank=True, null=True)
    session = models.ForeignKey('school.Session', blank=True, null=True, on_delete = models.CASCADE, related_name="bookings")
    date = models.DateField(blank=True, null=True)
    status = EnumField(
                BookingStatus, 
                max_length=50,
                default=BookingStatus.ACTIVE)
    teaching_record = models.CharField(max_length=500, blank=True, null=True)
    attendance_status = EnumField(
                AttendanceStatus, 
                max_length=50,
                default=AttendanceStatus.NONE)
    objects = BookingManager()


class CampBookingManager(models.Manager):
    
    def create_booking(self, sessions, data):
        bookings = set()
        for session in range(sessions): 

            booking = CampBooking.objects.create(
                student=data.get('student'),
                client=data.get('client'),
                session = data.get('session'),
                date = data.get('date') + session*datetime.timedelta(days=1),
                lunch = data.get('lunch'),
                note = data.get('note')
                )

            try: 
                count = CampSession.objects.filter(
                        identifier = booking.session.identifier,
                    ).count()
                if count > 0: 
                    booking.session.student_amount = booking.session.student_amount + 1

            except CampSession.DoesNotExist:
                raise exceptions.NotFound()
            
            booking.session.campbookings.add(booking)
            booking.session.save()

        return booking

    def get_student_count(self, session):
        return session.bookings.values('student__identifier').distinct().count()
    

class CampBooking(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    student = models.ForeignKey('school.Student' , related_name="campbookings")
    client = models.ForeignKey('school.Client',blank=True, null=True)
    session = models.ForeignKey('school.CampSession', blank=True, null=True, on_delete = models.CASCADE, related_name="campbookings")
    date = models.DateField(blank=True, null=True)
    status = EnumField(
                BookingStatus, 
                max_length=50,
                default=BookingStatus.ACTIVE)
    teaching_record = models.CharField(max_length=500, blank=True, null=True)
    attendance_status = EnumField(
                AttendanceStatus, 
                max_length=50,
                default=AttendanceStatus.ATTENDED)
    lunch = models.BooleanField(default=False, blank=True)
    note = models.CharField(max_length=500, blank=True, null=True)
    objects = CampBookingManager()


class BookingRequest(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True, default=uuid.uuid4)
    student = models.ForeignKey('school.Student')
    client = models.ForeignKey('school.Client', blank=True, null=True)
    session = models.ForeignKey('school.Session', blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    status = EnumField(
                Booking_Status, 
                max_length=50,
                default=Booking_Status.REQUEST)


class Badge(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    name = models.CharField(max_length=50, db_index=True, blank=True)
    description = models.CharField(max_length=200, blank=True)


class Session(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    location = models.CharField(max_length=100)
    day = models.CharField(max_length=100, default = None, null=True, blank=True)
    time = models.CharField(max_length=100, default = None, null=True, blank=True)
    club = models.CharField(max_length=50, db_index=True, blank=True)
    duration = models.DecimalField(max_digits=5, decimal_places=2)
    student_amount = models.IntegerField(default = 0)
    teacher = models.ForeignKey('school.Teacher', blank=True, null=True, on_delete = models.CASCADE, related_name="session",default=None)
    students = models.ManyToManyField('school.Student', blank=True)
    session_type = EnumField(
                SessionType, 
                max_length=50,
                default=SessionType.NONE)
    description = models.CharField(max_length=200, default = None, null=True, blank=True)
    status = EnumField(
                SessionStatus, 
                max_length=50,
                default=SessionStatus.ACTIVE)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    

class Trial(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    location = models.CharField(max_length=100)
    club = EnumField(
                Clubs, 
                max_length=50,
                default=Clubs.NONE)
    duration = models.DecimalField(max_digits=5, decimal_places=2)
    student_amount = models.IntegerField(default = 0)
    teacher = models.ForeignKey('school.Teacher', blank=True, on_delete = models.CASCADE, related_name="trial",null=True,default=None)
    student = models.ForeignKey('school.Student', blank=True, null=True, on_delete = models.CASCADE, related_name="trial",default=None)
    date = models.DateTimeField(blank=True, null=True)
    sales_representative = models.ForeignKey('school.Staff', blank=True, on_delete = models.CASCADE, related_name="trial",null=True,default=None)
    status = models.CharField(max_length=100, null=True, default=None)


class ClientNote(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    note =  models.CharField(max_length=2000)
    user = models.ForeignKey('school.User', blank=True,null=True)
    client = models.ForeignKey('school.Client', blank=True,null=True,default=None,on_delete = models.CASCADE, related_name="note")


class StudentNote(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    note =  models.CharField(max_length=2000)
    user = models.ForeignKey('school.User', blank=True,null=True)
    student = models.ForeignKey('school.Student', blank=True,null=True,default=None,on_delete = models.CASCADE, related_name="note")


class SessionNote(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    note =  models.CharField(max_length=2000)
    user = models.ForeignKey('school.User', blank=True,null=True)
    session = models.ForeignKey('school.Session', blank=True,null=True,default=None,on_delete = models.CASCADE, related_name="note")


class Branch(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    description = models.CharField(max_length=200, default = None, null=True, blank=True)
    short_id =  models.CharField(max_length=5, default = 'SP')
    name = models.CharField(max_length=50, default = 'SP')
    enrollments = models.IntegerField(default = 0, null=True, blank=True)
    active_students = models.IntegerField(default = 0, null=True, blank=True)
    inactive_students = models.IntegerField(default = 0, null=True, blank=True)


class Camp(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    name = models.CharField(max_length=100, default = None, null=True, blank=True)
    description = models.CharField(max_length=200, default = None, null=True, blank=True)
    location = models.CharField(max_length=100)
    weeks = models.IntegerField(default = 1)
    status = EnumField(
                SessionStatus, 
                max_length=50,
                default=SessionStatus.ACTIVE)
    

class CampWeek(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    name = models.CharField(max_length=100, default = None, null=True, blank=True)
    week = models.IntegerField(default = 1)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    camp = models.ForeignKey('school.Camp', blank=True, null=True, on_delete = models.CASCADE, related_name="campweek",default=None)


class CampSession(DateModel):
    identifier = models.UUIDField(unique=True, db_index=True,
        default=uuid.uuid4)
    description = models.CharField(max_length=200, default = None, null=True, blank=True)
    week = models.ForeignKey('school.CampWeek', blank=True, null=True, on_delete = models.CASCADE,default=None)
    location = models.CharField(max_length=100)
    club = models.CharField(max_length=50, db_index=True, blank=True)
    teacher = models.ForeignKey('school.Teacher', blank=True, null=True, on_delete = models.CASCADE, related_name="campsession",default=None)
    status = EnumField(
                SessionStatus, 
                max_length=50,
                default=SessionStatus.ACTIVE)
    duration = models.DecimalField(max_digits=5, decimal_places=2)
    session_type = EnumField(
                CampSessionType, 
                max_length=50,
                default=CampSessionType.NONE)
    camp = models.ForeignKey('school.Camp', blank=True, null=True, on_delete = models.CASCADE, related_name="campsession",default=None)
    student_amount = models.IntegerField(default = 0)


class Enrollment(DateModel):
    student = models.ForeignKey('school.Student' , related_name="student")
    session = models.ForeignKey('school.Session', blank=True, null=True, on_delete = models.CASCADE, related_name="session")


