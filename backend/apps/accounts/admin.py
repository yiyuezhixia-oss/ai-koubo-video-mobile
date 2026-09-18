from django.contrib import admin

from .models import AccessToken, Profile, UserRightsRequest


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("uid", "user", "nickname", "wx_openid", "phone", "created_at")
    search_fields = ("uid", "user__username", "nickname", "wx_openid", "phone")
    list_filter = ("created_at",)


@admin.register(AccessToken)
class AccessTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "expires_at", "last_used_at", "revoked_at", "created_at")
    search_fields = ("user__username", "user__profile__uid")
    list_filter = ("label", "revoked_at", "created_at")
    readonly_fields = ("token_hash", "created_at", "last_used_at")


@admin.register(UserRightsRequest)
class UserRightsRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "request_type", "status", "created_at", "completed_at")
    search_fields = ("user__username", "user__profile__uid", "content")
    list_filter = ("request_type", "status", "created_at")
