from auditor.agent.schemas import SubmittedClaim
from auditor.agent.validator import locate_quote, validate_claims
from auditor.enums import ClaimAttribute, ClaimLabel

TEXT = "It is rated IPX4. The case is small. It is rated IPX4."
QUOTE = "It is rated IPX4"


def claim(quote: str, label: ClaimLabel = ClaimLabel.SUPPORTED, **changes) -> SubmittedClaim:
    values = {
        "quote": quote,
        "brand_id": "zentro",
        "attribute": ClaimAttribute.WATER_RESISTANCE,
        "label": label,
        "fact_ids": ["zentro-air2-ipx"],
        "rationale": "Matches the IP rating.",
    }
    values.update(changes)
    return SubmittedClaim(**values)


def validate(*claims: SubmittedClaim, seen: set[str] | None = None):
    return validate_claims(
        TEXT,
        claims,
        seen_fact_ids={"zentro-air2-ipx"} if seen is None else seen,
        known_brand_ids={"zentro", "kovalt"},
    )


def test_locate_quote_prefers_the_first_unused_occurrence_after_the_cursor() -> None:
    first = locate_quote(TEXT, QUOTE, set(), cursor=0)
    second = locate_quote(TEXT, QUOTE, {first}, cursor=first[1])
    assert first == (0, 16)
    assert second == (37, 53)
    assert locate_quote(TEXT, QUOTE, {first, second}, cursor=53) is None


def test_locate_quote_falls_back_to_an_earlier_unused_occurrence() -> None:
    # Claims out of reading order still get a free occurrence.
    assert locate_quote(TEXT, QUOTE, {(37, 53)}, cursor=53) == (0, 16)


def test_locate_quote_returns_none_when_the_text_is_absent() -> None:
    assert locate_quote(TEXT, "It is rated IPX5", set(), cursor=0) is None


def test_offsets_are_computed_by_code_for_a_repeated_sentence() -> None:
    claims, issues = validate(claim(QUOTE), claim(QUOTE))

    assert issues == []
    assert [(c.start, c.end) for c in claims] == [(0, 16), (37, 53)]
    assert all(TEXT[c.start : c.end] == c.quote for c in claims)


def test_a_third_copy_of_a_twice_repeated_sentence_is_rejected() -> None:
    claims, issues = validate(claim(QUOTE), claim(QUOTE), claim(QUOTE))
    assert claims == []
    assert issues == [
        "claim 3: quote is already used by an earlier claim; each claim needs its own text"
    ]


def test_all_issues_are_collected_in_one_pass() -> None:
    claims, issues = validate(
        claim("It is rated IPX9"),
        claim("The case is small", label=ClaimLabel.CONTRADICTED, fact_ids=[]),
        claim(QUOTE, fact_ids=["kovalt-pulse-ipx"]),
        claim(QUOTE, brand_id="ghost"),
    )

    assert claims == []
    assert len(issues) == 4
    assert issues[0].startswith("claim 1: quote not found")
    assert issues[1].startswith("claim 2: a contradicted claim must cite at least one fact ID")
    assert issues[2].startswith("claim 3: fact IDs ['kovalt-pulse-ipx'] were not returned")
    assert issues[3] == "claim 4: unknown brand_id 'ghost'"


def test_unknown_may_cite_nothing() -> None:
    claims, issues = validate(claim("The case is small", label=ClaimLabel.UNKNOWN, fact_ids=[]))
    assert issues == []
    assert claims[0].label == ClaimLabel.UNKNOWN


def test_matching_is_exact_and_case_sensitive() -> None:
    _, issues = validate(claim("it is rated IPX4"))
    assert issues[0].startswith("claim 1: quote not found")
