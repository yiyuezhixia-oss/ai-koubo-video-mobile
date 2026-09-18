from django.contrib import admin

from .models import ApiCallLog, ExternalJob, MediaFile, Task, Voice, VoiceAuthorization


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "status", "current_step", "selected_voice", "point_cost_total", "updated_at")
    search_fields = ("title", "user__username", "user__profile__uid", "original_text", "rewritten_text")
    list_filter = ("status", "current_step", "source_type", "created_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Voice)
class VoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "user", "status", "provider", "provider_voice_id", "confirmed_at", "must_use_before")
    search_fields = ("name", "provider_voice_id", "user__username", "user__profile__uid")
    list_filter = ("status", "provider", "created_at")


@admin.register(VoiceAuthorization)
class VoiceAuthorizationAdmin(admin.ModelAdmin):
    list_display = ("user", "voice", "ownership_confirmed", "separate_consent_confirmed", "accepted_at")
    search_fields = ("user__username", "user__profile__uid", "voice__name", "ip_address")
    list_filter = ("ownership_confirmed", "separate_consent_confirmed", "accepted_at")


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = ("id", "file_type", "user", "storage_type", "file_size", "duration", "created_at")
    search_fields = ("file_path", "file_url", "user__username", "user__profile__uid")
    list_filter = ("file_type", "storage_type", "created_at")


@admin.register(ExternalJob)
class ExternalJobAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "job_type", "status", "provider_task_id", "task", "cost_points", "updated_at")
    search_fields = ("provider_task_id", "provider", "job_type", "task__title", "user__profile__uid")
    list_filter = ("provider", "job_type", "status", "created_at")


@admin.register(ApiCallLog)
class ApiCallLogAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "api_type", "request_status", "http_status", "duration_ms", "created_at")
    search_fields = ("provider", "api_type", "endpoint", "error_message", "request_id")
    list_filter = ("provider", "api_type", "request_status", "created_at")
