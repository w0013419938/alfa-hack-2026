"""Сквозные сценарии для каждой демо-учётки: от создания заявки до финального статуса.

Это те же сценарии, что описаны для жюри в docs/test-scenarios.md.
"""

from tests.e2e.conftest import PDF, STANDARD_APPLICATION, action_codes


def test_client_good_auto_approval_to_issue(api):
    client = api("client_good")
    draft = client.create_application()
    assert draft["status"] == "DRAFT"
    assert {"edit", "submit", "cancel"} <= action_codes(draft)

    submitted = client.action(draft["id"], "submit")
    assert submitted["status"] == "SUBMITTED"

    offer_sent = client.wait_until_processed(draft["id"])
    assert offer_sent["status"] == "OFFER_SENT"
    offer = offer_sent["offer"]
    assert offer["offer_type"] == "as_requested"
    assert offer["amount"] == STANDARD_APPLICATION["amount"]
    assert offer["term_months"] == STANDARD_APPLICATION["term_months"]
    assert offer["monthly_payment"] > 0
    assert action_codes(offer_sent) == {"accept_offer", "decline_offer"}
    # В истории видны все шаги автоматической обработки
    actions = [item["action"] for item in offer_sent["timeline"]]
    assert actions == ["create", "submit", "start_validation", "validation_passed", "checks_completed", "auto_approve"]

    contract_draft = client.get(f"/applications/{draft['id']}/contract")
    assert contract_draft.status_code == 200
    assert "Проект договора" in contract_draft.text

    accepted = client.action(draft["id"], "accept_offer")
    assert accepted["status"] == "OFFER_ACCEPTED"
    assert accepted["offer"]["status"] == "accepted"
    assert action_codes(accepted) == {"sign", "decline_offer"}

    signing = client.action(draft["id"], "sign")
    assert signing["status"] in ("SIGNING", "ISSUED")
    issued = client.wait_until_processed(draft["id"])
    assert issued["status"] == "ISSUED"
    assert issued["is_final"] is True
    assert issued["available_actions"] == []
    assert issued["timeline"][-1]["action"] == "issue"
    assert {step["state"] for step in issued["progress"]} == {"done"}

    documents = client.get(f"/applications/{draft['id']}/documents").json()
    assert [item["kind"] for item in documents] == ["contract"]
    download = client.get(documents[0]["download_url"].removeprefix("/api/v1"))
    assert download.status_code == 200
    assert "Подписано" in download.text


def test_client_medium_counter_offer_then_decline(api):
    client = api("client_medium")
    draft = client.create_application()
    client.action(draft["id"], "submit")
    result = client.wait_until_processed(draft["id"])

    assert result["status"] == "OFFER_SENT"
    offer = result["offer"]
    assert offer["offer_type"] == "counter_offer"
    # Встречное предложение: меньше сумма или дольше срок
    assert offer["amount"] < STANDARD_APPLICATION["amount"] or offer["term_months"] > STANDARD_APPLICATION["term_months"]
    assert result["timeline"][-1]["action"] == "auto_counter_offer"
    assert result["timeline"][-1]["comment"]

    declined = client.action(draft["id"], "decline_offer", comment="Нужна вся сумма")
    assert declined["status"] == "CLIENT_DECLINED"
    assert declined["offer"]["status"] == "declined"
    assert declined["is_final"] is True


def test_client_border_manual_review_then_employee_approves(api):
    client = api("client_border")
    employee = api("employee")
    draft = client.create_application()
    client.action(draft["id"], "submit")
    review = client.wait_until_processed(draft["id"])
    assert review["status"] == "MANUAL_REVIEW"
    assert action_codes(review) == {"cancel"}

    card = employee.get(f"/backoffice/applications/{draft['id']}").json()
    assert {"approve", "counter_offer", "request_info", "reject"} == action_codes(card)
    assert card["scoring"]["grade"]
    assert len(card["scoring"]["factors"]) > 0
    assert all(factor["explanation"] for factor in card["scoring"]["factors"])
    assert {check["check_type"] for check in card["checks"]} == {"egrul", "bki"}
    assert card["decision"]["outcome"] == "manual_review"
    assert card["suggested_offer"]["amount"] == STANDARD_APPLICATION["amount"]

    # Комментарий обязателен
    employee.employee_action(draft["id"], "approve", expected_status_code=422, comment="")
    approved = employee.employee_action(draft["id"], "approve", comment="Одобряем на меньшую сумму", amount=1_200_000, term_months=30)
    assert approved["status"] == "OFFER_SENT"
    assert approved["offers"][0]["offer_type"] == "counter_offer"

    client_view = client.application(draft["id"])
    assert client_view["offer"]["amount"] == 1_200_000
    assert client_view["timeline"][-1]["comment"] == "Одобряем на меньшую сумму"

    client.action(draft["id"], "accept_offer")
    client.action(draft["id"], "sign")
    assert client.wait_until_processed(draft["id"])["status"] == "ISSUED"


def test_client_bad_rejected_with_reason(api):
    client = api("client_bad")
    draft = client.create_application()
    client.action(draft["id"], "submit")
    result = client.wait_until_processed(draft["id"])

    assert result["status"] == "REJECTED"
    assert result["is_final"] is True
    assert result["available_actions"] == []
    reason = result["timeline"][-1]
    assert reason["action"] == "auto_reject"
    assert "ликвидац" in reason["comment"].lower()
    assert "просрочка" in reason["comment"].lower()


def test_client_info_needs_document_then_offer(api):
    client = api("client_info")
    draft = client.create_application()
    client.action(draft["id"], "submit")
    needs_info = client.wait_until_processed(draft["id"])

    assert needs_info["status"] == "NEEDS_INFO"
    decision_step = next(step for step in needs_info["progress"] if step["code"] == "decision")
    assert decision_step["state"] == "action"
    request = needs_info["info_request"]
    assert request["comment"]
    assert [item["kind"] for item in request["documents"]] == ["bank_statement"]
    assert request["documents"][0]["uploaded"] is False
    # Пока документа нет, кнопка есть, но неактивна — и объясняет почему
    provide = next(item for item in needs_info["available_actions"] if item["code"] == "provide_info")
    assert provide["enabled"] is False and provide["disabled_reason"]
    client.action(draft["id"], "provide_info", expected_status_code=409)

    client.upload(draft["id"], "bank_statement", "выписка.pdf", PDF)
    with_document = client.application(draft["id"])
    assert with_document["info_request"]["documents"][0]["uploaded"] is True
    assert "provide_info" in action_codes(with_document)

    client.action(draft["id"], "provide_info", comment="Выписку загрузила")
    result = client.wait_until_processed(draft["id"])
    assert result["status"] == "OFFER_SENT"
    assert result["info_request"] is None
    assert "provide_info" in [item["action"] for item in result["timeline"]]


def test_client_timeout_bki_failure_goes_to_manual_review(api):
    client = api("client_timeout")
    employee = api("employee")
    draft = client.create_application()
    client.action(draft["id"], "submit")
    result = client.wait_until_processed(draft["id"], timeout=60)

    assert result["status"] == "MANUAL_REVIEW"
    assert "Бюро кредитных историй" in result["timeline"][-1]["comment"]

    card = employee.get(f"/backoffice/applications/{draft['id']}").json()
    bki = next(check for check in card["checks"] if check["check_type"] == "bki")
    assert bki["status"] == "timeout"
    assert bki["attempts"] > 1  # были повторные попытки
    egrul = next(check for check in card["checks"] if check["check_type"] == "egrul")
    assert egrul["status"] == "ok"
    assert card["decision"]["reasons"][0]["code"] == "integration_error"

    rejected = employee.employee_action(draft["id"], "reject", comment="Не удалось проверить кредитную историю")
    assert rejected["status"] == "REJECTED"
    assert client.application(draft["id"])["timeline"][-1]["comment"] == "Не удалось проверить кредитную историю"


def test_validation_needs_info_then_provide_info_then_offer(api):
    """Анкета без выручки → NEEDS_INFO с перечнем полей → исправление → provide_info → OFFER_SENT."""
    client = api("client_good")
    draft = client.create_application(monthly_revenue=None, amount=100)
    client.action(draft["id"], "submit")
    needs_info = client.wait_until_processed(draft["id"])

    assert needs_info["status"] == "NEEDS_INFO"
    fields = {item["field"] for item in needs_info["info_request"]["fields"]}
    assert {"monthly_revenue", "amount"} <= fields
    assert needs_info["timeline"][-1]["action"] == "validation_failed"

    fixed = client.patch(f"/applications/{draft['id']}", json={"monthly_revenue": 800000, "amount": 1500000, "version": needs_info["version"]})
    assert fixed.status_code == 200, fixed.text
    client.action(draft["id"], "provide_info", comment="Исправил")
    result = client.wait_until_processed(draft["id"])
    assert result["status"] == "OFFER_SENT"


def test_employee_request_info_then_client_answers(api):
    client = api("client_border")
    employee = api("employee")
    draft = client.create_application()
    client.action(draft["id"], "submit")
    assert client.wait_until_processed(draft["id"])["status"] == "MANUAL_REVIEW"

    employee.employee_action(
        draft["id"],
        "request_info",
        comment="Пришлите отчётность и уточните выручку",
        requested_documents=["financial_report"],
        requested_fields=["monthly_revenue"],
    )
    needs_info = client.application(draft["id"])
    assert needs_info["status"] == "NEEDS_INFO"
    assert needs_info["info_request"]["created_by"] == "Кредитный специалист"
    assert needs_info["info_request"]["fields"][0]["field"] == "monthly_revenue"

    client.upload(draft["id"], "financial_report", "отчётность.pdf", PDF)
    # Клиент «улучшает» анкету — но раз уточнения просил специалист, решение всё равно за ним
    client.patch(f"/applications/{draft['id']}", json={"monthly_revenue": 9000000, "amount": 500000})
    client.action(draft["id"], "provide_info")
    after = client.wait_until_processed(draft["id"])
    assert after["status"] == "MANUAL_REVIEW"
    card = employee.get(f"/backoffice/applications/{draft['id']}").json()
    assert card["decision"]["reasons"][0]["code"] == "returned_to_employee"
    # Проверки и скоринг пересчитаны по свежим данным — специалисту видна актуальная картина
    assert len([check for check in card["checks"] if check["check_type"] == "bki"]) == 2


def test_client_can_cancel_draft(api):
    client = api("client_good")
    draft = client.create_application()
    cancelled = client.action(draft["id"], "cancel")
    assert cancelled["status"] == "CANCELLED"
    assert cancelled["available_actions"] == []
