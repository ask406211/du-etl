from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from .config import get_settings


def is_retryable(exception: BaseException) -> bool:

    # Retry network-related errors such as timeouts and connection failures.
    if isinstance(exception, httpx.TransportError):
        return True

    # Retry server errors (HTTP 500–599).
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code >= 500

    return False


@retry(
    retry=retry_if_exception(is_retryable),
    wait=wait_exponential(min=1, max=10),
    stop=stop_after_attempt(4),
    reraise=True,
)
def get_from_api(
    url: str,
    parameters: dict[str, Any],
) -> httpx.Response:

    response = httpx.get(
        url,
        params=parameters,
        timeout=get_settings().http_timeout,
    )

    response.raise_for_status()

    return response


def build_state_filter(states: list[str]) -> str:

    if not states:
        raise ValueError("At least one state must be provided")

    valid_states = []

    for state in states:
        state = state.strip()

        if state:
            # Escape single quotes for the ArcGIS query.
            state = state.replace("'", "''")
            valid_states.append(state)

    if not valid_states:
        raise ValueError("At least one valid state must be provided")

    state_list = ", ".join(
        f"'{state}'" for state in valid_states
    )

    return f"State IN ({state_list})"


def fetch_chapters(states: list[str]) -> list[dict[str, Any]]:

    settings = get_settings()
    state_filter = build_state_filter(states)

    chapters = []
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
            settings.du_feature_service_url,
            parameters,
        )

        data = response.json()

        # ArcGIS may return HTTP 200 even when the request itself failed.
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

        # Stop when there are no more pages.
        if not data.get("exceededTransferLimit", False):
            break

        if not page:
            break

        result_offset += len(page)

    return chapters
