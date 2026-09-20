from django.urls import path
from django.contrib import admin
from accounts import views
from workspace import views as workspace_views
urlpatterns = [path('', views.root, name='root'), path('signin/', views.SignIn.as_view(), name='signin'), path('password/change/', views.change_password, name='change_password'), path('console/', workspace_views.console, name='console'), path('signout/', views.signout, name='signout')]

urlpatterns += [path('console/view-as/', workspace_views.view_as, name='view_as'), path('console/<int:audit_id>/controls/<int:control_id>/', workspace_views.detail, name='control_detail'), path('console/<int:audit_id>/controls/<int:control_id>/history/', workspace_views.history, name='control_history')]

urlpatterns += [path('console/<int:audit_id>/workflow/', workspace_views.workflow, name='workflow'), path('console/<int:audit_id>/findings.pdf', workspace_views.findings_pdf, name='findings_pdf')]

urlpatterns += [path('console/<int:audit_id>/controls.pdf', workspace_views.controls_pdf, name='controls_pdf')]

urlpatterns += [path('admin/', admin.site.urls)]
