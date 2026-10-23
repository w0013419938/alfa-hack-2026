"""Юнит-тесты клиента внешних сервисов: ретраи, таймауты, ошибки (сеть подменена httpx.MockTransport)."""

import httpx

from app.integrations.external_client import HttpExternalDataClient

INN = "7701001012"


def make_client(handler, max_attempts=3):
    return HttpExternalDataClient(
        base_url="http://mock",
        timeout_seconds=0.5,
        max_attempts=max_attempts,
        backoff_seconds=0,
        transport=httpx.MockTransport(handler),
    )


def test_success_on_first_attempt():
    client = make_client(lambda request: httpx.Response(200, json={"rating": 700}))
    result = client.get_bki_report(INN)
    assert result.status == "ok"
    assert result.data == {"rating": 700}
    assert result.attempts == 1


def test_retries_after_server_error_and_succeeds():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"rating": 650})

    result = make_client(handler).get_bki_report(INN)
    assert result.status == "ok"
    assert result.attempts == 3
    assert len(calls) == 3


def test_timeout_after_all_attempts():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("timeout", request=request)

    result = make_client(handler, max_attempts=2).get_bki_report(INN)
    assert result.status == "timeout"
    assert result.data is None
    assert result.attempts == 2
    assert len(calls) == 2


def test_server_error_after_all_attempts():
    result = make_client(lambda request: httpx.Response(500)).get_egrul(INN)
    assert result.status == "error"
    assert result.error_message == "HTTP 500"
    assert result.attempts == 3


def test_connection_error_is_reported_not_raised():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    result = make_client(handler).get_egrul(INN)
    assert result.status == "error"
    assert "соединения" in result.error_message


def test_bad_request_is_not_retried():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(400)

    result = make_client(handler).get_bki_report(INN)
    assert result.status == "error"
    assert len(calls) == 1


def test_egrul_not_found_means_company_does_not_exist():
    result = make_client(lambda request: httpx.Response(404)).get_egrul(INN)
    assert result.status == "ok"
    assert result.data["not_found"] is True


def test_request_id_is_forwarded():
    seen = {}

    def handler(request):
        seen["request_id"] = request.headers.get("X-Request-ID")
        return httpx.Response(200, json={})

    make_client(handler).get_egrul(INN)
    assert seen["request_id"]
