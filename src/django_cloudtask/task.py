import enum
import json
import time
import typing as t

import structlog
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import reverse
from google.cloud.tasks_v2 import CloudTasksClient

log = structlog.get_logger()
registry = {}
schedule_registry = {}


class RetryTaskException(Exception):
    pass


class TaskResponse(enum.IntEnum):
    SUCCESS = 200
    RETRY = 429
    FAIL = 500


class Task:
    client = None

    def __init__(self, f, queue: str, should_retry=True):
        self.f = f
        self.queue = queue
        self.should_retry = should_retry

    @classmethod
    def get_client(cls):
        if cls.client is None:
            cls.client = CloudTasksClient()
        return cls.client

    @property
    def name(self):
        return f"{self.f.__module__}.{self.f.__name__}"

    def __str__(self):
        return f"<Task {self.name}>"

    def __call__(self, *args, **kwargs):
        return self.f(*args, **kwargs)

    def enqueue(self, *args, **kwargs):
        client = self.get_client()
        parent = client.queue_path(settings.PROJECT_ID, settings.PROJECT_REGION, self.queue)
        body = {
            "http_request": {
                "http_method": "POST",
                "url": f"https://{settings.TASK_DOMAIN}{reverse('task-execute')}",
                "oidc_token": {"service_account_email": settings.TASK_SERVICE_ACCOUNT},
                "body": json.dumps(
                    {"function": self.name, "args": args, "kwargs": kwargs}, cls=DjangoJSONEncoder
                ).encode("utf-8"),
            },
        }
        response = self.get_client().create_task(parent, body)
        log.info("tasks.queued", name=self.name, task_id=response.name)
        return response


class DebugTask(Task):
    def enqueue(self, *args, **kwargs):
        # execute all tasks inline
        body = json.dumps(
            {"function": self.name, "args": args, "kwargs": kwargs}, cls=DjangoJSONEncoder
        ).encode("utf-8")
        body = json.loads(body.decode("utf-8"))
        execute_task(body["function"], body["args"], body["kwargs"])


def get_task_class() -> t.Type[Task]:
    if settings.DEBUG:
        return DebugTask
    return Task


def register_task(
    should_retry=True, queue=settings.TASK_DEFAULT_QUEUE, schedule=None
) -> t.Union[Task, t.Callable[[t.Callable], Task]]:
    def do_register(f, _should_retry, _queue) -> Task:
        task = get_task_class()(f, _queue, should_retry=_should_retry)
        registry[task.name] = task
        if schedule is not None:
            schedule_registry[task.name] = schedule
        return task

    def as_decorator(f) -> Task:
        return do_register(f, should_retry, queue)

    if callable(should_retry):
        # called with @register_task
        return do_register(should_retry, True, queue)
    return as_decorator


def execute_task(name, args, kwargs) -> TaskResponse:
    task = registry.get(name)
    if task is None:
        log.error("tasks.unknown", name=name)
        return TaskResponse.SUCCESS
    start = time.time()
    log.info("tasks.start", name=name)
    try:
        task(*args, **kwargs)
        log.info("tasks.finish", name=name, time=f"{int((time.time() - start) * 1000)}ms")
        return TaskResponse.SUCCESS
    except RetryTaskException:
        log.info("task.force_retry", name=name)
        return TaskResponse.RETRY
    except Exception:
        log.exception("task.crash", name=name, should_retry=task.should_retry)
        if task.should_retry:
            return TaskResponse.FAIL
        return TaskResponse.SUCCESS
