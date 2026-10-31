"""Finds which brands an answer mentions. Plain code, no model: cheap, deterministic, testable."""

import re
from collections.abc import Sequence

from auditor.catalogue.schema import Brand


class MentionDetector:
    """Whole-word, case-insensitive search for every brand name and alias.

    - Whole word: "Kovalt" must not match inside "Kovaltron". We use (?<!\\w) and (?!\\w)
      instead of \\b, because \\b fails next to names that end in a symbol or digit.
    - Longest name first: regex alternation takes the first alternative that matches,
      so "Nova Sound" must come before "Nova" or the longer name would never be seen.
      That matters when one brand's name starts with another brand's name.
    """

    def __init__(self, brands: Sequence[Brand]) -> None:
        self._brand_by_name: dict[str, str] = {}
        for brand in brands:
            for name in (brand.name, *brand.aliases):
                self._brand_by_name[name.casefold()] = brand.brand_id
        names = sorted(self._brand_by_name, key=len, reverse=True)
        self._pattern = (
            re.compile(
                r"(?<!\w)(" + "|".join(re.escape(name) for name in names) + r")(?!\w)",
                re.IGNORECASE,
            )
            if names
            else None
        )

    def detect(self, text: str) -> list[str]:
        """Sorted brand IDs mentioned at least once in `text`."""
        if self._pattern is None:
            return []
        found = {self._brand_by_name[match.casefold()] for match in self._pattern.findall(text)}
        return sorted(found)
