
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from .config import get_settings


def is_retryable(exception: BaseException) -> bool:
    """Retry transient failures only: timeouts, connection errors, 5xx."""
    if isinstance(exception, httpx.TransportError):  # timeouts + connect errors
        return True
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code >= 500
    return False


@retry(
    retry=retry_if_exception(is_retryable),
    wait=wait_exponential(min=1, max=10),
    stop=stop_after_attempt(4),
    reraise=True,
)
def get_from_api(url: str, parameters: dict[str, Any]) -> httpx.Response:
    """Make an API request, retrying temporary failures."""
    response = httpx.get(
        url,
        params=parameters,
        timeout=get_settings().http_timeout,
    )

    response.raise_for_status()

    return response


def build_state_filter(states: list[str]) -> str:
    """Create the ArcGIS filter for the requested states."""
    if not states:
        raise ValueError("At least one state must be provided")

    state_values = [
        state.strip().replace("'", "''")
        for state in states
        if state.strip()
    ]

    if not state_values:
        raise ValueError("At least one valid state must be provided")

    states_for_query = ", ".join(
        f"'{state}'" for state in state_values
    )

    return f"State IN ({states_for_query})"


def fetch_chapters(states: list[str]) -> list[dict]:
    """Fetch chapter records from the Ducks Unlimited API."""
    state_filter = build_state_filter(states)

    chapters: list[dict] = []
    result_offset = 0

    while True:
        parameters = {
            "where": state_filter,
            "outFields": "*",
            "outSR": 4326,
            "returnGeometry": "true",
            "f": "json",
            "resultOffset": result_offset,
        }

        response = get_from_api(
            get_settings().du_feature_service_url,
            parameters,
        )

        data = response.json()

        # ArcGIS can return HTTP 200 even when the request failed.
        if "error" in data:
            raise RuntimeError(
                f"ArcGIS API returned an error: {data['error']}"
            )

        page = data.get("features", [])

        if not isinstance(page, list):
            raise RuntimeError(
                "Unexpected response from ArcGIS: features is not a list"
            )

        chapters.extend(page)

        # Stop when ArcGIS tells us there are no more records.
        if not data.get("exceededTransferLimit", False):
            break

        # Avoid getting stuck if the API says there are more records
        # but doesn't actually return any.
        if not page:
            break

        result_offset += len(page)

    return chapters
