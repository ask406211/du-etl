"""Tests for the extract layer. HTTP is mocked; no network is touched."""

import httpx
import pytest
import respx
from tenacity import wait_none

from conftest import API_URL
from du_etl.extract import build_state_filter, fetch_chapters, get_from_api


@pytest.fixture
def no_backoff():
    """Same retry policy, but without the real exponential sleeps."""
    return get_from_api.retry_with(wait=wait_none())


def test_server_errors_are_retried(no_backoff):
    """A retry policy that silently never fires looks exactly like one that works."""
    with respx.mock:
        route = respx.get(API_URL).mock(return_value=httpx.Response(503))
        with pytest.raises(httpx.HTTPStatusError):
            no_backoff(API_URL, {})
    assert route.call_count == 4, "5xx must be retried up to stop_after_attempt(4)"


def test_client_errors_are_not_retried(no_backoff):
    """A malformed query will be malformed on every attempt: fail fast."""
    with respx.mock:
        route = respx.get(API_URL).mock(return_value=httpx.Response(400))
        with pytest.raises(httpx.HTTPStatusError):
            no_backoff(API_URL, {})
    assert route.call_count == 1


def test_timeouts_are_retried(no_backoff):
    with respx.mock:
        route = respx.get(API_URL).mock(side_effect=httpx.ConnectTimeout("slow"))
        with pytest.raises(httpx.ConnectTimeout):
            no_backoff(API_URL, {})
    assert route.call_count == 4


def test_arcgis_error_body_with_http_200_is_detected():
    """ArcGIS returns HTTP 200 with an `error` key, so raise_for_status is not enough."""
    body = {"error": {"code": 400, "message": "Invalid where clause"}}
    with respx.mock:
        respx.get(API_URL).mock(return_value=httpx.Response(200, json=body))
        with pytest.raises(RuntimeError, match="Invalid where clause"):
            fetch_chapters(["CA"])


def test_fetch_returns_features():
    body = {"features": [{"attributes": {"ChapterID": "CA-1"}}]}
    with respx.mock:
        respx.get(API_URL).mock(return_value=httpx.Response(200, json=body))
        assert len(fetch_chapters(["CA"])) == 1


def test_state_filter_is_built_for_arcgis():
    assert build_state_filter(["CA"]) == "State IN ('CA')"
    assert build_state_filter(["CA", "OR"]) == "State IN ('CA', 'OR')"


def test_state_filter_escapes_quotes():
    """Single quotes are doubled so a value cannot break out of the clause."""
    assert "''" in build_state_filter(["O'Hare"])


def test_state_filter_rejects_empty_input():
    with pytest.raises(ValueError):
        build_state_filter([])
    with pytest.raises(ValueError):
        build_state_filter(["  "])
