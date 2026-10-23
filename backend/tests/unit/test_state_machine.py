"""Юнит-тесты таблицы переходов машины состояний."""

import pytest

from app.domain.state_machine import TRANSITIONS, find_transition
from app.domain.statuses import FINAL_STATUSES, Actor, ApplicationStatus

S = ApplicationStatus

# Все допустимые переходы: (из статуса, действие, в статус, кто)
ALLOWED = [
    (S.DRAFT, "submit", S.SUBMITTED, Actor.CLIENT),
    (S.DRAFT, "cancel", S.CANCELLED, Actor.CLIENT),
    (S.SUBMITTED, "start_validation", S.VALIDATION, Actor.SYSTEM),
    (S.SUBMITTED, "technical_error", S.MANUAL_REVIEW, Actor.SYSTEM),
    (S.VALIDATION, "validation_failed", S.NEEDS_INFO, Actor.SYSTEM),
    (S.VALIDATION, "validation_passed", S.CHECKS, Actor.SYSTEM),
    (S.VALIDATION, "technical_error", S.MANUAL_REVIEW, Actor.SYSTEM),
    (S.NEEDS_INFO, "provide_info", S.SUBMITTED, Actor.CLIENT),
    (S.NEEDS_INFO, "cancel", S.CANCELLED, Actor.CLIENT),
    (S.CHECKS, "checks_completed", S.SCORING, Actor.SYSTEM),
    (S.CHECKS, "technical_error", S.MANUAL_REVIEW, Actor.SYSTEM),
    (S.SCORING, "auto_approve", S.OFFER_SENT, Actor.SYSTEM),
    (S.SCORING, "auto_counter_offer", S.OFFER_SENT, Actor.SYSTEM),
    (S.SCORING, "auto_reject", S.REJECTED, Actor.SYSTEM),
    (S.SCORING, "send_to_manual_review", S.MANUAL_REVIEW, Actor.SYSTEM),
    (S.SCORING, "auto_request_info", S.NEEDS_INFO, Actor.SYSTEM),
    (S.SCORING, "technical_error", S.MANUAL_REVIEW, Actor.SYSTEM),
    (S.MANUAL_REVIEW, "approve", S.OFFER_SENT, Actor.EMPLOYEE),
    (S.MANUAL_REVIEW, "counter_offer", S.OFFER_SENT, Actor.EMPLOYEE),
    (S.MANUAL_REVIEW, "request_info", S.NEEDS_INFO, Actor.EMPLOYEE),
    (S.MANUAL_REVIEW, "reject", S.REJECTED, Actor.EMPLOYEE),
    (S.MANUAL_REVIEW, "cancel", S.CANCELLED, Actor.CLIENT),
    (S.OFFER_SENT, "accept_offer", S.OFFER_ACCEPTED, Actor.CLIENT),
    (S.OFFER_SENT, "decline_offer", S.CLIENT_DECLINED, Actor.CLIENT),
    (S.OFFER_ACCEPTED, "sign", S.SIGNING, Actor.CLIENT),
    (S.OFFER_ACCEPTED, "decline_offer", S.CLIENT_DECLINED, Actor.CLIENT),
    (S.SIGNING, "issue", S.ISSUED, Actor.SYSTEM),
]


@pytest.mark.parametrize(("from_status", "action", "to_status", "actor"), ALLOWED)
def test_allowed_transition(from_status, action, to_status, actor):
    transition = find_transition(from_status, action)
    assert transition is not None, f"{from_status} --{action}--> должен быть разрешён"
    assert transition.to_status == to_status
    assert actor in transition.actors


def test_table_has_no_extra_transitions():
    """В таблице ровно те переходы, что перечислены выше (ничего лишнего не добавили случайно)."""
    from_table = {(status, t.action) for t in TRANSITIONS for status in t.from_statuses}
    expected = {(from_status, action) for from_status, action, _, _ in ALLOWED}
    assert from_table == expected


@pytest.mark.parametrize(
    ("from_status", "action"),
    [
        (S.DRAFT, "accept_offer"),  # нельзя принять предложение, которого нет
        (S.DRAFT, "approve"),  # сотрудник не одобряет черновик
        (S.SUBMITTED, "submit"),  # повторная отправка — не переход
        (S.OFFER_SENT, "sign"),  # сначала нужно принять предложение
        (S.SCORING, "cancel"),  # пока идёт автообработка, отзывать нельзя
        (S.REJECTED, "submit"),
        (S.ISSUED, "cancel"),
        (S.CHECKS, "approve"),
    ],
)
def test_forbidden_transition(from_status, action):
    assert find_transition(from_status, action) is None


@pytest.mark.parametrize("final_status", sorted(FINAL_STATUSES))
def test_no_transitions_from_final_statuses(final_status):
    assert not [t for t in TRANSITIONS if final_status in t.from_statuses]


def test_employee_actions_require_comment():
    for transition in TRANSITIONS:
        if Actor.EMPLOYEE in transition.actors:
            assert transition.requires_comment, transition.action


def test_actions_are_unique_per_status():
    """Для пары (статус, действие) должен быть ровно один переход — иначе машина неоднозначна."""
    seen = set()
    for transition in TRANSITIONS:
        for status in transition.from_statuses:
            key = (status, transition.action)
            assert key not in seen, key
            seen.add(key)
