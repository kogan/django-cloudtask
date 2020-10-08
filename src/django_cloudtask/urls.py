from django.urls import path

from .views import execute_task

urlpatterns = [path("execute/", execute_task, name="task-execute")]
