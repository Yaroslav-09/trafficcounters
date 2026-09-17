from django.contrib import admin
from django.urls import path, include

from counters.views import healthz

urlpatterns = [
    path('healthz/', healthz, name='healthz'),
    path('admin/', admin.site.urls),
    path('', include('counters.urls')),
]
