from django.urls import path
from django.contrib import admin
from accounts import views
from workspace import views as workspace_views
urlpatterns = [path('', views.root, name='root'), path('signin/', views.SignIn.as_view(), name='signin'), path('password/change/', views.change_password, name='change_password'), path('console/', workspace_views.console, name='console'), path('signout/', views.signout, name='signout')]

urlpatterns += [path('console/view-as/', workspace_views.view_as, name='view_as'), path('console/<int:audit_id>/controls/<int:control_id>/', workspace_views.detail, name='control_detail'), path('console/<int:audit_id>/controls/<int:control_id>/history/', workspace_views.history, name='control_history')]

urlpatterns += [path('console/<int:audit_id>/workflow/', workspace_views.workflow, name='workflow'), path('console/<int:audit_id>/findings.pdf', workspace_views.findings_pdf, name='findings_pdf')]

urlpatterns += [path('console/<int:audit_id>/controls.pdf', workspace_views.controls_pdf, name='controls_pdf')]

from workspace.legislation import import_legislation, compliance_panel
from workspace.invitations import create_account
urlpatterns += [path('admin/legislation/import/', admin.site.admin_view(import_legislation), name='import_legislation'), path('console/<int:audit_id>/compliance/', compliance_panel, name='legal_compliance'), path('admin/users/new/', admin.site.admin_view(create_account), name='create_account'), path('admin/', admin.site.urls)]

from workspace.logo import organization_logo
from django.views.generic.base import RedirectView
urlpatterns += [path('console/users/new/', RedirectView.as_view(pattern_name='create_account'))]
urlpatterns += [path('privacy/', views.privacy, name='privacy')]
urlpatterns += [path('branding/<int:organization_id>/logo/', organization_logo, name='organization_logo')]

from workspace import cards
urlpatterns += [path('cards/', cards.entry, name='card_entry'), path('cards/work/', cards.workspace, name='card_workspace'), path('cards/save/', cards.save, name='card_save'), path('cards/leave/', cards.leave, name='card_leave'), path('console/<int:audit_id>/send-controls/', cards.dispatch, name='card_dispatch')]
