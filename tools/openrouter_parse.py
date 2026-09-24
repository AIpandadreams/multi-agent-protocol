#!/usr/bin/env python
"""openrouter_parse.py -- classify one OpenRouter chat-completions response.

WHY THIS IS A SEPARATE FILE (and not a --parse-fixture flag on the wrapper):
    Every dangerous failure mode in DESIGN-PACKAGE §4 is a property of the RESPONSE,
    not of the transport -- HTTP 200 carrying an error body, silent truncation at
    max_tokens, a rate-limit body, a route that answered from a different model than
    the one requested. Those cannot be tested through a wrapper that must make a
    network call to reach its own parser. Splitting the parser out gives the controls
    a real seam to drive with fixtures, WITHOUT adding a flag to the production path
    that skips the network (a bypass flag in the shipping tool is a surface; a
    library boundary is not).

THE RULE THIS FILE EXISTS TO ENFORCE (DESIGN-PACKAGE §4, closing line):
    ⛔⛔ A voice that FAILED and a voice that FOUND NOTHING must never be
    indistinguishable in the record. So this parser NEVER returns "no findings" by
    omission. Every outcome is an explicit STATUS with a REASON, and the caller
    writes that into the verdict file even when the dispatch died -- an absent or
    empty verdict file is itself a dispatch failure, never a quiet clean bill.

USAGE:
    openrouter_parse.py --raw <file> --http <code> --requested <model_id>
                        --content-out <file> [--terminator <str>]

STDOUT: KEY=VALUE lines (STATUS, REASON, MODEL_ANSWERED, FINISH_REASON,
        PROMPT_TOKENS, COMPLETION_TOKENS, CONTENT_BYTES).
EXIT:   0 = STATUS=OK, 1 = STATUS=FAILED (REASON names it), 2 = usage error.
"""

import argparse
import json
import os
import sys

# A fleet ruling (2026-08-09): the terminator flipped to plain
# words + a nonce token. The old `=== END OF VERDICT ===` was markdown-bait —
# glm normalized the leading `===` to `###` and a complete CONFIRM verdict
# failed certification on formatting alone.
DEFAULT_TERMINATOR = "END OF VERDICT EOV-7Q4Z"
# TRANSITION: the legacy string is still ACCEPTED — loudly, via a
# TERMINATOR=legacy-accepted-transition key on the OK emit plus a stderr WARN
# — until legacy acceptance is removed at a later ruled date (R4 step 4).
#
# SCOPE, stated as implemented: acceptance applies whenever the EFFECTIVE
# terminator is the fleet default, however it got there. It is NOT conditioned
# on "the caller omitted --terminator" — a caller passing the default string
# explicitly is byte-identical to defaulting, so that distinction is not
# expressible here and claiming it would be a false contract. A caller asking
# for a DIFFERENT terminator gets strict behavior, which is the case that
# matters: a custom terminator is a deliberate override, and the transition
# has nothing to say about it. (Measured before the wording was fixed.)
LEGACY_TERMINATOR = "=== END OF VERDICT ==="


def _final_line(content):
    """The last non-empty line of `content`, stripped. `""` when there is none.

    Stripped, so an indented terminator (a model that puts it inside a list) is
    still recognised; whole-line, so a terminator quoted inside a sentence is
    not. Same shape as `codex_review.sh`'s awk
    (`sub(/\r$/,""); gsub(/^[ \t]+|[ \t]+$/,"")`) -- CR included, because a
    CRLF body would otherwise leave a trailing CR on the token and no equality
    would ever hold.
    """
    for line in reversed(content.splitlines()):
        line = line.strip()
        if line:
            return line
    return ""


def emit(pairs):
    for k, v in pairs:
        sys.stdout.write("%s=%s\n" % (k, v))


def _one_line(s):
    """Flatten a provider string into ONE `KEY=value` line, cap 200.

    Same shape the top-level `error` branch already applies inline
    (`str(...)[:200].replace("\\n", " ")`) -- factored out so the per-choice
    branch cannot drift from it [[emitter-and-verifier-are-one-grammar]]. CR is
    collapsed too: the shell reads this stream with awk, and a lone CR would
    ride into the value invisibly. `=` needs no escaping -- the reader strips
    only up to the FIRST `=` (`sub(/^[^=]*=/,"")`), so it survives intact.
    """
    return str(s)[:200].replace("\r", " ").replace("\n", " ")


def fail(reason, extra=None):
    pairs = [("STATUS", "FAILED"), ("REASON", reason)]
    if extra:
        pairs.extend(extra)
    emit(pairs)
    return 1


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--http", required=True)
    ap.add_argument("--requested", required=True)
    ap.add_argument("--content-out", required=True)
    ap.add_argument("--terminator", default=DEFAULT_TERMINATOR)
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit:
        return 2

    # The content file is written on EVERY path below, including failures, so the
    # caller always has a verdict artifact to point at. Truncate it up front.
    try:
        with open(a.content_out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("")
    except OSError as exc:
        emit([("STATUS", "FAILED"), ("REASON", "CONTENT_OUT_UNWRITABLE")])
        sys.stderr.write("cannot write %s: %s\n" % (a.content_out, exc))
        return 1

    if not os.path.isfile(a.raw):
        return fail("NO_RESPONSE_BODY")
    try:
        rawtext = open(a.raw, "r", encoding="utf-8", errors="replace").read()
    except OSError:
        return fail("NO_RESPONSE_BODY")
    if not rawtext.strip():
        # curl wrote nothing: connection died, DNS, or the watchdog killed it.
        return fail("EMPTY_RESPONSE_BODY")

    try:
        doc = json.loads(rawtext)
    except ValueError:
        # A non-JSON body is often an HTML error/interstitial page. Name it; do NOT
        # let it read as an empty verdict.
        return fail("NON_JSON_BODY", [("HTTP", a.http)])

    # --- error bodies FIRST, before status, because HTTP 200 can carry one ---------
    # (DESIGN-PACKAGE §4: "parse for the verdict shape, never trust the status".)
    err = doc.get("error")
    if isinstance(err, dict):
        code = err.get("code", "")
        msg = str(err.get("message", ""))[:200].replace("\n", " ")
        low = (str(code) + " " + msg).lower()
        if "rate" in low and "limit" in low:
            reason = "RATE_LIMITED"
        elif any(w in low for w in ("credit", "quota", "insufficient", "balance", "payment")):
            reason = "CREDIT_EXHAUSTED"
        elif (a.http == "401" or str(code) == "401" or "user not found" in low
              or any(w in low for w in ("unauthorized", "invalid api key", "no auth credentials",
                                        "invalid_authentication", "api key appears to be invalid"))):
            # Per a ruling addendum and the owner's report: OpenRouter answers a revoked or wrong key with
            # HTTP 401 and the message "User not found." -- the generic "not found" branch below
            # read that as MODEL_NOT_FOUND. An auth failure names the SHELL (refresh the key), a
            # missing model names the ROUTE; the two remedies differ, so the reason must too.
            # Ordered before the "not found" branch on purpose.
            reason = "AUTH_FAILED"
        elif "not found" in low or str(code) == "404":
            reason = "MODEL_NOT_FOUND"
        else:
            reason = "PROVIDER_ERROR"
        return fail(reason, [("HTTP", a.http), ("PROVIDER_MESSAGE", msg)])

    # Status is checked only AFTER the body, and a non-2xx without an error object
    # still fails -- it is never a verdict.
    if not a.http.startswith("2"):
        if a.http == "429":
            return fail("RATE_LIMITED", [("HTTP", a.http)])
        return fail("HTTP_%s" % a.http, [("HTTP", a.http)])

    choices = doc.get("choices")
    if not isinstance(choices, list) or not choices:
        return fail("NO_CHOICES", [("HTTP", a.http)])
    ch0 = choices[0] if isinstance(choices[0], dict) else {}
    finish = ch0.get("finish_reason") or ch0.get("native_finish_reason") or "unknown"
    msg_obj = ch0.get("message") if isinstance(ch0.get("message"), dict) else {}
    content = msg_obj.get("content")
    if content is None:
        content = ""
    if not isinstance(content, str):
        content = json.dumps(content)

    # Requirement 5: record what ACTUALLY answered. Never assume it is what we asked
    # for -- an unverified assumption the design package flagged as unverified.
    answered = doc.get("model") or "UNREPORTED"

    # Requirement (5b), from the owner's and creator's reviews: the SERVING
    # ENDPOINT is a separate axis from the model id. Pinning the model does not attribute
    # the provider -- one route was measured being served by two different providers --
    # so a correlation matrix built on model id alone silently treats two endpoints as
    # one voice.
    #
    # ⛔ THIS AXIS CANNOT BE REPAIRED RETROACTIVELY. A row written without it is missing
    #    the value forever, because nothing in the stored response can reconstruct which
    #    endpoint answered. That is why capture precedes spending rather than following it.
    #
    # ABSENT is recorded EXPLICITLY and never as a blank. A blank cell is ambiguous
    # between "the response carried no provider" and "this row predates capture" -- and
    # those two need different remedies, so they must not share a representation.
    provider = doc.get("provider")
    if not isinstance(provider, str) or not provider.strip():
        provider = "ABSENT"

    usage = doc.get("usage") if isinstance(doc.get("usage"), dict) else {}
    ptok = usage.get("prompt_tokens", "UNKNOWN")
    ctok = usage.get("completion_tokens", "UNKNOWN")
    # Per a fleet ruling: reasoning spend is reported beside the effort that was sent, so the
    # effort pin is checked per verdict. ABSENT is explicit for the same reason the
    # provider cell is: a blank cannot tell "not reported" from "predates capture".
    details = usage.get("completion_tokens_details")
    rtok = details.get("reasoning_tokens", "ABSENT") if isinstance(details, dict) else "ABSENT"

    common = [
        ("MODEL_ANSWERED", answered),
        ("SERVING_PROVIDER", provider),
        ("MODEL_REQUESTED", a.requested),
        ("FINISH_REASON", finish),
        ("PROMPT_TOKENS", ptok),
        ("COMPLETION_TOKENS", ctok),
        ("REASONING_TOKENS", rtok),
        ("CONTENT_BYTES", len(content.encode("utf-8"))),
        ("HTTP", a.http),
    ]

    # Write whatever content arrived even on the failure paths below: a truncated
    # verdict is evidence about what went wrong, and deleting it would destroy that.
    with open(a.content_out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)

    if finish == "length":
        # Silent truncation: "a verdict that stops mid-sentence still looks like a
        # verdict". It must never be graded as one.
        emit([("STATUS", "FAILED"), ("REASON", "TRUNCATED_AT_MAX_TOKENS")] + common)
        return 1

    if not content.strip():
        # Distinguishable from "the reviewer found nothing": that would still carry
        # the terminator. An empty body is a dispatch failure.
        #
        # ⛔ CURE (creator, 2026-09-03, driven by the round-5 glm-5.3 leg). The
        # top-level `error` branch above surfaces PROVIDER_MESSAGE, but OpenRouter
        # reports a PROVIDER-SIDE failure PER CHOICE: `choices[0].error` alongside
        # `finish_reason: "error"` and an empty content string. That path landed
        # here, so the provider's own explanation was read into `ch0` and then
        # dropped on the floor -- the operator got "EMPTY_CONTENT" and nothing to
        # act on. Two error shapes must not have one reporting grammar and one
        # blind spot [[emitter-and-verifier-are-one-grammar]].
        #
        # Reported ONLY when present: a fabricated or blank PROVIDER_MESSAGE would
        # be worse than its absence, because it cannot be told from a provider that
        # genuinely said nothing [[honest-failure-outcomes]].
        cerr = ch0.get("error") if isinstance(ch0.get("error"), dict) else {}
        extra = []
        cmsg = cerr.get("message")
        if isinstance(cmsg, str) and cmsg.strip():
            extra.append(("PROVIDER_MESSAGE", _one_line(cmsg)))
        if cerr.get("code") not in (None, ""):
            extra.append(("PROVIDER_ERROR_CODE", _one_line(str(cerr["code"]))))
        cmeta = cerr.get("metadata")
        if isinstance(cmeta, dict) and cmeta:
            extra.append(("PROVIDER_ERROR_META",
                          _one_line(json.dumps(cmeta, sort_keys=True))))
        emit([("STATUS", "FAILED"), ("REASON", "EMPTY_CONTENT")] + common + extra)
        return 1

    term_key = ("TERMINATOR", "current")
    if a.terminator:
        # The terminator is the only positive proof the voice finished speaking.
        # Without it we cannot tell a complete "no findings" from a severed stream.
        #
        # ⛔ P1c CURE (2026-09-04). This was `a.terminator not in
        #    content` -- a MEMBERSHIP test, and the legacy branch below was
        #    `LEGACY_TERMINATOR in content`, the same one. Membership passes on
        #    exactly the failure this check exists to catch: a voice that echoes
        #    the dispatch prompt (which CARRIES the terminator instruction) and is
        #    then severed contains the terminator and no verdict. The identical
        #    defect is documented at `codex_review.sh:493` under the name "MENTION
        #    IS NOT COMPLETION"; that lane stops at "some line equals" only because
        #    its runner appends a `CODEX_EXIT=` trailer after the model text.
        #    Nothing is appended here -- `openrouter_review.sh:1294` cats this
        #    content as the LAST bytes of the verdict file -- so the bar is the
        #    stronger one already in `opus_judge_headless.ps1:239`: the terminator
        #    is the FINAL NON-EMPTY LINE [[emitter-and-verifier-are-one-grammar]].
        last = _final_line(content)
        accepted = [a.terminator]
        if a.terminator == DEFAULT_TERMINATOR:
            # R4 transition: legacy accepted, never silently. SCOPE unchanged --
            # acceptance keys on the EFFECTIVE terminator being the fleet default,
            # however it got there; a caller asking for a DIFFERENT terminator gets
            # strict behavior, which is the case that matters.
            accepted.append(LEGACY_TERMINATOR)
        if last == LEGACY_TERMINATOR and LEGACY_TERMINATOR in accepted:
            term_key = ("TERMINATOR", "legacy-accepted-transition")
            sys.stderr.write(
                "WARN: legacy terminator accepted (a ruled transition; "
                "move the dispatch prompt to %r)\n" % DEFAULT_TERMINATOR)
        elif last not in accepted:
            # ⛔ TWO OUTCOMES, deliberately. "The token is in the body but the
            #    body did not end on it" and "the token is nowhere" call for
            #    different acts -- re-read the tail for an echo vs re-dispatch a
            #    severed stream -- and collapsing them into one label would make
            #    the operator guess [[lookup-failure-needs-own-outcome]]. The tail
            #    is REPORTED on the not-final path, because the whole question the
            #    operator has at that moment is what came after
            #    [[collected-is-not-reported]].
            if any(t in content for t in accepted):
                emit([("STATUS", "FAILED"),
                      ("REASON", "TERMINATOR_NOT_FINAL")] + common
                     + [("TERMINATOR_TAIL", _one_line(last))])
            else:
                emit([("STATUS", "FAILED"), ("REASON", "NO_TERMINATOR")] + common)
            return 1

    if answered != "UNREPORTED" and answered != a.requested:
        # Not fatal -- a provider may serve a pinned id from a versioned backend --
        # but it is recorded loudly, because a convergence record that names a voice
        # it cannot prove answered is worth nothing.
        emit([("STATUS", "OK"), ("REASON", "OK_MODEL_SUBSTITUTED")]
             + common + [term_key])
        return 0

    emit([("STATUS", "OK"), ("REASON", "OK")] + common + [term_key])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
