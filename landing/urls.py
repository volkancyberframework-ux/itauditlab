from django.urls import path
from . import views
from . import travel
from mobile_api import web_billing

app_name = 'landing'
urlpatterns = [
    path('mobiluygulama', web_billing.page, name='mobile_membership'),
    path('mobiluygulama/', web_billing.page),
    path('mobiluygulama/checkout', web_billing.checkout, name='mobile_checkout'),
    path('mobiluygulama/success', web_billing.success, name='mobile_success'),
    path('mobiluygulama/webhook', web_billing.webhook, name='mobile_webhook'),
    path('travelbootcamp', travel.page, name='travel_bootcamp'),
    path('travelbootcamp/', travel.page),
    path('travelbootcamp/checkout', travel.checkout, name='travel_checkout'),
    path('travelbootcamp/success', travel.success, name='travel_success'),
    path('travelbootcamp/status', travel.status, name='travel_status'),
    path('travelbootcamp/webhook', travel.webhook, name='travel_webhook'),
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
