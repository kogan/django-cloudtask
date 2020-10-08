from importlib import import_module

from django.apps import AppConfig


class TasksConfig(AppConfig):
    name = "django_cloudtask"

    def ready(self):
        for cfg in self.apps.get_app_configs():
            try:
                import_module(f"{cfg.name}.tasks")
            except ImportError as e:
                if f"{cfg.name}.tasks" not in str(e):
                    raise
