"""Checks the model's submitted claims, and turns quotes into character offsets.

Every check here exists because the model can be wrong in a way that would otherwise
reach the database or the review queue unnoticed.
"""

from collections.abc import Sequence

from auditor.agent.schemas import SubmittedClaim, ValidatedClaim
from auditor.enums import ClaimLabel

Span = tuple[int, int]


def locate_quote(text: str, quote: str, used_spans: set[Span], cursor: int) -> Span | None:
    """Return (start, end) of `quote` in `text`, or None if no usable occurrence exists.

    Code, not the model, computes offsets: models cannot count characters reliably, but
    they can copy text. A sentence may appear twice in an answer, so we pick an
    occurrence that no earlier claim has used, preferring the first one at or after
    `cursor` (the end of the previous claim). Models list claims in reading order, so
    the second claim quoting a repeated sentence gets its second occurrence.
    """
    starts = []
    position = text.find(quote)
    while position != -1:
        starts.append(position)
        position = text.find(quote, position + 1)

    unused = [start for start in starts if (start, start + len(quote)) not in used_spans]
    if not unused:
        return None
    after_cursor = [start for start in unused if start >= cursor]
    start = after_cursor[0] if after_cursor else unused[0]
    return start, start + len(quote)


def validate_claims(
    text: str,
    claims: Sequence[SubmittedClaim],
    *,
    seen_fact_ids: set[str],
    known_brand_ids: set[str],
) -> tuple[list[ValidatedClaim], list[str]]:
    """Validate every claim and return (validated claims, issues).

    ALL issues are collected in one pass, not just the first. The model gets one repair
    turn at most, so it must see every problem at once to fix them all together.
    If there is any issue, no claims are returned: we save all or nothing.
    """
    validated: list[ValidatedClaim] = []
    issues: list[str] = []
    used_spans: set[Span] = set()
    cursor = 0

    for number, claim in enumerate(claims, start=1):
        where = f"claim {number}"
        claim_issues = []

        span = locate_quote(text, claim.quote, used_spans, cursor)
        if span is None:
            if claim.quote in text:
                # Two claims on the same words would be counted twice in the metrics.
                claim_issues.append(
                    f"{where}: quote is already used by an earlier claim; "
                    "each claim needs its own text"
                )
            else:
                claim_issues.append(
                    f"{where}: quote not found in the answer text; copy it exactly, "
                    f"character for character: {claim.quote!r}"
                )
        else:
            used_spans.add(span)
            cursor = span[1]

        if claim.brand_id not in known_brand_ids:
            claim_issues.append(f"{where}: unknown brand_id {claim.brand_id!r}")

        # A decisive label is an accusation or an endorsement; it needs evidence.
        # "Missing evidence" is what `unknown` is for.
        if claim.label != ClaimLabel.UNKNOWN and not claim.fact_ids:
            claim_issues.append(
                f"{where}: a {claim.label} claim must cite at least one fact ID; "
                "use unknown if the catalogue cannot decide"
            )

        # Only facts the model actually looked up may be cited, so a citation proves the
        # model saw that fact and did not invent an ID.
        unseen = [fact_id for fact_id in claim.fact_ids if fact_id not in seen_fact_ids]
        if unseen:
            claim_issues.append(
                f"{where}: fact IDs {unseen} were not returned by get_brand_facts in this "
                "conversation; look them up before citing them"
            )

        if span is not None and not claim_issues:
            validated.append(
                ValidatedClaim(
                    quote=claim.quote,
                    start=span[0],
                    end=span[1],
                    brand_id=claim.brand_id,
                    product=claim.product,
                    attribute=claim.attribute,
                    label=claim.label,
                    fact_ids=tuple(claim.fact_ids),
                    rationale=claim.rationale,
                )
            )
        issues.extend(claim_issues)

    if issues:
        return [], issues
    return validated, issues
