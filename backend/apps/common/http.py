import json

from django.http import JsonResponse


def ok(data=None, **extra):
    payload = {"success": True}
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return JsonResponse(payload, json_dumps_params={"ensure_ascii": False})


def fail(message, status=400, code="bad_request", **extra):
    payload = {"success": False, "code": code, "message": message}
    payload.update(extra)
    return JsonResponse(payload, status=status, json_dumps_params={"ensure_ascii": False})


def parse_json(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def require_method(request, methods):
    if request.method not in methods:
        return fail("请求方法不支持", status=405, code="method_not_allowed")
    return None

