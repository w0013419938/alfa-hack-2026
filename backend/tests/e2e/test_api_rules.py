"""Правила API: авторизация, права доступа, недопустимые переходы, идемпотентность, документы, справочники."""

import threading

from tests.e2e.conftest import PDF, action_codes


# ---------- Авторизация ----------


def test_login_and_me(client):
    response = client.post("/api/v1/auth/login", json={"login": "client_good", "password": "client_good123"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["role"] == "client"
    assert me["company"]["inn"] == "7701001012"


def test_wrong_password(client):
    response = client.post("/api/v1/auth/login", json={"login": "client_good", "password": "wrong"})
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Неверный логин или пароль"


def test_no_token_and_bad_token(client):
    assert client.get("/api/v1/applications").status_code == 401
    assert client.get("/api/v1/applications", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_request_id_header(client):
    response = client.get("/api/v1/health", headers={"X-Request-ID": "test-request-12345"})
    assert response.headers["X-Request-ID"] == "test-request-12345"


# ---------- Права доступа ----------


def test_client_cannot_see_other_company_application(api):
    owner = api("client_good")
    stranger = api("client_bad")
    draft = owner.create_application()
    owner.upload(draft["id"], "other", "doc.pdf", PDF)
    document_id = owner.get(f"/applications/{draft['id']}/documents").json()[0]["id"]

    assert stranger.get(f"/applications/{draft['id']}").status_code == 404
    assert stranger.patch(f"/applications/{draft['id']}", json={"amount": 600000}).status_code == 404
    assert stranger.post(f"/applications/{draft['id']}/actions/cancel").status_code == 404
    assert stranger.get(f"/applications/{draft['id']}/documents").status_code == 404
    assert stranger.get(f"/applications/{draft['id']}/documents/{document_id}/download").status_code == 404
    assert draft["id"] not in [item["id"] for item in stranger.get("/applications").json()["items"]]
    assert owner.application(draft["id"])["status"] == "DRAFT"


def test_roles_are_separated(api):
    client = api("client_good")
    employee = api("employee")
    assert client.get("/backoffice/applications").status_code == 403
    assert client.get("/backoffice/stats").status_code == 403
    assert employee.get("/applications").status_code == 403
    assert employee.get("/company").status_code == 403
    assert employee.get("/feed").status_code == 403


# ---------- Машина состояний через API ----------


def test_invalid_transitions_return_409(api):
    client = api("client_good")
    employee = api("employee")
    draft = client.create_application()

    response = client.post(f"/applications/{draft['id']}/actions/accept_offer")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "transition_not_allowed"
    assert "Черновик" in response.json()["error"]["message"]

    assert client.post(f"/applications/{draft['id']}/actions/sign").status_code == 409
    assert client.post(f"/applications/{draft['id']}/actions/unknown").status_code == 404
    # Сотрудник не может одобрить черновик
    assert employee.post(f"/backoffice/applications/{draft['id']}/actions/approve", json={"comment": "Одобряю"}).status_code == 409


def test_repeated_action_is_idempotent(api):
    client = api("client_good")
    draft = client.create_application()
    client.action(draft["id"], "submit")
    client.wait_until_processed(draft["id"])
    # Повторная отправка той же команды — не ошибка и не новое событие
    repeated = client.action(draft["id"], "submit")
    assert repeated["timeline"].count(next(item for item in repeated["timeline"] if item["action"] == "submit")) == 1
    assert [item["action"] for item in repeated["timeline"]].count("submit") == 1

    client.action(draft["id"], "accept_offer")
    again = client.action(draft["id"], "accept_offer")
    assert again["status"] == "OFFER_ACCEPTED"
    assert [item["action"] for item in again["timeline"]].count("accept_offer") == 1


def test_concurrent_accept_creates_single_event(api):
    client = api("client_good")
    draft = client.create_application()
    client.action(draft["id"], "submit")
    assert client.wait_until_processed(draft["id"])["status"] == "OFFER_SENT"

    codes = []

    def accept():
        codes.append(client.post(f"/applications/{draft['id']}/actions/accept_offer").status_code)

    threads = [threading.Thread(target=accept) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert all(code == 200 for code in codes), codes
    final = client.application(draft["id"])
    assert final["status"] == "OFFER_ACCEPTED"
    assert [item["action"] for item in final["timeline"]].count("accept_offer") == 1


def test_version_conflict_on_edit(api):
    client = api("client_good")
    draft = client.create_application()
    first = client.patch(f"/applications/{draft['id']}", json={"amount": 1600000, "version": draft["version"]})
    assert first.status_code == 200
    stale = client.patch(f"/applications/{draft['id']}", json={"amount": 1700000, "version": draft["version"]})
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "version_conflict"


def test_cannot_edit_after_submit(api):
    client = api("client_good")
    draft = client.create_application()
    client.action(draft["id"], "submit")
    response = client.patch(f"/applications/{draft['id']}", json={"amount": 1600000})
    assert response.status_code == 409


# ---------- Валидация входных данных ----------


def test_input_validation_errors_are_in_russian(api):
    client = api("client_good")
    response = client.post("/applications", json={"product_code": "working_capital", "amount": -5})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"][0]["field"] == "amount"
    assert "больше" in error["details"][0]["message"]

    unknown_product = client.post("/applications", json={"product_code": "nope"})
    assert unknown_product.status_code == 400
    assert unknown_product.json()["error"]["code"] == "unknown_product"


# ---------- Документы ----------


def test_document_upload_rules(api):
    client = api("client_good")
    draft = client.create_application()
    assert client.upload(draft["id"], "bank_statement", "../../etc/passwd.pdf", PDF)["filename"] == "passwd.pdf"
    client.upload(draft["id"], "bank_statement", "script.exe", b"MZ", expected_status_code=400)
    client.upload(draft["id"], "bank_statement", "fake.pdf", b"not a pdf at all", expected_status_code=400)
    client.upload(draft["id"], "contract", "contract.pdf", PDF, expected_status_code=400)
    client.upload(draft["id"], "no_such_kind", "doc.pdf", PDF, expected_status_code=400)

    client.action(draft["id"], "submit")
    client.upload(draft["id"], "bank_statement", "late.pdf", PDF, expected_status_code=409)


# ---------- Справочники, калькулятор, лента, бэкофис ----------


def test_products_dictionaries_calculator_recommend(client):
    products = client.get("/api/v1/products").json()
    assert {item["code"] for item in products} >= {"express", "working_capital", "investment"}
    assert all(item["description"] and item["rate_text"] for item in products)

    purposes = client.get("/api/v1/dictionaries/purposes").json()
    assert any(item["code"] == "working_capital" for item in purposes)

    calc = client.get("/api/v1/calculator", params={"product": "working_capital", "amount": 1200000, "term": 12}).json()
    assert calc["monthly_payment"] > 100000
    assert calc["total_payment"] == round(calc["monthly_payment"] * 12, 2)
    out_of_range = client.get("/api/v1/calculator", params={"product": "working_capital", "amount": 1, "term": 12})
    assert out_of_range.status_code == 400

    recommendations = client.post(
        "/api/v1/products/recommend",
        json={"purpose_code": "equipment", "amount": 2000000, "term_months": 36, "urgency": "month", "has_collateral": True},
    ).json()
    assert recommendations[0]["suitable"] is True
    assert recommendations[0]["reasons"]


def test_feed_is_personalized(api):
    feed = api("client_info").get("/feed").json()
    assert feed
    assert all(item["reason"] for item in feed)
    assert any("ИП" in item["reason"] for item in feed)  # client_info — индивидуальный предприниматель


def test_backoffice_queue_filters_and_stats(api):
    employee = api("employee")
    queue = employee.get("/backoffice/applications", params={"status": "MANUAL_REVIEW", "page_size": 5}).json()
    assert queue["total"] >= 1
    assert all(item["status"] == "MANUAL_REVIEW" for item in queue["items"])
    assert all(item["status_label"] and item["timeline"] for item in queue["items"])
    assert all("approve" in action_codes(item) for item in queue["items"])

    graded = employee.get("/backoffice/applications", params={"grade": "A"}).json()
    assert all(item["grade"] == "A" for item in graded["items"])
    assert employee.get("/backoffice/applications", params={"status": "WRONG"}).status_code == 400

    stats = employee.get("/backoffice/stats").json()
    assert stats["total"] == sum(item["count"] for item in stats["by_status"])
    assert 0 <= stats["auto_approval_rate"] <= 1
    assert stats["decided_count"] >= stats["auto_approved_count"]


def test_seed_history_is_present(api):
    """Демо-история для очереди сотрудника загружена и разнообразна."""
    employee = api("employee")
    statuses = {item["status"] for item in employee.get("/backoffice/applications", params={"page_size": 100}).json()["items"]}
    assert {"MANUAL_REVIEW", "OFFER_SENT", "REJECTED", "ISSUED", "DRAFT", "NEEDS_INFO"} <= statuses
