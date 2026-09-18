from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.accounts.services import SYSTEM_VOICES
from apps.creator.models import Voice
from apps.integrations.minimax import MiniMaxClient


class Command(BaseCommand):
    help = "Generate one reusable TTS sample for every built-in system voice."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        sample_text = "你好，这是一段音色试听。愿你的每一次表达都自然、清晰、有感染力。"
        target_dir = settings.BASE_DIR.parent / "frontend" / "public" / "audio" / "voices"
        target_dir.mkdir(parents=True, exist_ok=True)
        client = MiniMaxClient()

        for voice_id, _ in SYSTEM_VOICES:
            target = target_dir / f"{voice_id}.mp3"
            if not target.exists() or options["force"]:
                remote_url = client.synthesize(sample_text, voice_id)
                if not remote_url:
                    raise RuntimeError(f"{voice_id} 未返回试听音频")
                from apps.common.storage import download_remote_file
                payload = download_remote_file(remote_url, target.name).read()
                if not payload:
                    raise RuntimeError(f"{voice_id} 返回空音频")
                target.write_bytes(payload)

            sample_url = f"/audio/voices/{voice_id}.mp3"
            Voice.objects.filter(provider_voice_id=voice_id, provider="minimax_system").update(
                sample_audio_url=sample_url
            )
            self.stdout.write(self.style.SUCCESS(f"OK {voice_id}: {target.stat().st_size} bytes"))
