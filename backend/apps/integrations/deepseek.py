import json
import urllib.error
import urllib.request

from django.conf import settings


class DeepSeekClient:
    """Server-side DeepSeek chat client. API keys never leave the backend."""

    def __init__(self):
        self.base_url = settings.DEEPSEEK_BASE_URL.rstrip("/")
        self.api_key = settings.DEEPSEEK_API_KEY
        self.model = settings.DEEPSEEK_MODEL

    def rewrite(self, text, requirement):
        if not self.api_key:
            if settings.ALLOW_PROVIDER_MOCKS:
                return f"{text}\n\n这是一版更自然、适合短视频真人口播的改写文案。"
            raise RuntimeError("DeepSeek API 未配置，请在 backend/.env 设置 DEEPSEEK_API_KEY")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是中文短视频口播文案编辑。只输出改写后的完整文案，不要解释。"},
                {"role": "user", "content": f"原文：\n{text}\n\n改写要求：\n{requirement}"},
            ],
            "stream": False,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"DeepSeek 调用失败：HTTP {exc.code}") from exc
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError("DeepSeek 调用失败，请检查网络和 API 配置") from exc
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            raise RuntimeError("DeepSeek 未返回改写文案")
        return content.strip()
