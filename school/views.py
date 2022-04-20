import uuid
import requests 
import csv

from collections import OrderedDict
from functools import partial

from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import exceptions, status, filters
from allauth.account.models import EmailAddress
from allauth.account.utils import complete_signup
from allauth.account.models import EmailConfirmation, EmailConfirmationHMAC
from allauth.account import app_settings as allauth_settings
from knox.auth import TokenAuthentication
from knox.models import AuthToken
from django.contrib.auth import login as django_login, logout as django_logout
from django.utils import timezone
from django.db.models import Q, Avg, Count
from django.forms.models import model_to_dict
from django.http import HttpResponse


from school import signals

from school.pagination import ResultsSetPagination

from config import settings
from school.models import *
from school.serializers import * 
from school.authentication import AdminAuthentication, UserAuthentication
from school.permissions import *
from school.pagination import *
from school.enums import Role
from school.filters import AdminStudentFilterSet, AdminClientFilterSet
from school.common import get_student_hours, get_client_hours, get_client_hours_penalty

from logging import getLogger
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from taggit.models import Tag



logger = getLogger('django')


def export_student_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students.csv"'

    writer = csv.writer(response)
    writer.writerow(['student_id', 
            'Student First Name', 
            'Student Last Name', 
            'Birth Date',
            'Medical Condition',
            'Language',
            'Client First Name',
            'Client Last Name',
            'Client Email'])

    students = Student.objects.all().values_list(
            'student_id', 
            'first_name', 
            'last_name', 
            'birth_date',
            'medical_condition',
            'language',
            'client__first_name',
            'client__last_name',
            'client__email')

    for student in students:
        writer.writerow(student)

    return response

def export_clients_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="clients.csv"'

    writer = csv.writer(response)
    writer.writerow([
            'Client First Name', 
            'Client Last Name', 
            'Client Email', 
            'Client Phone', 
            'Payment Status',
            'Language',
            'Hours Purchased',
            'Hours Remaining'])

    clients = Client.objects.all().values(
            'identifier',
            'first_name', 
            'last_name', 
            'email',
            'phone',
            'payment_status',
            'language').annotate(Sum('payment__hours_purchased'))

    for client in clients:
        client['hours_remaining'] = get_client_hours(Client.objects.get(identifier=client['identifier']))

        writer.writerow([
            client['first_name'], 
            client['last_name'],
            client['email'],
            client['phone'],
            client['payment_status'],
            client['language'],
            client['payment__hours_purchased__sum'],
            client['hours_remaining']
             ])

    return response

def export_bookings_csv(request, *args, **kwargs):
    params = request.GET
    
    try:
        if params['start_date']:
            start_date = request.GET['start_date']
    except:
        start_date=datetime.date.today()-datetime.timedelta(days=30)

    try:
        if params['end_date']:
            end_date = request.GET['end_date']

    except:
        end_date=datetime.date.today()
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="bookings.csv"'

    writer = csv.writer(response)
    writer.writerow([
            'Student ID', 
            'Student First Name', 
            'Student Last Name', 
            'Student First Name', 
            'Student Last Name',
            'Client Email', 
            'Duration', 
            'Location',
            'Time',
            'Date',
            'Club',
            'Teacher',
            'Teaching Record',
            'Attendance Status'])

    try:
        bookings = Booking.objects.filter(date__range=(start_date, end_date)).values_list(
                'student__student_id', 
                'student__first_name',
                'student__last_name',
                'client__first_name', 
                'client__last_name', 
                'client__email', 
                'session__duration',
                'session__location',
                'session__time',
                'date',
                'session__club',
                'session__teacher__email',
                'teaching_record',
                'attendance_status')
    except:
        return HttpResponse('Date Error')


    for booking in bookings:
        writer.writerow(booking)

    return response


@api_view(['GET'])
@permission_classes([AllowAny, ])
def root(request, format=None):
    return Response(
        [
            {'Admin': OrderedDict([
                ('Register', reverse('school:admin-register',
                    request=request,
                    format=format)),
                ('Login', reverse('school:admin-login',
                    request=request,
                    format=format)),
                ('Logout', reverse('school:admin-logout',
                    request=request,
                    format=format)),
                ('Password Change', reverse('school:admin-password-change',
                    request=request,
                    format=format)),
                ('Password Reset', reverse('school:admin-password-reset',
                    request=request,
                    format=format)),
                ('Booking', reverse('school:admin-booking-view',
                    request=request,
                    format=format)),
                ('Student', reverse('school:admin-students-view',
                    request=request,
                    format=format)),
                ('Client', reverse('school:admin-parent-view',
                    request=request,
                    format=format)),
                ('Teacher', reverse('school:admin-teacher-list',
                    request=request,
                    format=format)),    
                ('Club Session', reverse('school:admin-session-list',
                    request=request,
                    format=format)),
                ('Camp Session', reverse('school:admin-campsession-list',
                    request=request,
                    format=format)),
                ('Trial Session', reverse('school:admin-trialsession-list',
                    request=request,
                    format=format)),
                ('Student Index', reverse('school:admin-students-index',
                    request=request,
                    format=format)),
                ('Client Index', reverse('school:admin-clients-index',
                    request=request,
                    format=format)),
                ('Teacher Index', reverse('school:admin-teacher-index',
                    request=request,
                    format=format)),
                    
                    
            ])},
            {'User': OrderedDict([
                ('Register', reverse('school:user-register',
                    request=request,
                    format=format)),
                ('Login', reverse('school:user-login',
                    request=request,
                    format=format)),
                ('Logout', reverse('school:user-logout',
                    request=request,
                    format=format)),
                ('Password Change', reverse('school:user-password-change',
                    request=request,
                    format=format)),
                ('Password Reset', reverse('school:user-password-reset',
                    request=request,
                    format=format)),
                ('User', reverse('school:user-view',
                    request=request,
                    format=format)),
                ('Booking', reverse('school:user-booking-view',
                    request=request,
                    format=format)),
                    
            ])},
        ])


class ListModelMixin(object):
    """
    List a queryset.
    """

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({'status': 'success', 'data': serializer.data})


class ListAPIView(ListModelMixin,
                  GenericAPIView):
    """
    Concrete view for listing a queryset.
    """

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class RegisterView(GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny, )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save(request)
        token = AuthToken.objects.create(user=user)

        if user.role == Role.ADMIN or user.role == Role.TEACHER:
            from django.core.mail import send_mail
            from django.contrib.sites.shortcuts import get_current_site 

            context = {"current_site": get_current_site(self.request),
                        "user": user,
                        "url": 'https://admin.usersprojects.com/',
                        "request": self.request}
            get_adapter(self.request).send_mail('account/email/email_admin_confirmation',user.email,context)
        else:
            complete_signup(
            self.request._request,
            user,
            allauth_settings.EMAIL_VERIFICATION,
            None
        )

        return Response(
            {'status': 'success',
             'data': TokenSerializer({'user': user, 'token': token}).data},
            status=status.HTTP_201_CREATED
        )


class UserRegisterView(GenericAPIView):
    serializer_class = UserRegisterSerializer
    permission_classes = (AllowAny, )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save(request)
        token = AuthToken.objects.create(user=user)

        complete_signup(
            self.request._request,
            user,
            allauth_settings.EMAIL_VERIFICATION,
            None
        )

        return Response(
            {'status': 'success',
             'data': TokenSerializer({'user': user, 'token': token}).data},
            status=status.HTTP_201_CREATED
        )


class LoginView(GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        request = request
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer_class = TokenSerializer
        user = serializer.validated_data.get('user')

        # Before we create a new token, delete any other that might not have
        # been deleted because tokens are created on session login
        AuthToken.objects.exclude(expires=None)\
            .filter(user=user, expires__lt=timezone.now()).delete()
        token = AuthToken.objects.create(user=user)

        if getattr(settings, 'REST_SESSION_LOGIN', True):
            django_login(request, user)
        else:
            user_logged_in.send(sender=user.__class__, request=request,
                                user=user, token_key=token.token_key)

        serializer = serializer_class(instance={'user': user, 'token': token},
                                      context={'request': self.request})
        logger.info("user "+ user.email +" logged in")

        return Response({'status': 'success', 'data': serializer.data},
                        status=status.HTTP_200_OK)


class LogoutView(GenericAPIView):
    serializer_class = LogoutSerializer

    def post(self, request, *args, **kwargs):
        if hasattr(request.successful_authenticator, 'auth_class'):
            is_token_authenticated = (
                issubclass(request.successful_authenticator.auth_class, TokenAuthentication),
                request.auth is not None
            )
        else:
            is_token_authenticated = (
                isinstance(request.successful_authenticator, TokenAuthentication),
                request.auth is not None
            )

        if all(is_token_authenticated):
            if request._auth.expires is not None:
                request._auth.delete()
            user_logged_out.send(sender=request.user.__class__,
                                 request=request, user=request.user)
        else:
            django_logout(request)

        return Response(
            {"status": 'success'},
            status=status.HTTP_200_OK
        )


class PasswordChangeView(GenericAPIView):
    serializer_class = PasswordChangeSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": 'success'})


class PasswordResetView(GenericAPIView):
    serializer_class = PasswordResetSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": 'success'}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": 'success'})


class ResendVerifyEmailView(GenericAPIView):
    allowed_methods = ('POST',)
    serializer_class = ResendVerifyEmailSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')

        try:
            user = EmailAddress.objects.get(email__iexact=email).user
        except EmailAddress.DoesNotExist:
            # Do not inform a user about the existence oemail__iexactf an email.
            # Return "success" regardless of an actual email getting sent.
            return Response({'status': 'success'})

        try:
            from allauth.account.utils import send_email_confirmation
            send_email_confirmation(request._request, user, signup=True)
            
        except Exception as exc:
            logger.exception(exc)
            raise exceptions.ValidationError({'non_field_errors':
                ['Error sending the verification email.']})

        return Response({'status': 'success'})


class VerifyEmailView(GenericAPIView):
    allowed_methods = ('POST',)
    serializer_class = VerifyEmailSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        key = request.data.get('key')

        if not key:
            raise exceptions.ValidationError(
                {'key': ['The key is invalid.']})

        # Get HMAC confirmation
        emailconfirmation = EmailConfirmationHMAC.from_key(key)

        # Alternatively, get normal confirmation
        if not emailconfirmation:
            try:
                queryset = EmailConfirmation.objects.all_valid()
                emailconfirmation = queryset.get(key=key.lower())
            except AttributeError:
                raise exceptions.ValidationError(
                    {'key': ['The key is invalid.']})
            except EmailConfirmation.DoesNotExist:
                raise exceptions.ValidationError(
                    {'key': ['The key is invalid or has expired.']})

        emailconfirmation.confirm(self.request)
        return Response({'status': 'success'})


class AdminReportView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = ClientReportSerializer  
    
    def get_serializer_context(self):
        return {"start_date": self.request.query_params.get('start_date'),
                "end_date": self.request.query_params.get('end_date')}

    def get_queryset(self, **kwargs):
        queryset = Client.objects.filter().order_by('-updated')
        student = self.request.query_params.get('student')
        client = self.request.query_params.get('client')
        session = self.request.query_params.get('session')

        if student:
            queryset = queryset.filter(student__identifier=student)
        if client:
            queryset = queryset.filter(client__identifier=client)
        if session:
            queryset = queryset.filter(session__identifier=session)
        
        return queryset


class AdminReportTotalView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = ReportSerializer  

    def get_queryset(self, **kwargs):
        queryset = Booking.objects.filter().order_by('-updated')
        queryset.hours = 'one'


        return queryset


class AdminClubCreateView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = ClubSerializer    

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateClubSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        return Club.objects.filter(
        ).order_by('-created')

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success', 'data': ClubSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminClubView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = ClubSerializer  

    def delete(self, request, *args, **kwargs):
        try:
            club = Club.objects.get(
                identifier=kwargs['id']
            )
        except Club.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(club)
        instance = serializer.delete()
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            club = Club.objects.get(
                identifier=str(kwargs['id']),
            )
        except Club.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(club)
        return Response({'status': 'success', 'data': serializer.data})

    def patch(self, request, *args, **kwargs):
        try:
            club = Club.objects.get(
                identifier=kwargs['id'],
            )
        except Club.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(
            club, 
            data=request.data,
            partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success',
             'data': ClubSerializer(instance).data}
        )


class AdminStudentClubCreateView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = StudentClubSerializer    

    def get_serializer_context(self):
        return {"student": self.kwargs['id']}

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateStudentClubSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        return StudentClub.objects.filter(
            student__identifier=self.kwargs['id']
        ).order_by('-created')

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success', 'data': StudentClubSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminStudentClubView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = StudentClubSerializer  

    def delete(self, request, *args, **kwargs):
        try:
            club = StudentClub.objects.get(
                identifier=kwargs['club']
            )
        except StudentClub.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(club)
        instance = serializer.delete()
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            club = StudentClub.objects.get(
                identifier=str(kwargs['club']),
            )
        except StudentClub.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(club)
        return Response({'status': 'success', 'data': serializer.data})

    def patch(self, request, *args, **kwargs):
        try:
            club = StudentClub.objects.get(
                identifier=kwargs['club'],
            )
        except StudentClub.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(
            club, 
            data=request.data,
            partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success',
             'data': StudentClubSerializer(instance).data}
        )


class AdminBadgeAdd(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = StudentClubSerializer    

    def get_serializer_context(self):
        return {"club": self.kwargs['club'],
                "student": self.kwargs['id']}

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AddBadgeSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        return StudentClub.objects.filter(
            identifier=self.kwargs['club']
        ).order_by('-created')

    def post(self, request, *args, **kwargs):
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        return Response(
            {'status': 'success', 'data': ClubSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminBadgeCreateView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = BadgeSerializer    

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateBadgeSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        return Badge.objects.filter(
            club__identifier=self.kwargs['id']
        ).order_by('-created')

    def post(self, request, *args, **kwargs):
        request.data['club'] = kwargs['id']
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success', 'data': BadgeSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminBadgeView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = BadgeSerializer  

    def delete(self, request, *args, **kwargs):
        try:
            badge = Badge.objects.get(
                identifier=kwargs['id']
            )
        except Badge.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(badge)
        instance = serializer.delete()
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            badge = Badge.objects.get(
                identifier=str(kwargs['id']),
            )
        except Badge.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(badge)
        return Response({'status': 'success', 'data': serializer.data})

    def patch(self, request, *args, **kwargs):
        try:
            badge = Badge.objects.get(
                identifier=kwargs['id'],
            )
        except Badge.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(
            badge, 
            data=request.data,
            partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success',
             'data': BadgeSerializer(instance).data}
        )


class AdminStudentCreateView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = StudentSerializer  
    pagination_class = ResultsSetPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateStudentSerializer
        return super().get_serializer_class()

    def get_queryset(self):

        queryset = Student.objects.filter().order_by('-updated')
        queryset = self.get_serializer_class().setup_eager_loading(queryset)
        first_name = self.request.query_params.get('first_name')
        last_name = self.request.query_params.get('last_name')
        club = self.request.query_params.get('club')
        student_id = self.request.query_params.get('student_id')

        if first_name:
            queryset = queryset.filter(first_name__icontains=first_name)
        if last_name:
            queryset = queryset.filter(last_name__icontains=last_name)
        if club:
            try:
                queryset = queryset.filter(clubs__name__icontains=club)
            except: 
                queryset = queryset
        if student_id:
            queryset = queryset.filter(student_id__icontains=student_id)

        return queryset

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        logger.info("user: " + str(request.user) + " added student" + str(instance.student_id) +"at"+ str(datetime.datetime.now()))

        return Response(
            {'status': 'success', 'data': StudentSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminStudentList(ListAPIView):
    allowed_methods = ('GET')
    serializer_class = StudentIndexSerializer  

    def get_queryset(self):

        queryset = Student.objects.filter().order_by('-updated')
        first_name = self.request.query_params.get('first_name')
        last_name = self.request.query_params.get('last_name')
        club = self.request.query_params.get('club')
        student_id = self.request.query_params.get('student_id')

        if first_name:
            queryset = queryset.filter(first_name__icontains=first_name)
        if last_name:
            queryset = queryset.filter(last_name__icontains=last_name)
        if student_id:
            queryset = queryset.filter(student_id__icontains=student_id)

        return queryset

    
class AdminStudentView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = StudentSerializer  

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return UpdateStudentSerializer
        return super().get_serializer_class()

    def delete(self, request, *args, **kwargs):
        try:
            student = Student.objects.get(
                identifier=kwargs['id']
            )
        except Student.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(student)
        instance = serializer.delete()
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            student = Student.objects.get(
                identifier=str(kwargs['id']),
            )
        except Student.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(student)
        return Response({'status': 'success', 'data': serializer.data })

    def patch(self, request, *args, **kwargs):
        try:
            student = Student.objects.get(
                identifier=str(kwargs['id']),
            )
        except Student.DoesNotExist:
            raise exceptions.NotFound()

        if request.data.get('client')!=None:
            try:
                request.data['client'] = Client.objects.get(
                    identifier=request.data.get('client')
                ).id
            except Client.DoesNotExist:
                raise exceptions.NotFound()

        serializer = self.get_serializer(
            student, 
            data=request.data,
            partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success',
             'data': StudentSerializer(instance).data}
        )


class CreateAdminBookingView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = StudentBookingSerializer 
   
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UpdateStudentBookingSerializer
        return super().get_serializer_class()

    def get_queryset(self, **kwargs):
        queryset = Booking.objects.filter().order_by('-updated')
        queryset = self.get_serializer_class().setup_eager_loading(queryset)
        student_id = self.request.query_params.get('student_id')
        client_first_name = self.request.query_params.get('client_first_name')
        student_first_name = self.request.query_params.get('student_first_name')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        session = self.request.query_params.get('session')


        if student_id:
            queryset = queryset.filter(student__student_id__icontains=student_id)
        if start_date and end_date:
            queryset = queryset.filter(date__range=[start_date, end_date])
        if client_first_name:
            queryset = queryset.filter(client__first_name__icontains=client_first_name)
        if student_first_name:
            queryset = queryset.filter(client__first_name__icontains=student_first_name)
        if session:
            queryset = queryset.filter(session__identifier=session)
           
        return queryset

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        logger.info("user: " + str(request.user) + " added booking" + str(instance.identifier) +"at"+ str(datetime.datetime.now()))

        return Response(
            {'status': 'success', 'data': StudentBookingSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminBookingView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = StudentBookingSerializer  

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return UpdateStudentBookingSerializer
        return super().get_serializer_class()

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        try:
            booking = Booking.objects.get(
                identifier=self.kwargs['booking']
            )
        except Booking.DoesNotExist:
            raise exceptions.NotFound('Booking not found')

        try:
            session = Session.objects.get(
                identifier=booking.session.identifier
            )
        except Booking.DoesNotExist:
            raise exceptions.NotFound('Session not found')

        try:
            student = Student.objects.get(
                identifier= booking.student.identifier
            )
        except Student.DoesNotExist:
            raise exceptions.NotFound('Student not found')

        try: 
            count = Session.objects.filter(
                    identifier=booking.session.identifier,
                    students__identifier=student.identifier
                ).count()
            if count <= 1: 
                session.student_amount = session.student_amount - 1
        except Session.DoesNotExist:
            raise exceptions.NotFound("Session not found")
        
        session.bookings.remove(booking)
        session.save()
        
        if booking.attendance_status == AttendanceStatus.ATTENDED:
            booking.client.hours_remaining =  booking.client.hours_remaining + booking.session.duration
            student.hours = student.hours - booking.session.duration
        elif booking.attendance_status == AttendanceStatus.NOSHOW:
            booking.client.hours_remaining =  booking.client.hours_remaining + booking.session.duration
        elif booking.attendance_status == AttendanceStatus.ABSENT:
            booking.client.hours_remaining =  booking.client.hours_remaining + booking.session.duration/2
            student.hours = student.hours - booking.session.duration/2

        booking.client.save()
        student.save()

        serializer = self.get_serializer(booking)
        instance = serializer.delete()
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            booking = Booking.objects.get(
                identifier=self.kwargs['booking']
            )
        except Booking.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(booking)
        return Response({'status': 'success', 'data': serializer.data})

    def patch(self, request, *args, **kwargs):
        try:
            booking = Booking.objects.get(
                identifier=self.kwargs['booking'],
            )
        except Booking.DoesNotExist:
            raise exceptions.NotFound()

        request.data['student'] = str(booking.student.identifier)
        
        serializer = self.get_serializer(
            booking, 
            data=request.data,
            partial=True)

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        logger.info("user: " + str(request.user) + "  updated booking  " + str(instance.identifier) +"at"+ str(datetime.datetime.now()))

        return Response(
            {'status': 'success',
             'data': StudentBookingSerializer(instance).data}
        )


class CreateAdminCampBookingView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = StudentCampBookingSerializer 
   
    def get_serializer_context(self):
        return {"session": self.kwargs['session_id']}

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UpdateStudentCampBookingSerializer
        return super().get_serializer_class()

    def get_queryset(self, **kwargs):
        queryset = CampBooking.objects.filter(session__identifier=self.kwargs['session_id']).order_by('-updated')
        queryset = self.get_serializer_class().setup_eager_loading(queryset)

        student_id = self.request.query_params.get('student_id')
        client_first_name = self.request.query_params.get('client_first_name')
        student_first_name = self.request.query_params.get('student_first_name')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        session = self.request.query_params.get('session')


        if student_id:
            queryset = queryset.filter(student__student_id__icontains=student_id)
        if start_date and end_date:
            queryset = queryset.filter(date__range=[start_date, end_date])
        if client_first_name:
            queryset = queryset.filter(client__first_name__icontains=client_first_name)
        if student_first_name:
            queryset = queryset.filter(client__first_name__icontains=student_first_name)
        if session:
            queryset = queryset.filter(session__identifier=session)
           
        return queryset

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        logger.info("user: " + str(request.user) + " added camp booking" + str(instance.identifier) +"at"+ str(datetime.datetime.now()))

        return Response(
            {'status': 'success', 'data': StudentCampBookingSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminCampBookingView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = StudentCampBookingSerializer  

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return UpdateStudentCampBookingSerializer
        return super().get_serializer_class()

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        try:
            booking = CampBooking.objects.get(
                identifier=self.kwargs['booking']
            )
        except CampBooking.DoesNotExist:
            raise exceptions.NotFound('Booking not found')

        try:
            session = CampSession.objects.get(
                identifier=booking.session.identifier
            )
        except CampSession.DoesNotExist:
            raise exceptions.NotFound('Session not found')

        try:
            student = Student.objects.get(
                identifier= booking.student.identifier
            )
        except Student.DoesNotExist:
            raise exceptions.NotFound('Student not found')

        try: 
            count = CampSession.objects.filter(
                    identifier=booking.session.identifier,
                    students__identifier=student.identifier
                ).count()
            if count <= 1: 
                session.student_amount = session.student_amount - 1
        except CampSession.DoesNotExist:
            raise exceptions.NotFound("Session not found")
        
        session.bookings.remove(booking)
        session.save()
        
        if booking.attendance_status == AttendanceStatus.ATTENDED:
            booking.client.hours_remaining =  booking.client.hours_remaining + booking.session.duration
            student.hours = student.hours - booking.session.duration
        elif booking.attendance_status == AttendanceStatus.NOSHOW:
            booking.client.hours_remaining =  booking.client.hours_remaining + booking.session.duration
        elif booking.attendance_status == AttendanceStatus.ABSENT:
            booking.client.hours_remaining =  booking.client.hours_remaining + booking.session.duration/2
            student.hours = student.hours - booking.session.duration/2

        booking.client.save()
        student.save()

        serializer = self.get_serializer(booking)
        instance = serializer.delete()
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            booking = CampBooking.objects.get(
                identifier=self.kwargs['booking_id']
            )
        except CampBooking.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(booking)
        return Response({'status': 'success', 'data': serializer.data})

    def patch(self, request, *args, **kwargs):
        try:
            booking = CampBooking.objects.get(
                identifier=self.kwargs['booking_id'],
            )
        except CampBooking.DoesNotExist:
            raise exceptions.NotFound()

        request.data['student'] = str(booking.student.identifier)
        
        serializer = self.get_serializer(
            booking, 
            data=request.data,
            partial=True)

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success',
             'data': StudentCampBookingSerializer(instance).data}
        )


class AdminCampWeekCreateView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = CampWeekSerializer  
    pagination_class = ResultsSetPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateCampWeekSerializer
        return super().get_serializer_class()

    def get_queryset(self):

        queryset = CampWeek.objects.filter(camp__identifier=self.kwargs['id']).order_by('-updated')
        

        return queryset

    def post(self, request, *args, **kwargs):
        request.data['camp'] = self.kwargs['id']
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        return Response(
            {'status': 'success', 'data': CampWeekSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminStudentBookingView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = StudentBookingSerializer  

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return UpdateStudentBookingSerializer
        return super().get_serializer_class()

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        try:
            booking = Booking.objects.get(
                identifier=self.kwargs['booking']
            )
        except Booking.DoesNotExist:
            raise exceptions.NotFound()

        try:
            session = Session.objects.get(
                identifier=booking.session.identifier
            )
        except Booking.DoesNotExist:
            raise exceptions.NotFound('Session not found')

        session.bookings.remove(booking)
        session.save()

        serializer = self.get_serializer(booking)
        instance = serializer.delete()
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            booking = Booking.objects.get(
                identifier=self.kwargs['booking']
            )
        except Booking.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(booking)
        return Response({'status': 'success', 'data': serializer.data})

    def patch(self, request, *args, **kwargs):
        try:
            booking = Booking.objects.get(
                identifier=self.kwargs['booking'],
            )
        except Booking.DoesNotExist:
            raise exceptions.NotFound()

      
        request.data['student'] = kwargs['id']
        
        serializer = self.get_serializer(
            booking, 
            data=request.data,
            partial=True)

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success',
             'data': StudentBookingSerializer(instance).data}
        )


class CreateAdminClientNoteView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = ClientNoteSerializer 

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateClientNoteSerializer
        return super().get_serializer_class()

    def get_queryset(self, **kwargs):
        try:
            client = Client.objects.get(
                identifier=self.kwargs['id']
            )
        except Client.DoesNotExist:
            raise exceptions.NotFound()

        return client.note.order_by('-created')

    def post(self, request, *args, **kwargs):
        request.data['user']=str(request.user)
        request.data['client']=kwargs['id']
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success', 'data': ClientNoteSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminClientNoteView(GenericAPIView):
    allowed_methods = ('GET', 'DELETE')
    serializer_class = ClientNoteSerializer  

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return CreateClientNoteSerializer
        return super().get_serializer_class()

    def delete(self, request, *args, **kwargs):
        try:
            note = ClientNote.objects.get(
                identifier=kwargs['note_id']
            )
        except ClientNote.DoesNotExist:
            raise exceptions.NotFound()

        try:
            client = Client.objects.get(
                identifier=kwargs['id']
            )
        except Client.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(note)
        instance = serializer.delete()

        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            note = ClientNote.objects.get(
                identifier=kwargs['note_id']
            )
        except ClientNote.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(note)
        return Response({'status': 'success', 'data': serializer.data})


class CreateAdminStudentNoteView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = StudentNoteSerializer 

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateStudentNoteSerializer
        return super().get_serializer_class()

    def get_queryset(self, **kwargs):
        try:
            student = Student.objects.get(
                identifier=self.kwargs['id']
            )
        except Student.DoesNotExist:
            raise exceptions.NotFound()

        return student.note.order_by('-created')

    def post(self, request, *args, **kwargs):
        request.data['user']=str(request.user)
        request.data['student']=kwargs['id']
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success', 'data': StudentNoteSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminStudentNoteView(GenericAPIView):
    allowed_methods = ('GET', 'DELETE')
    serializer_class = StudentNoteSerializer  

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return CreateStudentNoteSerializer
        return super().get_serializer_class()

    def delete(self, request, *args, **kwargs):
        try:
            note = StudentNote.objects.get(
                identifier=kwargs['note_id']
            )
        except StudentNote.DoesNotExist:
            raise exceptions.NotFound()

        try:
            client = Student.objects.get(
                identifier=kwargs['id']
            )
        except Student.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(note)
        instance = serializer.delete()

        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            note = StudentNote.objects.get(
                identifier=kwargs['note_id']
            )
        except StudentNote.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(note)
        return Response({'status': 'success', 'data': serializer.data})


class CreateAdminSessionNoteView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = SessionNoteSerializer 

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateSessionNoteSerializer
        return super().get_serializer_class()

    def get_queryset(self, **kwargs):
        try:
            session = Session.objects.get(
                identifier=self.kwargs['id']
            )
        except Session.DoesNotExist:
            raise exceptions.NotFound()

        return session.note.order_by('-created')

    def post(self, request, *args, **kwargs):
        request.data['user']=str(request.user)
        request.data['session']=kwargs['id']
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success', 'data': SessionNoteSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminSessionNoteView(GenericAPIView):
    allowed_methods = ('GET', 'DELETE')
    serializer_class = SessionNoteSerializer  

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return CreateSessionNoteSerializer
        return super().get_serializer_class()

    def delete(self, request, *args, **kwargs):
        try:
            note = SesssionNote.objects.get(
                identifier=kwargs['note_id']
            )
        except SesssionNote.DoesNotExist:
            raise exceptions.NotFound()

        try:
            client = Sesssion.objects.get(
                identifier=kwargs['id']
            )
        except Sesssion.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(note)
        instance = serializer.delete()

        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            note = SesssionNote.objects.get(
                identifier=kwargs['note_id']
            )
        except SesssionNote.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(note)
        return Response({'status': 'success', 'data': serializer.data})


class CreateAdminPaymentView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = PaymentSerializer    

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreatePaymentSerializer
        return super().get_serializer_class()

    def get_queryset(self, **kwargs):
        try:
            client = Client.objects.get(
                identifier=self.kwargs['id']
            )
        except Client.DoesNotExist:
            raise exceptions.NotFound()

        return client.payment.order_by('-created')

    def post(self, request, *args, **kwargs):
        request.data['client']=kwargs['id']
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        logger.info("user: " + str(request.user) + " added payment" + str(instance.identifier) +"at"+ str(datetime.datetime.now()))

        response = requests.request(
            "POST", 
            "https://hooks.zapier.com/hooks/catch/4531952/o4qcl8o/", 
            data=PaymentSerializer(instance).data, 
            )
        return Response(
            {'status': 'success', 'data': PaymentSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminPaymentView(GenericAPIView):
    allowed_methods = ('GET', 'DELETE')
    serializer_class = PaymentSerializer  

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return CreatePaymentSerializer
        return super().get_serializer_class()

    def delete(self, request, *args, **kwargs):
        try:
            payment = Payment.objects.get(
                identifier=kwargs['payment_id']
            )
        except Payment.DoesNotExist:
            raise exceptions.NotFound()

        try:
            client = Client.objects.get(
                identifier=kwargs['id']
            )
        except Client.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(payment)
        instance = serializer.delete()

        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            payment = Payment.objects.get(
                identifier=kwargs['payment_id']
            )
        except Payment.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(payment)
        return Response({'status': 'success', 'data': serializer.data})


class CreateUserBookingView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = UserStudentBookingSerializer 
    pagination_class = ResultsSetPagination
   

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateStudentBookingRequestSerializer
        return super().get_serializer_class()

    def get_queryset(self, **kwargs):
        try: 
            client = Client.objects.get(identifier=self.request.user.client.identifier)
        except Client.DoesNotExist:
            raise exceptions.NotFound()
        except AttributeError:
            raise exceptions.NotFound("User Not Found")
        try:
            return Booking.objects.filter(
                client=client
                ).order_by('-created')
        except Booking.DoesNotExist:
            raise exceptions.NotFound("Booking Not Found")

    def post(self, request, *args, **kwargs):
        request.data['client'] = str(self.request.user.client.identifier)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success', 'data': UserStudentBookingSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class UserBookingView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = UserStudentBookingSerializer  

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return CreateUserStudentBookingSerializer
        return super().get_serializer_class()

    def delete(self, request, *args, **kwargs):
        try:
            booking = Booking.objects.get(
                identifier=kwargs['booking']
            )
        except Booking.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(booking)
        instance = serializer.delete()
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            booking = Booking.objects.get(
                identifier=kwargs['booking']
            )
        except Booking.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(booking)
        return Response({'status': 'success', 'data': serializer.data})

    def patch(self, request, *args, **kwargs):
        try:
            booking = Booking.objects.get(
                identifier=kwargs['booking'],
            )
        except Booking.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(
            booking, 
            data=request.data,
            partial=True)

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success',
             'data': UserStudentBookingSerializer(instance).data}
        )


class CreateAdminSessionView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = StudentSessionListSerializer 

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateStudentSessionSerializer
        return super().get_serializer_class()

    def get_queryset(self, **kwargs):
        queryset = Session.objects.filter(
            session_type="club"
            ).order_by('-created')
        queryset = self.get_serializer_class().setup_eager_loading(queryset)
        return queryset

    def post(self, request, *args, **kwargs):
        request.data['session_type']="club"
        if request.data.get('teacher'):
            request.data['teacher'] = request.data['teacher']['identifier']
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        logger.info("user: " + str(request.user) + " added session " + str(instance.identifier) +"at"+ str(datetime.datetime.now()))

        return Response(
            {'status': 'success', 'data': StudentSessionSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminSessionView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = StudentSessionSerializer  

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return UpdateStudentSessionSerializer
        return super().get_serializer_class()

    def delete(self, request, *args, **kwargs):
        try:
            session = Session.objects.get(
                identifier=kwargs['session']
            )
        except Session.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(session)
        instance = serializer.delete()
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            session = Session.objects.get(
                identifier=self.kwargs['session']
            )
        except Session.DoesNotExist:
            raise exceptions.NotFound()


        serializer = self.get_serializer(session)
        return Response({'status': 'success', 'data': serializer.data})

    def patch(self, request, *args, **kwargs):
        try:
            session = Session.objects.get(
                identifier=kwargs['session'],
            )
        except Session.DoesNotExist:
            raise exceptions.NotFound()

        if request.data.get('teacher')!=None:
            try:
                request.data['teacher']= Teacher.objects.get(
                    identifier=request.data.get('teacher')
                ).id
            except Teacher.DoesNotExist:
                raise exceptions.NotFound()

        serializer = self.get_serializer(
            session, 
            data=request.data,
            partial=True)

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success',
             'data': StudentSessionSerializer(instance).data}
        )


class CreateAdminCampSessionView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = StudentCampSessionSerializer    

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateStudentCampSessionSerializer
        return super().get_serializer_class()

    def get_queryset(self, **kwargs):
        return Session.objects.filter(
            session_type="camp"
            ).order_by('-created')

    def post(self, request, *args, **kwargs):
        request.data['session_type']="camp"
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        return Response(
            {'status': 'success', 'data': StudentCampSessionSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminCampSessionView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = CampSessionSerializer  

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return UpdateCampSessionSerializer
        return super().get_serializer_class()

    def delete(self, request, *args, **kwargs):
        try:
            session = CampSession.objects.get(
                identifier=kwargs['session_id']
            )
        except CampSession.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(session)
        instance = serializer.delete()
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            session = CampSession.objects.get(
                identifier=self.kwargs['session_id']
            )
        except CampSession.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(session)
        return Response({'status': 'success', 'data': serializer.data})

    def patch(self, request, *args, **kwargs):
        try:
            session = CampSession.objects.get(
                identifier=kwargs['session_id'],
            )
        except CampSession.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(
            session, 
            data=request.data,
            partial=True)

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success',
             'data': CampSessionSerializer(instance).data}
        )


class AdminCampSessionCreateView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = ShortCampSessionSerializer 
   
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateCampSessionSerializer
        return super().get_serializer_class()

    def get_queryset(self, **kwargs):
        queryset = CampSession.objects.filter(
            camp__identifier=self.kwargs['id'],
            ).order_by('week__week')
        queryset = self.get_serializer_class().setup_eager_loading(queryset)
        return queryset

    def post(self, request, *args, **kwargs):
        request.data['camp']=self.kwargs['id']
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        logger.info("user: " + str(request.user) + " added camp session " + str(instance.identifier) +"at"+ str(datetime.datetime.now()))

        return Response(
            {'status': 'success', 'data': CampSessionSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class CreateAdminTrialView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = StudentTrialSerializer 
    pagination_class = ResultsSetPagination
   

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateStudentTrialSerializer
        return super().get_serializer_class()

    def get_queryset(self, **kwargs):
        return Trial.objects.filter(
            
            ).order_by('-created')

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        context = {
                       "teacher": instance.teacher,
                       "student": instance.student,
                       "date": instance.date,
                       "location": instance.location,
                       "club": instance.club,
                       "staff": instance.sales_representative
                       }
        get_adapter(self.request).send_mail('account/email/email_teacher_trial',instance.teacher.email,context)
        return Response(
            {'status': 'success', 'data': StudentTrialSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminTrialView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = StudentTrialSerializer  

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return CreateStudentTrialSerializer
        return super().get_serializer_class()

    def delete(self, request, *args, **kwargs):
        try:
            session = Trial.objects.get(
                identifier=kwargs['session']
            )
        except Trial.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(session)
        instance = serializer.delete()
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            session = Trial.objects.get(
                identifier=self.kwargs['session']
            )
        except Trial.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(session)
        return Response({'status': 'success', 'data': serializer.data})

    def patch(self, request, *args, **kwargs):
        try:
            session = Trial.objects.get(
                identifier=kwargs['session'],
            )
        except Trial.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(
            session, 
            data=request.data,
            partial=True)

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success',
             'data': StudentTrialSerializer(instance).data}
        )


class CreateAdminCampView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = CampSerializer 
    pagination_class = ResultsSetPagination
   

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateCampSerializer
        return super().get_serializer_class()

    def get_queryset(self, **kwargs):
        return Camp.objects.filter(
            
            ).order_by('-created')

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        logger.info("user: " + str(request.user) + " created camp  " + str(instance.identifier) +"at"+ str(datetime.datetime.now()))

        return Response(
            {'status': 'success', 'data': CampSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminCampView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = CampSerializer  

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return CreateCampSerializer
        return super().get_serializer_class()

    def delete(self, request, *args, **kwargs):
        try:
            camp = Camp.objects.get(
                identifier=kwargs['id']
            )
        except Camp.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(camp)
        instance = serializer.delete()
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            camp = Camp.objects.get(
                identifier=self.kwargs['id']
            )
        except Camp.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(camp)
        return Response({'status': 'success', 'data': serializer.data})

    def patch(self, request, *args, **kwargs):
        try:
            camp = Camp.objects.get(
                identifier=kwargs['id'],
            )
        except Camp.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(
            camp, 
            data=request.data,
            partial=True)

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success',
             'data': CampSerializer(instance).data}
        )


class StudentBookingListView(ListAPIView):
    allowed_methods = ('GET')
    serializer_class = StudentBookingSerializer   
     
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UpdateStudentBookingSerializer
        return super().get_serializer_class()

    def get_queryset(self, **kwargs):
        return Booking.objects.filter(
            student__identifier = self.kwargs["id"]
            ).order_by('-created')

    def post(self, request, *args, **kwargs):
        request.data['student'] = kwargs["id"]
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        response = requests.request(
            "POST", 
            "https://hooks.zapier.com/hooks/catch/4531952/o4qcle5/", 
            data=StudentBookingZapierSerializer(instance).data, 
            )

        return Response(
            {'status': 'success', 'data': StudentBookingSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminTagView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = TagSerializer 

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TagCreateSerializer
        return super().get_serializer_class()

    def get_queryset(self, **kwargs):
        try:
            tags = Tag.objects.all(
                
            )
        except Tag.DoesNotExist:
            raise exceptions.NotFound()

        return tags

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success', 'data': TagSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminClientCreateView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = ClientSerializer  
    pagination_class = ResultsSetPagination  

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateClientSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = Client.objects.filter().order_by('-updated')
        first_name = self.request.query_params.get('first_name')
        last_name = self.request.query_params.get('last_name')
        location = self.request.query_params.get('location')
        email = self.request.query_params.get('email')
        hours_remaining = self.request.query_params.get('hours_remaining')

        if first_name:
            queryset = queryset.filter(first_name__icontains=first_name)
        if last_name:
            queryset = queryset.filter(last_name__icontains=last_name)
        if location:
            queryset = queryset.filter(location__icontains=location)
        if email:
            queryset = queryset.filter(email__icontains=email)
        if hours_remaining:
            queryset = queryset.filter(hours_remaining=hours_remaining)

        return queryset

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        logger.info("user: " + str(request.user) + "  added client  " + str(instance.identifier) +"at"+ str(datetime.datetime.now()))

        return Response(
            {'status': 'success', 'data': ClientSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminClientList(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = ClientListSerializer  

    def get_queryset(self):
        queryset = Client.objects.filter().order_by('-updated')
        first_name = self.request.query_params.get('first_name')
        last_name = self.request.query_params.get('last_name')
        email = self.request.query_params.get('email')

        if first_name:
            queryset = queryset.filter(first_name__icontains=first_name)
        if last_name:
            queryset = queryset.filter(last_name__icontains=last_name)
        if email:
            queryset = queryset.filter(email__icontains=email)
        return queryset


class AdminClientView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = ClientSerializer  

    def delete(self, request, *args, **kwargs):
        try:
            client = Client.objects.get(
                identifier=kwargs['id']
            )
        except Client.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(client)
        instance = serializer.delete()
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            client = Client.objects.get(
                identifier=str(kwargs['id']),
            )
        except Client.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(client)
        return Response({'status': 'success', 'data': serializer.data})

    def patch(self, request, *args, **kwargs):
        try:
            client = Client.objects.get(
                identifier=kwargs['id'],
            )

        except Client.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(
            client, 
            data=request.data,
            partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success',
             'data': ClientSerializer(instance).data}
        )


class AdminTeacherCreateView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = TeacherSerializer  
    pagination_class = ResultsSetPagination  

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateTeacherSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = Teacher.objects.filter().order_by('-updated')
        first_name = self.request.query_params.get('first_name')
        last_name = self.request.query_params.get('last_name')
        location = self.request.query_params.get('location')
        email = self.request.query_params.get('email')

        if first_name:
            queryset = queryset.filter(first_name__icontains=first_name)
        if last_name:
            queryset = queryset.filter(last_name__icontains=last_name)
        if location:
            queryset = queryset.filter(location__icontains=location)
        if email:
            queryset = queryset.filter(email__icontains=email)

        return queryset

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        from django.core.mail import send_mail
        from django.contrib.sites.shortcuts import get_current_site

        current_site = get_current_site(self.request)
        url = os.environ.get('PWD_ADMIN_SET_URL', 'https://admin.usersprojects.com/password/create/')
        context = {"current_site": current_site,
                       "user": instance,
                       "url": url + str(instance.identifier),
                       "request": self.request}
        get_adapter(self.request).send_mail('account/email/email_teacher_confirm',instance.email,context)

        return Response(
            {'status': 'success', 'data': TeacherSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminTeacherList(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = TeacherListSerializer  

    def get_queryset(self):
        queryset = Teacher.objects.filter().order_by('-updated')
        first_name = self.request.query_params.get('first_name')
        last_name = self.request.query_params.get('last_name')
        location = self.request.query_params.get('location')
        email = self.request.query_params.get('email')

        if first_name:
            queryset = queryset.filter(first_name__icontains=first_name)
        if last_name:
            queryset = queryset.filter(last_name__icontains=last_name)
        if location:
            queryset = queryset.filter(location__icontains=location)
        if email:
            queryset = queryset.filter(email__icontains=email)
        
        return queryset


class AdminTeacherView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = TeacherSerializer  

    def delete(self, request, *args, **kwargs):
        try:
            teacher = Teacher.objects.get(
                identifier=kwargs['id']
            )
        except Teacher.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(teacher)
        instance = serializer.delete()
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            teacher = Teacher.objects.get(
                identifier=str(kwargs['id']),
            )
        except Teacher.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(teacher)
        return Response({'status': 'success', 'data': serializer.data})

    def patch(self, request, *args, **kwargs):
        try:
            teacher = Teacher.objects.get(
                identifier=kwargs['id'],
            )

        except Teacher.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(
            teacher, 
            data=request.data,
            partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success',
             'data': TeacherSerializer(instance).data}
        )


class AdminStaffCreateView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = StaffSerializer  

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateStaffSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = Staff.objects.filter().order_by('-updated')
        first_name = self.request.query_params.get('first_name')
        last_name = self.request.query_params.get('last_name')
        location = self.request.query_params.get('location')
        email = self.request.query_params.get('email')

        if first_name:
            queryset = queryset.filter(first_name__icontains=first_name)
        if last_name:
            queryset = queryset.filter(last_name__icontains=last_name)
        if location:
            queryset = queryset.filter(location__icontains=location)
        if email:
            queryset = queryset.filter(email__icontains=email)

        return queryset

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        from django.core.mail import send_mail
        from django.contrib.sites.shortcuts import get_current_site

        current_site = get_current_site(self.request)
        url = os.environ.get('PWD_ADMIN_SET_URL', 'https://admin.usersprojects.com/password/create/')
        context = {"current_site": current_site,
                       "user": instance,
                       "url": url + str(instance.identifier),
                       "request": self.request}
        get_adapter(self.request).send_mail('account/email/email_teacher_confirm',instance.email,context)

        return Response(
            {'status': 'success', 'data': StaffSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminStaffList(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = StaffListSerializer  

    def get_queryset(self):
        queryset = Staff.objects.filter().order_by('-updated')
        first_name = self.request.query_params.get('first_name')
        last_name = self.request.query_params.get('last_name')
        location = self.request.query_params.get('location')
        email = self.request.query_params.get('email')

        if first_name:
            queryset = queryset.filter(first_name__icontains=first_name)
        if last_name:
            queryset = queryset.filter(last_name__icontains=last_name)
        if location:
            queryset = queryset.filter(location__icontains=location)
        if email:
            queryset = queryset.filter(email__icontains=email)
        
        return queryset


class AdminStaffView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = StaffSerializer  

    def delete(self, request, *args, **kwargs):
        try:
            staff = Staff.objects.get(
                identifier=kwargs['id']
            )
        except Staff.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(staff)
        instance = serializer.delete()
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            staff = Staff.objects.get(
                identifier=str(kwargs['id']),
            )
        except Staff.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(staff)
        return Response({'status': 'success', 'data': serializer.data})

    def patch(self, request, *args, **kwargs):
        try:
            staff = Staff.objects.get(
                identifier=kwargs['id'],
            )

        except Staff.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(
            staff, 
            data=request.data,
            partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success',
             'data': TeacherSerializer(instance).data}
        )


class AdminBranchCreateView(ListAPIView):
    allowed_methods = ('GET','POST')
    serializer_class = AdminBranchSerializer 
    pagination_class = ResultsSetPagination
   
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AdminBranchCreateSerializer
        return super().get_serializer_class()

    def get_queryset(self, **kwargs):
        return Branch.objects.filter(
            ).order_by('-created')

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success', 'data': AdminBranchSerializer(instance).data},
            status=status.HTTP_201_CREATED
        )


class AdminBranchView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = AdminBranchSerializer  

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return AdminBranchCreateSerializer
        return super().get_serializer_class()

    def delete(self, request, *args, **kwargs):
        try:
            branch = Branch.objects.get(
                identifier=kwargs['id']
            )
        except Branch.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(branch)
        instance = serializer.delete()
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            branch = Branch.objects.get(
                identifier=kwargs['id']
            )
        except Branch.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(branch)
        return Response({'status': 'success', 'data': serializer.data})

    def patch(self, request, *args, **kwargs):
        try:
            branch = Branch.objects.get(
                identifier=kwargs['id'],
            )
        except Branch.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(
            branch, 
            data=request.data,
            partial=True)

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success',
             'data': AdminBranchSerializer(instance).data}
        )


class UserClientView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = ClientSerializer  

    def delete(self, request, *args, **kwargs):
        try:
            client = Client.objects.get(
                identifier=kwargs['id']
            )
        except Client.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(client)
        instance = serializer.delete()
        return Response({'status': 'success'})

    def get(self, request, *args, **kwargs):
        try:
            client = Client.objects.get(
                identifier=str(kwargs['id']),
            )
        except Client.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(client)
        return Response({'status': 'success', 'data': serializer.data})

    def patch(self, request, *args, **kwargs):
        try:
            client = Client.objects.get(
                identifier=kwargs['id'],
            )

        except Client.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(
            client, 
            data=request.data,
            partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success',
             'data': ClientSerializer(instance).data}
        )


class UserStudentView(ListAPIView):
    allowed_methods = ('GET')
    serializer_class = StudentShortSerializer  

    def get_queryset(self, **kwargs):
        
        return Student.objects.filter(
           client=self.request.user.client
            ).order_by('-created')


class CreateUserView(GenericAPIView):
    serializer_class = UserRegisterSerializer
    permission_classes = (AllowAny, )

    def post(self, request, *args, **kwargs):
        try: 
            client = Client.objects.get(identifier=kwargs['client'])
            request.data['role'] = 'parent'
            request.data['client'] = client
            request.data['first_name'] = client.first_name
            request.data['last_name'] = client.last_name
            request.data['email'] = client.email
        except Client.DoesNotExist:
            try: 
                teacher = Teacher.objects.get(identifier=kwargs['client'])
                request.data['role'] = 'teacher'
                request.data['teacher'] = teacher
                request.data['first_name'] = teacher.first_name
                request.data['last_name'] = teacher.last_name
                request.data['email'] = teacher.email
            except Teacher.DoesNotExist:        
                try:
                    staff = Staff.objects.get(identifier=kwargs['client'])
                    request.data['role'] = 'staff'
                    request.data['staff'] = staff
                    request.data['first_name'] = staff.first_name
                    request.data['last_name'] = staff.last_name
                    request.data['email'] = staff.email
                except Staff.DoesNotExist:
                    raise exceptions.NotFound('User not found, please contact your administrator.')
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.save(request)
        token = AuthToken.objects.create(user=user)
        
        if user.role == Role.TEACHER or user.role == Role.STAFF:
            from django.core.mail import send_mail
            from django.contrib.sites.shortcuts import get_current_site 

            context = {"current_site": get_current_site(self.request),
                        "user": user,
                        "url": 'https://admin.usersprojects.com/',
                        "request": self.request}
            get_adapter(self.request).send_mail('account/email/email_admin_confirmation',user.email,context)
        else:
            complete_signup(
            self.request._request,
            user,
            allauth_settings.EMAIL_VERIFICATION,
            None
        )

        return Response(
            {'status': 'success',
             'data': TokenSerializer({'user': user, 'token': token}).data},
            status=status.HTTP_201_CREATED
        )


class UserView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = UserSerializer  

    def get(self, request, *args, **kwargs):
        
        try:
            client = User.objects.get(
                email = request.user
            )
        except User.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(client)
        return Response({'status': 'success', 'data': serializer.data})

    def patch(self, request, *args, **kwargs):
        try:
            user = User.objects.get(
                email = request.user
            )
        except User.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(
            user, 
            data=request.data,
            partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {'status': 'success',
             'data': UserSerializer(instance).data}
        )


class UserUpdateView(GenericAPIView):
    allowed_methods = ('GET','PATCH', 'DELETE')
    serializer_class = UserSerializer  

    def get(self, request, *args, **kwargs):
        try:
            client = User.objects.get(
                email = kwargs['id']
            )
        except User.DoesNotExist:
            raise exceptions.NotFound()

        serializer = self.get_serializer(client)
        return Response({'status': 'success', 'data': serializer.data})

    def patch(self, request, *args, **kwargs):
        try:
            user = User.objects.get(
                email = request.user
            )
        except User.DoesNotExist:
            raise exceptions.NotFound()

        client = request.data.get('client')
        staff = request.data.get('staff')
        teacher = request.data.get('teacher')
        if request.data.get('client'):
            try:
                request.data['client'] = Client.objects.get(identifier=client['identifier'])
            except Client.DoesNotExist:
                raise exceptions.NotFound()
        
        if request.data.get('staff'):
            try:
                request.data['staff'] = Staff.objects.get(identifier=staff['identifier'])
            except Staff.DoesNotExist:
                raise exceptions.NotFound()

        if request.data.get('teacher'):
            try:
                request.data['teacher'] = Teacher.objects.get(identifier=teacher['identifier'])
            except Teacher.DoesNotExist:
                raise exceptions.NotFound()

        serializer = self.get_serializer(
            user, 
            data=request.data,
            partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(request)
        return Response(
            {'status': 'success',
             'data': UserSerializer(instance).data}
        )
