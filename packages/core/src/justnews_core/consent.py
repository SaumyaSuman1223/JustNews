"""The server-side half of the consent story.

`frontend/lib/consent.ts` is where a reader's choice lives (the `jn_consent`
cookie) and where `jn_sid`, the browsing-session id, stops existing until
that choice is "granted". A request that reaches this API without an
`x-session-id` header - because the reader has not consented, or is on an
old client that predates this - still needs *some* value for the `NOT NULL`
`interaction_events.session_id` column. A fresh `uuid.uuid4()` per request
was the previous fallback, and it is worse than this: it gives every such
row an untraceable, unique id, so nothing in the data can even tell "this
is the same unconsented visitor acting twice" from "these are two different
people". One shared, greppable sentinel says plainly what happened instead
of manufacturing a fake identity for each event.
"""

from __future__ import annotations

UNCONSENTED_SESSION = "unconsented"
