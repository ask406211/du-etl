"""Unit tests for the transform layer. No network, no database."""

import json
from pathlib import Path

import pytest

from ducks_unlimited.transform import to_chapter, transform

FIXTURE = Path(__file__).parent / "fixtures" / "du_ca_response.json"
CA = ["CA"]


@pytest.fixture
def features() -> list[dict]:
    """The `features` list from a real DU API response for California."""
    return json.loads(FIXTURE.read_text())["features"]


def test_transform_returns_all_california_features(features):
    assert len(transform(features, CA)) == 3


def test_fields_are_mapped_from_the_right_source_keys(features):
    cal_poly = next(c for c in transform(features, CA) if c.chapter_id == "CA-0355")
    assert cal_poly.chapter_name == "California Polytechnic State University"
    assert cal_poly.city == "San Luis Obispo"
    assert cal_poly.state == "CA"


def test_latitude_and_longitude_are_not_swapped(features):
    """ArcGIS geometry.x is longitude, geometry.y is latitude.

    San Luis Obispo is ~35N, ~-120E. If these are swapped the chapter lands
    in the Indian Ocean, so this assertion is the guard against that bug.
    """
    cal_poly = next(c for c in transform(features, CA) if c.chapter_id == "CA-0355")
    assert 32 < cal_poly.latitude < 42, "latitude must come from geometry.y"
    assert -125 < cal_poly.longitude < -114, "longitude must come from geometry.x"


def test_missing_geometry_yields_null_coordinates():
    feature = {
        "attributes": {
            "ChapterID": "CA-9999",
            "University_Chapter": "No Geometry University",
            "City": "Nowhere",
            "State": "CA",
        }
    }
    chapter = to_chapter(feature)
    assert chapter.latitude is None and chapter.longitude is None


def test_out_of_scope_states_are_filtered_out(features):
    """Defensive filter: even if the API returns extra states, we drop them."""
    oregon = {
        "attributes": {
            "ChapterID": "OR-0001",
            "University_Chapter": "Oregon State University",
            "City": "Corvallis",
            "State": "OR",
        },
        "geometry": {"x": -123.28, "y": 44.56},
    }
    chapters = transform([*features, oregon], CA)
    assert {c.state for c in chapters} == {"CA"}
    assert len(chapters) == 3


def test_malformed_record_is_skipped_not_fatal(features):
    """One bad record must not abort the run; the good ones still load."""
    malformed = {"attributes": {"ChapterID": "CA-BAD"}}  # no University_Chapter
    chapters = transform([*features, malformed], CA)
    assert len(chapters) == 3


def test_state_filter_is_case_insensitive(features):
    assert len(transform(features, ["ca"])) == 3
