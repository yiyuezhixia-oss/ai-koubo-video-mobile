import math

from django.db import transaction
from django.utils import timezone

from .models import PointAccount, PointLedger, RedemptionCode


REWRITE_POINTS = 1
VOICE_CONFIRM_POINTS = 199
DIGITAL_HUMAN_POINTS_PER_MINUTE = 40
TTS_POINTS_PER_10K_CHARS = 128
TTS_MAX_CHARS = 2000


class InsufficientPoints(Exception):
    pass


class InvalidRedemptionCode(Exception):
    pass


def ensure_point_account(user):
    account, _ = PointAccount.objects.get_or_create(user=user)
    return account


def round_display_points(raw_points):
    points = math.ceil(raw_points)
    if points < 10:
        return max(points, 1)
    if points % 10 in (0, 9):
        return points
    next_ending_9 = points + ((9 - points % 10) % 10)
    next_ending_10 = points + ((10 - points % 10) % 10)
    return min(v for v in (next_ending_9, next_ending_10) if v >= points)


def calculate_tts_points(text):
    char_count = len((text or "").strip())
    if char_count <= 0:
        return 0
    if char_count > TTS_MAX_CHARS:
        raise ValueError(f"TTS 文案不能超过 {TTS_MAX_CHARS} 字")
    return round_display_points(char_count * TTS_POINTS_PER_10K_CHARS / 10000)


def calculate_digital_human_points(duration_seconds):
    seconds = max(float(duration_seconds or 0), 1)
    return math.ceil(seconds / 60) * DIGITAL_HUMAN_POINTS_PER_MINUTE


def _write_ledger(account, action, amount, reason, idempotency_key, task=None, external_job=None, note=""):
    ledger, created = PointLedger.objects.get_or_create(
        user=account.user,
        action=action,
        idempotency_key=idempotency_key,
        defaults={
            "task": task,
            "external_job": external_job,
            "amount": amount,
            "balance_after": account.balance,
            "frozen_after": account.frozen_balance,
            "reason": reason,
            "note": note,
        },
    )
    return ledger, created


@transaction.atomic
def claim_frozen_points(user, amount, reason, idempotency_key, task=None, external_job=None, note=""):
    account = PointAccount.objects.select_for_update().get(user=user)
    existing = PointLedger.objects.filter(user=user, action="freeze", idempotency_key=idempotency_key).first()
    if existing:
        return existing, False
    if account.balance < amount:
        raise InsufficientPoints(f"积分不足，需要 {amount} 积分，当前 {account.balance} 积分")
    account.balance -= amount
    account.frozen_balance += amount
    account.save(update_fields=["balance", "frozen_balance", "updated_at"])
    ledger, _ = _write_ledger(account, "freeze", -amount, reason, idempotency_key, task, external_job, note)
    return ledger, True


def freeze_points(user, amount, reason, idempotency_key, task=None, external_job=None, note=""):
    ledger, _ = claim_frozen_points(user, amount, reason, idempotency_key, task, external_job, note)
    return ledger


def _settlement_root(idempotency_key, action):
    suffix = f":{action}"
    if not idempotency_key.endswith(suffix):
        raise ValueError(f"{action} 幂等键必须以 {suffix} 结尾")
    return idempotency_key[: -len(suffix)]


def _validate_settlement(user, amount, idempotency_key, action, opposite_action):
    root = _settlement_root(idempotency_key, action)
    freeze = PointLedger.objects.filter(
        user=user,
        action="freeze",
        idempotency_key=f"{root}:freeze",
    ).first()
    if not freeze or freeze.amount != -amount:
        raise ValueError("积分结算缺少对应的冻结记录或金额不一致")
    if PointLedger.objects.filter(
        user=user,
        action=opposite_action,
        idempotency_key=f"{root}:{opposite_action}",
    ).exists():
        raise ValueError("该笔冻结积分已经完成相反方向的结算")


@transaction.atomic
def consume_frozen_points(user, amount, reason, idempotency_key, task=None, external_job=None, note=""):
    account = PointAccount.objects.select_for_update().get(user=user)
    existing = PointLedger.objects.filter(user=user, action="consume", idempotency_key=idempotency_key).first()
    if existing:
        return existing
    _validate_settlement(user, amount, idempotency_key, "consume", "refund")
    if account.frozen_balance < amount:
        raise ValueError("冻结积分余额不足，无法完成消费")
    account.frozen_balance -= amount
    account.total_consumed += amount
    account.save(update_fields=["frozen_balance", "total_consumed", "updated_at"])
    ledger, _ = _write_ledger(account, "consume", -amount, reason, idempotency_key, task, external_job, note)
    return ledger


@transaction.atomic
def refund_frozen_points(user, amount, reason, idempotency_key, task=None, external_job=None, note=""):
    account = PointAccount.objects.select_for_update().get(user=user)
    existing = PointLedger.objects.filter(user=user, action="refund", idempotency_key=idempotency_key).first()
    if existing:
        return existing
    _validate_settlement(user, amount, idempotency_key, "refund", "consume")
    if account.frozen_balance < amount:
        raise ValueError("冻结积分余额不足，无法完成退款")
    account.frozen_balance -= amount
    account.balance += amount
    account.save(update_fields=["balance", "frozen_balance", "updated_at"])
    ledger, _ = _write_ledger(account, "refund", amount, reason, idempotency_key, task, external_job, note)
    return ledger


@transaction.atomic
def redeem_code(user, code_value):
    code_text = (code_value or "").strip()
    if not code_text:
        raise InvalidRedemptionCode("请输入兑换码")
    try:
        code = RedemptionCode.objects.select_for_update().get(code__iexact=code_text)
    except RedemptionCode.DoesNotExist as exc:
        raise InvalidRedemptionCode("兑换码不存在") from exc
    if code.status != "unused":
        raise InvalidRedemptionCode("兑换码不可用或已被使用")
    if code.expires_at and code.expires_at < timezone.now():
        code.status = "expired"
        code.save(update_fields=["status", "updated_at"])
        raise InvalidRedemptionCode("兑换码已过期")
    account = PointAccount.objects.select_for_update().get(user=user)
    account.balance += code.points
    account.total_redeemed += code.points
    account.save(update_fields=["balance", "total_redeemed", "updated_at"])
    code.status = "used"
    code.used_by = user
    code.used_at = timezone.now()
    code.save(update_fields=["status", "used_by", "used_at", "updated_at"])
    PointLedger.objects.create(
        user=user,
        action="redeem",
        amount=code.points,
        balance_after=account.balance,
        frozen_after=account.frozen_balance,
        reason="redeem_code",
        idempotency_key=f"redeem:{code.code}",
        note=f"兑换码 {code.code}",
    )
    return account
