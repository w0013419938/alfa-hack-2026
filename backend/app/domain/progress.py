"""Шкала этапов заявки для экрана клиента: «Подана → Проверка данных → ... → Выдача».

Фронт рисует шкалу строго по этому полю и не знает, как статусы соотносятся с этапами.
Состояния этапа:
    done      — этап пройден;
    current   — сейчас на этом этапе работает банк;
    action    — этап ждёт действия клиента (исправить анкету, принять предложение, подписать);
    stopped   — процесс остановился на этом этапе (отказ, отзыв заявки, отказ от предложения);
    upcoming  — этап впереди.
Названия этапов и состояний — в config/labels.yaml (progress_steps, progress_states).
"""

from dataclasses import dataclass

from app.domain.statuses import ApplicationStatus

S = ApplicationStatus

STEPS = ["submitted", "validation", "checks", "scoring", "decision", "signing", "issued"]

DONE = "done"
CURRENT = "current"
ACTION = "action"
STOPPED = "stopped"
UPCOMING = "upcoming"

# Статус → (этап, состояние этого этапа). Все этапы до него — пройдены, после — впереди.
STEP_BY_STATUS = {
    S.DRAFT: ("submitted", ACTION),
    S.SUBMITTED: ("validation", CURRENT),
    S.VALIDATION: ("validation", CURRENT),
    S.CHECKS: ("checks", CURRENT),
    S.SCORING: ("scoring", CURRENT),
    S.MANUAL_REVIEW: ("decision", CURRENT),
    S.OFFER_SENT: ("decision", ACTION),
    S.OFFER_ACCEPTED: ("signing", ACTION),
    S.SIGNING: ("issued", CURRENT),
    S.ISSUED: ("issued", DONE),
    S.REJECTED: ("decision", STOPPED),
}


@dataclass
class EventInfo:
    action: str
    from_status: str | None
    to_status: str


def step_for_needs_info(events: list[EventInfo]) -> str:
    """Уточнения просят либо на проверке данных (анкета заполнена с ошибками), либо уже на этапе решения."""
    last = next((event for event in reversed(events) if event.to_status == S.NEEDS_INFO), None)
    return "validation" if last is not None and last.action == "validation_failed" else "decision"


def current_step(status: str, events: list[EventInfo]) -> tuple[str, str]:
    if status == S.NEEDS_INFO:
        return step_for_needs_info(events), ACTION
    if status in (S.CANCELLED, S.CLIENT_DECLINED):
        # Остановились на том этапе, где была заявка перед отзывом или отказом
        last = next((event for event in reversed(events) if event.to_status == status), None)
        previous_status = last.from_status if last and last.from_status else S.DRAFT
        previous_events = events[: events.index(last)] if last else events
        step, _ = current_step(previous_status, previous_events)
        return step, STOPPED
    return STEP_BY_STATUS.get(status, ("submitted", ACTION))


def build_progress(status: str, events: list[EventInfo]) -> list[tuple[str, str]]:
    """Список (код этапа, состояние) в порядке STEPS."""
    step, state = current_step(status, events)
    index = STEPS.index(step)
    result = []
    for position, code in enumerate(STEPS):
        if position < index:
            result.append((code, DONE))
        elif position == index:
            result.append((code, state))
        else:
            result.append((code, UPCOMING))
    return result
