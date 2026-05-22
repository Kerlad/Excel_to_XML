import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from utils.training_rules import (
    get_training_period_years, compute_expiry_date,
    is_program_expired, get_dynamic_status, TYPE_B_PROGRAMS
)


class TestTrainingRules:
    def test_type_a_always_3_years(self):
        for pid in range(1, 6):
            assert get_training_period_years(pid, True) == 3
            assert get_training_period_years(pid, False) == 3

    def test_type_b_3years_flag(self):
        for pid in TYPE_B_PROGRAMS:
            assert get_training_period_years(pid, True) == 3

    def test_type_b_1year_flag(self):
        for pid in [6, 10, 20, 29]:
            assert get_training_period_years(pid, False) == 1

    def test_compute_expiry_date_3years(self):
        expiry = compute_expiry_date("01.01.2025", 1, True)
        assert expiry == datetime(2028, 1, 1)

    def test_compute_expiry_date_1year(self):
        expiry = compute_expiry_date("01.01.2025", 6, False)
        assert expiry == datetime(2026, 1, 1)

    def test_compute_expiry_date_none(self):
        assert compute_expiry_date("", 1) is None

    def test_is_program_expired_false_future(self):
        future_date = (datetime.now() + timedelta(days=365)).strftime("%d.%m.%Y")
        assert not is_program_expired(future_date, 1)

    def test_is_program_expired_true_past(self):
        past_date = (datetime.now() - relativedelta(years=5)).strftime("%d.%m.%Y")
        assert is_program_expired(past_date, 1)

    def test_is_program_expired_invalid_date(self):
        assert not is_program_expired("invalid", 1)

    def test_get_dynamic_status_trained_3year_b(self):
        """Type B with 3-year flag should stay 'trained' for recent exams."""
        recent = (datetime.now() - timedelta(days=30)).strftime("%d.%m.%Y")
        assert get_dynamic_status('trained', recent, 10, True) == 'trained'

    def test_get_dynamic_status_trained_1year_expired(self):
        past = (datetime.now() - relativedelta(years=2)).strftime("%d.%m.%Y")
        status = get_dynamic_status('trained', past, 10, False)
        assert status == 'expired'

    def test_get_dynamic_status_not_trained(self):
        assert get_dynamic_status('not_trained', '', 10, True) == 'not_trained'
        assert get_dynamic_status('not_trained', '', 10, False) == 'not_trained'

    def test_get_dynamic_status_expired(self):
        assert get_dynamic_status('expired', '', 10, True) == 'expired'

    def test_get_dynamic_status_type_a(self):
        past = (datetime.now() - relativedelta(years=5)).strftime("%d.%m.%Y")
        status = get_dynamic_status('trained', past, 1, False)
        assert status == 'trained'

    def test_type_b_set_correct_range(self):
        assert 6 in TYPE_B_PROGRAMS
        assert 29 in TYPE_B_PROGRAMS
        assert 5 not in TYPE_B_PROGRAMS
        assert 30 not in TYPE_B_PROGRAMS
        assert len(TYPE_B_PROGRAMS) == 24
