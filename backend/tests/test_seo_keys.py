"""Pure unit tests for public detail-page URL keys (no database needed)."""

from app.core.seo import id_suffix, slug_for

# Ids that collided under the old 8-character prefix scheme.
COLLIDING_IDS = [
    "indian-army-agniveer-gd",
    "indian-army-technical",
    "indian-army-ncc-special-ent-295b496d",
    "indian-navy-mr",
    "indian-navy-ssr",
    "upsc-capf-ac",
    "upsc-capf-ac-2027",
    "agg-upsssc-moharir-2022",
    "agg-upsssc-cane-supervisor-2026",
    "agg-upsssc-junior-assistant-2026",
]


def test_id_suffix_is_unique_for_previously_colliding_ids():
    suffixes = [id_suffix(record_id) for record_id in COLLIDING_IDS]
    assert len(set(suffixes)) == len(COLLIDING_IDS)


def test_short_ids_are_preserved():
    assert id_suffix("afcat") == "afcat"
    assert slug_for("AFCAT", "afcat").endswith("-afcat")


def test_suffix_is_normalised_consistently():
    assert id_suffix("ABC-123_def") == id_suffix("abc123def")
