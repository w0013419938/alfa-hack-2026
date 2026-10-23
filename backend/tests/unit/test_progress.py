"""Юнит-тесты шкалы этапов заявки (поле progress)."""

import pytest

from app.domain.progress import STEPS, EventInfo, build_progress


def states(status, events=()):
    return dict(build_progress(status, list(events)))


def event(action, from_status, to_status):
    return EventInfo(action=action, from_status=from_status, to_status=to_status)


@pytest.mark.parametrize(
    ("status", "step", "state"),
    [
        ("DRAFT", "submitted", "action"),
        ("SUBMITTED", "validation", "current"),
        ("VALIDATION", "validation", "current"),
        ("CHECKS", "checks", "current"),
        ("SCORING", "scoring", "current"),
        ("MANUAL_REVIEW", "decision", "current"),
        ("OFFER_SENT", "decision", "action"),
        ("OFFER_ACCEPTED", "signing", "action"),
        ("SIGNING", "issued", "current"),
        ("REJECTED", "decision", "stopped"),
    ],
)
def test_current_step_for_status(status, step, state):
    result = states(status)
    assert result[step] == state
    index = STEPS.index(step)
    assert all(result[code] == "done" for code in STEPS[:index])
    assert all(result[code] == "upcoming" for code in STEPS[index + 1 :])


def test_issued_means_everything_done():
    assert set(states("ISSUED").values()) == {"done"}


def test_needs_info_after_validation_is_on_validation_step():
    result = states("NEEDS_INFO", [event("submit", "DRAFT", "SUBMITTED"), event("validation_failed", "VALIDATION", "NEEDS_INFO")])
    assert result["validation"] == "action"
    assert result["checks"] == "upcoming"


def test_needs_info_after_decision_is_on_decision_step():
    for action in ("auto_request_info", "request_info"):
        result = states("NEEDS_INFO", [event(action, "SCORING", "NEEDS_INFO")])
        assert result["decision"] == "action"
        assert result["scoring"] == "done"


def test_cancelled_stops_where_application_was():
    result = states("CANCELLED", [event("create", None, "DRAFT"), event("cancel", "DRAFT", "CANCELLED")])
    assert result["submitted"] == "stopped"
    review = states("CANCELLED", [event("send_to_manual_review", "SCORING", "MANUAL_REVIEW"), event("cancel", "MANUAL_REVIEW", "CANCELLED")])
    assert review["decision"] == "stopped"
    assert review["scoring"] == "done"


def test_client_declined_after_acceptance_stops_on_signing():
    events = [event("accept_offer", "OFFER_SENT", "OFFER_ACCEPTED"), event("decline_offer", "OFFER_ACCEPTED", "CLIENT_DECLINED")]
    assert states("CLIENT_DECLINED", events)["signing"] == "stopped"
    assert states("CLIENT_DECLINED", [event("decline_offer", "OFFER_SENT", "CLIENT_DECLINED")])["decision"] == "stopped"


def test_exactly_one_current_like_step():
    for status in ["DRAFT", "SUBMITTED", "CHECKS", "MANUAL_REVIEW", "OFFER_SENT", "REJECTED"]:
        values = list(states(status).values())
        assert sum(value in ("current", "action", "stopped") for value in values) == 1
