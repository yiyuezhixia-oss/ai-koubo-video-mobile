import time
from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from apps.accounts.services import authenticate_access_token, get_request_user
from apps.accounts.models import UserRightsRequest
from apps.billing.models import PointLedger
from apps.billing.services import (
    InvalidRedemptionCode,
    TTS_MAX_CHARS,
    VOICE_CONFIRM_POINTS,
    calculate_digital_human_points,
    calculate_tts_points,
    redeem_code,
)
from apps.common.http import fail, ok, parse_json

from .models import ExternalJob, MediaFile, Task, Voice, VoiceAuthorization
from .serializers import media_to_dict, point_account_to_dict, profile_to_dict, task_to_dict, voice_to_dict
from .services import (
    OperationInProgress,
    clone_voice_preview,
    complete_digital_human_from_callback,
    confirm_voice,
    create_task,
    discard_voice,
    generate_digital_human,
    generate_tts,
    get_user_task,
    rewrite_script,
    save_media_upload,
    sync_digital_human_job,
)


def idempotency_key(request, prefix):
    supplied = request.headers.get("X-Idempotency-Key", "")
    return supplied or f"{prefix}:{int(time.time() * 1000)}"


def current_account(user):
    return point_account_to_dict(user.point_account)


def task_payload(task):
    return {"task": task_to_dict(task), "account": current_account(task.user)}


def voice_payload(voice):
    return {"voice": voice_to_dict(voice), "account": current_account(voice.user)}


def handle_error(exc):
    status = 400
    code = "bad_request"
    if exc.__class__.__name__ == "InsufficientPoints":
        code = "insufficient_points"
    elif isinstance(exc, OperationInProgress):
        code = "operation_in_progress"
        status = 409
    elif isinstance(exc, PermissionError):
        code = "permission_denied"
        status = 403
    return fail(str(exc), status=status, code=code)


@csrf_exempt
def me_view(request):
    user = get_request_user(request)
    if request.method != "GET":
        return fail("Method not allowed", status=405, code="method_not_allowed")
    return ok(
        {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                **profile_to_dict(user.profile),
                "point_balance": user.point_account.balance,
            },
            "account": current_account(user),
        }
    )


@csrf_exempt
def rights_request_view(request):
    user = get_request_user(request)
    if request.method == "GET":
        items = UserRightsRequest.objects.filter(user=user)[:50]
        return ok({"items": [
            {
                "id": item.id,
                "request_type": item.request_type,
                "content": item.content,
                "status": item.status,
                "response_note": item.response_note,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ]})
    if request.method == "POST":
        data = parse_json(request)
        request_type = data.get("request_type", "")
        valid_types = {choice[0] for choice in UserRightsRequest.REQUEST_TYPES}
        if request_type not in valid_types:
            return fail("不支持的申请类型", code="invalid_request_type")
        item = UserRightsRequest.objects.create(
            user=user,
            request_type=request_type,
            content=str(data.get("content", "")).strip()[:2000],
        )
        return ok({"request": {"id": item.id, "request_type": item.request_type, "status": item.status}})
    return fail("Method not allowed", status=405, code="method_not_allowed")


@csrf_exempt
def pricing_view(request):
    if request.method != "POST":
        return fail("Method not allowed", status=405, code="method_not_allowed")
    data = parse_json(request)
    text = data.get("text", "")
    duration = data.get("duration_seconds", 60)
    try:
        return ok(
            {
                "rewrite_points": 1,
                "voice_confirm_points": VOICE_CONFIRM_POINTS,
                "tts_points": calculate_tts_points(text),
                "tts_max_chars": TTS_MAX_CHARS,
                "digital_human_points": calculate_digital_human_points(duration),
            }
        )
    except Exception as exc:
        return handle_error(exc)


@csrf_exempt
def redeem_code_view(request):
    user = get_request_user(request)
    if request.method != "POST":
        return fail("Method not allowed", status=405, code="method_not_allowed")
    try:
        account = redeem_code(user, parse_json(request).get("code", ""))
        return ok({"account": point_account_to_dict(account)})
    except InvalidRedemptionCode as exc:
        return fail(str(exc), code="invalid_redemption_code")


@csrf_exempt
def ledger_list_view(request):
    user = get_request_user(request)
    if request.method != "GET":
        return fail("Method not allowed", status=405, code="method_not_allowed")
    ledgers = PointLedger.objects.filter(user=user)[:50]
    return ok(
        {
            "items": [
                {
                    "id": item.id,
                    "action": item.action,
                    "amount": item.amount,
                    "balance_after": item.balance_after,
                    "frozen_after": item.frozen_after,
                    "reason": item.reason,
                    "note": item.note,
                    "created_at": item.created_at.isoformat(),
                }
                for item in ledgers
            ]
        }
    )


@csrf_exempt
def task_list_create_view(request):
    user = get_request_user(request)
    if request.method == "GET":
        tasks = Task.objects.filter(user=user).select_related("selected_voice", "tts_audio_file", "source_video_file", "output_video_file")
        return ok({"items": [task_to_dict(task) for task in tasks]})
    if request.method == "POST":
        data = parse_json(request)
        try:
            task = create_task(
                user,
                original_text=data.get("original_text", ""),
                source_type=data.get("source_type", "douyin_link"),
                source_url=data.get("source_url", ""),
            )
            return ok(task_payload(task))
        except Exception as exc:
            return handle_error(exc)
    return fail("Method not allowed", status=405, code="method_not_allowed")


@csrf_exempt
def task_detail_view(request, task_id):
    user = get_request_user(request)
    task = get_object_or_404(Task, id=task_id, user=user)
    if request.method == "GET":
        return ok(task_payload(task))
    if request.method == "PATCH":
        data = parse_json(request)
        editable = ["title", "original_text", "rewritten_text", "source_type", "source_url"]
        changed = []
        for key in editable:
            if key in data:
                setattr(task, key, data[key])
                changed.append(key)
        if changed:
            task.save(update_fields=[*changed, "updated_at"])
        return ok(task_payload(task))
    return fail("Method not allowed", status=405, code="method_not_allowed")


@csrf_exempt
def rewrite_task_view(request, task_id):
    user = get_request_user(request)
    if request.method != "POST":
        return fail("Method not allowed", status=405, code="method_not_allowed")
    task = get_object_or_404(Task, id=task_id, user=user)
    data = parse_json(request)
    try:
        task = rewrite_script(
            user,
            task,
            data.get("text", task.original_text),
            idempotency_key(request, f"rewrite:{task.id}"),
            yaoqiu=data.get("Requirement") or data.get("requirement") or data.get("yaoqiu", ""),
        )
        return ok(task_payload(task))
    except Exception as exc:
        return handle_error(exc)


@csrf_exempt
def voice_list_view(request):
    user = get_request_user(request)
    if request.method != "GET":
        return fail("Method not allowed", status=405, code="method_not_allowed")
    status = request.GET.get("status")
    voices = Voice.objects.filter(user=user)
    if status:
        voices = voices.filter(status=status)
    return ok({"items": [voice_to_dict(voice) for voice in voices]})


@csrf_exempt
def voice_detail_view(request, voice_id):
    user = get_request_user(request)
    voice = get_object_or_404(Voice, id=voice_id, user=user)
    if request.method != "GET":
        return fail("Method not allowed", status=405, code="method_not_allowed")
    return ok(voice_payload(voice))


@csrf_exempt
def voice_clone_preview_view(request):
    user = get_request_user(request)
    if request.method != "POST":
        return fail("Method not allowed", status=405, code="method_not_allowed")
    try:
        file_obj = request.FILES.get("audio_file")
        if not file_obj:
            return fail("请上传用于克隆的真实音频文件", code="missing_audio_file")
        voice_name = request.POST.get("voice_name", "")
        test_text = request.POST.get("text", "")
        ownership_confirmed = request.POST.get("ownership_confirmed") == "true"
        separate_consent_confirmed = request.POST.get("separate_consent_confirmed") == "true"
        if not ownership_confirmed or not separate_consent_confirmed:
            return fail("请确认声音权属并取得被编辑者的单独同意", status=403, code="voice_authorization_required")
        media = save_media_upload(user, file_obj, "source_audio")
        voice = clone_voice_preview(
            user,
            voice_name,
            test_text,
            idempotency_key(request, "voice-preview"),
            media=media,
        )
        VoiceAuthorization.objects.create(
            user=user,
            voice=voice,
            source_audio_file=media,
            ownership_confirmed=True,
            separate_consent_confirmed=True,
            ip_address=request.META.get("REMOTE_ADDR") or None,
            user_agent=request.headers.get("User-Agent", "")[:300],
        )
        return ok(voice_payload(voice))
    except Exception as exc:
        return handle_error(exc)


@csrf_exempt
def voice_confirm_view(request, voice_id):
    user = get_request_user(request)
    if request.method != "POST":
        return fail("Method not allowed", status=405, code="method_not_allowed")
    voice = get_object_or_404(Voice, id=voice_id, user=user)
    try:
        return ok(voice_payload(confirm_voice(user, voice, idempotency_key(request, f"voice-confirm:{voice.id}"))))
    except Exception as exc:
        return handle_error(exc)


@csrf_exempt
def voice_discard_view(request, voice_id):
    user = get_request_user(request)
    if request.method != "POST":
        return fail("Method not allowed", status=405, code="method_not_allowed")
    voice = get_object_or_404(Voice, id=voice_id, user=user)
    try:
        return ok(voice_payload(discard_voice(user, voice)))
    except Exception as exc:
        return handle_error(exc)


@csrf_exempt
def media_upload_view(request):
    user = get_request_user(request)
    if request.method != "POST":
        return fail("Method not allowed", status=405, code="method_not_allowed")
    try:
        data = request.POST
        file_obj = request.FILES.get("file")
        if not file_obj:
            return fail("请选择要上传的视频文件", code="missing_file")
        file_type = data.get("file_type", "source_video")
        if file_type != "source_video":
            return fail("不支持的文件类型", code="invalid_file_type")
        task_id = data.get("task_id")
        task = Task.objects.filter(id=task_id, user=user).first() if task_id else None
        if not task:
            return fail("任务不存在", status=404, code="task_not_found")
        duration = float(data.get("duration", 0) or 0)
        media = save_media_upload(user, file_obj, file_type, task=task, duration=duration)
        if media.task and media.file_type == "source_video":
            media.task.source_video_file = media
            media.task.status = "video_uploaded"
            media.task.current_step = "video"
            media.task.save(update_fields=["source_video_file", "status", "current_step", "updated_at"])
        return ok({"media": media_to_dict(media), "task": task_to_dict(media.task) if media.task else None})
    except Exception as exc:
        return handle_error(exc)


@csrf_exempt
def tts_generate_view(request, task_id):
    user = get_request_user(request)
    if request.method != "POST":
        return fail("Method not allowed", status=405, code="method_not_allowed")
    task = get_object_or_404(Task, id=task_id, user=user)
    data = parse_json(request)
    voice = get_object_or_404(Voice, id=data.get("voice_id"), user=user)
    try:
        if data.get("text") is not None:
            task.rewritten_text = data.get("text", "")
            task.save(update_fields=["rewritten_text", "updated_at"])
        task, points = generate_tts(
            user,
            task,
            voice,
            idempotency_key(request, f"tts:{task.id}"),
            pitch=data.get("pitch", 0),
            speed=data.get("speed", 1.0),
            volume=data.get("volume", 1.0),
            emotion=data.get("emotion", ""),
        )
        return ok({**task_payload(task), "points": points})
    except Exception as exc:
        return handle_error(exc)


@csrf_exempt
def digital_human_generate_view(request, task_id):
    user = get_request_user(request)
    if request.method != "POST":
        return fail("Method not allowed", status=405, code="method_not_allowed")
    task = get_object_or_404(Task, id=task_id, user=user)
    data = parse_json(request)
    media_id = data.get("source_video_media_id")
    source_video = MediaFile.objects.filter(id=media_id, user=user, file_type="source_video").first() if media_id else task.source_video_file
    if not source_video:
        return fail("Missing source video", code="missing_source_video")
    try:
        notify_url = data.get("notify_url", "")
        if not notify_url and settings.PUBLIC_BASE_URL:
            notify_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/api/callbacks/hihoo/digital-human/"
        if not notify_url and settings.ALLOW_PROVIDER_MOCKS:
            notify_url = "mock://hihoo-callback"
        if not notify_url:
            return fail("数字人回调地址未配置", code="missing_notify_url")
        task, job = generate_digital_human(user, task, source_video, idempotency_key(request, f"digital-human:{task.id}"), notify_url)
        return ok({**task_payload(task), "job": {"id": job.id, "status": job.status, "provider_task_id": job.provider_task_id}})
    except Exception as exc:
        return handle_error(exc)


@csrf_exempt
def task_sync_view(request, task_id):
    user = get_request_user(request)
    if request.method != "POST":
        return fail("Method not allowed", status=405, code="method_not_allowed")
    task = get_object_or_404(Task, id=task_id, user=user)
    job = task.external_jobs.filter(provider="hihoo", job_type="digital_human").order_by("-id").first()
    if not job:
        return fail("No external job", code="missing_external_job")
    try:
        if job.status not in ("succeeded", "failed"):
            job = sync_digital_human_job(job, idempotency_key(request, f"sync:{job.id}"))
        task.refresh_from_db()
        return ok({**task_payload(task), "job": {"id": job.id, "status": job.status, "provider_task_id": job.provider_task_id}})
    except Exception as exc:
        return handle_error(exc)


def get_request_or_query_user(request):
    raw_token = (request.GET.get("access_token") or "").strip()
    if raw_token:
        return authenticate_access_token(raw_token)
    return get_request_user(request)


@csrf_exempt
def task_download_output_view(request, task_id):
    user = get_request_or_query_user(request)
    if request.method != "GET":
        return fail("Method not allowed", status=405, code="method_not_allowed")
    task = get_object_or_404(Task.objects.select_related("output_video_file"), id=task_id, user=user)
    media = task.output_video_file
    if not media or not media.file_path:
        return fail("成片文件不存在，请先生成成片", status=404, code="missing_output_video")
    media_root = Path(settings.MEDIA_ROOT).resolve()
    file_path = (media_root / media.file_path).resolve()
    if media_root not in file_path.parents and file_path != media_root:
        return fail("文件路径无效", status=400, code="invalid_media_path")
    if not file_path.exists():
        return fail("成片文件已失效，请重新生成", status=404, code="output_video_not_found")
    filename = file_path.name
    return FileResponse(
        file_path.open("rb"),
        as_attachment=True,
        filename=filename,
        content_type=media.mime_type or "video/mp4",
    )


@csrf_exempt
def hihoo_callback_view(request):
    if request.method != "POST":
        return fail("Method not allowed", status=405, code="method_not_allowed")
    data = request.POST.dict() if request.POST else parse_json(request)
    provider_task_id = str(data.get("taskid") or data.get("task_id") or "")
    job = ExternalJob.objects.filter(provider="hihoo", provider_task_id=provider_task_id).first()
    if not job:
        return fail("Job not found", status=404, code="job_not_found")
    target_file = request.FILES.get("target_file")
    if target_file:
        complete_digital_human_from_callback(job, target_file, data)
        return ok({"received": True})
    with transaction.atomic():
        if job.status not in ("succeeded", "failed"):
            job = sync_digital_human_job(job, f"callback:{job.id}")
    return ok({"received": True})
