from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django.contrib.auth.views import *

from . import views
from django.conf.urls import url

import debug_toolbar

admin.autodiscover()


urlpatterns = (
    # Views
    url(r'^api/', include('school.urls', namespace='school')),
    url(r'^admin/', admin.site.urls),
    url(r'^accounts/', include('allauth.urls')),
   

)

# Add debug URL routes
if settings.DEBUG:
    urlpatterns = (
        url(r'^$', views.index, name='index'),
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ) + urlpatterns
