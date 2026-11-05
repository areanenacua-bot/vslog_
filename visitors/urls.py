from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('register-visitor/', views.register_visitor_view, name='register_visitor'),
    path('active-visitors/', views.active_visitors_view, name='active_visitors'),
    path('visitor-history/', views.visitor_history_view, name='visitor_history'),
    path('reports/', views.reports_view, name='reports'),
]
