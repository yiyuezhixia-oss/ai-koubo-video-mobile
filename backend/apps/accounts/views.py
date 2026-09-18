from django.views.decorators.csrf import csrf_exempt

from apps.common.http import fail, ok, parse_json

from .services import create_guest_user, issue_access_token, login_with_wechat


def _auth_payload(user, raw_token):
    return {
        "access_token": raw_token,
        "expires_in": 30 * 24 * 60 * 60,
        "user": {
            "id": user.id,
            "uid": user.profile.uid,
            "nickname": user.profile.nickname,
            "avatar_url": user.profile.avatar_url,
        },
    }


@csrf_exempt
def anonymous_login_view(request):
    if request.method != "POST":
        return fail("Method not allowed", status=405, code="method_not_allowed")
    try:
        user = create_guest_user()
        return ok(_auth_payload(user, issue_access_token(user, label="browser_dev")))
    except PermissionError as exc:
        return fail(str(exc), status=403, code="anonymous_auth_disabled")
    except Exception as exc:
        return fail(str(exc), code="auth_failed")


@csrf_exempt
def wechat_login_view(request):
    if request.method != "POST":
        return fail("Method not allowed", status=405, code="method_not_allowed")
    data = parse_json(request)
    try:
        user = login_with_wechat(
            data.get("code", ""),
            nickname=data.get("nickname", ""),
            avatar_url=data.get("avatar_url", ""),
        )
        return ok(_auth_payload(user, issue_access_token(user, label="wechat")))
    except ValueError as exc:
        return fail(str(exc), code="invalid_login_code")
    except Exception as exc:
        return fail(str(exc), code="wechat_login_failed")
