def profile_to_dict(profile):
    return {
        "uid": profile.uid,
        "nickname": profile.nickname,
        "avatar_url": profile.avatar_url,
        "phone": profile.phone,
    }


def point_account_to_dict(account):
    return {
        "balance": account.balance,
        "frozen_balance": account.frozen_balance,
        "total_consumed": account.total_consumed,
        "total_redeemed": account.total_redeemed,
    }


def media_to_dict(media):
    if not media:
        return None
    return {
        "id": media.id,
        "file_type": media.file_type,
        "file_name": media.file_path.rsplit("/", 1)[-1] if media.file_path else "",
        "file_path": media.file_path,
        "file_url": media.file_url,
        "storage_type": media.storage_type,
        "file_size": media.file_size,
        "duration": media.duration,
        "mime_type": media.mime_type,
    }


def voice_to_dict(voice):
    return {
        "id": voice.id,
        "name": voice.name,
        "status": voice.status,
        "provider": voice.provider,
        "provider_voice_id": voice.provider_voice_id,
        "sample_audio_url": voice.sample_audio_url,
        "clone_test_text": voice.clone_test_text,
        "confirmed_at": voice.confirmed_at.isoformat() if voice.confirmed_at else None,
        "first_used_at": voice.first_used_at.isoformat() if voice.first_used_at else None,
        "must_use_before": voice.must_use_before.isoformat() if voice.must_use_before else None,
        "error_message": voice.error_message,
        "created_at": voice.created_at.isoformat(),
    }


def task_to_dict(task):
    return {
        "id": task.id,
        "title": task.title,
        "source_type": task.source_type,
        "source_url": task.source_url,
        "original_text": task.original_text,
        "rewritten_text": task.rewritten_text,
        "selected_voice_id": task.selected_voice_id,
        "selected_voice": voice_to_dict(task.selected_voice) if task.selected_voice else None,
        "tts_audio_file": media_to_dict(task.tts_audio_file),
        "tts_audio_url": task.tts_audio_file.file_url if task.tts_audio_file else "",
        "source_video_file": media_to_dict(task.source_video_file),
        "source_video_name": task.source_video_file.file_path.rsplit("/", 1)[-1] if task.source_video_file and task.source_video_file.file_path else "",
        "output_video_file": media_to_dict(task.output_video_file),
        "output_video_url": task.output_video_file.file_url if task.output_video_file else "",
        "status": task.status,
        "current_step": task.current_step,
        "point_cost": task.point_cost_total,
        "refund_status": task.refund_status,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }
