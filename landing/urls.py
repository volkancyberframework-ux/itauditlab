from django.urls import path
from . import business_network
from . import regulation_views
from . import legal
from . import views
from . import travel
from . import mobile_waitlist
from mobile_api import web_billing, store_pages

app_name = 'landing'
urlpatterns = [
    path('api/business-network/cities/', business_network.cities, name='business_network_cities'),
    path('api/business-network/stats/', business_network.stats, name='business_network_stats'),
    path('mevzuat/', regulation_views.page, name='regulations'),
    path('api/mevzuat/', regulation_views.fragment, name='regulation_fragment'),
    path('robots.txt', regulation_views.robots, name='robots'),
    path('sitemap.xml', regulation_views.sitemap, name='sitemap'),
    path('ot-guvenligi-bootcamp/', views.ot_bootcamp, name='ot_bootcamp'),
    path('yasal/<slug:slug>/', legal.document, name='legal'),
    path('api/cerez-tercihi/', legal.cookie_consent, name='cookie_consent'),
    path('mobil-bekleme-listesi/', mobile_waitlist.page, name='mobile_waitlist'),
    path('mobiluygulama/gizlilik', store_pages.privacy, name='mobile_privacy'),
    path('mobiluygulama/destek', store_pages.support, name='mobile_support'),
    path('mobiluygulama', web_billing.page, name='mobile_membership'),
    path('mobiluygulama/', web_billing.page),
    path('mobiluygulama/csrf', web_billing.csrf_token, name='mobile_csrf'),
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
    path('kurumsal', views.corporate_home),
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
