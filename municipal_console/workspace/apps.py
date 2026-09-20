from django.apps import AppConfig
class WorkspaceConfig(AppConfig):
    name='workspace'
    def ready(self):
        from . import notifications
