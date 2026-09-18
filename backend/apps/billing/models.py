from django.conf import settings
from django.db import models


class PointAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="point_account")
    balance = models.IntegerField("可用积分", default=88)
    frozen_balance = models.IntegerField("冻结积分", default=0)
    total_consumed = models.IntegerField("累计消费", default=0)
    total_redeemed = models.IntegerField("累计兑换", default=0)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "积分账户"
        verbose_name_plural = "积分账户"

    def __str__(self):
        return f"{self.user} 可用 {self.balance} / 冻结 {self.frozen_balance}"


class PointLedger(models.Model):
    ACTION_CHOICES = [
        ("redeem", "兑换"),
        ("freeze", "冻结"),
        ("consume", "消费"),
        ("refund", "退款"),
        ("admin_adjust", "管理员调整"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="point_ledgers")
    task = models.ForeignKey("creator.Task", on_delete=models.SET_NULL, blank=True, null=True, related_name="point_ledgers")
    external_job = models.ForeignKey("creator.ExternalJob", on_delete=models.SET_NULL, blank=True, null=True, related_name="point_ledgers")
    action = models.CharField("动作", max_length=32, choices=ACTION_CHOICES)
    amount = models.IntegerField("积分变化")
    balance_after = models.IntegerField("可用积分快照")
    frozen_after = models.IntegerField("冻结积分快照")
    reason = models.CharField("原因", max_length=64)
    idempotency_key = models.CharField("幂等 Key", max_length=160)
    note = models.TextField("备注", blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "积分流水"
        verbose_name_plural = "积分流水"
        constraints = [
            models.UniqueConstraint(fields=["user", "action", "idempotency_key"], name="uniq_point_action_key")
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} {self.action} {self.amount}"


class RedemptionCode(models.Model):
    STATUS_CHOICES = [
        ("unused", "未使用"),
        ("used", "已使用"),
        ("expired", "已过期"),
        ("disabled", "已禁用"),
    ]
    code = models.CharField("兑换码", max_length=64, unique=True)
    points = models.PositiveIntegerField("兑换积分")
    status = models.CharField("状态", max_length=16, choices=STATUS_CHOICES, default="unused")
    used_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name="used_codes")
    used_at = models.DateTimeField("使用时间", blank=True, null=True)
    expires_at = models.DateTimeField("过期时间", blank=True, null=True)
    batch_name = models.CharField("批次", max_length=64, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name="created_codes")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "兑换码"
        verbose_name_plural = "兑换码"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} - {self.points}积分"

