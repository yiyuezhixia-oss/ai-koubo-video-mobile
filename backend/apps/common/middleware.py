from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class ApiAuthenticationErrorMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        from apps.accounts.services import AuthenticationRequired

        if isinstance(exception, AuthenticationRequired) and request.path.startswith("/api/"):
            return JsonResponse(
                {
                    "success": False,
                    "code": "authentication_required",
                    "message": str(exception),
                },
                status=401,
                json_dumps_params={"ensure_ascii": False},
            )
        return None


class SimpleCorsMiddleware:
    """Allow configured browser origins without opening production APIs to every site."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            from django.http import HttpResponse

            response = HttpResponse()
        else:
            response = self.get_response(request)
        origin = request.headers.get("Origin", "").rstrip("/")
        if origin and (settings.DEBUG or origin in settings.CORS_ALLOWED_ORIGINS):
            response["Access-Control-Allow-Origin"] = origin
            response["Vary"] = "Origin"
            response["Access-Control-Allow-Methods"] = "GET,POST,PATCH,DELETE,OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type,Authorization,X-Requested-With,X-Idempotency-Key"
        return response
