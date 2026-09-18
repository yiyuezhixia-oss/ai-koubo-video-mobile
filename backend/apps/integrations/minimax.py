import json
import mimetypes
import os
import uuid
import urllib.error
import urllib.request

from django.conf import settings


class MiniMaxClient:
    """Server-side MiniMax speech client using the official HTTP endpoints."""

    def __init__(self):
        self.base_url = settings.MINIMAX_BASE_URL.rstrip("/")
        self.api_key = settings.MINIMAX_API_KEY
        self.model = settings.MINIMAX_SPEECH_MODEL

    def _json_request(self, path, payload):
        if not self.api_key:
            if settings.ALLOW_PROVIDER_MOCKS:
                return None
            raise RuntimeError("MiniMax API 未配置，请在 backend/.env 设置 MINIMAX_API_KEY")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"MiniMax 调用失败：HTTP {exc.code}") from exc
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError("MiniMax 调用失败，请检查网络和 API 配置") from exc
        base_resp = data.get("base_resp", {})
        if base_resp.get("status_code", 0) != 0:
            raise RuntimeError(f"MiniMax 调用失败：{base_resp.get('status_msg', '未知错误')}")
        return data

    def _upload(self, file_name, content, purpose="voice_clone"):
        if not self.api_key:
            if settings.ALLOW_PROVIDER_MOCKS:
                return "mock-file-id"
            raise RuntimeError("MiniMax API 未配置，请在 backend/.env 设置 MINIMAX_API_KEY")
        boundary = f"----Zhixia{uuid.uuid4().hex}"
        content_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        body = b"".join([
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"purpose\"\r\n\r\n{purpose}\r\n".encode(),
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{os.path.basename(file_name)}\"\r\nContent-Type: {content_type}\r\n\r\n".encode(),
            content,
            f"\r\n--{boundary}--\r\n".encode(),
        ])
        request = urllib.request.Request(
            f"{self.base_url}/files/upload", data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError("MiniMax 克隆音频上传失败") from exc
        file_id = data.get("file", {}).get("file_id")
        if not file_id:
            raise RuntimeError("MiniMax 未返回克隆音频文件 ID")
        return file_id

    def clone_preview(self, file_name, content, voice_id, text):
        if not self.api_key and settings.ALLOW_PROVIDER_MOCKS:
            return {"voice_id": voice_id, "demo_audio": f"mock://voice-sample/{voice_id}.wav"}
        file_id = self._upload(file_name, content)
        return self._json_request("/voice_clone", {
            "file_id": file_id, "voice_id": voice_id, "text": text,
            "model": self.model, "language_boost": "Chinese",
            "need_noise_reduction": True, "need_volume_normalization": True,
        })

    def synthesize(self, text, voice_id, pitch=0, speed=1.0, volume=1.0):
        if not self.api_key and settings.ALLOW_PROVIDER_MOCKS:
            return "mock://tts/mock.wav"
        data = self._json_request("/t2a_v2", {
            "model": self.model, "text": text, "stream": False, "output_format": "url",
            "language_boost": "Chinese",
            "voice_setting": {"voice_id": voice_id, "speed": speed, "vol": volume, "pitch": pitch},
            "audio_setting": {"format": "mp3", "sample_rate": 32000, "bitrate": 128000, "channel": 1},
        })
        audio_url = data.get("data", {}).get("audio")
        if not audio_url:
            raise RuntimeError("MiniMax 未返回配音文件")
        return audio_url
