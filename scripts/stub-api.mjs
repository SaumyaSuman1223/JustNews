#!/usr/bin/env node
// A tiny fixture API for CI's structured-data check (see ci.yml's `web` job
// and e2e/structured-data.spec.ts). The rest of the web job's e2e suite
// deliberately runs with no live API - see accessibility.spec.ts's own
// comment on why the degraded state is worth exercising - so this stub is
// used only by that one test, against a second server instance on its own
// port, never the one the whole suite otherwise runs against.
//
// It is a required-field check, not schema validation: there is no public
// API for Google's Rich Results Test, and CLAUDE.md's honesty rule cuts
// against claiming this proves more than "the JSON-LD block has the fields
// a NewsArticle needs and they parse."
import { createServer } from "node:http";

const PORT = Number(process.env.STUB_PORT ?? 8089);

const ARTICLE = {
  id: 1,
  title: "Stub article for the structured-data check",
  snippet: "A fixture snippet, never real article text.",
  image_url: null,
  url: "https://example.test/stub-article",
  language: "en",
  published_at: "2026-01-01T00:00:00Z",
  source_id: 1,
  source_name: "Stub Wire",
  source_slug: "stub-wire",
  story_cluster_id: null,
};

const routes = {
  "GET /health": () => [200, { status: "ok" }],
  "GET /v1/articles/1": () => [200, ARTICLE],
};

const server = createServer((req, res) => {
  const handler = routes[`${req.method} ${req.url}`];
  const [status, body] = handler ? handler() : [404, { error: { code: "not_found" } }];
  res.writeHead(status, { "content-type": "application/json" });
  res.end(JSON.stringify(body));
});

server.listen(PORT, () => {
  console.log(`stub-api listening on ${PORT}`);
});
