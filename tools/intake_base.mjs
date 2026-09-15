// intake base-origin resolver -- the ONE implementation of what `BASE` may become.
//
// ⭐ WHY THIS FILE EXISTS (O-F-3, card row 3). The 09-09 round found that
// workpapers/p2-cutover-convergence-2026-09-08/fastpath_base_resolution_controls.mjs
// graded a HAND-WRITTEN MODEL of this resolver -- a model that returned the pinned
// origin where the shipped one REFUSES -- so a green battery was evidence about the
// model and was read as evidence about the guard. `<private-oid>` got those legs executing
// the shipped function, but only by spawning a sandboxed CHILD: the resolver lived in a
// script, and importing a script RUNS it. This module is the cure. It holds the resolver
// and nothing else, so the battery IMPORTS IT DIRECTLY and subject and battery share one
// implementation rather than two that agree until they do not.
//
// ⛔ PURE BY CONTRACT, AND THE CONTRACT IS THE POINT. No `process.env` read, no I/O,
// no top-level side effect -- `baseAdmit` is a function of its argument. The env read
// lives in the consumer (intake_fastpath_check.mjs keeps its own `BASE_REQUESTED`),
// because a module that reads the environment at import time cannot be imported by a
// grader without the grader inheriting whatever the environment happens to hold. That
// impurity is exactly what forced the child process this file removes.
//
// ⚠ EVERY BYTE BELOW WAS MOVED, NOT REWRITTEN, from intake_fastpath_check.mjs at the
// O-F-3 cure. The rationale travels with the code it explains: a ruling recorded beside
// the branch it governs survives an edit to that branch, and a ruling left behind in the
// file the code departed becomes an orphan nobody can act on.
//
// ⚠ CARD CITATIONS MOVED WITH IT. Rows 4, 9 and 10 of
// workpapers/cb-dispositions-2026-09-11/CARD_C-b_DISPOSITIONS_v2.md cite lines that now
// live HERE; the card and CARD_v2_GRADE_CHECK.py were re-pointed in the same commit,
// because a card citing the file a line used to be in is worse than no citation at all.
// ⛔ AND THIS NOTE DELIBERATELY DOES NOT SPELL THOSE IDS OUT. Row 9's claim is about
// the RULING COMMENTS that record why this resolver refuses; a meta-note ABOUT those
// comments is not one of them, and naming the ids here would inflate the very occurrence
// count the row is graded on -- a file discussing its own subject in its subject's
// vocabulary defeats a census of that vocabulary.

// ⛔ F3 — A SET-BUT-REJECTED ORIGIN OVERRIDE REFUSES; IT NEVER FALLS BACK TO
//   PRODUCTION (<principal>'s word, <entry-id> §1). The bare `env || PINNED` this
//   replaces had no screen at all: whatever `INTAKE_BASE_OVERRIDE` held became
//   the origin this checker signed an AGENT_READ HMAC against and sent `/pending`
//   to. Three cases, and they must stay separated:
//     unset (or blank)          -> the pinned origin. The normal path, silent.
//     set and ADMITTED          -> the override. Admitted = the pinned origin
//                                  itself, or an http/https LOOPBACK host.
//     set and NOT admitted      -> REFUSE: the worker leg does not run, and the
//                                  pinned origin is NOT substituted for it.
//   ⭐ AND THE REFUSAL PRINTS, every run it applies. This file is Monitor-driven
//   and its own header states SILENCE ≠ HEALTH — a refusal nobody is told about
//   is a dark checker, which is the exact failure class this file exists to
//   prevent [[advisory-line-naming-an-absence-is-the-gate-firing]]. It prints on
//   EVERY run rather than once on transition (the shape used for DEGRADED)
//   because a rejected override is not a transient condition that self-heals: it
//   is a configuration a human set and only a human clears, and one announcement
//   that scrolls away leaves the checker one-legged in silence thereafter.
//   ⚠ CONSIDERED AND NOT TAKEN: a hard `process.exit(2)`, which is what the
//   <name>-package class-B shard was ruled to do (REPORT.md row 4). That ruling
//   covers a DIFFERENT case — the packaged build has the literal removed and so
//   has NO origin at all, and a tool with no origin cannot do its job. Here the
//   INBOX leg is fully functional (it reads the poller's local
//   pending_inbox.jsonl and never touches BASE), so exiting would take BOTH legs
//   dark over a typo when only one is actually broken. The header's contract is
//   that both legs must die before intake goes dark; a refusal that kills the
//   working leg violates it. Refusing the worker leg alone also keeps the
//   existing failstreak accounting honest: workerOk stays false, so a rejected
//   override still drives the DEGRADED line at 3 consecutive runs.
//   ⚠ THE LOOPBACK ADMISSION IS NOT A CONVENIENCE — it is REQUIRED by a shipped
//   consumer: CONTROLS_fastpath_no_cursor.mjs drives this module — at the `spawn` that
//   sets `INTAKE_BASE_OVERRIDE` in the child env — against a
//   stub at `http://127.0.0.1:<ephemeral>`. A cure that admitted only the pinned
//   origin would break that control, which is the fleet's guard on the
//   destructive-cursor defect (<entry-id>). Measured, not assumed: that file is
//   the only setter of this variable in tools/ [[mention-is-not-use]].
//   ⛔ O-Q3b — THE ONE PLACE THE SECURITY FRAMING IS LITERALLY CORRECT, and it
//   was the one thing this comment did not say. Everything above treats a bad
//   override as MISCONFIGURATION rather than as an adversary, and for a typo or a
//   stale port that reading is right. It stops being right for one mechanism: a
//   `workers.dev` subdomain that names a DELETED OR RENAMED worker is
//   RECLAIMABLE — the name returns to the pool and anyone may register it. A
//   stale `INTAKE_BASE_OVERRIDE` left in a runbook, a scheduled task or an
//   operator's shell profile therefore becomes attacker-controlled with no local
//   access at any point and nothing on this machine changing. That is why the
//   refusal above is a refusal and not a fallback, and why the admitted set is an
//   allowlist of TWO shapes rather than a denylist of bad ones
//   [[denylists-cannot-deidentify]].
//   ⚠ STATED ONCE, HERE, ON PURPOSE. It belongs at the site that decides what
//   `BASE` becomes, not repeated at each refusal branch — a rationale restated at
//   N sites is a rationale that goes stale at N-1 of them, and a reader who finds
//   two copies has to work out which is current.
const BASE_PINNED = "https://agent-intake.<account>.workers.dev";
const BASE_LOOPBACK = new Set(["127.0.0.1", "localhost", "::1", "[::1]"]);
const stripSlash = (u) => u.replace(/\/+$/, "");
function baseAdmit(requested) {
  if (requested === "") return { base: BASE_PINNED, refused: null };
  // ⛔ RETURN THE NORMALIZED ORIGIN, NEVER THE REQUEST VERBATIM. `stripSlash` was
  // applied to the COMPARISON and not to the RETURN, so an operator who wrote the
  // pinned origin WITH a trailing slash took this equality fast path and
  // `BASE + "/pending"` built `//pending` AGAINST PRODUCTION — in the path that
  // signs an AGENT_READ HMAC over the path string, so the signed path and the
  // fetched URL then disagree about the request's own shape. Measured, not argued:
  // FP1_RESIDUAL_PROBE.mjs legs F-1(b)/F-1(c)/F-1[CURE-SHAPE] against the graded
  // blob. BASE_PINNED is itself the normalized form of anything this branch admits.
  if (stripSlash(requested) === stripSlash(BASE_PINNED)) return { base: BASE_PINNED, refused: null };
  let u;
  // ⛔ THE SECOND MOUTH. The proposed diff's `catch { return BASE_PINNED; }` sent
  // an UNPARSEABLE override to production by the same route as a rejected one —
  // the identical hole, one branch over. Both branches refuse here.
  try { u = new URL(requested); } catch { return { base: null, refused: "unparseable" }; }
  if (u.protocol !== "http:" && u.protocol !== "https:") return { base: null, refused: "scheme is not http/https" };
  if (!BASE_LOOPBACK.has(u.hostname)) return { base: null, refused: "host is neither the pinned origin nor loopback" };
  // ⭐ NARROWED TO THE ACTUAL TEST CONTRACT, on the codex anchor's finding
  // (codex-out-fastpath-origin-r1.txt Q3): "Evaluating the exact added resolver
  // confirmed that it also admits non-HTTP schemes, userinfo and query-bearing
  // URLs." Schemes were closed in the first pass; USERINFO and QUERY were not, and
  // they are not hypothetical — `https://user:pass@127.0.0.1/` passed a bare
  // hostname test, which is how a credential rides into a signed request and into
  // whatever logs it. The only shape any consumer actually needs is
  // `http://<loopback>[:port]` with an empty path.
  if (u.username || u.password) return { base: null, refused: "loopback override carries userinfo" };
  if (u.search || u.hash) return { base: null, refused: "loopback override carries a query or fragment" };
  if (u.pathname !== "" && u.pathname !== "/") return { base: null, refused: "loopback override carries a path" };
  // ⛔ SAME CURE, THE OTHER BRANCH. `http://127.0.0.1:3000/` passes every check
  // above (empty-or-"/" path is admitted on purpose) and returning it verbatim
  // builds `http://127.0.0.1:3000//pending`. `u.origin` is the parser's own
  // normalized form — scheme + host + port, no trailing slash — so both admitting
  // branches now return an origin rather than whatever the operator typed.
  return { base: u.origin, refused: null };
}

export { baseAdmit, BASE_PINNED, BASE_LOOPBACK, stripSlash };
