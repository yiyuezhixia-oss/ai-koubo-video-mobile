from django.contrib import admin

from .models import PointAccount, PointLedger, RedemptionCode


@admin.register(PointAccount)
class PointAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "frozen_balance", "total_consumed", "total_redeemed", "updated_at")
    search_fields = ("user__username", "user__profile__uid")


@admin.register(PointLedger)
class PointLedgerAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "amount", "reason", "balance_after", "frozen_after", "created_at")
    search_fields = ("user__username", "user__profile__uid", "idempotency_key", "reason")
    list_filter = ("action", "reason", "created_at")
    readonly_fields = ("created_at",)


@admin.register(RedemptionCode)
class RedemptionCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "points", "status", "used_by", "used_at", "expires_at", "batch_name")
    search_fields = ("code", "used_by__username", "used_by__profile__uid", "batch_name")
    list_filter = ("status", "batch_name", "created_at")

