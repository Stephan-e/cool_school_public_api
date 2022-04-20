import uuid
import random
import json

from rest_framework import serializers
from django.db import transaction
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email
from allauth.account.models import EmailAddress
from allauth.account import app_settings
from rest_framework import serializers
from rest_framework import exceptions, status, filters
from rest_framework.serializers import ModelSerializer
from django.db import transaction
from django.db.models import Sum
from django.contrib.auth import authenticate
from rest_auth.serializers import (
    PasswordChangeSerializer as DefaultPasswordChangeSerializer,
    PasswordResetSerializer as DefaultPasswordResetSerializer,
    PasswordResetConfirmSerializer as DefaultPasswordResetConfirmSerializer
)
from django.utils.translation import ugettext_lazy as _
from config import settings
from school.models import  *
from school.forms import PasswordResetForm
from school.enums import *
from school.fields import TimestampField
import datetime
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Count, Sum
from school.common import get_student_hours, get_client_hours, get_client_hours_penalty
from django.contrib.auth.models import Group
from taggit.models import Tag



class DateSerializer(serializers.ModelSerializer):
    created = serializers.SerializerMethodField()
    updated = serializers.SerializerMethodField()

    @staticmethod
    def get_created(obj):
        return int(obj.created.timestamp() * 1000)

    @staticmethod
    def get_updated(obj):
        return int(obj.updated.timestamp() * 1000)


class UserShortSerializer(DateSerializer):
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', )

    def validate(self, validated_data):
        return validated_data


class ShortStudentSerializer(serializers.ModelSerializer):
    status = serializers.CharField(required=False)
    location = serializers.CharField(required=False)

    class Meta:
        model = Student
        fields = (
            'identifier',
            'first_name',
            'last_name',
            'birth_date',
            'language',
            'medical_condition',
            'status',
            'location',
        )

    def delete(self):
        self.instance.delete()


class ClientShortSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    phone = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    hours_remaining = serializers.SerializerMethodField()
    total_hours_purchased = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = (
            'identifier',
            'first_name',
            'last_name',
            'email',
            'phone',
            'status',
            'location',
            'hours_remaining',
            'total_hours_purchased',
        )

    def get_total_hours_purchased(self, instance):
        try:
            hours_purchased = Payment.objects.filter(client=instance).aggregate(Sum('hours_purchased'))
            return hours_purchased['hours_purchased__sum']
        except Payment.DoesNotExist:
            return 0
        
    def get_hours_remaining(self, instance):
        return get_client_hours(instance)


class BadgeSerializer(serializers.ModelSerializer):
    identifier = serializers.UUIDField(read_only=True)
    
    class Meta:
        model = Badge
        fields = (
            'identifier',
            'name',
            'description',
        )

    def delete(self):
        self.instance.delete()


class CreateBadgeSerializer(BadgeSerializer):
    name = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    club = serializers.CharField(required=True)

    class Meta:
        model = BadgeSerializer.Meta.model
        fields = (
            'identifier',
            'name',
            'description',
            'club',
        )
        read_only_fields = (
            'identifier',
        )

    def validate(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return validated_data

    def create(self, validated_data):
        try:
            club = Club.objects.get(
                identifier=validated_data['club'],
                )
        except Club.DoesNotExist:
            raise exceptions.NotFound()

        badge = Badge.objects.create(
                name=validated_data['name'],
                description=validated_data['description'],
                )

        club.badges.add(badge)

        return badge


class ClubSerializer(serializers.ModelSerializer):
    identifier = serializers.UUIDField(read_only=True)
    badges = BadgeSerializer(many=True)
    name = serializers.CharField(required=False)
               
    class Meta:
        model = Club
        fields = (
            'identifier',
            'name',
            'description',
            'badges',
        )

    def delete(self):
        self.instance.delete()


class StudentClubSerializer(serializers.ModelSerializer):
    identifier = serializers.UUIDField(read_only=True)
    badges = BadgeSerializer(many=True)
    student = ShortStudentSerializer()
    club = ClubSerializer()
               
    class Meta:
        model = StudentClub
        fields = (
            'identifier',
            'badges',
            'student',
            'club',
        )

    def delete(self):
        self.instance.delete()


class ShortClubSerializer(serializers.ModelSerializer):
    identifier = serializers.UUIDField(read_only=True)
    name = serializers.CharField(required=False)

    class Meta:
        model = Club
        fields = (
            'identifier',
            'name',
            'description',
        )

    def delete(self):
        self.instance.delete()


class CreateClubSerializer(ClubSerializer):
    name = serializers.ChoiceField(
                required=True,
                source='name.value',
                choices=Clubs.choices())
    description = serializers.CharField(required=True)

    class Meta:
        model = Club
        fields = (
            'identifier',
            'name',
            'description',
        )
        read_only_fields = (
            'identifier',
        )

    def validate(self, validated_data):
        return validated_data

    def create(self, validated_data):
        club = Club.objects.create(
                description=validated_data.get('description'),
                name = validated_data['name']['value']
                )
        return club


class CreateStudentClubSerializer(ClubSerializer):
    club = serializers.CharField(required=True)

    class Meta:
        model = StudentClub
        fields = (
            'identifier',
            'club'
        )
        read_only_fields = (
            'identifier',
        )

    def validate(self, validated_data):
        return validated_data

    def create(self, validated_data):
        try:
            student = Student.objects.get(
                identifier=self.context['student'],
                )
        except Student.DoesNotExist:
            raise exceptions.NotFound("Student not found")

        try:
            club = Club.objects.get(
                identifier=validated_data['club'],
                )
        except Club.DoesNotExist:
            raise exceptions.NotFound("Club not found")

        try:
            club = StudentClub.objects.get(
                student=student,
                club=club,
                )
            raise exceptions.NotFound('The student is already in this club.')

        except StudentClub.DoesNotExist:
            pass

        club = StudentClub.objects.create(
                student=student,
                club = club
                )

        return club


class AddBadgeSerializer(serializers.ModelSerializer):
    badge = serializers.CharField()

    class Meta:
        model = Badge
        fields = (
            'identifier',
            'badge',
        )
        read_only_fields = (
            'identifier',
        )

    def validate(self, validated_data):
        return validated_data

    def create(self, validated_data):
        try:
            club = StudentClub.objects.get(
                student__identifier=self.context['student'],
                club__identifier=self.context['club'],
                )
        except Club.DoesNotExist:
            raise exceptions.NotFound('Club not found')
        try:
            badge = Badge.objects.get(
                identifier=validated_data['badge'],
                )
        except Badge.DoesNotExist:
            raise exceptions.NotFound("Badge not found")

        club.badges.add(badge)

        return club


class TagSerializer(serializers.ModelSerializer):
    name = serializers.CharField()

    class Meta:
        model = Tag
        fields = (
            'name',
        )


class TagCreateSerializer(serializers.ModelSerializer):
    name = serializers.CharField()

    class Meta:
        model = Tag
        fields = (
            'name',
        )


class StudentSerializer(serializers.ModelSerializer):
    clubs = StudentClubSerializer(many=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    client = ClientShortSerializer()
    birth_date = serializers.DateField()
    language = serializers.CharField()
    medical_condition = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    age = serializers.IntegerField()
    hours = serializers.SerializerMethodField()
    tags = serializers.CharField()

    class Meta:
        model = Student
        fields = (
            'identifier',
            'first_name',
            'last_name',
            'clubs',
            'client',
            'birth_date',
            'language',
            'medical_condition',
            'student_id',
            'hours',
            'status',
            'location',
            'age',
            'tags',
        )

    def setup_eager_loading(queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('client')

        return queryset

    def delete(self):
        self.instance.delete()

    def get_age(self, instance):
        today=datetime.datetime.today()
        return today.year - instance.birth_date.year - ((today.month, today.day) < (instance.birth_date.month, instance.birth_date.day))

    def get_hours(self, instance):
        return get_student_hours(instance)


class UpdateStudentSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    birth_date = serializers.DateField()
    language = serializers.CharField()
    medical_condition = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    location = serializers.CharField()
    student_id = serializers.CharField()

    class Meta:
        model = Student
        fields = (
            'first_name',
            'last_name',
            'client',
            'birth_date',
            'language',
            'medical_condition',
            'status',
            'location',
            'student_id',
        )

    def delete(self):
        self.instance.delete()


class StudentZapierSerializer(serializers.ModelSerializer):
    clubs = StudentClubSerializer(many=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    client = serializers.CharField(source='client.identifier')
    birth_date = serializers.DateField()
    language = serializers.CharField()
    medical_condition = serializers.CharField(required=False)
    status = serializers.CharField(required=False)


    class Meta:
        model = Student
        fields = (
            'identifier',
            'first_name',
            'last_name',
            'clubs',
            'client',
            'birth_date',
            'language',
            'medical_condition',
            'student_id',
            'status',
        )

    def delete(self):
        self.instance.delete()


class StudentShorterSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    status = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    age = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = (
            'identifier',
            'first_name',
            'last_name',
            'language',
            'student_id',
            'status',
            'location',
            'age',
        )

    def setup_eager_loading(queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('club')
        return queryset

    def delete(self):
        self.instance.delete()

    def get_age(self, instance):
        today=datetime.datetime.today()
        return today.year - instance.birth_date.year - ((today.month, today.day) < (instance.birth_date.month, instance.birth_date.day))

    
class StudentIndexSerializer(serializers.ModelSerializer):
    status = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    age = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = (
            'identifier',
            'first_name',
            'last_name',
            'student_id',
            'status',
            'location',
            'age',
        )

    def delete(self):
        self.instance.delete()

    def get_age(self, instance):
        today=datetime.datetime.today()
        return today.year - instance.birth_date.year - ((today.month, today.day) < (instance.birth_date.month, instance.birth_date.day))


class StudentShortSerializer(serializers.ModelSerializer):
    clubs = StudentClubSerializer(many=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    birth_date = serializers.DateField()
    language = serializers.CharField()
    medical_condition = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    age = serializers.SerializerMethodField()
    hours = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = (
            'identifier',
            'first_name',
            'last_name',
            'clubs',
            'birth_date',
            'language',
            'medical_condition',
            'student_id',
            'status',
            'location',
            'age',
            'hours',
        )

    def delete(self):
        self.instance.delete()

    def get_age(self, instance):
        today=datetime.datetime.today()
        return today.year - instance.birth_date.year - ((today.month, today.day) < (instance.birth_date.month, instance.birth_date.day))
    
    def get_hours(self, instance):
        
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


class CreateStudentSerializer(StudentSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    client = serializers.CharField()
    birth_date = serializers.DateField(required=False)
    language = serializers.CharField()
    medical_condition = serializers.CharField(required=False)
    student_id = serializers.CharField(required=False)
    status = serializers.ChoiceField(
                required=False,
                choices=ClientStatus)

    class Meta:
        model = StudentSerializer.Meta.model
        fields = (
            'identifier',
            'first_name',
            'last_name',
            'client',
            'birth_date',
            'language',
            'medical_condition',
            'student_id',
            'status',
            'location',
           
        )
        read_only_fields = (
            'identifier',
        )

    def create(self, validated_data):
        try:
            client = Client.objects.get(
                identifier=validated_data['client'],
                )
        except Client.DoesNotExist:
            raise exceptions.NotFound()

        student = Student.objects.create(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            birth_date=validated_data.get('birth_date'),
            client=client,
            medical_condition=validated_data.get('medical_condition'),
            language=validated_data.get('language'),
            location = client.location
            )
        

        student.student_id = "SP" + str(student.pk)
        student.save()

        return student


class ClientSerializer(serializers.ModelSerializer):
    student = StudentShortSerializer(many=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    phone = serializers.CharField(required=False)
    language = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    payment_status = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    hours_remaining = serializers.SerializerMethodField()
    total_hours_purchased = serializers.SerializerMethodField()
    penalty_hours = serializers.SerializerMethodField()
    tags = serializers.CharField()

    class Meta:
        model = Client
        fields = (
            'identifier',
            'first_name',
            'last_name',
            'email',
            'phone',
            'location',
            'language',
            'hours_remaining',
            'total_hours_purchased',
            'penalty_hours',
            'student',
            'created',
            'payment_status',
            'description',
            'status',
            'tags',
            'service_rate'
        )

    def setup_eager_loading(queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('student')
        return queryset
    
    def get_total_hours_purchased(self, instance):
        try:
            hours_purchased = Payment.objects.filter(client=instance).aggregate(Sum('hours_purchased'))
            return hours_purchased['hours_purchased__sum']
        except Payment.DoesNotExist:
            return 0
        
    def get_hours_remaining(self, instance):
        return get_client_hours(instance)

    def get_penalty_hours(self, instance):
        return get_client_hours_penalty(instance)

    def delete(self):
        self.instance.delete()


class ClientListSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    phone = serializers.CharField(required=False)
    language = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    payment_status = serializers.CharField(required=False)
    status = serializers.CharField(required=False)

    class Meta:
        model = Client
        fields = (
            'identifier',
            'first_name',
            'last_name',
            'email',
            'phone',
            'location',
            'language',
            'payment_status',
            'status',
            'created',
        )

    def delete(self):
        self.instance.delete()


class CreateClientSerializer(ClientSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    language = serializers.CharField(required=False)
    status = serializers.CharField(required=True)
    location = serializers.CharField()

    class Meta:
        model = ClientSerializer.Meta.model
        fields = (
            'identifier',
            'first_name',
            'last_name',
            'email',
            'phone',
            'location',
            'language',
            'status',
        )
        read_only_fields = (
            'identifier',
        )

    def validate(self, validated_data):
        validated_data['user'] = self.context['request'].user

        if validated_data.get('status') == 'Active':
            validated_data['status'] = 'active'
        if validated_data.get('status') == 'Inactive':
            validated_data['status'] = 'inactive'
            
        return validated_data

    def create(self, validated_data):
        
        if Client.objects.filter(email=validated_data.get('email')).exists():
            raise serializers.ValidationError(
                {"email": [_("A client is already registered "
                             "with this email address.")]})

        client = Client.objects.create(
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
                email=validated_data.get('email'),
                phone=validated_data.get('phone'),
                location=validated_data.get('location'),
                language=validated_data.get('language'),
                status =validated_data.get('status'),

                )

        return client


class TeacherSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)
    language = serializers.CharField(required=True)
    location = serializers.CharField(required=True)

    class Meta:
        model = Teacher
        fields = (
            'identifier',
            'first_name',
            'last_name',
            'email',
            'phone',
            'location',
            'language',
            'created',
        )

    def delete(self):
        self.instance.delete()


class TeacherListSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    phone = serializers.CharField(required=False)
    language = serializers.CharField(required=False)
    location = serializers.CharField(required=False)

    class Meta:
        model = Teacher
        fields = (
            'identifier',
            'first_name',
            'last_name',
            'email',
            'phone',
            'location',
            'language',
            'created',
        )

    def delete(self):
        self.instance.delete()


class CreateTeacherSerializer(TeacherSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    language = serializers.CharField(required=False)

    class Meta:
        model = TeacherSerializer.Meta.model
        fields = (
            'identifier',
            'first_name',
            'last_name',
            'email',
            'phone',
            'location',
            'language',
        )
        read_only_fields = (
            'identifier',
        )

    def validate(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return validated_data

    def create(self, validated_data):
        
        if Client.objects.filter(email=validated_data.get('email')).exists():
            raise serializers.ValidationError(
                {"email": [_("A teacher is already registered "
                             "with this email address.")]})

        teacher = Teacher.objects.create(
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
                email=validated_data.get('email'),
                phone=validated_data.get('phone'),
                location=validated_data.get('location'),
                language=validated_data.get('language'),
                )

        return teacher


class StaffSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)
    language = serializers.CharField(required=True)
    location = serializers.CharField(required=True)
    role = serializers.CharField(required=True)

    class Meta:
        model = Staff
        fields = (
            'identifier',
            'first_name',
            'last_name',
            'email',
            'phone',
            'location',
            'language',
            'created',
            'role',
        )

    def delete(self):
        self.instance.delete()


class StaffListSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    phone = serializers.CharField(required=False)
    language = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    role = serializers.CharField(required=False)

    class Meta:
        model = Staff
        fields = (
            'identifier',
            'first_name',
            'last_name',
            'email',
            'phone',
            'location',
            'language',
            'created',
            'role',
        )

    def delete(self):
        self.instance.delete()


class CreateStaffSerializer(StaffSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    language = serializers.CharField(required=False)
    role = serializers.CharField(required=False)
    

    class Meta:
        model = StaffSerializer.Meta.model
        fields = (
            'identifier',
            'first_name',
            'last_name',
            'email',
            'phone',
            'location',
            'language',
            'role',
        )
        read_only_fields = (
            'identifier',
        )

    def validate(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return validated_data

    def create(self, validated_data):
        
        if Client.objects.filter(email=validated_data.get('email')).exists():
            raise serializers.ValidationError(
                {"email": [_("A staff member is already registered "
                             "with this email address.")]})

        staff = Staff.objects.create(
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
                email=validated_data.get('email'),
                phone=validated_data.get('phone'),
                location=validated_data.get('location'),
                language=validated_data.get('language'),
                role = validated_data.get('role')
                )

        return staff


class ShortBookingSerializer(serializers.ModelSerializer):
    student = StudentShorterSerializer()
    client = ClientShortSerializer()
    date = serializers.DateField()
    status = serializers.CharField()
    teaching_record = serializers.CharField()
    attendance_status = serializers.CharField()

    class Meta:
        model = Booking
        fields = (
            'identifier',
            'student',
            'client',
            'date',
            'status',
            'teaching_record',
            'attendance_status',
        )

    def delete(self):
        self.instance.delete()


class ShortCampBookingSerializer(serializers.ModelSerializer):
    student = StudentShorterSerializer()
    client = ClientShortSerializer()
    date = serializers.DateField()
    status = serializers.CharField()
    teaching_record = serializers.CharField()
    attendance_status = serializers.CharField()

    class Meta:
        model = CampBooking
        fields = (
            'identifier',
            'student',
            'client',
            'date',
            'status',
            'teaching_record',
            'attendance_status',
            'lunch',
            'note',
        )

    def delete(self):
        self.instance.delete()


class UserStudentSessionSerializer(serializers.ModelSerializer):
    location = serializers.CharField()
    day = serializers.CharField()
    time = serializers.CharField()
    club = serializers.CharField()
    teacher = TeacherSerializer()
    session_type = serializers.CharField()
    status = serializers.CharField()

    class Meta:
        model = Session
        fields = (
            'identifier',
            'location',
            'day',
            'time',
            'club',
            'teacher',
            'duration',
            'session_type',
            'description',
            'status',

        )

    def delete(self):
        self.instance.delete()


class UserStudentCampSessionSerializer(serializers.ModelSerializer):
    location = serializers.CharField()
    day = serializers.CharField()
    time = serializers.CharField()
    club = serializers.CharField()
    teacher = TeacherSerializer()
    session_type = serializers.CharField()
    status = serializers.CharField()

    class Meta:
        model = Session
        fields = (
            'identifier',
            'location',
            'day',
            'time',
            'club',
            'teacher',
            'duration',
            'session_type',
            'description',
            'status',

        )

    def delete(self):
        self.instance.delete()


class StudentSessionListSerializer(serializers.ModelSerializer):
    location = serializers.CharField()
    day = serializers.CharField()
    time = serializers.CharField()
    club = serializers.CharField()
    teacher = TeacherSerializer()
    student_amount = serializers.SerializerMethodField()
    session_type = serializers.CharField()
    status = serializers.CharField()

    @staticmethod
    def get_student_amount(obj):
        return obj.bookings.get_student_count(obj)

    class Meta:
        model = Session
        fields = (
            'identifier',
            'location',
            'day',
            'time',
            'club',
            'teacher',
            'duration',
            'student_amount',
            'session_type',
            'description',
            'status',

        )
    def setup_eager_loading(queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('bookings')
        queryset = queryset.prefetch_related('teacher')

        return queryset

    def delete(self):
        self.instance.delete()


class StudentSessionSerializer(serializers.ModelSerializer):
    location = serializers.CharField()
    day = serializers.CharField()
    time = serializers.CharField()
    club = serializers.CharField()
    teacher = TeacherSerializer()
    bookings = ShortBookingSerializer(many=True)
    students = serializers.CharField()
    session_type = serializers.CharField()
    status = serializers.CharField()
    student_amount = serializers.SerializerMethodField()

    @staticmethod
    def get_student_amount(obj):
        return obj.bookings.get_student_count(obj)
    
    
    class Meta:
        model = Session
        fields = (
            'identifier',
            'location',
            'day',
            'time',
            'club',
            'teacher',
            'students',
            'duration',
            'students',
            'student_amount',
            'bookings',
            'session_type',
            'description',
            'status',

        )
    def setup_eager_loading(queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('bookings')
        queryset = queryset.prefetch_related('teacher')

        return queryset

    def delete(self):
        self.instance.delete()


class CreateStudentSessionSerializer(serializers.ModelSerializer):
    location = serializers.CharField()
    day = serializers.CharField()
    time = serializers.CharField()
    club = serializers.CharField()
    teacher = serializers.CharField(required=False, allow_blank=True)
    duration = serializers.DecimalField(max_digits=5, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
                required=False,
                choices=SessionStatus.choices())

    class Meta:
        model = Session
        fields = (
            'location',
            'day',
            'club',
            'time',
            'teacher',
            'duration',
            'description',
            'status',
        )

    def validate(self, validated_data):
        return validated_data

    def create(self, validated_data):
        try:
            teacher = Teacher.objects.get(identifier=validated_data.get('teacher'))
        except Teacher.DoesNotExist:
            teacher = None
        except ValueError:
            teacher = None

        session = Session.objects.create(
                location=validated_data.get('location'),
                day=validated_data.get('day'),
                time=validated_data.get('time'),
                club=validated_data.get('club'),
                duration=validated_data.get('duration'),
                teacher =teacher,
                session_type = 'club',
                description = validated_data.get('description'),

                )
        return session


class UpdateStudentSessionSerializer(serializers.ModelSerializer):
    location = serializers.CharField()
    day = serializers.CharField()
    time = serializers.CharField()
    club = serializers.CharField()
    duration = serializers.DecimalField(max_digits=5, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
                required=False,
                choices=SessionStatus.choices())

    class Meta:
        model = Session
        fields = (
            'location',
            'day',
            'club',
            'time',
            'teacher',
            'duration',
            'description',
            'status',

        )


class StudentCampSessionSerializer(serializers.ModelSerializer):
    location = serializers.CharField()
    club = serializers.CharField()
    teacher = TeacherSerializer()
    bookings = ShortBookingSerializer(many=True)
    session_type = serializers.CharField()
    status = serializers.CharField()

    class Meta:
        model = Session
        fields = (
            'identifier',
            'location',
            'club',
            'teacher',
            'duration',
            'student_amount',
            'bookings',
            'start_date',
            'end_date',
            'session_type',
            'description',
            'status',
        )

    def delete(self):
        self.instance.delete()


class CreateStudentCampSessionSerializer(serializers.ModelSerializer):
    location = serializers.CharField()
    club = serializers.CharField()
    teacher = serializers.CharField(required=False, allow_blank=True)
    duration = serializers.DecimalField(max_digits=5, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    status = serializers.ChoiceField(
                required=False,
                choices=ClientStatus.choices(),
                allow_blank=True)    

    class Meta:
        model = Session
        fields = (
            'location',
            'club',
            'teacher',
            'duration',
            'start_date',
            'end_date',
            'teacher',
            'description',
            'status',
        )

    def validate(self, validated_data):
        return validated_data

    def create(self, validated_data):
        try:
            teacher = Teacher.objects.get(identifier=validated_data.get('teacher'))
        except Teacher.DoesNotExist:
            teacher = None
        except ValueError:
            teacher = None

        session = Session.objects.create(
                location=validated_data.get('location'),
                club=validated_data.get('club'),
                duration=validated_data.get('duration'),
                start_date=validated_data.get('start_date'),
                end_date=validated_data.get('end_date'),
                teacher=teacher,
                session_type = 'camp',
                description = validated_data.get('description')
                )
        return session


class CampSerializer(serializers.ModelSerializer):
    identifier = serializers.UUIDField(read_only=True)
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    location = serializers.CharField()
    status = serializers.CharField()
    weeks = serializers.IntegerField()
               
    class Meta:
        model = Camp
        fields = (
            'identifier',
            'name',
            'description',
            'location',
            'status',
            'weeks',
        )

    def delete(self):
        self.instance.delete()


class CreateCampSerializer(ClubSerializer):
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    location = serializers.CharField()
    status = serializers.ChoiceField(
                required=False,
                choices=SessionStatus.choices())
    weeks = serializers.IntegerField()

    class Meta:
        model = Camp
        fields = (
            'name',
            'description',
            'location',
            'status',
            'weeks',
        )
        read_only_fields = (
            'identifier',
        )

    def validate(self, validated_data):
        return validated_data


class CampWeekSerializer(serializers.ModelSerializer):
    identifier = serializers.UUIDField(read_only=True)
    week = serializers.IntegerField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    camp = CampSerializer()
               
    class Meta:
        model = CampWeek
        fields = (
            'identifier',
            'week',
            'start_date',
            'end_date',
            'camp',
        )

    
    def delete(self):
        self.instance.delete()


class CreateCampWeekSerializer(ClubSerializer):
    identifier = serializers.UUIDField(read_only=True)
    week = serializers.CharField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    camp = serializers.CharField()

    class Meta:
        model = CampWeek
        fields = (
            'identifier',
            'week',
            'start_date',
            'end_date',
            'camp',
        )
        read_only_fields = (
            'identifier',
        )

    def validate(self, validated_data):
        try:
            validated_data['camp'] = Camp.objects.get(identifier=validated_data.get('camp'))
        except CampSession.DoesNotExist:
            raise exceptions.NotFound('Camp not found')
        return validated_data 


class ShortCampSessionSerializer(serializers.ModelSerializer):
    location = serializers.CharField()
    club = serializers.CharField()
    session_type = serializers.CharField()
    status = serializers.CharField()
    week = CampWeekSerializer()
    total_lunch_amount = serializers.SerializerMethodField()
    total_students = serializers.SerializerMethodField()

    class Meta:
        model = CampSession
        fields = (
            'identifier',
            'location',
            'club',
            'duration',
            'student_amount',
            'session_type',
            'description',
            'status',
            'week',
            'total_lunch_amount',
            'total_students',
        )

    def setup_eager_loading(queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('teacher')
        queryset = queryset.prefetch_related('camp')
        queryset = queryset.prefetch_related('week')

        return queryset

    def get_total_lunch_amount(self,instance):

        try:
            bookings=CampBooking.objects.filter(session=instance,lunch=True).count()
            return bookings
        except CampBooking.DoesNotExist:
            return 0 

    def get_total_students(self,instance):
        try:
            bookings=CampBooking.objects.filter(session=instance).values('student__identifier').distinct().count()
            return bookings
        except CampBooking.DoesNotExist:
            return 0 


    def delete(self):
        self.instance.delete()


class CampSessionSerializer(serializers.ModelSerializer):
    location = serializers.CharField()
    club = serializers.CharField()
    teacher = TeacherSerializer()
    campbookings = ShortCampBookingSerializer(many=True)
    session_type = serializers.CharField()
    status = serializers.CharField()
    camp = CampSerializer()
    week = CampWeekSerializer()
    total_lunch_amount = serializers.SerializerMethodField()
    total_students = serializers.SerializerMethodField()

    class Meta:
        model = CampSession
        fields = (
            'identifier',
            'location',
            'club',
            'teacher',
            'duration',
            'student_amount',
            'campbookings',
            'session_type',
            'description',
            'status',
            'week',
            'camp',
            'total_lunch_amount',
            'total_students',
        )

    def get_total_lunch_amount(self,instance):

        try:
            bookings=CampBooking.objects.filter(session=instance,lunch=True).count()
            return bookings
        except CampBooking.DoesNotExist:
            return 0 

    def get_total_students(self,instance):
        try:
            bookings=CampBooking.objects.filter(session=instance).values('student__identifier').distinct().count()
            return bookings
        except CampBooking.DoesNotExist:
            return 0 

    def delete(self):
        self.instance.delete()


class CreateCampSessionSerializer(serializers.ModelSerializer):
    location = serializers.CharField()
    club = serializers.ChoiceField(
                required=False,
                choices=Clubs.choices(),
                allow_blank=True)  
    teacher = serializers.CharField(required=True)
    duration = serializers.DecimalField(max_digits=5, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
                required=False,
                choices=SessionStatus.choices(),
                allow_blank=True)    
    session_type = serializers.ChoiceField(
                required=False,
                choices=CampSessionType.choices(),
                allow_blank=True)  
    week = serializers.CharField()
    camp = serializers.CharField()

    class Meta:
        model = CampSession
        fields = (
            'location',
            'club',
            'teacher',
            'duration',
            'week',
            'description',
            'status',
            'session_type',
            'camp',
        )

    def validate(self, validated_data):
        return validated_data

    def create(self, validated_data):
        try:
            teacher = Teacher.objects.get(identifier=validated_data.get('teacher'))
        except Teacher.DoesNotExist:
            raise exceptions.NotFound('Teacher not found')

        try:
            camp = Camp.objects.get(identifier=validated_data.get('camp'))
        except CampSession.DoesNotExist:
            raise exceptions.NotFound('Camp not found')

        try:
            week = CampWeek.objects.get(identifier=validated_data.get('week'))
        except CampWeek.DoesNotExist:
            raise exceptions.NotFound('Week not found')
        
        session = CampSession.objects.create(
                location=validated_data.get('location'),
                club=validated_data.get('club'),
                teacher=teacher,
                duration=validated_data.get('duration'),
                week=week,
                description = validated_data.get('description'),
                status = validated_data.get('status'),
                session_type = validated_data.get('session_type'),
                camp = camp
                )
        return session

    
class UpdateCampSessionSerializer(serializers.ModelSerializer):
    location = serializers.CharField(required=False)
    club = serializers.ChoiceField(
                required=False,
                choices=Clubs.choices(),
                allow_blank=True)  
    teacher = serializers.CharField(required=False)
    duration = serializers.DecimalField(max_digits=5, decimal_places=2,required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
                required=False,
                choices=SessionStatus.choices(),
                allow_blank=True)    
    session_type = serializers.ChoiceField(
                required=False,
                choices=CampSessionType.choices(),
                allow_blank=True)  
    week = serializers.CharField(required=False)
    camp = serializers.CharField(required=False)

    class Meta:
        model = CampSession
        fields = (
            'location',
            'club',
            'teacher',
            'duration',
            'week',
            'description',
            'status',
            'session_type',
            'camp',
        )

    def validate(self, validated_data):
        if validated_data['teacher']:
            try:
                validated_data['teacher'] = Teacher.objects.get(identifier=validated_data.get('teacher'))
            except Teacher.DoesNotExist:
                raise exceptions.NotFound('Teacher not found')
        
        if validated_data['camp']:
            try:
                validated_data['camp'] = Camp.objects.get(identifier=validated_data.get('camp'))
            except CampSession.DoesNotExist:
                raise exceptions.NotFound('Camp not found')

        if validated_data['week']:
            try:
                validated_data['week'] = CampWeek.objects.get(identifier=validated_data.get('week'))
            except CampWeek.DoesNotExist:
                raise exceptions.NotFound('Week not found')

        return validated_data

        
class StudentTrialSerializer(serializers.ModelSerializer):
    location = serializers.CharField()
    club = serializers.CharField()
    teacher = TeacherSerializer()
    student = ShortStudentSerializer()
    status = serializers.CharField()
    sales_representative = StaffSerializer()    

    class Meta:
        model = Trial
        fields = (
            'identifier',
            'location',
            'club',
            'teacher',
            'duration',
            'date',
            'student',
            'status',
            'sales_representative',
        )

    def delete(self):
        self.instance.delete()


class CreateStudentTrialSerializer(serializers.ModelSerializer):
    location = serializers.CharField()
    club = serializers.ChoiceField(choices=Clubs.choices())
    teacher = serializers.CharField(required=False, allow_blank=True)
    duration = serializers.DecimalField(max_digits=5, decimal_places=2)
    date = serializers.DateTimeField()
    student = serializers.CharField(required=False, allow_blank=True)
    sales_representative = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
                required=False,
                choices=Booking_Status.choices(),
                allow_blank=True) 

    class Meta:
        model = Trial
        fields = (
            'location',
            'club',
            'teacher',
            'duration',
            'date',
            'student',
            'sales_representative',
            'status',
        )

    def validate(self, validated_data):
        return validated_data

    def create(self, validated_data):
        try:
            teacher = Teacher.objects.get(identifier=validated_data.get('teacher'))
        except Teacher.DoesNotExist:
            teacher = None
        except ValueError:
            teacher = None

        try:
            student = Student.objects.get(identifier=validated_data.get('student'))
        except Teacher.DoesNotExist:
            student = None
        except ValueError:
            student = None

        try:
            staff = Staff.objects.get(identifier=validated_data.get('sales_representative'))
        except Staff.DoesNotExist:
            staff = None
        except ValueError:
            staff = None

        session = Trial.objects.create(
                location=validated_data.get('location'),
                date=validated_data.get('date'),
                club=validated_data.get('club'),
                duration=validated_data.get('duration'),
                teacher = teacher,
                student = student,
                sales_representative = staff,
                )
        return session


class ClientNoteSerializer(serializers.ModelSerializer):
    note = serializers.CharField()
    user = UserShortSerializer()
    client = ClientShortSerializer()

    class Meta:
        model = ClientNote
        fields = (
            'identifier',
            'note',
            'client',
            'user',
        )

    def delete(self):
        self.instance.delete()


class CreateClientNoteSerializer(serializers.ModelSerializer):
    note = serializers.CharField()
    client = serializers.CharField()
    user = serializers.CharField()

    class Meta:
        model = ClientNote
        fields = (
            'note',
            'user',
            'client',
        )

    def create(self, validated_data):
        try:
            client = Client.objects.get(
                identifier=validated_data.get('client')
            )
        except Client.DoesNotExist:
            raise exceptions.NotFound("Client not found")

        try:
            user = User.objects.get(
                email=validated_data.get('user')
            )
        except User.DoesNotExist:
            raise exceptions.NotFound("User not found")

        note = ClientNote.objects.create(
                note=validated_data.get('note'),
                user=user,
                client = client
                )
        
        return note


class StudentNoteSerializer(serializers.ModelSerializer):
    note = serializers.CharField()
    user = UserShortSerializer()
    student = StudentShorterSerializer()

    class Meta:
        model = StudentNote
        fields = (
            'identifier',
            'note',
            'student',
            'user',
        )

    def delete(self):
        self.instance.delete()


class CreateStudentNoteSerializer(serializers.ModelSerializer):
    note = serializers.CharField()
    student = serializers.CharField()
    user = serializers.CharField()

    class Meta:
        model = StudentNote
        fields = (
            'note',
            'user',
            'student',
        )

    def create(self, validated_data):
        try:
            student = Student.objects.get(
                identifier=validated_data.get('student')
            )
        except Student.DoesNotExist:
            raise exceptions.NotFound("Student not found")

        try:
            user = User.objects.get(
                email=validated_data.get('user')
            )
        except User.DoesNotExist:
            raise exceptions.NotFound("User not found")

        note = StudentNote.objects.create(
                note=validated_data.get('note'),
                user=user,
                student = student
                )
        
        return note


class SessionNoteSerializer(serializers.ModelSerializer):
    note = serializers.CharField()
    user = UserShortSerializer()
    session = serializers.CharField()

    class Meta:
        model = SessionNote
        fields = (
            'identifier',
            'note',
            'session',
            'user',
        )

    def delete(self):
        self.instance.delete()


class CreateSessionNoteSerializer(serializers.ModelSerializer):
    note = serializers.CharField()
    session = serializers.CharField()
    user = serializers.CharField()

    class Meta:
        model = SessionNote
        fields = (
            'note',
            'user',
            'session',
        )

    def create(self, validated_data):
        try:
            session = Session.objects.get(
                identifier=validated_data.get('session')
            )
        except Session.DoesNotExist:
            raise exceptions.NotFound("Session not found")

        try:
            user = User.objects.get(
                email=validated_data.get('user')
            )
        except User.DoesNotExist:
            raise exceptions.NotFound("User not found")

        note = SessionNote.objects.create(
                note=validated_data.get('note'),
                user=user,
                session = session
                )
        
        return note


class PaymentSerializer(serializers.ModelSerializer):
    hours_purchased = serializers.DecimalField(max_digits=5, decimal_places=2)
    date_purchased = serializers.DateField()
    method = serializers.CharField()
    amount = serializers.IntegerField()
    client = serializers.CharField(source='client.identifier')

    class Meta:
        model = Payment
        fields = (
            'identifier',
            'hours_purchased',
            'date_purchased',
            'method',
            'amount',
            'client',
        )

    def delete(self):

        try:
            client = Client.objects.get(
                identifier=self.instance.client.identifier
            )
        except Client.DoesNotExist:
            raise exceptions.NotFound()
        
        if get_client_hours(client) <= 0:
            client.payment_status = PaymentStatus.PENDING
        client.save()

        self.instance.delete()


class CreatePaymentSerializer(serializers.ModelSerializer):
    hours_purchased = serializers.DecimalField(max_digits=5, decimal_places=2)
    date_purchased = serializers.DateField()
    method = serializers.CharField()
    amount = serializers.IntegerField()
    client = serializers.CharField()

    class Meta:
        model = Payment
        fields = (
            'hours_purchased',
            'date_purchased',
            'method',
            'amount',
            'client',
        )

    def create(self, validated_data):
        try:
            client = Client.objects.get(
                identifier=validated_data.get('client')
            )
        except Client.DoesNotExist:
            raise exceptions.NotFound("Client not found")

        payment = Payment.objects.create(
                hours_purchased=validated_data.get('hours_purchased'),
                date_purchased=validated_data.get('date_purchased'),
                method = validated_data.get('method'),
                amount = validated_data.get('amount'),
                client = client,
                )
        client.payment_status = PaymentStatus.CONFIRMED
        client.save()
        return payment


class ClientReportSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    status = serializers.CharField()
    location = serializers.CharField()
    hours = serializers.SerializerMethodField()
    payment_status = serializers.CharField()
    payment = serializers.SerializerMethodField()
    hours_remaining = serializers.SerializerMethodField()
    total_hours_purchased = serializers.SerializerMethodField()


    class Meta:
        model = Client
        fields = (
            'identifier',
            'email',
            'first_name',
            'last_name',
            'hours_remaining',
            'total_hours_purchased',
            'status',
            'hours',
            'location',
            'payment',
            'payment_status'  
        )

    def get_total_hours_purchased(self, instance):
        try:
            hours_purchased = Payment.objects.filter(client=instance).aggregate(Sum('hours_purchased'))
            return hours_purchased['hours_purchased__sum']
        except Payment.DoesNotExist:
            return 0
        
    def get_hours_remaining(self, instance):
        attended = 0
        absent = 0

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

    def get_hours(self,instance):
        bookings = {}
       
        if self.context['start_date'] == None:
            start_date=datetime.date.today()-datetime.timedelta(days=30)
        else:
            start_date = self.context['start_date']

        if self.context['end_date'] == None:
            end_date=datetime.date.today()
        else:
            end_date = self.context['end_date']

        data = Booking.objects.filter(client__identifier=instance.identifier) 

        bookings['none'] = data.filter(attendance_status="none", date__range=(start_date, end_date)) \
            .values('session__duration') \
            .annotate(Sum('session__duration'))

        bookings['attended'] = data.filter(attendance_status="attended", date__range=(start_date, end_date)) \
            .values('session__duration') \
            .annotate(Sum('session__duration'))

        bookings['noshow'] = data.filter(attendance_status="noshow", date__range=(start_date, end_date)) \
            .values('session__duration') \
            .annotate(Sum('session__duration'))
        
        bookings['absent'] = data.filter(attendance_status="absent", date__range=(start_date, end_date)) \
            .values('session__duration') \
            .annotate(Sum('session__duration'))
         
        return bookings
    
    def get_payment(self,instance):
        payments = {}
        payments = Payment.objects.filter(client__identifier=instance.identifier).values() 
        return payments


class ReportSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    status = serializers.CharField()
    location = serializers.CharField()
    hours = serializers.SerializerMethodField()
    payment_status = serializers.CharField()
    payment = serializers.SerializerMethodField()
    hours_remaining = serializers.SerializerMethodField()
    total_hours_purchased = serializers.SerializerMethodField()


    class Meta:
        model = Client
        fields = (
            'identifier',
            'email',
            'first_name',
            'last_name',
            'hours_remaining',
            'total_hours_purchased',
            'status',
            'hours',
            'location',
            'payment',
            'payment_status'  
        )

    def get_total_hours_purchased(self, instance):
        try:
            hours_purchased = Payment.objects.filter(client=instance).aggregate(Sum('hours_purchased'))
            return hours_purchased['hours_purchased__sum']
        except Payment.DoesNotExist:
            return 0
        
    def get_hours_remaining(self, instance):
        attended = 0
        absent = 0

        try:
            hours_purchased = Payment.objects.filter(client=instance).aggregate(Sum('hours_purchased'))
        except Payment.DoesNotExist:
            hours_purchased = 0

        try:
            camp_attended = CampBooking.objects.filter(client=instance, attendance_status="attended").aggregate(Sum('session__duration'))
            camp_absent = CampBooking.objects.filter(client=instance, attendance_status="absent").aggregate(Sum('session__duration'))

            if camp_attended['session__duration__sum'] == None:
                attended = 0
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

    def get_hours(self,instance):
        bookings = {}
       
        if self.context['start_date'] == None:
            start_date=datetime.date.today()-datetime.timedelta(days=30)
        else:
            start_date = self.context['start_date']

        if self.context['end_date'] == None:
            end_date=datetime.date.today()
        else:
            end_date = self.context['end_date']

        data = Booking.objects.filter(client__identifier=instance.identifier) 
        bookings['none'] = data.filter(attendance_status="none", date__range=(start_date, end_date)) \
            .values('session__duration') \
            .annotate(Sum('session__duration'))

        bookings['attended'] = data.filter(attendance_status="attended", date__range=(start_date, end_date)) \
            .values('session__duration') \
            .annotate(Sum('session__duration'))

        bookings['noshow'] = data.filter(attendance_status="noshow", date__range=(start_date, end_date)) \
            .values('session__duration') \
            .annotate(Sum('session__duration'))
        
        bookings['absent'] = data.filter(attendance_status="absent", date__range=(start_date, end_date)) \
            .values('session__duration') \
            .annotate(Sum('session__duration'))
         
        return bookings
    
    def get_payment(self,instance):
        payments = {}
        payments = Payment.objects.filter(client__identifier=instance.identifier).values() 
        return payments


class StudentBookingSerializer(serializers.ModelSerializer):
    student = StudentShorterSerializer()
    client = ClientShortSerializer()
    session = UserStudentSessionSerializer()
    date = serializers.DateField()
    status = serializers.CharField()
    teaching_record = serializers.CharField()
    attendance_status =serializers.CharField()

    class Meta:
        model = Booking
        fields = (
            'identifier',
            'student',
            'session',
            'client',
            'date',
            'status',
            'teaching_record',
            'attendance_status',
        )

    def setup_eager_loading(queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('student')
        queryset = queryset.prefetch_related('session')
        queryset = queryset.prefetch_related('client')


        return queryset

    def delete(self):
        self.instance.delete()


class StudentBookingZapierSerializer(serializers.ModelSerializer):
    student = serializers.CharField(source='student.identifier')
    client = serializers.CharField(source='client.identifier')
    session = serializers.CharField(source='session.identifier')
    date = serializers.DateField()
    status = serializers.CharField()


    class Meta:
        model = Booking
        fields = (
            'identifier',
            'student',
            'session',
            'client',
            'date',
            'status',
        )

    def delete(self):
        self.instance.delete()


class CreateStudentBookingRequestSerializer(serializers.ModelSerializer):
    student = serializers.CharField()
    session = serializers.CharField()
    date = serializers.CharField(allow_blank=True, required=False)

    class Meta:
        model = Booking
        fields = (
            'student',
            'session',
            'date',
        )

    def validate(self, validated_data):
        
        return validated_data

    def create(self, validated_data):

        try:
            student = Student.objects.get(
                identifier=validated_data['student']
            )
        except Student.DoesNotExist:
            raise exceptions.NotFound()

        try:
            client = Client.objects.get(
                identifier=student.client.identifier
            )
        except Client.DoesNotExist:
            raise exceptions.NotFound()

        try:
            session = Session.objects.get(
                identifier=validated_data.get('session')
            )
        except Session.DoesNotExist:
            raise exceptions.NotFound()

        if validated_data.get('date') != None:
            date = serializers.DateField()

        booking = BookingRequest.objects.create(
                student=student,
                client=client,
                session = session,
                date = date
                )

        return booking


class UpdateStudentBookingSerializer(StudentBookingSerializer):
    student = serializers.CharField()
    session = serializers.CharField()
    date = serializers.DateField()
    status = serializers.CharField(required=False)
    status = serializers.ChoiceField(
                required=False,
                choices=ClientStatus.choices(),
                allow_blank=True)
    teaching_record = serializers.CharField(required=False)
    session_amount = serializers.IntegerField(required=False)
    attendance_status = serializers.ChoiceField(
                required=False,
                choices=AttendanceStatus.choices(),
                allow_blank=True)


    class Meta:
        model = StudentBookingSerializer.Meta.model
        fields = (
            'student',
            'session',
            'date',
            'status',
            'teaching_record',
            'session_amount',
            'attendance_status',
        )

    def validate(self, validated_data):
        
        return validated_data

    def create(self, validated_data):

        try:
            student = Student.objects.get(
                identifier=validated_data['student']
            )
        except Student.DoesNotExist:
            raise exceptions.NotFound()

        try:
            client = Client.objects.get(
                identifier=student.client.identifier
            )
        except Client.DoesNotExist:
            raise exceptions.NotFound()

        try:
            session = Session.objects.get(
                identifier=validated_data.get('session')
            )
        except Session.DoesNotExist:    
            raise exceptions.NotFound('No club or camp sessions found')

        if validated_data.get('session_amount') != None and validated_data.get('session_amount') > 0:
            validated_data['student'] = student
            validated_data['session'] = session
            validated_data['client'] = client
    
            try:
                booking = Booking.objects.create_booking(
                        validated_data.get('session_amount'),
                        validated_data,
                    )
            except: 
                raise exceptions.ValidationError(
                        {'Session': ['Creating a series of bookings caused an error']})
     
        else:
            try: 
                bookings = Booking.objects.get(
                    student=student,
                    date = validated_data.get('date')
                )
                raise exceptions.ValidationError(
                        {'Session': ['This booking already exists.']})

            except Booking.DoesNotExist:
                pass

        
            booking = Booking.objects.create(
                student=student,
                client=client,
                session = session,
                date = validated_data.get('date'),
                duration = session.duration
                )
                        
            session.bookings.add(booking)
            session.save()

       
        client.tags.add("Club")
        student.tags.add("Club")
        client.save()
        student.save()
        return booking

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            client = Client.objects.get(
                identifier=instance.client.identifier
            )
        except Client.DoesNotExist:
            raise exceptions.NotFound("Client")

        if validated_data.get('teaching_record') != None:
            instance.teaching_record = validated_data.get('teaching_record')
        else: 
            validated_data.get('teaching_record') == instance.teaching_record

        if validated_data.get('attendance_status') == None:
            instance.attendance_status = AttendanceStatus.NONE
        else:
            instance.attendance_status = validated_data.get('attendance_status')
           
        instance.save()
        return instance


class UserStudentBookingSerializer(serializers.ModelSerializer):
    student = StudentShorterSerializer()
    client = ClientShortSerializer()
    session = UserStudentSessionSerializer()
    date = serializers.DateField()
    status = serializers.CharField()
    teaching_record = serializers.CharField()
    attendance_status = serializers.CharField()

    class Meta:
        model = Booking
        fields = (
            'identifier',
            'student',
            'session',
            'client',
            'date',
            'status',
            'teaching_record',
            'attendance_status'
           
        )

    def delete(self):
       
        self.instance.delete()


class CreateUserStudentBookingSerializer(serializers.ModelSerializer):
    student = serializers.CharField()
    session = serializers.CharField()
    date = serializers.DateField()
    status = serializers.CharField(required=False)
    status = serializers.ChoiceField(
                required=False,
                choices=ClientStatus.choices(),
                allow_blank=True)  

    class Meta:
        model = Booking
        fields = (
            'student',
            'session',
            'date',
            'status',
        )

    def validate(self, validated_data):
        
        return validated_data

    def create(self, validated_data):

        try:
            student = Student.objects.get(
                identifier=validated_data['student']
            )
        except Student.DoesNotExist:
            raise exceptions.NotFound()

        try:
            client = Client.objects.get(
                identifier=student.client.identifier
            )
        except Client.DoesNotExist:
            raise exceptions.NotFound()

        try:
            session = Session.objects.get(
                identifier=validated_data.get('session')
            )
        except Session.DoesNotExist:
            raise exceptions.NotFound()

        try: 
            Session.objects.get(
                students__identifier=student.identifier,
                date = validated_data.get('date')
            )
            raise exceptions.ValidationError(
                    {'Session': ['This booking already exists.']})

        except Session.DoesNotExist:

            booking = Booking.objects.create(
                student=student,
                client=client,
                session = session,
                date = validated_data.get('date'),
                duration=session.duration
                )

        return booking


class StudentCampBookingSerializer(serializers.ModelSerializer):
    student = StudentShorterSerializer()
    client = ClientShortSerializer()
    session = ShortCampSessionSerializer()
    date = serializers.DateField()
    status = serializers.CharField()
    teaching_record = serializers.CharField()
    attendance_status =serializers.CharField()


    class Meta:
        model = CampBooking
        fields = (
            'identifier',
            'student',
            'session',
            'client',
            'date',
            'status',
            'teaching_record',
            'attendance_status',
            'lunch',
            'note',
        )

    def setup_eager_loading(queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('student')
        queryset = queryset.prefetch_related('session')
        queryset = queryset.prefetch_related('client')


        return queryset

    def delete(self):
        self.instance.delete()


class UpdateStudentCampBookingSerializer(StudentBookingSerializer):
    student = serializers.CharField()
    session = serializers.CharField()
    date = serializers.DateField()
    status = serializers.ChoiceField(
                required=False,
                choices=ClientStatus.choices(),
                allow_blank=True)
    teaching_record = serializers.CharField(required=False)
    session_amount = serializers.IntegerField(required=False)
    attendance_status = serializers.ChoiceField(
                required=False,
                choices=AttendanceStatus.choices(),
                allow_blank=True)
    lunch = serializers.BooleanField(required=False)
    note = serializers.CharField(required=False)


    class Meta:
        model = StudentBookingSerializer.Meta.model
        fields = (
            'student',
            'session',
            'date',
            'status',
            'teaching_record',
            'session_amount',
            'attendance_status',
            'lunch',
            'note',
        )

    def validate(self, validated_data):
        
        return validated_data

    def create(self, validated_data):

        try:
            student = Student.objects.get(
                identifier=validated_data['student']
            )
        except Student.DoesNotExist:
            raise exceptions.NotFound()

        try:
            client = Client.objects.get(
                identifier=student.client.identifier
            )
        except Client.DoesNotExist:
            raise exceptions.NotFound()

        try:
            session = CampSession.objects.get(
                identifier=self.context['session']
            )
        except CampSession.DoesNotExist:    
            raise exceptions.NotFound('No club or camp sessions found')

        if validated_data.get('session_amount') != None and validated_data.get('session_amount') > 0:
            
            validated_data['student'] = student
            validated_data['session'] = session
            validated_data['client'] = client
            try:
                booking = CampBooking.objects.create_booking(
                        validated_data.get('session_amount'),
                        validated_data,
                    )
            except: 
                raise exceptions.ValidationError(
                        {'Session': ['Creating a series of bookings caused an error']})
        else:

            booking = CampBooking.objects.create(
                student=student,
                client=client,
                session = session,
                date = validated_data.get('date'),
                lunch = validated_data.get('lunch'),
                note = validated_data.get('note')
                )
                        
            session.bookings.add(booking)
            session.save()
        client.tags.add("Camp")
        student.tags.add("Camp")
        client.save()
        student.save()
        return booking

    @transaction.atomic
    def update(self, instance, validated_data):

        if validated_data.get('teaching_record') != None:
            instance.teaching_record = validated_data.get('teaching_record')
        else: 
            validated_data.get('teaching_record') == instance.teaching_record

        if validated_data.get('attendance_status') != None:
            instance.attendance_status = validated_data.get('attendance_status')

        if validated_data.get('lunch') != None:
            instance.lunch = validated_data.get('lunch')
        
        if validated_data.get('note') != None:
            instance.lunch = validated_data.get('note')
        
        if instance.date < datetime.datetime.now().date() :
            instance.status = BookingStatus.INACTIVE

        instance.save()

        return instance


class AdminBranchSerializer(serializers.ModelSerializer):
    description = serializers.CharField()
    short_id = serializers.CharField()
    name = serializers.CharField()
    enrollments = serializers.IntegerField()
    active_students = serializers.IntegerField()
    inactive_students = serializers.IntegerField()
    identifier = serializers.UUIDField(read_only=True)


    class Meta:
        model = Branch
        fields = (
            'description',
            'short_id',
            'name',
            'enrollments',
            'active_students',
            'inactive_students',    
            'identifier'       
        )

    def delete(self):
        self.instance.delete()


class AdminBranchCreateSerializer(serializers.ModelSerializer):
    description = serializers.CharField()
    short_id = serializers.CharField()
    name = serializers.CharField()
    enrollments = serializers.IntegerField(required=False)
    active_students = serializers.IntegerField(required=False)
    inactive_students = serializers.IntegerField(required=False)
    identifier = serializers.UUIDField(read_only=True)

    class Meta:
        model = Branch
        fields = (
            'description',
            'short_id',
            'name',
            'enrollments',
            'active_students',
            'inactive_students',    
            'identifier',       
        )
        read_only_fields = ('identifier', 'updated',)


    def delete(self):
        self.instance.delete()

class GroupSerializer(serializers.ModelSerializer):    
    class Meta:
        model = Group
        fields = ('name',)

class UserSerializer(DateSerializer):
    role = serializers.ChoiceField(
        required=False,
        source='role.value',
        choices=Role.choices())
    client = ClientSerializer()
    teacher = TeacherSerializer()
    staff = StaffSerializer()
    groups = GroupSerializer(many=True)
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'created', 'updated', 'role', 'client', 'teacher','staff','groups')
        read_only_field = ('created', 'updated',)

    def validate(self, validated_data):
        return validated_data


class UserUpdateSerializer(DateSerializer):
    role = serializers.ChoiceField(
        required=False,
        source='role.value',
        choices=Role.choices())
    client = serializers.CharField()
    teacher = serializers.CharField(source='teacher.identifer')
    staff = serializers.CharField()
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'created', 'updated', 'role', 'client', 'teacher','staff')
        read_only_field = ('created', 'updated',)


class TokenSerializer(serializers.Serializer):
    token = serializers.CharField()
    user = UserSerializer()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(required=False, allow_blank=True,
        max_length=50, write_only=True)
    last_name = serializers.CharField(required=False, allow_blank=True,
        max_length=50, write_only=True)
    password1 = serializers.CharField(required=True, write_only=True,
        max_length=128, style={'input_type': 'password'})
    password2 = serializers.CharField(required=True, write_only=True,
        max_length=128, style={'input_type': 'password'})
    role = serializers.ChoiceField(
        required=False,
        choices=Role.choices())
    client = serializers.CharField(required=False,max_length=50)

    def validate_email(self, email):
        return get_adapter().clean_email(email)

    def validate_password1(self, password):
        return get_adapter().clean_password(password)

    def validate(self, validated_data):
        email = validated_data.get('email')
        password1 = validated_data.get('password1')
        password2 = validated_data.get('password2')

        if password1 != password2:
            raise serializers.ValidationError(
                {"non_field_errors": [
                    _("The two password fields don't match.")]})

        # Further email address validation related to the company.
        if EmailAddress.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                {"email": [_("A user is already registered "
                             "with this email address.")]})

        return validated_data

    def save(self, request):
        
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.validated_data
        adapter.save_user(request, user, self)
        setup_user_email(request, user, [])
        try:
            user.role = request.data['role']
        except Exception as exc:
            user.role = Role.PARENT

        try: 
            client = request.data['client']
        except Exception as exc:
            client = ''

        
        if(client):
            try:
                client = Client.objects.get(
                    identifier=client,
                    )
                user.client = client

            except Client.DoesNotExist:
                raise exceptions.NotFound()

        user.save()
        
        return user


class UserRegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(required=False, allow_blank=True,
        max_length=50, write_only=True)
    last_name = serializers.CharField(required=False, allow_blank=True,
        max_length=50, write_only=True)
    password1 = serializers.CharField(required=True, write_only=True,
        max_length=128, style={'input_type': 'password'})
    password2 = serializers.CharField(required=True, write_only=True,
        max_length=128, style={'input_type': 'password'})
    role = serializers.ChoiceField(
        required=False,
        choices=Role.choices())

    def validate_email(self, email):
        return get_adapter().clean_email(email)

    def validate_password1(self, password):
        return get_adapter().clean_password(password)

    def validate(self, validated_data):
        email = validated_data.get('email')
        password1 = validated_data.get('password1')
        password2 = validated_data.get('password2')

        if password1 != password2:
            raise serializers.ValidationError(
                {"non_field_errors": [
                    _("The two password fields don't match.")]})

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                {"email": [_("A user is already registered "
                             "with this email address.")]})

        return validated_data

    def save(self, request):
        
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.validated_data
        adapter.save_user(request, user, self)
        try:
            user.role = request.data['role']
        except Exception as exc:
            user.role = Role.PARENT

        try: 
            client = request.data['client']
        except Exception as exc:
            client = ''
        try: 
            teacher = request.data['teacher']
        except Exception as exc:
            teacher = ''
        try: 
            staff = request.data['staff']
        except Exception as exc:
            staff = ''
    
        if(client):
            user.client = client
            my_group = Group.objects.get(name='Parent') 
            my_group.user_set.add(user)

        if(teacher):
            user.teacher = teacher
            my_group = Group.objects.get(name='Teacher') 
            my_group.user_set.add(user)
        
        if(staff):
            user.staff = staff
            my_group = Group.objects.get(name='Staff') 
            my_group.user_set.add(user)

        user.save()
        
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=True, allow_blank=False)
    password = serializers.CharField(max_length=128,
        style={'input_type': 'password'})

    def _validate_user(self, email, password):
        user = None

        if email and password:
            user = authenticate(email=email, password=password)
        else:
            raise serializers.ValidationError(
                {"non_field_errors": [
                    _('Must include "email" and "password".')
                ]}
            )

        return  user

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        user = self._validate_user(email, password)

        if user:
            if not user.is_active:
                raise serializers.ValidationError(
                    {"non_field_errors": [_('User account is disabled.')]})
        else:
            raise serializers.ValidationError(
                {"non_field_errors": [
                    _('Unable to log in with provided credentials.')
                ]})

        # If required, is the email verified?
        if 'rest_auth.registration' in settings.INSTALLED_APPS:
            if (app_settings.EMAIL_VERIFICATION
                    == app_settings.EmailVerificationMethod.MANDATORY):
                email_address = user.emailaddress_set.get(email=user.email)
                if not email_address.verified:
                    raise serializers.ValidationError(
                        {"user": [_('Email is not verified.')]})

        attrs['user'] = user
        return attrs


class LogoutSerializer(serializers.Serializer):
    pass


class PasswordChangeSerializer(DefaultPasswordChangeSerializer):
    """
    Override the default serializer in order to mask the password fields.
    """
    old_password = serializers.CharField(
        max_length=128, style={'input_type': 'password'})
    new_password1 = serializers.CharField(
        max_length=128, style={'input_type': 'password'})
    new_password2 = serializers.CharField(
        max_length=128, style={'input_type': 'password'})


class PasswordResetSerializer(DefaultPasswordResetSerializer):
    password_reset_form_class = PasswordResetForm


class PasswordResetConfirmSerializer(DefaultPasswordResetConfirmSerializer):
    """
    Override the default serializer in order to mask the password fields.
    """
    new_password1 = serializers.CharField(
        max_length=128, style={'input_type': 'password'})
    new_password2 = serializers.CharField(
        max_length=128, style={'input_type': 'password'})


class ResendVerifyEmailSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)


class VerifyEmailSerializer(serializers.Serializer):
    key = serializers.CharField(required=True)
