from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path('prihlaseni/', LoginView.as_view(template_name='counters/login.html'), name='login'),
    path('odhlaseni/', LogoutView.as_view(), name='logout'),
    path('', views.map_view, name='map'),
    path('api/counters/', views.counters_json, name='counters_json'),
    path('counters/add/', views.counter_add, name='counter_add'),
    path('counters/list/', views.counter_list, name='counter_list'),
    path('counters/<int:pk>/', views.counter_detail, name='counter_detail'),
    path('counters/<int:pk>/delete/', views.counter_delete, name='counter_delete'),
    path('counters/<int:pk>/clear-history/', views.counter_clear_history, name='counter_clear_history'),
]
