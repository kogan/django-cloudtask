import json

import structlog
from django.conf import settings
from django.core.management import BaseCommand
from django.urls import reverse
from google.api_core.protobuf_helpers import field_mask
from google.cloud.scheduler import CloudSchedulerClient
from google.cloud.scheduler_v1.gapic.enums import Job as JobEnum
from google.cloud.scheduler_v1.types import Job

log = structlog.get_logger()


class Command(BaseCommand):
    help = "Synchronise tasks with a cron setting with CloudScheduler"

    def handle(self, *args, **kwargs):
        from django_cloudtask.task import schedule_registry

        client = CloudSchedulerClient()
        parent = client.location_path(settings.PROJECT_ID, settings.PROJECT_REGION)
        existing_config = {
            job.name: (job.description, job.schedule, job.state) for job in client.list_jobs(parent)
        }
        current_config = {
            client.job_path(
                settings.PROJECT_ID, settings.PROJECT_REGION, task_id.replace(".", "-")
            ): (
                task_id,
                schedule,
            )
            for task_id, schedule in schedule_registry.items()
        }
        for name, (task_id, schedule, _) in existing_config.items():
            # a task used to exist
            if name not in current_config:
                log.info("sync_scheduler.delete", task_id=task_id, schedule=schedule)
                client.delete_job(name)

        for name, (task_id, schedule) in current_config.items():
            # Can't update paused items - we've already deleted them so we'll recreate them to update the schedule
            if name in existing_config:
                # task changed it's schedule
                if existing_config[name][1] != schedule:
                    log.info(
                        "sync_scheduler.update",
                        task_id=task_id,
                        schedule=schedule,
                        old_schedule=existing_config[name][1],
                    )
                    job = Job()
                    job.name = name
                    job.schedule = schedule

                    if existing_config[name][2] == JobEnum.State.PAUSED:
                        log.info("sync_scheduler.resume", task_id=task_id, schedule=schedule)
                        client.resume_job(name)

                    client.update_job(
                        job,
                        field_mask(None, job),
                    )

                    if existing_config[name][2] == JobEnum.State.PAUSED:
                        log.info("sync_scheduler.pause", task_id=task_id, schedule=schedule)
                        client.pause_job(name)
            else:
                # new task was created
                log.info(
                    "sync_scheduler.create",
                    task_id=task_id,
                    schedule=schedule,
                )
                client.create_job(
                    parent,
                    {
                        "name": name,
                        "description": task_id,
                        "schedule": schedule,
                        "http_target": {
                            "http_method": "POST",
                            "body": json.dumps(
                                {"function": task_id, "args": [], "kwargs": {}}
                            ).encode("utf-8"),
                            "oidc_token": {
                                "service_account_email": settings.TASK_SERVICE_ACCOUNT,
                                "audience": f"https://{settings.TASK_DOMAIN}{reverse('task-execute')}",
                            },
                            "uri": f"https://{settings.TASK_DOMAIN}{reverse('task-execute')}",
                        },
                        "time_zone": "Australia/Melbourne",
                    },
                )

        log.info("Cloud Scheduler is up-to-date.")
