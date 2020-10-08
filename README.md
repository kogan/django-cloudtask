# django-cloudtask
A django package for managing long running tasks via Cloud Run and Cloud Scheduler

[![CircleCI](https://circleci.com/gh/kogan/django-cloudtask.svg?style=svg)](https://circleci.com/gh/kogan/django-cloudtask)

## Should I be using this package?

Not yet - we're still trying to make this package usable by the general public.

There are a lot of assumptions being made that might not be suitable for your project.


## Usage

### Setup

include `django_cloudtask` in your installed apps.

### Configuration

Make sure these are in your django settings:

 - `PROJECT_ID`
   - the GCP project
 - `PROJECT_REGION`
   - GCP region
 - `TASK_SERVICE_ACCOUNT`
   - Service account which will be authenticated against
 - `TASK_DOMAIN`
   - domain which receives tasks (cloud run)
 - `TASK_DEFAULT_QUEUE`
   - default queue tasks will be added to

### Defining a task

Tasks __must__ be defined in a file called `tasks.py` at the root level of an app directory.

e.g.,

```
my-project/
  app/
    tasks.py
    urls.py
    views.py
  manage.py
  settings.py

```

Tasks are defined using the `@register_task` decorator.

```
@register_task(should_retry: bool, queue: str, schedule: str)
```

`:should_retry:` Will retry the task if there was an uncaught exception

`:queue:` What Queue this task belongs to (Queues are set up in GCP)

`:schedule:` Cron-like string defining when this task should be executed

Note: a scheduled task cannot have any arguments (but can have kwargs with defaults).

e.g.,

```
from django_cloudtask import register_task

@register_task
def my_task(some, args, kwarg=False):
   ...

@register_task(schedule="0 5 * * *")
def scheduled_task():
    ...

```

### Calling a task

Tasks may be scheduled by calling `enqueue(*args, **kwargs)`.

`args` and `kwargs` must be JSON serialisable.

Tasks may also be called directly which will execute in the current call stack.

e.g.,

```
# execute asynchronously
my_task.enqueue(1, "start the task", kwarg=True)


# execute immediately
scheduled_task()
```


## Contributing

We use `pre-commit <https://pre-commit.com/>` to enforce our code style rules
locally before you commit them into git. Once you install the pre-commit library
(locally via pip is fine), just install the hooks::

    pre-commit install -f --install-hooks

The same checks are executed on the build server, so skipping the local linting
(with `git commit --no-verify`) will only result in a failed test build.

Current style checking tools:

- flake8: python linting
- isort: python import sorting
- black: python code formatting

Note:

    You must have python3.6 available on your path, as it is required for some
    of the hooks.
