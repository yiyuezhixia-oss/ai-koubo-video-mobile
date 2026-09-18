import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings


class HiHooClient:
    def __init__(self):
        self.base_url = os.getenv("HIHOO_BASE_URL", "https://api.hihookeji.com").rstrip("/")
        self.api_key = os.getenv("HIHOO_API_KEY", "")
        self.sign_sk = os.getenv("HIHOO_SIGN_SK", "")
        self.enable_sign = os.getenv("HIHOO_ENABLE_SIGN", "false").lower() == "true"
        self.submit_endpoint = os.getenv("HIHOO_DIGITAL_HUMAN_ENDPOINT", "/api/humanmeta/index")
        self.query_endpoint = os.getenv("HIHOO_DIGITAL_HUMAN_QUERY_ENDPOINT", "/api/queryclonehumanv3/index")
        self.task_type = os.getenv("HIHOO_DIGITAL_HUMAN_TASKTYPE", "huamanclonev1")

    @property
    def enabled(self):
        return bool(self.api_key)

    def _headers(self, params):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if self.enable_sign and self.sign_sk:
            query = urllib.parse.urlencode(params)
            headers["sign"] = hashlib.md5((query + self.sign_sk).encode("utf-8")).hexdigest()
        return headers

    def _post_form(self, endpoint, params):
        data = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + endpoint,
            data=data,
            headers=self._headers(params),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"HiHoo 调用失败：{exc}") from exc

    def submit_digital_human(self, audio_url, video_url, notify_url):
        if settings.ALLOW_PROVIDER_MOCKS and (
            not str(audio_url).startswith("https://") or not str(video_url).startswith("https://")
        ):
            return {"code": 200, "msg": "mock", "data": {"taskid": f"mock_hihoo_{int(time.time())}"}}
        if not self.enabled:
            if settings.ALLOW_PROVIDER_MOCKS:
                return {"code": 200, "msg": "mock", "data": {"taskid": f"mock_hihoo_{int(time.time())}"}}
            raise RuntimeError("HiHoo API 未配置，无法提交真实数字人任务")
        return self._post_form(
            self.submit_endpoint,
            {
                "key": self.api_key,
                "audio_url": audio_url,
                "video_url": video_url,
                "notify_url": notify_url,
            },
        )

    def query_digital_human(self, taskid):
        if settings.ALLOW_PROVIDER_MOCKS and str(taskid).startswith("mock_hihoo_"):
            return {
                "code": 200,
                "msg": "mock",
                "data": {
                    "taskid": taskid,
                    "status": 3,
                    "result_video_url": f"mock://digital-human/{taskid}.mp4",
                    "video_time": 1,
                },
            }
        if not self.enabled:
            if not settings.ALLOW_PROVIDER_MOCKS:
                raise RuntimeError("HiHoo API 未配置，无法查询真实数字人任务")
            return {
                "code": 200,
                "msg": "mock",
                "data": {
                    "taskid": taskid,
                    "status": 3,
                    "result_video_url": f"mock://digital-human/{taskid}.mp4",
                    "video_time": 30,
                },
            }
        return self._post_form(
            self.query_endpoint,
            {
                "key": self.api_key,
                "taskid": taskid,
                "tasktype": self.task_type,
            },
        )

    def check_points(self):
        if not self.enabled:
            if not settings.ALLOW_PROVIDER_MOCKS:
                raise RuntimeError("HiHoo API 未配置，无法查询真实账户")
            return {"code": 200, "data": {"total": 0}, "msg": "mock"}
        endpoint = "/api/userinfo/checkpoints"
        return self._post_form(endpoint, {"key": self.api_key})
