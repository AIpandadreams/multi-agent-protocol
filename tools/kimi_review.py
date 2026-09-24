#!/usr/bin/env python3
"""Kimi K3 reviewer-lane dispatcher (the private workspace). REVIEWER-ONLY voice — never a judge
(standing bar until the calibration ledger closes; set by a series of fleet rulings).

Reads a review prompt from --prompt-file, calls the Kimi Code Anthropic-compatible
endpoint (direct, the principal's Allegretto subscription — NOT OpenRouter; a pipe switch, so
calibration rows carry the pipe note), writes the reply text to --out and run metadata
to --meta. Text-only voice: Kimi cannot read local files or execute anything, so every
dispatch must inline all needed evidence (premise-marking discipline applies to its
verdicts exactly as to opus text voices).

Key handling: KIMI_API_KEY from process env, else HKCU\\Environment (the var may
postdate the shell). The key value is NEVER printed, logged, or written.

No external watchdog needed: the HTTP call runs in-process with an explicit timeout —
there is no child process to orphan (unlike the codex CLI lane).

Exit codes: 0 = reply written · 2 = usage/key error · 3 = transport/HTTP failure after
one retry · 4 = 200-response body malformed · 5 = well-formed 200 TRUNCATED at
max_tokens before any text block (a thinking model can spend the whole budget
reasoning). 4 and 5 both save the body to --out with a .raw suffix; they are
separate codes because the fix differs -- 4 is a parser/schema problem, 5 is
purely --max-tokens, and one code for both misdirects the diagnosis.
"""
import argparse, json, os, sys, time, urllib.request, urllib.error

API = "https://api.kimi.com/coding/v1/messages"


def get_key():
    k = os.environ.get("KIMI_API_KEY")
    if k:
        return k
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as h:
            v, _ = winreg.QueryValueEx(h, "KIMI_API_KEY")
            return v or None
    except OSError:
        return None


def call(key, model, prompt, max_tokens, timeout):
    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        # A fleet ruling (the principal first-hand, 2026-09-06): the voice runs with thinking ON,
        # pinned here rather than left to the vendor default. MEASURED 2026-09-06 on
        # api.kimi.com/coding/v1/messages, model kimi-k3, before this line existed:
        # the default already returned a `thinking` content block (thinking_tokens in
        # usage.output_tokens_details); `thinking.type` set to anything but "enabled"
        # (including "disabled" and a bogus value) removed it; `budget_tokens` 1024 vs
        # 200000 and the Anthropic-style `effort` / `output_config.effort` /
        # `reasoning_effort` fields all returned 200 with NO measurable change -- the
        # endpoint validates none of them. So "enabled" is the whole dial this API
        # exposes, and the pin exists so a vendor default flip cannot silently turn the
        # voice into a no-thinking one. No budget is sent because none is honored.
        "thinking": {"type": "enabled"},
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "content-type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    })
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
    return time.time() - t0, raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--meta")
    ap.add_argument("--model", default="kimi-for-coding")
    ap.add_argument("--max-tokens", type=int, default=16000)
    ap.add_argument("--timeout", type=int, default=600)
    a = ap.parse_args()

    key = get_key()
    if not key:
        print("KIMI_API_KEY absent (env + HKCU\\Environment)", file=sys.stderr)
        return 2
    try:
        prompt = open(a.prompt_file, encoding="utf-8").read()
    except OSError as e:
        print("prompt unreadable: %s" % e, file=sys.stderr)
        return 2

    last_err = None
    for attempt in (1, 2):
        try:
            secs, raw = call(key, a.model, prompt, a.max_tokens, a.timeout)
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:2000]
            last_err = "HTTP %s: %s" % (e.code, detail)
            if e.code < 500:          # 4xx will not improve on retry
                print(last_err, file=sys.stderr)
                return 3
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = "transport: %s" % e
        if attempt == 1:
            time.sleep(5)
    else:
        print("failed after retry: %s" % last_err, file=sys.stderr)
        return 3

    try:
        obj = json.loads(raw)
        text = "".join(b.get("text", "") for b in obj.get("content", [])
                       if b.get("type") == "text")
        if not text:
            # ⚠ TRUNCATION IS NOT MALFORMATION, and conflating them sends the
            # next operator to the parser instead of to --max-tokens. Measured
            # 2026-09-03: a kimi-for-coding run returned a perfectly well-formed
            # body whose ONLY content block was `thinking` -- 15,997 of 16,000
            # output tokens spent reasoning, stop_reason "max_tokens", zero text.
            # rc 4 fired correctly and its WORDS were false, which cost a
            # diagnosis. A thinking model can always think past its budget, so
            # this outcome gets its own code and says the actual cause.
            #
            # ⚠ The FIRST version of this message said "raise --max-tokens",
            # which was a CONFOUNDED attribution: the re-dispatch changed the
            # budget AND added a brevity directive, and the successful run then
            # used 1,814 of 48,000 tokens -- so the budget was never the binding
            # constraint. Corrected to name the directive, because a wrong cure
            # baked into an instrument outlives the run that wrote it.
            if obj.get("stop_reason") == "max_tokens":
                u = obj.get("usage") or {}
                th = (u.get("output_tokens_details") or {}).get("thinking_tokens")
                open(a.out + ".raw", "w", encoding="utf-8").write(raw)
                print("TRUNCATED before any text block: stop_reason=max_tokens, "
                      "output_tokens=%s (thinking_tokens=%s) against --max-tokens "
                      "%d. The body is WELL-FORMED and the model never got to its "
                      "answer -- do NOT go looking at the parser.\n"
                      "  FIX: put an explicit BREVITY instruction in the prompt "
                      "(answer directly, reason only as much as each question "
                      "needs, open with the answer). Measured 2026-09-03: the "
                      "same prompt that burned 15,997 thinking tokens returned "
                      "in 1,814 total (886 thinking) once that directive was "
                      "added -- so a bigger budget alone is NOT the established "
                      "cure and may just buy a longer runaway. Raise --max-tokens "
                      "too if you like, but the directive is what was measured "
                      "to work.\n"
                      "  Raw saved to %s.raw"
                      % (u.get("output_tokens"), th, a.max_tokens, a.out),
                      file=sys.stderr)
                return 5
            raise ValueError("no text blocks")
    except (ValueError, KeyError) as e:
        open(a.out + ".raw", "w", encoding="utf-8").write(raw)
        print("malformed 200 body (%s); raw saved to %s.raw" % (e, a.out),
              file=sys.stderr)
        return 4

    open(a.out, "w", encoding="utf-8", newline="\n").write(text)
    meta = {
        "model_requested": a.model,
        "model_served": obj.get("model"),
        "latency_s": round(secs, 2),
        "usage": obj.get("usage"),
        "stop_reason": obj.get("stop_reason"),
        "prompt_bytes": len(prompt.encode("utf-8")),
        "reply_bytes": len(text.encode("utf-8")),
        "endpoint": API,
        "pipe": "direct-kimi-allegretto (NOT openrouter)",
    }
    if a.meta:
        open(a.meta, "w", encoding="utf-8", newline="\n").write(
            json.dumps(meta, indent=2))
    print(json.dumps(meta))
    return 0


if __name__ == "__main__":
    sys.exit(main())
