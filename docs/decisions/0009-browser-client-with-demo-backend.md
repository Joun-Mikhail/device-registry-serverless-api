# 0009 — A browser client with a demo backend

## Context

The API is not deployed to a public address: a permanently running environment
costs money, and a shared API key handed out in a README is not an access model.
That leaves anyone evaluating this project — a reviewer, a hiring manager, a
non-technical reader — with nothing to *use*. Reading an OpenAPI page is not the
same as using the thing it describes.

Three options were on the table:

1. **Deploy a public demo stack.** Honest, and the only option that proves the
   deployment works. It also means a live endpoint, a shared key in public, and a
   bill that grows if anyone abuses it.
2. **A recorded video or a screenshot tour.** Cheap, but it is a claim rather than
   something the reader can operate. It also goes stale silently.
3. **A client that ships its own backend.** The interface is real; the storage
   behind it is a local implementation of the same operations.

## Decision

Option 3, with option 1 kept available rather than excluded.

`docs/site/app.html` is one file — no build step, no framework, no dependency —
that talks to a `backend` object with `list`, `create`, `update`, `remove`. Two
implement it:

- `DemoBackend` keeps devices in memory in the page, seeded with five examples.
- `LiveBackend(baseUrl, apiKey)` issues the real HTTP calls with an `x-api-key`
  header, configured through the *Connect to a live API* panel and remembered for
  the tab only (`sessionStorage`).

The validation the page applies before submitting mirrors
`src/validation/device_validator.py` — the same length limits, the same allowed
types and statuses, the same trimming.

Two rules follow from that, and both are load-bearing:

- **The mode is stated, never implied.** A banner says which backend is active and
  what that means. Demo mode says nothing is saved to a server.
- **The interface does not claim a success it did not get.** Connecting only
  reports "Connected." if the first listing actually returned; a failure clears the
  table rather than leaving the previous backend's rows visible under a live
  banner, and says why. This was a real defect, caught by a browser test before it
  shipped, not a hypothetical.

For a browser to reach the deployed API at all, the HTTP API needs CORS. That is
now in `template.yaml` as an `AllowedOrigins` parameter defaulting to the project's
GitHub Pages origin — a wildcard would let any page on the internet drive a
reader's API key.

## Consequence

The project is usable in one click by someone who will never open a terminal, and
the same interface becomes the front end of a real deployment the moment there is
one — no rewrite, one URL and one key.

The cost is a second implementation of the validation rules, in a second language,
which can drift from the Python. The mitigation is that the rules are small,
declared as constants at the top of the file next to a pointer to their source,
and that the contract tests still guard the real ones. If the duplication starts
to hurt, the honest fix is to generate the constants from `docs/openapi.yaml`
rather than to hand-maintain both.

The demo backend also proves nothing about the deployment. It is deliberately not
presented as evidence that the stack deploys — the CI badge, the coverage report
and `scripts/local_server.py` carry that weight instead.
