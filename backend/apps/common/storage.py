import hashlib
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile, SpooledTemporaryFile
from urllib.request import Request, urlopen
from urllib.parse import quote
from uuid import uuid4

from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile


OUTPUT_WATERMARK_CROP_TOP = 64


def media_duration(file_obj):
    try:
        from mutagen import File as MutagenFile

        file_obj.seek(0)
        parsed = MutagenFile(file_obj)
        return float(parsed.info.length) if parsed and getattr(parsed, "info", None) else 0
    except Exception:
        return 0
    finally:
        file_obj.seek(0)


def build_public_url(path):
    public_base = getattr(settings, "PUBLIC_BASE_URL", "").rstrip("/")
    media_url = getattr(settings, "MEDIA_URL", "/media/")
    if public_base:
        return f"{public_base}{media_url}{path}".replace("\\", "/")
    return f"{media_url}{path}".replace("\\", "/")


def save_uploaded_file(uploaded_file, subdir):
    if getattr(settings, "MEDIA_STORAGE_BACKEND", "local") == "object":
        return save_uploaded_file_to_object_storage(uploaded_file, subdir)

    media_root = Path(settings.MEDIA_ROOT)
    target_dir = media_root / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(uploaded_file.name).name
    digest = hashlib.sha1(f"{safe_name}:{uploaded_file.size}".encode("utf-8")).hexdigest()[:12]
    target_name = f"{digest}-{safe_name}"
    target_path = target_dir / target_name
    with target_path.open("wb") as fh:
        for chunk in uploaded_file.chunks():
            fh.write(chunk)
    relative = f"{subdir}/{target_name}"
    return relative, build_public_url(relative)


def save_cropped_output_video(uploaded_file, subdir="output_video"):
    """Remove the provider watermark band before persisting a final video."""
    suffix = Path(uploaded_file.name).suffix or ".mp4"
    with NamedTemporaryFile(suffix=suffix) as source, NamedTemporaryFile(suffix=".mp4") as output:
        uploaded_file.seek(0)
        for chunk in uploaded_file.chunks():
            source.write(chunk)
        source.flush()
        command = [
            getattr(settings, "FFMPEG_BINARY", "ffmpeg"),
            "-y",
            "-i",
            source.name,
            "-vf",
            f"crop=trunc(iw/2)*2:trunc((ih-{OUTPUT_WATERMARK_CROP_TOP})/2)*2:0:{OUTPUT_WATERMARK_CROP_TOP}",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            output.name,
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError("成片去除顶部水印失败，请稍后重试")
        output.seek(0)
        processed = File(output, name=Path(uploaded_file.name).stem + "-cropped.mp4")
        processed.content_type = "video/mp4"
        duration = media_duration(processed)
        relative, public_url = save_uploaded_file(processed, subdir)
        processed.seek(0, 2)
        size = processed.tell()
    return relative, public_url, size, "video/mp4", duration


def save_uploaded_file_to_object_storage(uploaded_file, subdir):
    required = {
        "OBJECT_STORAGE_ENDPOINT_URL": settings.OBJECT_STORAGE_ENDPOINT_URL,
        "OBJECT_STORAGE_ACCESS_KEY_ID": settings.OBJECT_STORAGE_ACCESS_KEY_ID,
        "OBJECT_STORAGE_SECRET_ACCESS_KEY": settings.OBJECT_STORAGE_SECRET_ACCESS_KEY,
        "OBJECT_STORAGE_BUCKET": settings.OBJECT_STORAGE_BUCKET,
        "OBJECT_STORAGE_PUBLIC_BASE_URL": settings.OBJECT_STORAGE_PUBLIC_BASE_URL,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"对象存储配置不完整：{', '.join(missing)}")

    import boto3

    safe_name = Path(uploaded_file.name).name
    digest = hashlib.sha1(f"{safe_name}:{uploaded_file.size}".encode("utf-8")).hexdigest()[:12]
    object_key = f"{subdir}/{uuid4().hex[:12]}-{digest}-{safe_name}"
    uploaded_file.seek(0)
    client = boto3.client(
        "s3",
        endpoint_url=settings.OBJECT_STORAGE_ENDPOINT_URL,
        aws_access_key_id=settings.OBJECT_STORAGE_ACCESS_KEY_ID,
        aws_secret_access_key=settings.OBJECT_STORAGE_SECRET_ACCESS_KEY,
        region_name=settings.OBJECT_STORAGE_REGION,
    )
    extra_args = {}
    content_type = getattr(uploaded_file, "content_type", "")
    if content_type:
        extra_args["ContentType"] = content_type
    client.upload_fileobj(uploaded_file, settings.OBJECT_STORAGE_BUCKET, object_key, ExtraArgs=extra_args)
    public_url = f"{settings.OBJECT_STORAGE_PUBLIC_BASE_URL}/{quote(object_key, safe='/')}"
    return object_key, public_url


def download_remote_file(url, file_name, max_bytes=50 * 1024 * 1024):
    request = Request(url, headers={"User-Agent": "ZhixiaAI/1.0"})
    with urlopen(request, timeout=60) as response:
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise RuntimeError("远程媒体文件超过 50MB 限制")
        content_type = response.headers.get_content_type()
    if not data:
        raise RuntimeError("远程媒体文件为空")
    if content_type in {"text/html", "application/xhtml+xml"}:
        raise RuntimeError("远程地址返回的是网页，不是可下载的媒体文件")
    uploaded = ContentFile(data, name=file_name)
    uploaded.content_type = content_type
    return uploaded


def cache_remote_file(
    url,
    file_name,
    subdir,
    max_bytes=600 * 1024 * 1024,
    crop_output_video=False,
    expected_content_type_prefixes=None,
):
    request = Request(url, headers={"User-Agent": "ZhixiaAI/1.0"})
    with urlopen(request, timeout=120) as response:
        content_type = response.headers.get_content_type()
        if content_type in {"text/html", "application/xhtml+xml"}:
            raise RuntimeError("远程地址返回的是网页，不是可下载的媒体文件")
        if expected_content_type_prefixes and not any(
            content_type.startswith(prefix) for prefix in expected_content_type_prefixes
        ):
            expected = "、".join(expected_content_type_prefixes)
            raise RuntimeError(f"远程媒体类型不正确：期望 {expected}，实际 {content_type}")
        total = 0
        with SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b") as temporary:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise RuntimeError(f"远程媒体文件超过 {max_bytes // (1024 * 1024)}MB 限制")
                temporary.write(chunk)
            if total == 0:
                raise RuntimeError("远程媒体文件为空")
            temporary.seek(0)
            uploaded = File(temporary, name=file_name)
            uploaded.content_type = content_type
            duration = media_duration(uploaded)
            if crop_output_video:
                return save_cropped_output_video(uploaded, subdir)
            object_path, public_url = save_uploaded_file(uploaded, subdir)
    return object_path, public_url, total, content_type, duration
