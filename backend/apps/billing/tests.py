from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import PointAccount, PointLedger
from .services import claim_frozen_points, consume_frozen_points, refund_frozen_points


class PointSettlementTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="billing-test")
        self.account = PointAccount.objects.create(user=self.user, balance=100)

    def test_same_freeze_key_is_claimed_only_once(self):
        first, first_claimed = claim_frozen_points(
            self.user, 40, "digital_human", "operation-1:freeze"
        )
        second, second_claimed = claim_frozen_points(
            self.user, 40, "digital_human", "operation-1:freeze"
        )

        self.account.refresh_from_db()
        self.assertTrue(first_claimed)
        self.assertFalse(second_claimed)
        self.assertEqual(first.id, second.id)
        self.assertEqual(self.account.balance, 60)
        self.assertEqual(self.account.frozen_balance, 40)
        self.assertEqual(PointLedger.objects.filter(action="freeze").count(), 1)

    def test_cannot_consume_without_matching_freeze(self):
        with self.assertRaisesRegex(ValueError, "缺少对应的冻结记录"):
            consume_frozen_points(self.user, 40, "digital_human", "missing:consume")

    def test_consumed_freeze_cannot_also_be_refunded(self):
        claim_frozen_points(self.user, 40, "digital_human", "operation-2:freeze")
        consume_frozen_points(self.user, 40, "digital_human", "operation-2:consume")

        with self.assertRaisesRegex(ValueError, "相反方向"):
            refund_frozen_points(self.user, 40, "digital_human", "operation-2:refund")

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, 60)
        self.assertEqual(self.account.frozen_balance, 0)
        self.assertEqual(self.account.total_consumed, 40)
