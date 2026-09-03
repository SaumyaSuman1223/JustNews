FastAPI service: auth, users, feed, saves, search, admin, transparency.
Layering rule: routers → services → repositories. Business logic must not
know it is on HTTP. TODO(session 3.x).
