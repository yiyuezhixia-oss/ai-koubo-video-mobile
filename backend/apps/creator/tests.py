import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.billing.models import PointLedger
from apps.billing.services import ensure_point_account

from .models import MediaFile, Task, VoiceAuthorization
from apps.accounts.models import UserRightsRequest
from .models import ExternalJob, Voice
from .services import VIDEO_MAX_BYTES, generate_digital_human, generate_tts, rewrite_script, save_media_upload, sync_digital_human_job


class ComplianceApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="compliance-test")
        self.client.force_login(self.user)

    def test_user_rights_request_is_persisted(self):
        response = self.client.post(
            "/api/user-rights/",
            data=json.dumps({"request_type": "data_delete", "content": "删除测试数据"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        request = UserRightsRequest.objects.get(user=self.user)
        self.assertEqual(request.request_type, "data_delete")
        self.assertEqual(request.status, "pending")

    def test_voice_clone_rejects_missing_authorization(self):
        audio = SimpleUploadedFile("voice.mp3", b"audio-bytes", content_type="audio/mpeg")
        response = self.client.post(
            "/api/voices/clone/preview/",
            data={"audio_file": audio, "voice_name": "测试", "text": "你好"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "voice_authorization_required")
        self.assertFalse(VoiceAuthorization.objects.exists())


class MediaUploadApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="upload-test")
        self.client.force_login(self.user)
        self.task = Task.objects.create(user=self.user, title="Upload test")
        self.media_dir = TemporaryDirectory()
        self.settings_override = override_settings(
            MEDIA_STORAGE_BACKEND="local",
            MEDIA_ROOT=self.media_dir.name,
        )
        self.settings_override.enable()
    def tearDown(self):
        self.settings_override.disable()
        self.media_dir.cleanup()

    def test_bare_filename_cannot_create_fake_upload(self):
        response = self.client.post(
            "/api/media/upload/",
            data=json.dumps(
                {
                    "task_id": self.task.id,
                    "file_type": "source_video",
                    "file_name": "D:/video/local-only.mp4",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "missing_file")
        self.assertFalse(MediaFile.objects.exists())

    def test_multipart_upload_persists_bytes_and_links_task(self):
        video = SimpleUploadedFile("shared.mp4", b"video-bytes", content_type="video/mp4")

        response = self.client.post(
            "/api/media/upload/",
            data={
                "task_id": self.task.id,
                "file_type": "source_video",
                "duration": "12",
                "file": video,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        media = MediaFile.objects.get()
        self.task.refresh_from_db()
        self.assertEqual(payload["media"]["storage_type"], "local")
        self.assertEqual(media.task_id, self.task.id)
        self.assertEqual(media.file_size, len(b"video-bytes"))
        self.assertEqual(media.duration, 0)
        self.assertEqual(self.task.source_video_file_id, media.id)
        self.assertEqual(self.task.status, "video_uploaded")

    def test_non_mp4_video_is_rejected_before_storage(self):
        video = SimpleUploadedFile("shared.mov", b"video-bytes", content_type="video/quicktime")

        response = self.client.post(
            "/api/media/upload/",
            data={"task_id": self.task.id, "file_type": "source_video", "file": video},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("仅支持 MP4", response.json()["message"])
        self.assertFalse(MediaFile.objects.exists())

    def test_video_over_500mb_is_rejected_before_storage(self):
        video = SimpleUploadedFile("large.mp4", b"x", content_type="video/mp4")
        video.size = VIDEO_MAX_BYTES + 1

        with self.assertRaisesRegex(ValueError, "500MB"):
            save_media_upload(self.user, video, "source_video", task=self.task)

        self.assertFalse(MediaFile.objects.exists())

    def test_share_text_extracts_real_douyin_url(self):
        response = self.client.post(
            "/api/tasks/",
            data=json.dumps(
                {
                    "original_text": "复制打开抖音 https://v.douyin.com/abc-123/ 其他口令",
                    "source_type": "douyin_link",
                    "source_url": "https://v.douyin.com/abc-123/",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["task"]["source_url"], "https://v.douyin.com/abc-123/")

    def test_output_video_download_returns_attachment(self):
        output_dir = Path(self.media_dir.name) / "output_video"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "result.mp4"
        output_path.write_bytes(b"video-result")
        media = MediaFile.objects.create(
            user=self.user,
            task=self.task,
            file_type="output_video",
            storage_type="local",
            file_path="output_video/result.mp4",
            file_url="/media/output_video/result.mp4",
            file_size=len(b"video-result"),
            mime_type="video/mp4",
        )
        self.task.output_video_file = media
        self.task.status = "completed"
        self.task.current_step = "preview"
        self.task.save()

        response = self.client.get(f"/api/tasks/{self.task.id}/download-output/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "video/mp4")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("result.mp4", response["Content-Disposition"])
        response.close()

    def test_task_without_douyin_url_is_rejected(self):
        response = self.client.post(
            "/api/tasks/",
            data=json.dumps(
                {
                    "original_text": "这只是普通文案",
                    "source_type": "douyin_link",
                    "source_url": "",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("抖音分享链接", response.json()["message"])


class PaidFlowIdempotencyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="paid-flow-test")
        self.account = ensure_point_account(self.user)
        self.account.balance = 1000
        self.account.save(update_fields=["balance"])
        self.media_dir = TemporaryDirectory()
        self.settings_override = override_settings(
            MEDIA_STORAGE_BACKEND="local",
            MEDIA_ROOT=self.media_dir.name,
        )
        self.settings_override.enable()
        self.cache_patcher = patch(
            "apps.creator.services.cache_remote_file",
            side_effect=lambda url, name, subdir, **kwargs: (
                f"{subdir}/{name}",
                f"/media/{subdir}/{name}",
                5,
                "video/mp4" if name.endswith(".mp4") else "audio/mpeg",
                0,
            ),
        )
        self.cache_patcher.start()

    def tearDown(self):
        self.cache_patcher.stop()
        self.settings_override.disable()
        self.media_dir.cleanup()

    @patch("apps.creator.services.DeepSeekClient.rewrite")
    def test_rewrite_duplicate_key_calls_provider_and_charges_once(self, run_workflow):
        run_workflow.return_value = {
            "data": {
                "initial_text": "原文内容足够长，能够代表工作流已经从抖音分享里提取出真实正文，而不是只返回一个短链接或口令。",
                "Last_text": (
                    "这是一段已经改写完成的口播文案，语气自然，表达完整，用户可以直接拿去生成配音。"
                    "开头能抓住注意力，中间有清晰的故事转折，结尾也能收束观点。"
                    "它不会包含链接，也不会暴露提示词，更不会要求用户继续补充素材。"
                    "这样的内容才算真正进入下一步配音流程。"
                ),
            }
        }
        task = Task.objects.create(
            user=self.user,
            original_text="原文",
            source_type="douyin_link",
            source_url="https://v.douyin.com/example/",
        )

        rewrite_script(self.user, task, "原文", "rewrite-once", "更口语")
        rewrite_script(self.user, task, "原文", "rewrite-once", "更口语")

        task.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(run_workflow.call_count, 1)
        self.assertIn("已经改写完成的口播文案", task.rewritten_text)
        self.assertEqual(task.point_cost_total, 1)
        self.assertEqual(self.account.balance, 999)
        self.assertEqual(self.account.total_consumed, 1)

    @patch("apps.creator.services.DeepSeekClient.rewrite")
    def test_rewrite_failure_refunds_once_and_is_not_retried(self, run_workflow):
        run_workflow.side_effect = RuntimeError("provider unavailable")
        task = Task.objects.create(
            user=self.user,
            original_text="原文",
            source_type="douyin_link",
            source_url="https://v.douyin.com/example/",
        )

        with self.assertRaisesRegex(RuntimeError, "provider unavailable"):
            rewrite_script(self.user, task, "原文", "rewrite-fail")
        with self.assertRaisesRegex(RuntimeError, "provider unavailable"):
            rewrite_script(self.user, task, "原文", "rewrite-fail")

        self.account.refresh_from_db()
        self.assertEqual(run_workflow.call_count, 1)
        self.assertEqual(self.account.balance, 1000)
        self.assertEqual(self.account.frozen_balance, 0)
        self.assertEqual(PointLedger.objects.filter(action="refund").count(), 1)

    @patch("apps.creator.services.DeepSeekClient.rewrite")
    def test_rewrite_rejects_generic_prompt_and_refunds(self, run_workflow):
        run_workflow.return_value = {
            "data": {
                "initial_text": "已经提取到的原文",
                "Last_text": "请你提供需要二创的【原文案】以及你的【具体要求】",
            }
        }
        task = Task.objects.create(
            user=self.user,
            original_text="这是一段可用于验证通用拒答内容的真实口播原文，长度足够让改写请求进入 DeepSeek 客户端。",
            source_type="manual",
        )

        with self.assertRaisesRegex(RuntimeError, "无效"):
            rewrite_script(self.user, task, task.original_text, "rewrite-generic")

        self.assertIn("只输出改写后的文案", run_workflow.call_args.args[1])
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, 1000)
        self.assertEqual(self.account.frozen_balance, 0)

    @patch("apps.creator.services.DeepSeekClient.rewrite")
    def test_rewrite_requires_extracted_original_text(self, run_workflow):
        run_workflow.return_value = {"data": {"Last_text": "改写完成，但缺少提取原文"}}
        task = Task.objects.create(
            user=self.user,
            original_text="抖音分享口令不是原始文案",
            source_type="douyin_link",
            source_url="https://v.douyin.com/example/",
        )

        with self.assertRaisesRegex(RuntimeError, "AI 改写结果过短"):
            rewrite_script(self.user, task, task.original_text, "rewrite-no-initial")

        task.refresh_from_db()
        self.assertNotEqual(task.rewritten_text, "改写完成，但缺少提取原文")
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, 1000)

    @patch("apps.creator.services.MiniMaxClient.synthesize")
    def test_tts_duplicate_key_persists_audio_and_charges_once(self, run_workflow):
        run_workflow.return_value = {"data": {"output": "https://media.example.com/tts.mp3"}}
        voice = Voice.objects.create(
            user=self.user,
            name="少女音色",
            provider_voice_id="female-shaonv",
            status="available",
        )
        task = Task.objects.create(user=self.user, rewritten_text="需要生成的文案")

        first_task, points = generate_tts(self.user, task, voice, "tts-once")
        second_task, second_points = generate_tts(self.user, task, voice, "tts-once")

        self.account.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(run_workflow.call_count, 1)
        self.assertEqual(points, second_points)
        self.assertEqual(first_task.tts_audio_file_id, second_task.tts_audio_file_id)
        self.assertEqual(MediaFile.objects.filter(file_type="tts_audio").count(), 1)
        self.assertEqual(task.point_cost_total, points)
        self.assertEqual(self.account.total_consumed, points)

    @patch("apps.creator.services.MiniMaxClient.synthesize")
    def test_tts_forwards_supported_voice_parameters(self, run_workflow):
        run_workflow.return_value = {"data": {"output": "https://media.example.com/tts.mp3"}}
        voice = Voice.objects.create(user=self.user, name="御姐女声", provider_voice_id="female-yujie", status="available")
        task = Task.objects.create(user=self.user, rewritten_text="参数测试")

        generate_tts(self.user, task, voice, "tts-params", pitch=4, speed=1.2, volume=0.8, emotion="calm")

        self.assertEqual(run_workflow.call_args.args, ("参数测试", "female-yujie"))
        self.assertEqual(run_workflow.call_args.kwargs, {"pitch": 4, "speed": 1.2, "volume": 0.8})

    def test_tts_rejects_unsupported_emotion_before_charging(self):
        voice = Voice.objects.create(user=self.user, name="御姐女声", provider_voice_id="female-yujie", status="available")
        task = Task.objects.create(user=self.user, rewritten_text="参数测试")

        with self.assertRaisesRegex(ValueError, "不支持的声音情绪"):
            generate_tts(self.user, task, voice, "tts-invalid-emotion", emotion="excited")

        self.assertFalse(PointLedger.objects.filter(user=self.user, reason="tts").exists())

    @patch("apps.creator.services.HiHooClient.query_digital_human")
    @patch("apps.creator.services.HiHooClient.submit_digital_human")
    def test_digital_human_submit_and_repeated_sync_charge_once(self, submit, query):
        submit.return_value = {"code": 200, "data": {"taskid": "hihoo-123"}}
        query.return_value = {
            "code": 200,
            "data": {
                "status": 3,
                "result_video_url": "https://media.example.com/result.mp4",
                "video_time": 30,
            },
        }
        task, source_video = self._digital_human_task()

        _, first_job = generate_digital_human(
            self.user,
            task,
            source_video,
            "digital-once",
            "https://api.example.com/callback",
        )
        _, second_job = generate_digital_human(
            self.user,
            task,
            source_video,
            "digital-once",
            "https://api.example.com/callback",
        )
        self.assertEqual(query.call_count, 0)
        sync_digital_human_job(first_job)
        sync_digital_human_job(second_job)

        task.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(submit.call_count, 1)
        self.assertEqual(query.call_count, 1)
        self.assertEqual(ExternalJob.objects.count(), 1)
        self.assertEqual(MediaFile.objects.filter(file_type="output_video").count(), 1)
        self.assertEqual(task.status, "completed")
        self.assertEqual(task.point_cost_total, 40)
        self.assertEqual(self.account.total_consumed, 40)

    @patch("apps.creator.services.HiHooClient.query_digital_human")
    @patch("apps.creator.services.HiHooClient.submit_digital_human")
    def test_digital_human_failure_refunds_once(self, submit, query):
        submit.return_value = {"code": 200, "data": {"taskid": "hihoo-fail"}}
        query.return_value = {"code": 200, "data": {"status": 4, "msg": "生成失败"}}
        task, source_video = self._digital_human_task()
        _, job = generate_digital_human(
            self.user,
            task,
            source_video,
            "digital-fail",
            "https://api.example.com/callback",
        )

        sync_digital_human_job(job)
        sync_digital_human_job(job)

        task.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(query.call_count, 1)
        self.assertEqual(task.status, "failed")
        self.assertEqual(task.refund_status, "refunded")
        self.assertEqual(self.account.balance, 1000)
        self.assertEqual(self.account.frozen_balance, 0)
        self.assertEqual(PointLedger.objects.filter(action="refund").count(), 1)

    @patch("apps.creator.services.HiHooClient.submit_digital_human")
    def test_digital_human_rejects_audio_over_five_minutes_before_charging(self, submit):
        task, source_video = self._digital_human_task()
        task.tts_audio_file.duration = 301
        task.tts_audio_file.save(update_fields=["duration"])

        with self.assertRaisesRegex(ValueError, "5 分钟"):
            generate_digital_human(
                self.user,
                task,
                source_video,
                "digital-too-long",
                "https://api.example.com/callback",
            )

        self.account.refresh_from_db()
        self.assertEqual(submit.call_count, 0)
        self.assertEqual(self.account.balance, 1000)
        self.assertEqual(self.account.frozen_balance, 0)

    @patch("apps.creator.services.HiHooClient.submit_digital_human")
    def test_digital_human_rejects_audio_longer_than_video_before_charging(self, submit):
        task, source_video = self._digital_human_task()
        task.tts_audio_file.duration = 35
        task.tts_audio_file.save(update_fields=["duration"])

        with self.assertRaisesRegex(ValueError, "配音比视频长 5.0 秒"):
            generate_digital_human(self.user, task, source_video, "audio-too-long", "https://api.example.com/callback")

        self.account.refresh_from_db()
        self.assertEqual(submit.call_count, 0)
        self.assertEqual(self.account.balance, 1000)

    def _digital_human_task(self):
        task = Task.objects.create(user=self.user, rewritten_text="数字人文案")
        tts_audio = MediaFile.objects.create(
            user=self.user,
            task=task,
            file_type="tts_audio",
            storage_type="object",
            file_url="https://media.example.com/tts.mp3",
            duration=30,
            mime_type="audio/mpeg",
        )
        source_video = MediaFile.objects.create(
            user=self.user,
            task=task,
            file_type="source_video",
            storage_type="object",
            file_url="https://media.example.com/source.mp4",
            duration=30,
            mime_type="video/mp4",
        )
        task.tts_audio_file = tts_audio
        task.source_video_file = source_video
        task.status = "video_uploaded"
        task.current_step = "video"
        task.save()
        return task, source_video


class HiHooCallbackApiTests(TestCase):
    @patch("apps.creator.views.sync_digital_human_job")
    def test_form_encoded_callback_finds_and_syncs_job(self, sync_job):
        user = get_user_model().objects.create_user(username="callback-test")
        task = Task.objects.create(user=user, title="Callback")
        job = ExternalJob.objects.create(
            user=user,
            task=task,
            provider="hihoo",
            job_type="digital_human",
            provider_task_id="provider-123",
            status="processing",
        )
        sync_job.return_value = job

        response = self.client.post(
            "/api/callbacks/hihoo/digital-human/",
            data={"taskid": "provider-123", "status": "3"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["data"]["received"])
        sync_job.assert_called_once()

    @patch("apps.creator.views.complete_digital_human_from_callback")
    def test_multipart_callback_uses_uploaded_result_file(self, complete_job):
        user = get_user_model().objects.create_user(username="callback-file-test")
        task = Task.objects.create(user=user, title="Callback file")
        job = ExternalJob.objects.create(
            user=user,
            task=task,
            provider="hihoo",
            job_type="digital_human",
            provider_task_id="provider-file-123",
            status="processing",
        )
        complete_job.return_value = job
        uploaded = SimpleUploadedFile("result.mp4", b"rendered-video", content_type="video/mp4")

        response = self.client.post(
            "/api/callbacks/hihoo/digital-human/",
            data={"taskid": "provider-file-123", "errcode": "0", "target_file": uploaded},
        )

        self.assertEqual(response.status_code, 200)
        complete_job.assert_called_once()
        self.assertEqual(complete_job.call_args.args[1].name, "result.mp4")
