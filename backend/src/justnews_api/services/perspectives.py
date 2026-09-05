"""Perspectives (ADR 0013): grouping articles by a fact already on file -
who published them - never a guess about what the text says.

A story's or topic's Perspectives are its articles grouped by
``Source.source_role``. ``wire`` and an unroled source are both excluded
from the groups: a wire service is not a perspective (it exists precisely to
keep Reuters/AP out of one), and an unroled source's silence is correct -
inventing a role for it would be exactly the unverifiable assertion the ADR
rules out.
"""

from __future__ import annotations

from dataclasses import dataclass

# Deliberately excludes "wire" - see the module docstring. Order here is
# display order, and it is the order the UI renders groups in.
ROLE_ORDER = ("industry", "government", "academic", "investor", "consumer", "public")


@dataclass(frozen=True, slots=True)
class PerspectiveSource:
    id: int
    slug: str
    name: str
    homepage_url: str


@dataclass(frozen=True, slots=True)
class PerspectiveGroup:
    role: str
    article_count: int
    sources: list[PerspectiveSource]


def group_by_role(
    rows: list[tuple[str | None, int, str, str, str]],
) -> list[PerspectiveGroup]:
    """`rows`: one entry per live article, as
    ``(source_role, source_id, source_slug, source_name, source_homepage_url)``.
    """
    sources_by_role: dict[str, dict[int, PerspectiveSource]] = {}
    article_counts: dict[str, int] = {}

    for role, source_id, slug, name, homepage_url in rows:
        if role is None or role == "wire" or role not in ROLE_ORDER:
            continue
        sources_by_role.setdefault(role, {})[source_id] = PerspectiveSource(
            id=source_id, slug=slug, name=name, homepage_url=homepage_url
        )
        article_counts[role] = article_counts.get(role, 0) + 1

    return [
        PerspectiveGroup(
            role=role,
            article_count=article_counts[role],
            sources=sorted(sources_by_role[role].values(), key=lambda s: s.name),
        )
        for role in ROLE_ORDER
        if role in sources_by_role
    ]
