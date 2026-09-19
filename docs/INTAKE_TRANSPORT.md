# Agent intake — transport protocol (client side)

This document states the transport contract between an agent-side client and an intake
worker, as the client implements it. It describes a **protocol**, not a deployment: the
worker's origin, its credentials and its server-side constants are supplied by the
operator and are not part of this text.

## 1. Routes

Nine routes are reachable from the client side. Each is listed with the method the client
uses, the credential role it presents, and what the client establishes about it.

| route | method | credential role | what the client establishes |
|---|---|---|---|
| `/publish` | POST | publish | Publishes one text row `{from, text}` (optionally `silent: true`). Text is 1..4000 characters; the client refuses out-of-range text offline before any network act. |
| `/close` | POST | publish | Publishes a ruling **closure**, keyed on the ruling and carrying the `rev` of the card being closed and a caller id `cid`. A re-POST overwrites; nothing deletes on re-open. Irreversible from the client's view. |
| `/beacon` | POST | beacon | Liveness stamp. Empty body. `200` with `{"ok":true}` is the only success. |
| `/pending` | GET | read | Returns `{items:[...]}`, each item carrying a numeric `id`. Without a cursor it is a **pure read** that consumes nothing. With `?after=<id>` it is the single consumer's read: the poller appends every item to its inbox **before** committing `max(id)` as its cursor (process, then commit). |
| `/pendpick` | — | read | Named in client commentary only: a **consuming** read that deletes every id at or below `after`. No client in this set calls it; the health check pins itself to bare `/pending` precisely because a second consumer destroyed items in production. |
| `/rule` | GET | rule | Signed read of a rule gate: `GET /rule?action_id=<id>`. The **query string is part of the signed path**. A GET with any body is rejected uniformly. The client sends no body and is structurally unable to write. |
| `/rulegate` | — | rule | Named in client commentary only: the server-internal read that `GET /rule` projects to. Not client-callable as measured. |
| `/ruleclaim` | — | rule | Named in client commentary only: the write lane behind `PUT /rule` (mints a claim token, consumes the verifier record, write-once). No client in this set writes it. |
| `/fleet` | POST | fleet | The fleet poster's route, reached by a separate poster that is credential- **and** path-locked to it and refuses any other endpoint. Named in this set only as the route the closure client declines to reuse. |

Four credential roles are distinct on the client side — **publish**, **beacon**, **rule**,
**read** (pending) — and a fifth, **fleet**, belongs to the separate poster. A credential is
a 64-hex-character key read from the operator's key store; a malformed key refuses before
any request is built.

## 2. Request headers

Every signed request carries three headers; one route family adds a fourth.

| header | carries | on |
|---|---|---|
| `x-intake-ts` | the request timestamp, milliseconds since the epoch, decimal | all signed routes |
| `x-intake-nonce` | a per-request random value, 16 bytes, base64url | all signed routes |
| `x-intake-sig` | the request signature (construction: §3) | all signed routes |
| `x-intake-consumer` | the consumer identity, lowercase | `/rule` — enforced on PUT only; the read client sends it regardless |

`content-type: application/json` accompanies every body-bearing POST. A redirect on any
signed route is an **error**, never followed: a signed header must not be re-sent to a
target the admitted origin merely points at.

## 3. Signature construction

**Algorithm.** HMAC-SHA-256. The key is a 32-byte secret, held by the verifier as 64
lowercase hex characters and imported raw. The signature travels in `x-intake-sig` as the
MAC in 64 lowercase hex characters; a header of any other shape is refused before any
verification is attempted.

**Canonical string (v1).** Five fields joined by `|`:

    METHOD|PATH|TS|NONCE|BODYHASH

| field | value |
|---|---|
| `METHOD` | the request method, uppercase |
| `PATH` | the request path, **including the query string** on a route that has one (the `/rule` client signs `pathname + search`, and the verifier reconstructs the same `pathname + search` from the URL it acts on) |
| `TS` | the `x-intake-ts` value: milliseconds since the epoch, 10–16 decimal digits |
| `NONCE` | the `x-intake-nonce` value: 16–64 characters of `[A-Za-z0-9_-]` |
| `BODYHASH` | lowercase hex SHA-256 of the exact request body bytes; a request with no body hashes the empty string |

The fields cannot collide: the timestamp is digits, the nonce and body hash are drawn from
alphabets without `|`, and no method or path carries `|`.

**Host-bound construction (v2).** Six fields, each prefixed by its length in UTF-8 bytes:

    v2|<n>:METHOD|<n>:PATH|<n>:TS|<n>:NONCE|<n>:BODYHASH|<n>:ORIGIN

`ORIGIN` is the serialized origin of the endpoint the client dials (scheme and host
lowercase, default port omitted, nothing after the authority). No version marker travels on
the wire: the verifier tells the constructions apart by reconstruction — it builds each
candidate string it accepts and accepts the request if any one verifies. The origin it
reconstructs against is a static allowlist configured at the verifier, **never** the
request's own `Host` or URL, because a self-reported origin would bind nothing. Which
constructions the agent routes accept is a deployment setting — v1 only (the default when
the setting is absent), both, or v2 only — and any other value refuses every request on
those routes. Device-authenticated routes accept v1 only. A client signs v1 unless it is
configured to sign v2.

**Order of checks and the comparison.** At every request-authentication site the verifier:
(1) rejects a timestamp outside its freshness window; (2) consumes the nonce through a
single-threaded coordinator — the first consumer wins and a replay is refused — **before**
verifying the signature; (3) verifies with the platform's constant-time HMAC verify. No
equality operator is applied to a signature value at any site. These three properties were
measured on the deployed verifier at each of its three authentication sites, and each
measurement was shown to discriminate: removing the property it tests makes it fail. The
freshness window's length is a server constant and is not stated here (§6).

**What this section does not establish.** The measurement covers how a *presented*
signature is checked. It says nothing about how the shared secret is generated, stored,
distributed or rotated. The construction is exactly as strong as the secret's custody, and
nothing in this document attests to that custody.

## 4. Replay protection and re-assertion

**Nonce de-duplication.** Every signed request carries a fresh random nonce and its own
timestamp (§2). The worker rejects a nonce it has already accepted inside its freshness
window, and rejects a timestamp outside that window; the window's length is a deployment
constant and is not stated here. A client never reuses a nonce: the value is generated per
request, immediately before signing, and is not persisted.

**Single consumer.** Consumption of pending items is committed by exactly one client — the
poller — and only after the items have been written to its inbox. Every other reader of
`/pending` reads without a cursor and de-duplicates **client-side** against its own floor
(`id > floor`), so that a read can never destroy an item another process has not yet seen.

**Re-assertion (publisher).** The publisher never throws. A publish that cannot be
delivered is **queued** on disk and re-delivered on the next flush; a flush that fails
stops and leaves the remainder queued — nothing is dropped and nothing is reordered. A
change-hash keyed on the text prevents an unchanged row from being re-published. Each call
returns one of `published | queued | failed | refused | disabled`, and the caller decides
what to do with it.

**Uniform refusal.** From the client's view a rejected request is a generic `400` with
`{"error":"rejected"}`; the client learns no distinction between a bad signature, a stale
timestamp, a replayed nonce, or a rate limit. Clients treat every non-`200` as failure.

## 5. Failure posture

The shape below is protocol: a conforming client behaves this way. The constants that
follow it are **this deployment's defaults**, not part of the protocol, and a deployment may
choose its own.

- **One-shot clients** (beacon, ping, rule read, close) refuse **before any network act**
  on every guard, never substitute an origin, and exit nonzero on every non-`200`.
- **Loops** (the pending poller, the health check) **degrade and stay up**: a dark worker
  is logged and polling continues; a loop never exits on a transport failure.
- **The publisher never throws** (§4): an undeliverable publish is queued, not dropped.
- **Watchdogs alarm on absence.** They are fail-closed on their verdict — an absent
  consumption ledger alarms and never passes, a missing inbox is an error distinct from a
  stale one, an unparseable inbox line counts as stale, a child that times out is an error —
  and best-effort only on the notification leg.
- **The one deliberate fail-open on the client side:** an unparseable quiet-hours bound
  **delivers** rather than withholds.

**Defaults in this deployment:**

| constant | default |
|---|---|
| pending-poller period | 60 s |
| health-check fetch timeout | 15 s |
| consecutive failures before the health check reports degraded | 3 |
| window after which a picked-up, unconsumed item is stale | 10 min |
| watchdog child timeout | 60 s |

## 6. What this text does not cover

The worker's implementation, its rate limiting, its lockout policy, its storage, and
every server-side constant. Those belong to the worker's own repository and are not
disclosed by publishing the client set.
