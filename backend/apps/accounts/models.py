import random
import string

from django.conf import settings
from django.db import models


def generate_uid():
    return "ZX" + "".join(random.choices(string.digits, k=8))


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    uid = models.CharField("UID", max_length=16, unique=True, default=generate_uid)
    wx_openid = models.CharField("微信 OpenID", max_length=128, blank=True, unique=True, null=True)
    wx_unionid = models.CharField("微信 UnionID", max_length=128, blank=True)
    nickname = models.CharField("昵称", max_length=64, blank=True)
    avatar_url = models.URLField("头像", blank=True)
    phone = models.CharField("手机号", max_length=32, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "用户资料"
        verbose_name_plural = "用户资料"

    def __str__(self):
        return self.nickname or self.user.username or self.uid


class AccessToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="access_tokens")
    token_hash = models.CharField("令牌哈希", max_length=64, unique=True)
    label = models.CharField("来源", max_length=32, default="wechat")
    expires_at = models.DateTimeField("过期时间")
    last_used_at = models.DateTimeField("最后使用", blank=True, null=True)
    revoked_at = models.DateTimeField("撤销时间", blank=True, null=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "访问令牌"
        verbose_name_plural = "访问令牌"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} ({self.label})"


class UserRightsRequest(models.Model):
    REQUEST_TYPES = [
        ("complaint", "投诉举报"),
        ("account_delete", "注销账号"),
        ("data_export", "导出个人数据"),
        ("data_delete", "删除个人数据"),
    ]
    STATUS_CHOICES = [("pending", "待处理"), ("completed", "已完成"), ("rejected", "已驳回")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rights_requests")
    request_type = models.CharField("申请类型", max_length=32, choices=REQUEST_TYPES)
    content = models.TextField("申请说明", blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default="pending")
    response_note = models.TextField("处理说明", blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    completed_at = models.DateTimeField("完成时间", blank=True, null=True)

    class Meta:
        verbose_name = "用户权益申请"
        verbose_name_plural = "用户权益申请"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}:{self.request_type}:{self.status}"
