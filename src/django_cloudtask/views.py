import functools
import json

from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .task import execute_task as task_execute
from .utils import verify_jwt


def require_oidc(f):
    """
    For use with Google endpoints.
    Requires a view to be authenticated.
    """

    @functools.wraps(f)
    def wrapper(request, *args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return HttpResponseForbidden()
        if not verify_jwt(token[len("Bearer ") :]):
            return HttpResponseForbidden()
        return f(request, *args, **kwargs)

    return csrf_exempt(wrapper)


@require_oidc
def execute_task(request):
    body = json.loads(request.body)
    function = body["function"]
    args = body["args"]
    kwargs = body["kwargs"]
    status = task_execute(function, args, kwargs)
    return JsonResponse({}, status=status)
