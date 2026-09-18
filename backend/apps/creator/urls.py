from django.urls import path

from . import views


urlpatterns = [
    path("me/", views.me_view, name="api_me"),
    path("user-rights/", views.rights_request_view, name="api_user_rights"),
    path("pricing/", views.pricing_view, name="api_pricing"),
    path("points/redeem-code/", views.redeem_code_view, name="api_redeem_code"),
    path("points/ledger/", views.ledger_list_view, name="api_point_ledger"),
    path("tasks/", views.task_list_create_view, name="api_tasks"),
    path("tasks/<int:task_id>/", views.task_detail_view, name="api_task_detail"),
    path("tasks/<int:task_id>/rewrite/", views.rewrite_task_view, name="api_task_rewrite"),
    path("tasks/<int:task_id>/tts/", views.tts_generate_view, name="api_task_tts"),
    path("tasks/<int:task_id>/digital-human/", views.digital_human_generate_view, name="api_task_digital_human"),
    path("tasks/<int:task_id>/sync/", views.task_sync_view, name="api_task_sync"),
    path("tasks/<int:task_id>/download-output/", views.task_download_output_view, name="api_task_download_output"),
    path("voices/", views.voice_list_view, name="api_voices"),
    path("voices/<int:voice_id>/", views.voice_detail_view, name="api_voice_detail"),
    path("voices/clone/preview/", views.voice_clone_preview_view, name="api_voice_clone_preview"),
    path("voices/<int:voice_id>/confirm/", views.voice_confirm_view, name="api_voice_confirm"),
    path("voices/<int:voice_id>/discard/", views.voice_discard_view, name="api_voice_discard"),
    path("media/upload/", views.media_upload_view, name="api_media_upload"),
    path("callbacks/hihoo/digital-human/", views.hihoo_callback_view, name="api_hihoo_callback"),
]
