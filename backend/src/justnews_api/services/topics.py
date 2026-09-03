from __future__ import annotations

from justnews_core.models import Topic


def label_for(topic: Topic, language: str) -> str:
    """The display label in the reader's language, falling back to English and
    then the slug - a topic missing a translation must still render as
    something, never a blank cell or a raw concept id."""
    by_language = {label.language: label.label for label in topic.labels}
    return (
        by_language.get(language) or by_language.get("en") or topic.slug.replace("-", " ").title()
    )
