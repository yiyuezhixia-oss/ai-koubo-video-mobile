from email.message import Message
from unittest.mock import Mock, patch
from urllib.parse import quote

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from .storage import cache_remote_file, download_remote_file, save_uploaded_file


class ObjectStorageTests(SimpleTestCase):
    @override_settings(
        MEDIA_STORAGE_BACKEND="object",
        OBJECT_STORAGE_ENDPOINT_URL="https://example.r2.cloudflarestorage.com",
        OBJECT_STORAGE_ACCESS_KEY_ID="access-key",
        OBJECT_STORAGE_SECRET_ACCESS_KEY="secret-key",
        OBJECT_STORAGE_BUCKET="media",
        OBJECT_STORAGE_REGION="auto",
        OBJECT_STORAGE_PUBLIC_BASE_URL="https://media.example.com",
    )
    @patch("boto3.client")
    def test_upload_returns_public_https_url(self, client_factory):
        client = Mock()
        client_factory.return_value = client
        upload = SimpleUploadedFile("测试 视频.mp4", b"video-bytes", content_type="video/mp4")

        object_key, public_url = save_uploaded_file(upload, "source_video")

        self.assertTrue(object_key.startswith("source_video/"))
        self.assertTrue(object_key.endswith("-测试 视频.mp4"))
        self.assertEqual(public_url, f"https://media.example.com/{quote(object_key, safe='/')}")
        client.upload_fileobj.assert_called_once_with(
            upload,
            "media",
            object_key,
            ExtraArgs={"ContentType": "video/mp4"},
        )

    @override_settings(
        MEDIA_STORAGE_BACKEND="object",
        OBJECT_STORAGE_ENDPOINT_URL="",
        OBJECT_STORAGE_ACCESS_KEY_ID="",
        OBJECT_STORAGE_SECRET_ACCESS_KEY="",
        OBJECT_STORAGE_BUCKET="",
        OBJECT_STORAGE_PUBLIC_BASE_URL="",
    )
    def test_missing_object_storage_config_fails_clearly(self):
        upload = SimpleUploadedFile("video.mp4", b"video-bytes", content_type="video/mp4")

        with self.assertRaisesRegex(RuntimeError, "对象存储配置不完整"):
            save_uploaded_file(upload, "source_video")

    @patch("apps.common.storage.urlopen")
    def test_download_remote_media_returns_uploadable_file(self, urlopen):
        headers = Message()
        headers["Content-Type"] = "audio/mpeg"
        response = Mock()
        response.headers = headers
        response.read.return_value = b"audio-bytes"
        urlopen.return_value.__enter__.return_value = response

        downloaded = download_remote_file("https://provider.example/temporary.mp3", "tts-1.mp3")

        self.assertEqual(downloaded.name, "tts-1.mp3")
        self.assertEqual(downloaded.content_type, "audio/mpeg")
        self.assertEqual(downloaded.read(), b"audio-bytes")

    @patch("apps.common.storage.urlopen")
    def test_download_remote_media_rejects_html_download_page(self, urlopen):
        headers = Message()
        headers["Content-Type"] = "text/html"
        response = Mock()
        response.headers = headers
        response.read.return_value = b"<html>temporary download page</html>"
        urlopen.return_value.__enter__.return_value = response

        with self.assertRaisesRegex(RuntimeError, "网页，不是可下载的媒体文件"):
            download_remote_file("https://provider.example/temporary", "tts-1.mp3")

    @override_settings(
        MEDIA_STORAGE_BACKEND="object",
        OBJECT_STORAGE_ENDPOINT_URL="https://example.r2.cloudflarestorage.com",
        OBJECT_STORAGE_ACCESS_KEY_ID="access-key",
        OBJECT_STORAGE_SECRET_ACCESS_KEY="secret-key",
        OBJECT_STORAGE_BUCKET="media",
        OBJECT_STORAGE_REGION="auto",
        OBJECT_STORAGE_PUBLIC_BASE_URL="https://media.example.com",
    )
    @patch("boto3.client")
    @patch("apps.common.storage.urlopen")
    def test_remote_video_is_streamed_into_object_storage(self, urlopen, client_factory):
        headers = Message()
        headers["Content-Type"] = "video/mp4"
        response = Mock()
        response.headers = headers
        response.read.side_effect = [b"first-chunk", b"second-chunk", b""]
        urlopen.return_value.__enter__.return_value = response
        client = Mock()
        client_factory.return_value = client

        object_path, public_url, size, content_type, duration = cache_remote_file(
            "https://provider.example/result.mp4",
            "result.mp4",
            "output_video",
        )

        self.assertTrue(object_path.startswith("output_video/"))
        self.assertEqual(public_url, f"https://media.example.com/{object_path}")
        self.assertEqual(size, len(b"first-chunksecond-chunk"))
        self.assertEqual(content_type, "video/mp4")
        self.assertEqual(duration, 0)
        client.upload_fileobj.assert_called_once()

    @patch("apps.common.storage.urlopen")
    def test_remote_cache_rejects_unexpected_media_type(self, urlopen):
        headers = Message()
        headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        response = Mock()
        response.headers = headers
        response.read.side_effect = [b"xlsx-bytes", b""]
        urlopen.return_value.__enter__.return_value = response

        with self.assertRaisesRegex(RuntimeError, "远程媒体类型不正确"):
            cache_remote_file(
                "https://provider.example/file.xlsx",
                "result.mp4",
                "output_video",
                expected_content_type_prefixes=("video/",),
            )
