import hashlib
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.billing.services import ensure_point_account

from .models import AccessToken, Profile


class AuthenticationRequired(Exception):
    pass


def _token_hash(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


SYSTEM_VOICES = (
    ("male-qn-qingse", "青涩男声"),
    ("male-qn-jingying", "精英男声"),
    ("male-qn-badao", "霸道男声"),
    ("male-qn-daxuesheng", "男大学生"),
    ("presenter_male", "男主持人"),
    ("audiobook_male_1", "有声书男声一"),
    ("audiobook_male_2", "有声书男声二"),
    ("female-shaonv", "少女音色"),
    ("female-yujie", "御姐女声"),
    ("female-chengshu", "成熟女声"),
    ("female-tianmei", "甜美女声"),
    ("presenter_female", "女主持人"),
    ("audiobook_female_1", "有声书女声一"),
    ("audiobook_female_2", "有声书女声二"),
    ("clever_boy", "聪明男童"),
    ("cute_girl", "可爱女童"),
)


def ensure_default_voice(user):
    from apps.creator.models import Voice

    existing = {
        voice.provider_voice_id: voice
        for voice in Voice.objects.filter(
            user=user,
            provider_voice_id__in=[voice_id for voice_id, _ in SYSTEM_VOICES],
        )
    }
    default_voice = None
    for provider_voice_id, name in SYSTEM_VOICES:
        sample_url = f"/audio/voices/{provider_voice_id}.mp3"
        voice = existing.get(provider_voice_id)
        if not voice:
            voice = Voice.objects.create(
                user=user,
                provider_voice_id=provider_voice_id,
                name=name,
                provider="minimax_system",
                status="available",
                sample_audio_url=sample_url,
                confirmed_at=timezone.now(),
                must_use_before=None,
            )
        if provider_voice_id == "female-shaonv":
            default_voice = voice
    return default_voice


def create_guest_user():
    if not settings.ALLOW_ANONYMOUS_AUTH:
        raise PermissionError("生产环境不允许匿名登录，请使用微信登录")
    User = get_user_model()
    username = f"guest_{uuid4().hex}"
    user = User.objects.create_user(username=username, password=None, email="")
    Profile.objects.create(
        user=user,
        nickname="体验用户",
    )
    ensure_point_account(user)
    ensure_default_voice(user)
    return user


def issue_access_token(user, label="wechat"):
    raw_token = secrets.token_urlsafe(48)
    AccessToken.objects.create(
        user=user,
        token_hash=_token_hash(raw_token),
        label=label,
        expires_at=timezone.now() + timedelta(days=30),
    )
    return raw_token


def authenticate_access_token(raw_token):
    token = AccessToken.objects.select_related("user").filter(
        token_hash=_token_hash(raw_token),
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).first()
    if not token:
        raise AuthenticationRequired("登录状态无效或已过期，请重新登录")
    now = timezone.now()
    if not token.last_used_at or token.last_used_at < now - timedelta(minutes=5):
        AccessToken.objects.filter(pk=token.pk).update(last_used_at=now)
    return token.user


def login_with_wechat(code, nickname="", avatar_url=""):
    if not settings.WECHAT_APP_ID or not settings.WECHAT_APP_SECRET:
        raise RuntimeError("微信小程序 AppID 或 AppSecret 尚未配置")
    if not (code or "").strip():
        raise ValueError("缺少 wx.login 返回的 code")
    query = urllib.parse.urlencode(
        {
            "appid": settings.WECHAT_APP_ID,
            "secret": settings.WECHAT_APP_SECRET,
            "js_code": code.strip(),
            "grant_type": "authorization_code",
        }
    )
    request = urllib.request.Request(
        f"https://api.weixin.qq.com/sns/jscode2session?{query}",
        headers={"Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"微信登录服务调用失败：{exc}") from exc
    if payload.get("errcode") not in (None, 0, "0") or not payload.get("openid"):
        raise RuntimeError(payload.get("errmsg") or "微信登录凭证校验失败")

    profile = Profile.objects.select_related("user").filter(wx_openid=payload["openid"]).first()
    if profile:
        user = profile.user
    else:
        User = get_user_model()
        user = User.objects.create_user(username=f"wx_{uuid4().hex}", password=None)
        profile = Profile.objects.create(
            user=user,
            wx_openid=payload["openid"],
            wx_unionid=payload.get("unionid", ""),
            nickname=(nickname or "微信用户").strip()[:64],
            avatar_url=avatar_url or "",
        )
    changed = []
    if nickname and profile.nickname != nickname.strip()[:64]:
        profile.nickname = nickname.strip()[:64]
        changed.append("nickname")
    if avatar_url and profile.avatar_url != avatar_url:
        profile.avatar_url = avatar_url
        changed.append("avatar_url")
    if payload.get("unionid") and profile.wx_unionid != payload["unionid"]:
        profile.wx_unionid = payload["unionid"]
        changed.append("wx_unionid")
    if changed:
        profile.save(update_fields=[*changed, "updated_at"])
    ensure_point_account(user)
    ensure_default_voice(user)
    return user


def get_request_user(request):
    authorization = request.headers.get("Authorization", "")
    scheme, _, raw_token = authorization.partition(" ")
    if scheme.lower() == "bearer" and raw_token:
        user = authenticate_access_token(raw_token.strip())
        ensure_point_account(user)
        Profile.objects.get_or_create(user=user, defaults={"nickname": user.username})
        return user
    if getattr(request, "user", None) and request.user.is_authenticated:
        ensure_point_account(request.user)
        Profile.objects.get_or_create(user=request.user, defaults={"nickname": request.user.username})
        return request.user
    raise AuthenticationRequired("请先登录")
