import io
import math
import mimetypes
import re
import struct
import subprocess
import time
import wave
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.billing.services import (
    REWRITE_POINTS,
    VOICE_CONFIRM_POINTS,
    calculate_digital_human_points,
    calculate_tts_points,
    claim_frozen_points,
    consume_frozen_points,
    refund_frozen_points,
)
from apps.billing.models import PointLedger
from apps.common.storage import cache_remote_file, media_duration, save_cropped_output_video, save_uploaded_file
from apps.integrations.deepseek import DeepSeekClient
from apps.integrations.hihoo import HiHooClient
from apps.integrations.minimax import MiniMaxClient

from .models import ApiCallLog, ExternalJob, MediaFile, Task, Voice


VIDEO_MAX_BYTES = 500 * 1024 * 1024
DEFAULT_REWRITE_REQUIREMENT = "保留原意，改写为自然流畅、适合短视频真人口播的完整文案。只输出改写后的文案，不要询问用户或输出说明。"
INVALID_REWRITE_MARKERS = (
    "请你提供需要二创",
    "请提供需要二创",
    "请提供原文案",
    "具体要求",
    "已按「",
    "只输出改写后的文案",
    "不要询问用户",
    "优化。",
)
URL_PATTERN = re.compile(r"https?://|v\.douyin\.com|www\.", re.IGNORECASE)


class OperationInProgress(Exception):
    pass


def _claim_paid_operation(user, amount, reason, idempotency_key, task=None, allow_in_progress=False):
    _, claimed = claim_frozen_points(
        user,
        amount,
        reason,
        f"{idempotency_key}:freeze",
        task=task,
    )
    if claimed:
        return True
    if PointLedger.objects.filter(
        user=user,
        action="consume",
        idempotency_key=f"{idempotency_key}:consume",
    ).exists():
        return False
    refund = PointLedger.objects.filter(
        user=user,
        action="refund",
        idempotency_key=f"{idempotency_key}:refund",
    ).first()
    if refund:
        raise RuntimeError(refund.note or "该请求此前已失败并退回积分")
    if allow_in_progress:
        return None
    raise OperationInProgress("相同请求正在处理中，请勿重复提交")


def _require_public_https_url(label, media_url):
    parsed = urlparse(media_url or "")
    if settings.ALLOW_PROVIDER_MOCKS and parsed.scheme in {"mock", "http", ""}:
        return
    if parsed.scheme != "https" or not parsed.hostname or parsed.hostname in {"127.0.0.1", "localhost"}:
        raise ValueError(f"{label}尚未存入公网对象存储，请先配置生产媒体存储")


def create_task(user, original_text="", source_type="manual", source_url=""):
    text = (original_text or "").strip()
    if source_type == "douyin_link":
        match = re.search(r"https?://[^\s]+", source_url or text, flags=re.IGNORECASE)
        if not match:
            raise ValueError("请提供有效的抖音分享链接")
        source_url = match.group(0)
    task = Task.objects.create(
        user=user,
        title=(text[:24] if text else "未命名口播任务"),
        source_type=source_type,
        source_url=source_url,
        original_text=text,
        rewritten_text="",
        status="draft",
        current_step="script",
    )
    return task


def get_user_task(user, task_id):
    return Task.objects.get(id=task_id, user=user)


def save_media_upload(user, uploaded_file, file_type, task=None, duration=0):
    if file_type == "source_video":
        suffix = Path(uploaded_file.name).suffix.lower()
        content_type = (getattr(uploaded_file, "content_type", "") or "").lower()
        if suffix != ".mp4" or content_type not in {"video/mp4", "application/octet-stream"}:
            raise ValueError("HiHoo 数字人仅支持 MP4 视频")
        if (getattr(uploaded_file, "size", 0) or 0) > VIDEO_MAX_BYTES:
            raise ValueError("视频文件不能超过 500MB")
        duration = media_duration(uploaded_file)
    subdir_map = {
        "source_audio": "source_audio",
        "tts_audio": "tts_audio",
        "source_video": "source_video",
        "output_video": "output_video",
    }
    subdir = subdir_map.get(file_type, "misc")
    if file_type == "output_video":
        relative, public_url, processed_size, processed_type, processed_duration = save_cropped_output_video(uploaded_file, subdir)
        duration = processed_duration or duration
    else:
        relative, public_url = save_uploaded_file(uploaded_file, subdir)
        processed_size = getattr(uploaded_file, "size", 0) or 0
        processed_type = getattr(uploaded_file, "content_type", "") or mimetypes.guess_type(relative)[0] or ""
    storage_type = "object" if settings.MEDIA_STORAGE_BACKEND == "object" else "local"
    return MediaFile.objects.create(
        user=user,
        task=task,
        file_type=file_type,
        storage_type=storage_type,
        file_path=relative,
        file_url=public_url,
        file_size=processed_size,
        duration=duration,
        mime_type=processed_type,
    )


def save_remote_media(user, remote_url, file_name, file_type, task=None, duration=0):
    if settings.ALLOW_PROVIDER_MOCKS and str(remote_url).startswith("mock://"):
        audio_bytes = _mock_wav_bytes()
        content_map = {
            "tts_audio": (audio_bytes, "audio/wav"),
            "source_audio": (audio_bytes, "audio/wav"),
            "output_video": (_mock_mp4_bytes(), "video/mp4"),
        }
        data, content_type = content_map.get(file_type, (b"mock-media", "application/octet-stream"))
        uploaded = ContentFile(data, name=file_name)
        uploaded.content_type = content_type
        relative, public_url = save_uploaded_file(uploaded, {
            "tts_audio": "tts_audio",
            "output_video": "output_video",
            "source_audio": "source_audio",
        }.get(file_type, "misc"))
        return MediaFile.objects.create(
            user=user,
            task=task,
            file_type=file_type,
            storage_type="local",
            file_path=relative,
            file_url=public_url,
            file_size=len(data),
            duration=duration,
            mime_type=content_type,
        )
    subdir_map = {
        "tts_audio": "tts_audio",
        "output_video": "output_video",
        "source_audio": "source_audio",
    }
    content_type_prefixes = {
        "tts_audio": ("audio/",),
        "source_audio": ("audio/",),
        "output_video": ("video/",),
    }
    cache_args = (remote_url, file_name, subdir_map.get(file_type, "misc"))
    cache_options = {
        "expected_content_type_prefixes": content_type_prefixes.get(file_type),
    }
    if file_type == "output_video":
        relative, public_url, file_size, content_type, detected_duration = cache_remote_file(
            *cache_args,
            crop_output_video=True,
            **cache_options,
        )
    else:
        relative, public_url, file_size, content_type, detected_duration = cache_remote_file(
            *cache_args,
            **cache_options,
        )
    return MediaFile.objects.create(
        user=user,
        task=task,
        file_type=file_type,
        storage_type="object" if settings.MEDIA_STORAGE_BACKEND == "object" else "local",
        file_path=relative,
        file_url=public_url,
        file_size=file_size,
        duration=detected_duration or duration,
        mime_type=content_type or mimetypes.guess_type(relative)[0] or "",
    )


def _mock_wav_bytes(duration_seconds=0.8, sample_rate=16000, frequency=440):
    frame_count = int(duration_seconds * sample_rate)
    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            frames = bytearray()
            for index in range(frame_count):
                sample = int(12000 * math.sin(2 * math.pi * frequency * index / sample_rate))
                frames.extend(struct.pack("<h", sample))
            wav_file.writeframes(bytes(frames))
        return buffer.getvalue()


def _mock_mp4_bytes(duration_seconds=1):
    with TemporaryDirectory() as directory:
        output_path = Path(directory) / "mock-output.mp4"
        command = [
            getattr(settings, "FFMPEG_BINARY", "ffmpeg"),
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x10131c:s=720x1280:d={duration_seconds}",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r=44100:cl=mono:d={duration_seconds}",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"本地 mock 成片生成失败：{result.stderr[-300:]}")
        return output_path.read_bytes()


def validate_rewrite_payload(initial_text, rewritten_text):
    initial = str(initial_text or "").strip()
    rewritten = str(rewritten_text or "").strip()
    if not initial:
        raise RuntimeError("请粘贴完整原文或字幕后再改写")
    if URL_PATTERN.search(initial) and len(initial) < 80:
        raise RuntimeError("文案工作流只返回了链接，没有返回提取后的原始文案")
    if not rewritten:
        raise RuntimeError("AI 未返回改写文案")
    if URL_PATTERN.search(rewritten):
        raise RuntimeError("AI 改写结果包含链接，不符合口播文案验收标准")
    if any(marker in rewritten for marker in INVALID_REWRITE_MARKERS):
        raise RuntimeError("AI 改写结果包含提示词或无效说明，不符合口播文案验收标准")
    if len(rewritten) < 80:
        raise RuntimeError("AI 改写结果过短，不符合可直接口播的最低标准")
    return initial, rewritten


def rewrite_script(user, task, text, idempotency_key, yaoqiu=""):
    source_text = (text or task.original_text).strip()
    if not source_text or URL_PATTERN.search(source_text):
        raise ValueError("请粘贴视频原文或字幕，DeepSeek 不解析抖音分享链接")
    claimed = _claim_paid_operation(user, REWRITE_POINTS, "rewrite", idempotency_key, task=task)
    if not claimed:
        return task
    client = DeepSeekClient()
    started = time.perf_counter()
    try:
        response = client.rewrite(source_text, (yaoqiu or "").strip() or DEFAULT_REWRITE_REQUIREMENT)
        response_data = response.get("data", response) if isinstance(response, dict) else response
        rewritten = response_data.get("rewritten_text") or response_data.get("Last_text") if isinstance(response_data, dict) else response_data
        initial_text, rewritten = validate_rewrite_payload(source_text, rewritten)
        task.original_text = initial_text
        task.rewritten_text = rewritten
        task.status = "rewrite_done"
        task.current_step = "rewrite"
        task.point_cost_total += REWRITE_POINTS
        task.error_message = ""
        task.save()
        consume_frozen_points(user, REWRITE_POINTS, "rewrite", f"{idempotency_key}:consume", task=task)
        ApiCallLog.objects.create(
            user=user,
            task=task,
            provider="deepseek",
            api_type="rewrite",
            endpoint="chat/completions",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return task
    except Exception as exc:
        task.status = "failed"
        task.error_message = str(exc)
        task.refund_status = "refunded"
        task.save(update_fields=["status", "error_message", "refund_status", "updated_at"])
        refund_frozen_points(user, REWRITE_POINTS, "rewrite", f"{idempotency_key}:refund", task=task, note=str(exc))
        ApiCallLog.objects.create(
            user=user,
            task=task,
            provider="deepseek",
            api_type="rewrite",
            request_status="failed",
            error_message=str(exc),
        )
        raise


def make_provider_voice_id(user_id):
    return f"Zhixia{user_id}{int(time.time())}"


def clone_voice_preview(user, voice_name, test_text, idempotency_key, media=None):
    voice_name = (voice_name or "").strip()
    test_text = (test_text or "").strip()
    if not media:
        raise ValueError("请上传用于克隆的真实音频文件")
    if not voice_name:
        raise ValueError("请填写音色名称")
    if not test_text:
        raise ValueError("请填写试听文案")
    provider_voice_id = make_provider_voice_id(user.id)
    voice, created = Voice.objects.get_or_create(
        user=user,
        idempotency_key=idempotency_key,
        defaults={
            "name": voice_name,
            "provider_voice_id": provider_voice_id,
            "source_audio_file": media,
            "clone_test_text": test_text,
            "status": "cloning",
        },
    )
    if not created:
        if voice.status in {"pending_confirm", "available"}:
            return voice
        if voice.status == "failed":
            raise RuntimeError(voice.error_message or "该克隆请求此前已失败")
        raise OperationInProgress("相同音色克隆请求正在处理中")
    client = MiniMaxClient()
    started = time.perf_counter()
    try:
        source_path = Path(settings.MEDIA_ROOT) / media.file_path
        if source_path.exists():
            audio_bytes = source_path.read_bytes()
        else:
            from apps.common.storage import download_remote_file
            audio_bytes = download_remote_file(media.file_url, Path(media.file_path).name).read()
        data = client.clone_preview(Path(media.file_path).name, audio_bytes, provider_voice_id, test_text)
        sample_url = data.get("demo_audio") or data.get("test_audio")
        returned_voice_id = data.get("voice_id") or provider_voice_id
        if not sample_url:
            raise RuntimeError("声音克隆工作流未返回试听音频 URL")
        _require_public_https_url("试听音频", sample_url)
        sample_suffix = Path(unquote(urlparse(sample_url).path)).suffix.lower() or ".mp3"
        sample_media = save_remote_media(
            user,
            sample_url,
            f"voice-sample-{voice.id}{sample_suffix}",
            "source_audio",
        )
        voice.name = data.get("voice_name") or voice_name
        voice.provider_voice_id = returned_voice_id
        voice.sample_audio_file = sample_media
        voice.sample_audio_url = sample_media.file_url
        voice.status = "pending_confirm"
        voice.error_message = ""
        voice.save(
            update_fields=["name", "provider_voice_id", "sample_audio_file", "sample_audio_url", "status", "error_message", "updated_at"]
        )
        ApiCallLog.objects.create(
            user=user,
            provider="minimax",
            api_type="voice_clone_preview",
            endpoint="voice_clone",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return voice
    except Exception as exc:
        voice.status = "failed"
        voice.error_message = str(exc)
        voice.save(update_fields=["status", "error_message", "updated_at"])
        ApiCallLog.objects.create(user=user, provider="minimax", api_type="voice_clone_preview", request_status="failed", error_message=str(exc))
        raise


@transaction.atomic
def confirm_voice(user, voice, idempotency_key):
    voice = Voice.objects.select_for_update().get(pk=voice.pk)
    if voice.user_id != user.id:
        raise PermissionError("无权操作该音色")
    if voice.status == "available":
        return voice
    if voice.status != "pending_confirm":
        raise ValueError("只有试听确认后的音色可以入库")
    freeze_points(user, VOICE_CONFIRM_POINTS, "voice_clone", f"{idempotency_key}:freeze")
    now = timezone.now()
    voice.status = "available"
    voice.confirmed_at = now
    voice.must_use_before = now + timezone.timedelta(days=7)
    voice.save(update_fields=["status", "confirmed_at", "must_use_before", "updated_at"])
    consume_frozen_points(user, VOICE_CONFIRM_POINTS, "voice_clone", f"{idempotency_key}:consume")
    return voice


def discard_voice(user, voice):
    if voice.user_id != user.id:
        raise PermissionError("无权操作该音色")
    voice.status = "discarded"
    voice.discarded_at = timezone.now()
    voice.save(update_fields=["status", "discarded_at", "updated_at"])
    return voice


def generate_tts(user, task, voice, idempotency_key, pitch=0, speed=1.0, volume=1.0, emotion=""):
    if voice.user_id != user.id or voice.status != "available":
        raise ValueError("请选择可用音色")
    text = task.rewritten_text or task.original_text
    points = calculate_tts_points(text)
    if points <= 0:
        raise ValueError("配音文案不能为空")
    pitch = max(-12, min(12, int(pitch)))
    speed = max(0.5, min(2.0, float(speed)))
    volume = max(0.1, min(2.0, float(volume)))
    emotion = str(emotion or "").strip().lower()
    supported_emotions = {"happy", "sad", "angry", "fearful", "disgusted", "surprised", "calm"}
    if emotion and emotion not in supported_emotions:
        raise ValueError("不支持的声音情绪")
    claimed = _claim_paid_operation(user, points, "tts", idempotency_key, task=task)
    if not claimed:
        if not task.tts_audio_file:
            raise RuntimeError("该配音请求已扣费，但没有找到生成结果，请联系管理员")
        return task, points
    client = MiniMaxClient()
    started = time.perf_counter()
    try:
        response = client.synthesize(text, voice.provider_voice_id, pitch=pitch, speed=speed, volume=volume)
        response_data = response.get("data", response) if isinstance(response, dict) else response
        audio_url = response_data.get("output") if isinstance(response_data, dict) else response_data
        if not audio_url:
            raise RuntimeError("TTS 工作流未返回音频 URL")
        _require_public_https_url("TTS 音频", audio_url)
        suffix = Path(unquote(urlparse(audio_url).path)).suffix.lower()
        if suffix not in {".mp3", ".wav", ".m4a", ".aac"}:
            suffix = ".mp3"
        media = save_remote_media(
            user,
            audio_url,
            f"tts-{task.id}{suffix}",
            "tts_audio",
            task=task,
            duration=max(len(text) / 4, 1),
        )
        task.selected_voice = voice
        task.tts_audio_file = media
        task.status = "tts_done"
        task.current_step = "video"
        task.point_cost_total += points
        task.save()
        if not voice.first_used_at:
            voice.first_used_at = timezone.now()
            voice.save(update_fields=["first_used_at", "updated_at"])
        consume_frozen_points(user, points, "tts", f"{idempotency_key}:consume", task=task)
        ApiCallLog.objects.create(
            user=user,
            task=task,
            provider="minimax",
            api_type="voice_tts",
            endpoint="t2a_v2",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return task, points
    except Exception as exc:
        task.status = "failed"
        task.error_message = str(exc)
        task.refund_status = "refunded"
        task.save(update_fields=["status", "error_message", "refund_status", "updated_at"])
        refund_frozen_points(user, points, "tts", f"{idempotency_key}:refund", task=task, note=str(exc))
        ApiCallLog.objects.create(user=user, task=task, provider="minimax", api_type="voice_tts", request_status="failed", error_message=str(exc))
        raise


def generate_digital_human(user, task, source_video, idempotency_key, notify_url):
    if not task.tts_audio_file:
        raise ValueError("请先生成配音")
    if source_video.user_id != user.id or source_video.task_id != task.id:
        raise PermissionError("该视频不属于当前任务")
    for label, media_url in (
        ("配音", task.tts_audio_file.file_url),
        ("视频", source_video.file_url),
    ):
        _require_public_https_url(label, media_url)
    duration = task.tts_audio_file.duration or 60
    if duration > 300:
        raise ValueError("数字人口播配音不能超过 5 分钟，请缩短文案后重新生成配音")
    video_duration = source_video.duration or 0
    if video_duration and duration > video_duration + 0.5:
        difference = duration - video_duration
        raise ValueError(
            f"配音比视频长 {difference:.1f} 秒。请上传至少 {duration:.1f} 秒的视频，或缩短文案后重新生成配音"
        )
    points = calculate_digital_human_points(duration)
    claimed = _claim_paid_operation(
        user,
        points,
        "digital_human",
        idempotency_key,
        task=task,
        allow_in_progress=True,
    )
    if not claimed:
        job = ExternalJob.objects.filter(
            user=user,
            provider="hihoo",
            job_type="digital_human",
            idempotency_key=idempotency_key,
        ).first()
        if not job:
            raise RuntimeError("该数字人请求已结算，但没有找到任务记录，请联系管理员")
        if job.status == "failed":
            raise RuntimeError(job.error_message or "该数字人请求此前已失败")
        return task, job
    job = ExternalJob.objects.create(
        user=user,
        task=task,
        provider="hihoo",
        job_type="digital_human",
        status="pending",
        cost_points=points,
        idempotency_key=idempotency_key,
        request_payload_summary={"audio_url": task.tts_audio_file.file_url, "video_url": source_video.file_url},
    )
    client = HiHooClient()
    try:
        response = client.submit_digital_human(task.tts_audio_file.file_url, source_video.file_url, notify_url)
        task_id = str((response.get("data") or {}).get("taskid") or "")
        if response.get("code") not in (200, "200") or not task_id:
            raise RuntimeError(response.get("msg") or "HiHoo 提交失败")
        job.provider_task_id = task_id
        job.status = "processing"
        job.response_payload_summary = response
        job.submitted_at = timezone.now()
        job.save()
        task.source_video_file = source_video
        task.status = "generating"
        task.current_step = "generating"
        task.save()
        return task, job
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
        task.status = "failed"
        task.error_message = str(exc)
        task.refund_status = "refunded"
        task.save(update_fields=["status", "error_message", "refund_status", "updated_at"])
        refund_frozen_points(user, points, "digital_human", f"{idempotency_key}:refund", task=task, external_job=job, note=str(exc))
        raise


@transaction.atomic
def sync_digital_human_job(job, idempotency_key="sync"):
    job = ExternalJob.objects.select_for_update().select_related("task", "user").get(pk=job.pk)
    if job.status in {"succeeded", "failed"}:
        return job
    client = HiHooClient()
    result = client.query_digital_human(job.provider_task_id)
    if result.get("code") not in (200, "200"):
        raise RuntimeError(result.get("msg") or "HiHoo 查询失败")
    data = result.get("data") or result
    if "status" not in data:
        raise RuntimeError("HiHoo 查询响应缺少任务状态")
    status = int(data["status"])
    task = Task.objects.select_for_update().get(pk=job.task_id)
    if status == 3:
        result_url = data.get("result_video_url")
        if not result_url:
            raise RuntimeError("HiHoo 已返回成功，但缺少成片 URL")
        source_url = (job.request_payload_summary or {}).get("video_url", "")
        if result_url == source_url:
            # V1 sends the rendered video as target_file in its multipart callback.
            # The query endpoint can echo the source URL after processing completes.
            job.status = "processing"
            job.response_payload_summary = result
            job.save(update_fields=["status", "response_payload_summary", "updated_at"])
            return job
        _require_public_https_url("数字人成片", result_url)
        result_suffix = Path(unquote(urlparse(result_url).path)).suffix.lower() or ".mp4"
        media = save_remote_media(
            job.user,
            result_url,
            f"digital-human-{job.id}{result_suffix}",
            "output_video",
            task=task,
            duration=float(data.get("video_time") or 0),
        )
        job.status = "succeeded"
        job.result_url = result_url
        job.result_media_file = media
        job.response_payload_summary = result
        job.finished_at = timezone.now()
        job.save()
        task.output_video_file = media
        task.status = "completed"
        task.current_step = "preview"
        task.point_cost_total += job.cost_points
        task.refund_status = ""
        task.error_message = ""
        task.save()
        consume_frozen_points(
            job.user,
            job.cost_points,
            "digital_human",
            f"{job.idempotency_key}:consume",
            task=task,
            external_job=job,
        )
    elif status == 4:
        error = data.get("msg") or result.get("msg") or "数字人生成失败"
        job.status = "failed"
        job.error_message = error
        job.response_payload_summary = result
        job.finished_at = timezone.now()
        job.save()
        task.status = "failed"
        task.error_message = error
        task.refund_status = "refunded"
        task.save()
        refund_frozen_points(
            job.user,
            job.cost_points,
            "digital_human",
            f"{job.idempotency_key}:refund",
            task=task,
            external_job=job,
            note=error,
        )
    else:
        job.status = "processing"
        job.response_payload_summary = result
        job.save(update_fields=["status", "response_payload_summary", "updated_at"])
    return job


@transaction.atomic
def complete_digital_human_from_callback(job, uploaded_file, callback_data=None):
    job = ExternalJob.objects.select_for_update().select_related("task", "user").get(pk=job.pk)
    task = Task.objects.select_for_update().get(pk=job.task_id)
    callback_data = callback_data or {}
    media = save_media_upload(
        job.user,
        uploaded_file,
        "output_video",
        task=task,
        duration=float(callback_data.get("video_time") or 0),
    )
    already_consumed = PointLedger.objects.filter(
        user=job.user,
        action="consume",
        idempotency_key=f"{job.idempotency_key}:consume",
    ).exists()
    job.status = "succeeded"
    job.result_url = media.file_url
    job.result_media_file = media
    job.response_payload_summary = callback_data
    job.error_message = ""
    job.finished_at = timezone.now()
    job.save()
    task.output_video_file = media
    task.status = "completed"
    task.current_step = "preview"
    if not already_consumed:
        task.point_cost_total += job.cost_points
    task.refund_status = ""
    task.error_message = ""
    task.save()
    if not already_consumed:
        consume_frozen_points(
            job.user,
            job.cost_points,
            "digital_human",
            f"{job.idempotency_key}:consume",
            task=task,
            external_job=job,
        )
    return job
