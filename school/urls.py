from django.conf.urls import *
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

urlpatterns = (
    url(r'^$', views.root),
    
    url(r'^user/auth/register/$', views.UserRegisterView.as_view(), name='user-register'),
    url(r'^user/auth/login/$', views.LoginView.as_view(), name='user-login'),
    url(r'^user/auth/logout/$', views.LogoutView.as_view(), name='user-logout'),
    url(r'^user/auth/password/change/$', views.PasswordChangeView.as_view(), name='user-password-change'),
    url(r'^user/auth/password/reset/$', views.PasswordResetView.as_view(), name='user-password-reset'),
    url(r'^user/auth/create/(?P<client>([a-zA-Z0-9\_\-]+))/$', views.CreateUserView.as_view(), name='user-create'),
    
    url(r'^user/$', views.UserView.as_view(), name='user-view'),
    url(r'^user/(?P<id>\w+|[\w.%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4})/$', views.UserUpdateView.as_view(), name='user-edit-view'),
    url(r'^user/client/(?P<id>([a-zA-Z0-9\_\-]+))/$', views.UserClientView.as_view(), name='user-client-view'),
    url(r'^user/student/$', views.UserStudentView.as_view(), name='user-student-view'),
    url(r'^user/student/(?P<id>([a-zA-Z0-9\_\-]+))/$', views.AdminStudentView.as_view(), name='admin-student-view'),
    url(r'^user/student/(?P<id>([a-zA-Z0-9\_\-]+))/booking/$', views.StudentBookingListView.as_view(), name='user-node-view'),
    url(r'^user/booking/$', views.CreateUserBookingView.as_view(), name='user-booking-view'),
    url(r'^user/booking/(?P<booking>([a-zA-Z0-9\_\-]+))/$', views.UserBookingView.as_view(), name='user-node-view'),

    url(r'^admin/auth/register/$', views.RegisterView.as_view(), name='admin-register'),
    url(r'^admin/auth/login/$', views.LoginView.as_view(), name='admin-login'),
    url(r'^admin/auth/logout/$', views.LogoutView.as_view(), name='admin-logout'),
    url(r'^admin/auth/password/change/$', views.PasswordChangeView.as_view(), name='admin-password-change'),
    url(r'^admin/auth/password/reset/$', views.PasswordResetView.as_view(), name='admin-password-reset'),
    url(r'^admin/auth/create/(?P<client>([a-zA-Z0-9\_\-]+))/$', views.CreateUserView.as_view(), name='admin-create'),
        
    url(r'^admin/club/$', views.AdminClubCreateView.as_view(), name='admin-course-view'),
    url(r'^admin/club/(?P<id>([a-zA-Z0-9\_\-]+))/$', views.AdminClubView.as_view(), name='admin-course-view'),
    url(r'^admin/club/(?P<id>([a-zA-Z0-9\_\-]+))/badge/$', views.AdminBadgeCreateView.as_view(), name='admin-course-view'),
    
    url(r'^admin/camp/$', views.CreateAdminCampView.as_view(), name='admin-camp-view'),
    url(r'^admin/camp/(?P<id>([a-zA-Z0-9\_\-]+))/$', views.AdminCampView.as_view(), name='admin-camp-view'),
    url(r'^admin/camp/(?P<id>([a-zA-Z0-9\_\-]+))/session/$', views.AdminCampSessionCreateView.as_view(), name='admin-campsession-view'),
    url(r'^admin/camp/(?P<id>([a-zA-Z0-9\_\-]+))/session/(?P<session_id>([a-zA-Z0-9\_\-]+))/$', views.AdminCampSessionView.as_view(), name='admin-camp-view'),
    url(r'^admin/camp/(?P<id>([a-zA-Z0-9\_\-]+))/session/(?P<session_id>([a-zA-Z0-9\_\-]+))/booking/$', views.CreateAdminCampBookingView.as_view(), name='admin-camp-view'),
    url(r'^admin/camp/(?P<id>([a-zA-Z0-9\_\-]+))/session/(?P<session_id>([a-zA-Z0-9\_\-]+))/booking/(?P<booking_id>([a-zA-Z0-9\_\-]+))/$', views.AdminCampBookingView.as_view(), name='admin-camp-view'),
    url(r'^admin/camp/(?P<id>([a-zA-Z0-9\_\-]+))/week/$', views.AdminCampWeekCreateView.as_view(), name='admin-campweek-view'),

    url(r'^admin/badge/$', views.AdminBadgeCreateView.as_view(), name='user-badge-view'),
    url(r'^admin/badge/(?P<id>([a-zA-Z0-9\_\-]+))/$', views.AdminBadgeView.as_view(), name='user-badge-view'),
    
    url(r'^admin/session/$', views.CreateAdminSessionView.as_view(), name='admin-session-list'),
    url(r'^admin/session/(?P<session>([a-zA-Z0-9\_\-]+))/$', views.AdminSessionView.as_view(), name='admin-session-view'),
    url(r'^admin/session/(?P<id>([a-zA-Z0-9\_\-]+))/note/$', views.CreateAdminSessionNoteView.as_view(), name='user-node-view'),
    url(r'^admin/session/(?P<id>([a-zA-Z0-9\_\-]+))/note/(?P<note_id>([a-zA-Z0-9\_\-]+))/$', views.AdminSessionNoteView.as_view(), name='user-node-view'),
    url(r'^admin/camp_session/$', views.CreateAdminCampSessionView.as_view(), name='admin-campsession-list'),
    url(r'^admin/camp_session/(?P<session>([a-zA-Z0-9\_\-]+))/$', views.AdminCampSessionView.as_view(), name='admin-campsession-view'),
    url(r'^admin/trial_session/$', views.CreateAdminTrialView.as_view(), name='admin-trialsession-list'),
    url(r'^admin/trial_session/(?P<session>([a-zA-Z0-9\_\-]+))/$', views.AdminTrialView.as_view(), name='admin-trialsession-view'),

    url(r'^admin/booking/$', views.CreateAdminBookingView.as_view(), name='admin-booking-view'),
    url(r'^admin/booking/(?P<booking>([a-zA-Z0-9\_\-]+))/$', views.AdminBookingView.as_view(), name='user-node-view'),
    url(r'^admin/bookings/csv/$', views.export_bookings_csv, name='admin-students-index'),

    url(r'^admin/student/$', views.AdminStudentCreateView.as_view(), name='admin-students-view'),
    url(r'^admin/student/(?P<id>([a-zA-Z0-9\_\-]+))/$', views.AdminStudentView.as_view(), name='admin-student-view'),
    url(r'^admin/student/(?P<id>([a-zA-Z0-9\_\-]+))/club/$', views.AdminStudentClubCreateView.as_view(), name='user-club-view'),
    url(r'^admin/student/(?P<id>([a-zA-Z0-9\_\-]+))/camp/$', views.AdminStudentClubCreateView.as_view(), name='user-club-view'),
    url(r'^admin/student/(?P<id>([a-zA-Z0-9\_\-]+))/club/(?P<club>([a-zA-Z0-9\_\-]+))/$', views.AdminStudentClubView.as_view(), name='user-club-add'),
    url(r'^admin/student/(?P<id>([a-zA-Z0-9\_\-]+))/club/(?P<club>([a-zA-Z0-9\_\-]+))/badge/$', views.AdminBadgeAdd.as_view(), name='user-badge-add'),
    url(r'^admin/student/(?P<id>([a-zA-Z0-9\_\-]+))/booking/$', views.StudentBookingListView.as_view(), name='user-node-view'),
    url(r'^admin/student/(?P<id>([a-zA-Z0-9\_\-]+))/booking/(?P<booking>([a-zA-Z0-9\_\-]+))/$', views.AdminStudentBookingView.as_view(), name='user-node-view'),
    url(r'^admin/student/(?P<id>([a-zA-Z0-9\_\-]+))/note/$', views.CreateAdminStudentNoteView.as_view(), name='user-node-view'),
    url(r'^admin/student/(?P<id>([a-zA-Z0-9\_\-]+))/note/(?P<note_id>([a-zA-Z0-9\_\-]+))/$', views.AdminStudentNoteView.as_view(), name='user-node-view'),
    url(r'^admin/students/$', views.AdminStudentList.as_view(), name='admin-students-index'),
    url(r'^admin/students/csv/$', views.export_student_csv, name='admin-students-index'),

    url(r'^admin/client/$', views.AdminClientCreateView.as_view(), name='admin-parent-view'),
    url(r'^admin/client/(?P<id>([a-zA-Z0-9\_\-]+))/$', views.AdminClientView.as_view(), name='user-node-view'),
    url(r'^admin/client/(?P<id>([a-zA-Z0-9\_\-]+))/payment/$', views.CreateAdminPaymentView.as_view(), name='user-node-view'),
    url(r'^admin/client/(?P<id>([a-zA-Z0-9\_\-]+))/payment/(?P<payment_id>([a-zA-Z0-9\_\-]+))/$', views.AdminPaymentView.as_view(), name='user-node-view'),
    url(r'^admin/client/(?P<id>([a-zA-Z0-9\_\-]+))/note/$', views.CreateAdminClientNoteView.as_view(), name='user-node-view'),
    url(r'^admin/client/(?P<id>([a-zA-Z0-9\_\-]+))/note/(?P<note_id>([a-zA-Z0-9\_\-]+))/$', views.AdminClientNoteView.as_view(), name='user-node-view'),
    url(r'^admin/clients/$', views.AdminClientList.as_view(), name='admin-clients-index'),
    url(r'^admin/clients/csv/$', views.export_clients_csv, name='admin-students-index'),

    url(r'^admin/teacher/$', views.AdminTeacherCreateView.as_view(), name='admin-teacher-list'),
    url(r'^admin/teacher/(?P<id>([a-zA-Z0-9\_\-]+))/$', views.AdminTeacherView.as_view(), name='user-teacher-view'),
    url(r'^admin/teachers/$', views.AdminTeacherList.as_view(), name='admin-teacher-index'),

    url(r'^admin/staff/$', views.AdminStaffCreateView.as_view(), name='admin-staff-list'),
    url(r'^admin/staff/(?P<id>([a-zA-Z0-9\_\-]+))/$', views.AdminStaffView.as_view(), name='user-staff-view'),

    url(r'^admin/branch/$', views.AdminBranchCreateView.as_view(), name='admin-branch-list'),
    url(r'^admin/branch/(?P<id>([a-zA-Z0-9\_\-]+))/$', views.AdminBranchView.as_view(), name='user-branch-view'),

    url(r'^admin/tag/$', views.AdminTagView.as_view(), name='admin-tag-list'),
)

urlpatterns = format_suffix_patterns(urlpatterns)
