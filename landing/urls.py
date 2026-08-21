from django.urls import path
from . import views

app_name = 'landing'
urlpatterns = [
    path('', views.home, name='home'),
    path('kariyer-pusulasi/', views.home, name='career_compass'),
    path('kurumsal/', views.corporate_home, name='corporate'),
    path('api/kurumsal-talep/', views.submit_corporate_inquiry, name='corporate_inquiry'),
    path('api/partnerlik/', views.submit_partner_application, name='partner_application'),
    path('trafik/', views.traffic_dashboard, name='traffic_dashboard'),
    path('api/lead/', views.submit_lead, name='submit_lead'),
    path('api/assessment/', views.save_assessment, name='save_assessment'),
    path('api/waiting-list/', views.join_waiting_list, name='waiting_list'),
    path('api/newsletter/', views.subscribe_newsletter, name='newsletter'),
    path('api/certificate/', views.verify_certificate, name='verify_certificate'),
    path('odeme/', views.create_checkout, name='checkout'),
]
