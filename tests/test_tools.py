"""
tests/test_tools.py

One test per failure mode for each of the three FitFindr tools.
suggest_outfit and create_fit_card hit the live Groq API — requires GROQ_API_KEY in .env.
"""

import pytest
from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def real_item():
    """A listing we know exists in the dataset."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert results, "fixture requires at least one matching listing"
    return results[0]


@pytest.fixture
def outfit_suggestion(real_item):
    """A real LLM-generated outfit string for use in fit card tests."""
    return suggest_outfit(real_item, get_example_wardrobe())


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    # Failure mode: no match — must return [] not raise
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    # Failure mode: listings above max_price must be excluded
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    # Failure mode: listings whose size field doesn't contain the requested size must be excluded
    results = search_listings("top", size="XL", max_price=100)
    assert all("xl" in item["size"].lower() for item in results)


def test_search_returns_at_most_three():
    # Failure mode: tool must cap results at 3 regardless of how many match
    results = search_listings("vintage", size=None, max_price=500)
    assert len(results) <= 3


def test_search_result_shape():
    # Failure mode: each returned dict must have the expected keys
    results = search_listings("jacket", size=None, max_price=200)
    required_keys = {"title", "price", "platform", "condition"}
    for item in results:
        assert required_keys.issubset(item.keys()), f"Missing keys in: {item}"


def test_search_zero_price_ceiling():
    # Failure mode: max_price=0 should exclude everything priced above $0
    results = search_listings("tee", size=None, max_price=0)
    assert all(item["price"] <= 0 for item in results)


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def test_suggest_outfit_returns_string(real_item):
    result = suggest_outfit(real_item, get_example_wardrobe())
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_outfit_empty_wardrobe_does_not_crash(real_item):
    # Failure mode: empty wardrobe must produce a suggestion, not an exception
    result = suggest_outfit(real_item, get_empty_wardrobe())
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_outfit_explicit_empty_items(real_item):
    # Failure mode: {"items": []} passed directly — must not crash or return ""
    result = suggest_outfit(real_item, {"items": []})
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_outfit_references_item_title(real_item):
    # The suggestion should be grounded in the actual item
    result = suggest_outfit(real_item, get_example_wardrobe())
    title_words = real_item["title"].lower().split()
    assert any(word in result.lower() for word in title_words)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def test_fit_card_returns_string(real_item, outfit_suggestion):
    result = create_fit_card(outfit_suggestion, real_item)
    assert isinstance(result, str)
    assert len(result) > 0


def test_fit_card_empty_outfit_returns_error_string(real_item):
    # Failure mode: empty outfit must return an error string, not raise
    result = create_fit_card("", real_item)
    assert isinstance(result, str)
    assert "error" in result.lower()


def test_fit_card_whitespace_outfit_returns_error_string(real_item):
    # Failure mode: whitespace-only outfit must also return an error string
    result = create_fit_card("   ", real_item)
    assert isinstance(result, str)
    assert "error" in result.lower()


def test_fit_card_varies_across_runs(real_item, outfit_suggestion):
    # Failure mode: captions must not be identical (temperature too low)
    outputs = {create_fit_card(outfit_suggestion, real_item) for _ in range(3)}
    assert len(outputs) > 1, "All 3 captions were identical — increase LLM temperature"


def test_fit_card_mentions_platform(real_item, outfit_suggestion):
    result = create_fit_card(outfit_suggestion, real_item)
    assert real_item["platform"].lower() in result.lower()


def test_fit_card_mentions_price(real_item, outfit_suggestion):
    result = create_fit_card(outfit_suggestion, real_item)
    assert str(int(real_item["price"])) in result
