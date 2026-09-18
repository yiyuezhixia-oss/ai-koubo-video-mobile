import json
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from .models import AccessToken, Profile
from .services import SYSTEM_VOICES, ensure_default_voice, issue_access_token
from apps.billing.services import ensure_point_account


class AuthenticationApiTests(TestCase):
    def test_all_system_voices_are_initialized_idempotently(self):
        user = get_user_model().objects.create_user(username="voice-catalog")

        ensure_default_voice(user)
        ensure_default_voice(user)

        self.assertEqual(user.voices.filter(provider="minimax_system").count(), len(SYSTEM_VOICES))
        self.assertEqual(
            set(user.voices.values_list("provider_voice_id", flat=True)),
            {voice_id for voice_id, _ in SYSTEM_VOICES},
        )
        self.assertFalse(user.voices.filter(sample_audio_url="").exists())

    def test_protected_api_rejects_missing_token(self):
        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "authentication_required")

    @override_settings(ALLOW_ANONYMOUS_AUTH=True)
    def test_anonymous_sessions_have_separate_users_and_uids(self):
        first = self.client.post("/api/auth/anonymous/", data="{}", content_type="application/json").json()["data"]
        second = self.client.post("/api/auth/anonymous/", data="{}", content_type="application/json").json()["data"]

        self.assertNotEqual(first["user"]["id"], second["user"]["id"])
        self.assertNotEqual(first["user"]["uid"], second["user"]["uid"])
        me = self.client.get(
            "/api/me/",
            HTTP_AUTHORIZATION=f"Bearer {first['access_token']}",
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["data"]["user"]["uid"], first["user"]["uid"])
        self.assertEqual(
            get_user_model().objects.get(id=first["user"]["id"]).voices.get(provider_voice_id="female-shaonv").sample_audio_url,
            "/audio/voices/female-shaonv.mp3",
        )

    @override_settings(WECHAT_APP_ID="wx-app", WECHAT_APP_SECRET="wx-secret")
    @patch("apps.accounts.services.urllib.request.urlopen")
    def test_same_wechat_openid_returns_same_user(self, urlopen):
        response = Mock()
        response.read.return_value = json.dumps(
            {"openid": "openid-123", "session_key": "session-key", "unionid": "union-123"}
        ).encode("utf-8")
        urlopen.return_value.__enter__.return_value = response

        first = self.client.post(
            "/api/auth/wechat/",
            data=json.dumps({"code": "code-1", "nickname": "用户甲"}),
            content_type="application/json",
        ).json()["data"]
        second = self.client.post(
            "/api/auth/wechat/",
            data=json.dumps({"code": "code-2"}),
            content_type="application/json",
        ).json()["data"]

        self.assertEqual(first["user"]["id"], second["user"]["id"])
        self.assertEqual(Profile.objects.filter(wx_openid="openid-123").count(), 1)
        self.assertEqual(AccessToken.objects.filter(user_id=first["user"]["id"]).count(), 2)

    def test_bearer_token_takes_precedence_over_admin_session_cookie(self):
        User = get_user_model()
        session_user = User.objects.create_user(username="session-admin")
        Profile.objects.create(user=session_user, nickname="管理员")
        ensure_point_account(session_user)
        ensure_default_voice(session_user)
        token_user = User.objects.create_user(username="token-user")
        token_profile = Profile.objects.create(user=token_user, nickname="令牌用户")
        ensure_point_account(token_user)
        ensure_default_voice(token_user)
        raw_token = issue_access_token(token_user, label="test")
        self.client.force_login(session_user)

        response = self.client.get(
            "/api/me/",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["user"]["uid"], token_profile.uid)
