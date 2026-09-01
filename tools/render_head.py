#!/usr/bin/env python3
"""render_head — the head renderer for agent role MEMORY.md files.

It regenerates two sections of a role's MEMORY.md from the workspace's own
state. The ⚡ working-state block and the ## Next Step section become
RENDERINGS of open ledger state (plans/*.plan.yaml) + derived lane tails
(channel/*.md), stamped with a source-mtime footer so a later run can grade
whether the head is still fresh (the "F8" freshness comparator implemented
below). Hand-authored judgment lives in ## Standing judgment, which this
tool NEVER generates and NEVER modifies.

DESIGN NOTES. The behaviours listed below were each added to close a defect
found in review. The reasoning is kept because it explains why the code has
the shape it does:
- comparator fail directions, scoped footer recognition, markdown
  canonicalization (fence/case/indent/suffix/BOM/CRLF), prose flattening,
  and a controlled exit-code contract
- structural (unique-in-section) footer recognition replacing an earlier
  positional last-line rule, unclosed-fence recovery, tick lane-tail scan
  scoped to the rendered ⚡ section, the CommonMark backtick-info fence
  rule, plan-shape validation + AttributeError mapping, and a footer-token
  emission guard
- seat_digest aligned on the shared seat-resolution contract: seat names
  compare NORMALIZED via norm_seat (engine→owner, helper→builder; canonical
  seats incl. creator self-resolve), there is no `owner or owner_seat`
  fallback, and a step missing its REQUIRED owner renders a loud DEFECT
  line in EVERY seat's digest and is never dispatched

Contract highlights:
- Single dispatch surface: exactly ONE Next-Step-shaped heading, per the
  DECLARED canonicalization rule (stated in full in this header, and NOT
  in the shipping docs/DESIGN.md, which has no such section): ATX
  level-2, 0-3 space
  indent tolerated, case-insensitive, trailing CR / ATX closing hashes /
  "(live)"-style suffixes canonicalized, BOM-at-byte-0 transparent, fenced
  code blocks excluded. The renderer REFUSES (exit 2, no write) if the input
  carries more than one such surface, and asserts post-render that exactly
  one remains (the single-surface whitelist rule, mechanical).
- Footer grammar (JOINT FREEZE with the wake/sleep consumers — wake.md 6c
  / sleep.md step 3 read it, including the lane-tail stamp token):
    <!-- render_head v1 rendered_at=<ISO> sources=<rel>@<epoch>[,<rel>@<epoch>] tails=<16hex> -->
  one line, exactly the token order above; the `tails=` token is the
  SHA-256/16-hex digest of the emitted `Lane tails at render: …` line
  (terminator excluded) and is OPTIONAL on read — a pre-token footer
  still parses, and its head simply gains no tail-line exemption at wake
  6c. Emitters split from this grammar (a separate twin implementation) must
  take the grammar at or before the emitter or their verify leg reads
  the new footer as corrupt. <rel> = workspace-relative path,
  forward slashes, no whitespace AND no comma (both refused at emit);
  <epoch> = int(mtime) at render time. The footer is RECOGNIZED structurally:
  the UNIQUE footer-shaped line inside THE canonical Next Step section —
  never first-match-anywhere, never by position alone. Zero matches = hand/
  unrendered; two or more = REFUSED (exit 2, ambiguous stamp — an appended
  lookalike line can never BECOME the footer). A footer-shaped line outside
  the section (judgment/prose) is inert. Benign non-footer lines appended
  after the footer are content drift: freshness still grades (F8 measures
  sources, not section purity) and the next render overwrites them.
- Idempotence: if nothing but the generated footer's rendered_at would
  change, the file is NOT rewritten (render twice = byte-identical). The
  comparison is scoped: ONLY the generated footer's stamp is neutralized —
  a rendered_at-shaped string anywhere else is content and forces a write.
- Byte-safe writes: reads/writes via bytes (no newline translation). CRLF
  role files are read through EOL-insensitive structure scanning (rendered
  sections are re-emitted LF; all other bytes untouched).

Modes:
  render (default)   regenerate the two rendered sections; a hand-demoted
                     head (rendered ⚡ present, Next Step missing) is REFUSED
                     with a named recovery: --adopt regenerates the pair
                     with all bytes preserved
  --adopt            transition of a hand-authored file: every dispatch /
                     legacy-⚡ / rendered heading is DEMOTED in place to a
                     `#### [superseded ...]` heading with its body preserved
                     byte-intact, then the single rendered pair is appended
                     (re-running --adopt is safe: it re-demotes and appends)
  --check            F8 staleness comparator, strict (wake/sleep grade):
                     any source mtime != its stamp (forward OR backward), an
                     unreadable source, or a new/missing source is STALE
                     (exit 3)
  --check --tick     daemon grade (noise-thresholded): STALE when a source
                     lags >24h, a source mtime REGRESSED below its stamp, a
                     lane tail advanced >20 entries, a source is unreadable,
                     or a source appeared/vanished

Exit codes (contract — every expected failure class maps here, no raw
tracebacks):
  0 ok/current/fresh
  2 refused, no write (second surface; hand head without --adopt; corrupt
    multi-⚡ state without --adopt; TWO OR MORE footer-shaped lines in the
    dispatch section = ambiguous stamp; unclosed code fence hiding structure
    (recovery: --adopt closes it at EOF); source path with whitespace/comma;
    footer-shaped token in a ledger value (joint-consumer protection);
    workspace without plans/ = ledger not adopted; nothing to render)
  3 stale (--check)
  4 unrendered (--check: no scoped footer; F3 hand-head comparators apply)
  5 error (bad UTF-8, bad YAML, plan top-level not a mapping, unreadable
    file, bad/naive --now, footer parse error, post-render invariant) —
    controlled one-line message
"""
import argparse
import hashlib
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError as exc:   # PyYAML is the one non-stdlib prerequisite.
    if getattr(exc, "name", None) != "yaml":
        raise                # a present-but-BROKEN install (transitive import
                             # failure) is not "not installed" - surface it.
    yaml = None              # CORRECTED: an earlier form of this comment said
                             # "a workspace with no plans/ still renders". It
                             # does not. `require_adopted()` REFUSES such a
                             # workspace (rc 2) before any plan is read, so it
                             # never reaches this import's consequences at all.
                             # Measured both branches with PyYAML made genuinely
                             # unimportable: no-yaml + no-plans gives rc 2
                             # REFUSED; no-yaml + WITH plans gives rc 5, the
                             # declared load error below. That second branch is
                             # the only reason `yaml = None` exists: it turns an
                             # uncaught ImportError at session start into a
                             # declared failure with an exit code.


class _PyYAMLMissing(Exception):
    """Stand-in so `except _YAML_ERROR` stays valid when yaml is None.

    `except yaml.YAMLError` resolves the attribute while HANDLING an
    exception, so a bare `yaml = None` would turn every error path into an
    AttributeError raised from inside the handler.
    """


_YAML_ERROR = yaml.YAMLError if yaml is not None else _PyYAMLMissing

sys.stdout.reconfigure(encoding="utf-8")

# The `tails=` token (group 3) is OPTIONAL for compatibility in BOTH
# directions: a pre-tails footer (no token) still fullmatches, so old heads
# grade exactly as before this change — never retroactively exempt, never
# newly corrupt; and because verifier and emitter share THIS one regex in
# THIS one file, a token-bearing footer cannot be read as corrupt by the
# verify leg it ships with. ⚠ Deployments that copy the emitter without
# this grammar (a separate twin implementation) WOULD read the new footer as
# corrupt via their own stale fullmatch — the grammar must land at or
# before the emitter everywhere the pair is split across files.
FOOTER_RE = re.compile(
    r"<!-- render_head v1 rendered_at=(\S+) sources=(\S+?)"
    r"(?: tails=([0-9a-f]{16}))? -->")
# A line that STRUCTURALLY opens as a v1 footer (the token this renderer would
# have written) — used to catch a real footer corrupted by a trailing edit,
# which FOOTER_RE.fullmatch alone would silently drop while binding a separate
# appended lookalike (post-cure finding PC-1). Distinct from a mid-sentence
# mention of the token, which does NOT begin the line.
FOOTER_ATTEMPT_RE = re.compile(r"^<!-- render_head v1 rendered_at=")
# D1 cure: the id is the FIRST <PREFIX>-<n> anywhere in an entry heading's
# TITLE, not only immediately after the "## ". The legacy anchor made the
# current house form (`## ORCH → OWNER — ORCH-NNNN …`) invisible in an
# orchestrator-to-owner lane file, whose headings never derived an id at all.
#
# ⚠ This regex NO LONGER RECOGNIZES HEADINGS — it only extracts an id from
# a title that find_sections() has already recognized. Two earlier drafts
# tried to do both here and each got the heading half wrong:
#   draft 1  `^##[^\n]*?…`  — `^##` also opens `###`/`####`, so every
#            SUB-heading inside an entry BODY became an entry (spurious
#            matches in a live lane file, e.g. `### What this does to
#            ORCH-NNN`), against the protocol's explicit "a mention inside
#            an entry's body is not an occurrence".
#   draft 2  `^##[ \t][^\n]*?…` — fixed that, but still counted
#            heading-shaped lines INSIDE FENCED CODE BLOCKS as entries
#            (caught in review), and rejected the 0-3 space indentation this
#            module's own declared H2 grammar accepts.
# Both were second heading grammars competing with the module's real one.
# find_sections() already handles fences (CommonMark open/close), 0-3
# space indents, `####` demotion and trailing-hash canonicalization —
# so the lane scan INHERITS it rather than freezing a rival rule.
#
# ⛔ THE ANCHOR IS THE WHOLE POINT (a review finding, F1). Draft 3 read the id
# with a bare `\b([A-Z]+)-(\d+)\b` .search() over the entire title. Fixing the
# HEADING axis that way broke the ID axis: with no positional anchor, ANY
# uppercase-token-hyphen-number substring became a lane identity. Measured
# on a live corpus, the prefix set ballooned sharply, minting `UTC-4` out of "UTC-04:00" and an `XX-1234` out of
# ordinary prose; and because .search() is first-match, headings that DID
# carry a real id had it SHADOWED by a fabricated one. Every fabricated
# row is then written into the dispatch line and graded by the F8
# verifier on every tick, forever.
#
# So the id is anchored to where an entry actually declares it, at the
# two positions a canonical heading uses: the title START, or after a
# `SENDER -> RECIPIENT -` routing prefix (the house form D1 exists to
# see), each optionally bracketed. Result, measured over the whole
# heading corpus: the prefix set is back to exactly the subject's own
# set, ZERO fabricated, and a strict superset of every legitimate
# subject capture.
#
# ── P5 cure — THE SEPARATOR, NOT THE ANCHOR ─────────────────────────────────
# The anchor above stays exactly as it is; this cure widens only what sits
# BETWEEN the prefix and the number, and only at those same two anchored
# positions. Motivating defect, measured on a live corpus: one
# builder-to-orch lane file had H2 entry headings and ZERO
# visible ids, because the house form for that lane separates prefix from
# number with a SPACE (`## BUILDER → ORCH — ENTRY NNNN …`) and this pattern
# required a hyphen. The family's reported tail therefore fell back to an
# id long out of date.
#
# ⛔ WHY THIS IS NOT DRAFT 3 AGAIN. Draft 3 (above) removed the ANCHOR and
# fabricated prefixes wholesale. This keeps the anchor and relaxes one
# character
# class, so a fabrication can only be minted by a title that ALREADY starts at
# an anchored position — a strictly smaller surface than a `.search()`.
#
# ⛔ THE SPACE FORM IS A FABRICATION HAZARD IN ONE SPECIFIC SHAPE, and it was
# named in review before the cure was written:
# admitting a space turns `## WAKE <ISO-8601 timestamp> — owner / chan …`
# into a `WAKE-<year>` id across every wake-sentinel lane — trading a
# blind spot for a fabricated one, which passes a cure's other controls. The
# guard is the negative lookahead `(?!-\d)`: a number that continues into
# `-<digit>` is a DATE, not an entry number. Sentinel lanes measured at ZERO
# ids both before and after (control C), and control D pins the discriminator
# by putting both forms in ONE file with opposite required verdicts.
#
# `+` and `&` join the routing-token class for the live multi-recipient form
# (`## BUILDER → ORCH+CREATOR — ENTRY NNNN …`), which the single-token class
# could not route past.
#
# ⚠ DISCLOSED RESIDUAL, not fixed here: a title carrying a SECOND `—`-delimited
# segment before its id (`## ORCH → OWNER — E-lane dispatch — ORCH-NNNN …`)
# stays invisible. Admitting arbitrary intermediate segments is a real widening of the anchor
# and belongs to its own round with its own fabrication measurement, not to a
# separator fix riding along unmeasured (discipline: shape change is adjudication).
ENTRY_ID_RE = re.compile(
    r"^[\s\[]*"                                      # optional bracket/space
    r"(?:[A-Z][A-Za-z+&]*\s*(?:\u2192|->)\s*[A-Z][A-Za-z+& ]*?\s*[\u2014\-\u00b7]+\s*)?"  # routing prefix
    r"[\s\[]*"
    r"([A-Z]+)[-\u2011 ](\d+)\b(?!-\d)")

# ── THE SEPARATOR-LESS ARM ──────────────────────────────────────────────────
# ENTRY_ID_RE above is UNCHANGED and is still tried FIRST. This arm adds the
# one live form it cannot express: `ENNNN`, `ENNN` — prefix and number with NO
# separator at all. The wake skill has always called both forms live
# ("`ORCH-NNNN` and `ENNN` are both live forms"); the grammar only ever
# matched one of them, so a large block of real headings was invisible on
# today's corpus and every lane family carrying them reported a stale tail.
#
# ⛔ WHY THE >=3-DIGIT FLOOR, AND WHY IT IS THE WHOLE SAFETY ARGUMENT.
# Making the separator merely OPTIONAL re-mints the id-fabrication failure this floor exists to prevent: with
# no separator and no floor, any title opening `<CAPS><digits>` becomes an id,
# and 1-2 digit runs are where the false ones live (`X9`, `AB3`, a version
# token, a section number). The floor is priced at ZERO real ids on today's
# corpus — it is recorded as "a floor chosen against latent risk",
# not against a measured loss — while it keeps a guard that a >=2 floor
# forfeits. Measured before adoption, on the live corpus, and stated as
# the safety RESULT rather than as corpus size: every newly-visible
# heading was an E-form heading, minted-beyond-E 0, lost 0.
#
# ⛔ THE ANCHOR AND THE DATE GUARD ARE NOT RELAXED HERE. Same `^` anchor, same
# routing prefix, same `(?!-\d)` — so `## WAKE <ISO-8601 timestamp> …` is
# still not a `WAKE-2026`, twice over: the space stops this arm before the
# digits, and the date guard stops the other. This widens the SEPARATOR class
# only, exactly as the P5 cure above did, and for the same reason.
#
# ⚠ The residual disclosed at P5 is UNCHANGED and still open: a title with a
# second `—`-delimited segment before its id stays invisible. Not this arm's
# business (discipline: shape change is adjudication).
ENTRY_ID_NOSEP_RE = re.compile(
    r"^[\s\[]*"
    r"(?:[A-Z][A-Za-z+&]*\s*(?:\u2192|->)\s*[A-Z][A-Za-z+& ]*?\s*[\u2014\-\u00b7]+\s*)?"
    r"[\s\[]*"
    r"([A-Z]+)(\d{3,})\b(?!-\d)")


def match_entry_id(title):
    """The entry-id grammar: separated form first, then the floored bare form.

    \u26d4 ORDER IS LOAD-BEARING, not stylistic. ENTRY_ID_RE must be tried first so
    that a separated id is never re-read by the bare arm. Both arms expose the
    SAME two groups (prefix, number), so every existing `m.group(1)/m.group(2)`
    consumer keeps its contract and nothing downstream needs to know which arm
    matched (discipline: emitter and verifier are one grammar).
    """
    return ENTRY_ID_RE.match(title) or ENTRY_ID_NOSEP_RE.match(title)
# Canonicalization (the rule declared in this file's header — NOT the
# shipping docs/DESIGN.md, which has no such section): ATX H2, 0-3 space
# indent, trailing CR and
# trailing-whitespace tolerated; ATX closing hashes stripped from the title.
H2_LINE_RE = re.compile(r"^ {0,3}##[ \t]+(.+?)[ \t]*\r?$")
ATX_CLOSE_RE = re.compile(r"[ \t]+#+$")
FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
FENCE_CLOSE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*\r?$")
NEXT_STEP_CANON_RE = re.compile(r"^next step\b", re.I)
LEGACY_ZAP_TITLE_RE = re.compile(r"^⚡\s*working[\s-]state", re.I)
RENDERED_ZAP_TITLE = "⚡ working state (rendered)"
LANE_TAIL_RE = re.compile(r"^- lane tail ([A-Z]+)-(\d+) @ (\S+)\r?$", re.M)
LANE_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")  # chronological lane ordering
SRC_DELIM_RE = re.compile(r"[\s,]")  # refused in <rel>: whitespace + the , separator
# The sentinel watcher-mesh probe marker. MUST stay byte-identical to
# tools/dashboard/parse.py (does not ship in this repo) — its
# ::is_canary_lane marker — pinned by a control in
# tools/tests/render_head_canary_controls.py (does not ship in this repo),
# because a rename on one side that
# the other misses silently re-opens the stale-head refusal this excludes.
CANARY_MARKER = "CANARY-DO-NOT-ACT-CANARY-"

# ⛔ OPS ALERT FLAGS ARE NOT SOURCES — same defect class as CANARY_MARKER above,
# different producer family. Existence-signalled alert flags are written into
# channel/ with a fixed name and UNLINKED when the condition clears
# (a clock daemon's alert path, and the sibling poller wrappers this
# copied — neither ships in this repo).
# channel/*.md matches them, so a flag present at render time is STAMPED into the
# footer and then deletes itself — "stamped but missing" — and every seat that
# wakes in that window gets a stale-head refusal for a reason unconnected to its
# own state. A flag's intended disappearance between render and grade is
# enough on its own to demote the reading seat's head.
#
# ANCHORED PREFIX, not a substring, and not the narrower `_FAILING.md` form.
# Ruled on measured evidence that the convention has ALREADY DRIFTED in the
# workspace this was written against. The producers there do NOT share one
# suffix: the `ALERT_<producer>_FAILING.md` form is NOT universal there —
# inbound-notice and drain flags carry no `_FAILING` at all, and not every
# flag lives in `channel/`; some sit at the workspace root. So keying on
# `_FAILING` would MISS a flag that IS in this glob's scope — which is the
# direction the canary comment above names as unsurvivable.
#
# ⚠ The names are deliberately not reproduced here. What makes the anchor
#   correct is the SHAPE of the drift — one producer family, more than one
#   naming convention — and a reader can check that against their own
#   workspace. A list of another deployment's private flag filenames would
#   read as a contract this tool does not have.
#
# The anchor is safe in the other direction too (silently dropping a REAL
# lane): a lane filename is <sender>_to_<recipient>_<date>.md, so it can only
# begin "ALERT_" if a SEAT is named ALERT, and none is. A bare "ALERT"
# substring WOULD drop a real lane — e.g. orch_to_builder_topic_<date>.md.
# Pinned to the producer's own constant by a control in
# tools/tests/render_head_alert_controls.py (does not ship in this repo)
# — the control asserts the
# producer's ALERT_NAME startswith THIS prefix, i.e. producer-vs-consumer,
# never both-equal-a-third-literal written in the test.
#
# NOTE ON CROSS-REPO REFERENCES. A few comments below name files that do
# NOT ship in this repo -- they live in the private workspace this tool was
# developed in, and they are the controls that pin the literals duplicated
# here. Each such reference says so inline. They are kept rather than
# deleted because the pinning relationship is a real fact about how these
# constants stay correct, and a reader who does not know a control exists
# cannot ask whether it still holds. They are NOT resolvable from this
# repo, and nothing here depends on them at runtime.
# (discipline: tests must not create the contract)
ALERT_PREFIX = "ALERT_"

TICK_MAX_AGE_S = 24 * 3600      # F8 tick threshold leg 1
TICK_MAX_ENTRIES = 20           # F8 tick threshold leg 2

RC_OK, RC_REFUSED, RC_STALE, RC_UNRENDERED, RC_ERROR = 0, 2, 3, 4, 5


class SystemExit_(Exception):
    def __init__(self, code, msg):
        self.code, self.msg = code, msg


# ------------------------------------------------------------------ sections -
class Section:
    def __init__(self, start, body_start, end, title):
        self.start, self.body_start, self.end, self.title = start, body_start, end, title


def canon_title(raw):
    """Canonical heading title: trailing CR/whitespace already excluded by
    H2_LINE_RE's capture; ATX closing hashes stripped here."""
    return ATX_CLOSE_RE.sub("", raw)


class SectionList(list):
    """List of Section, plus structural scan facts:
    unclosed_fence = (line_no_1based, char, min_len) when a fence opened but
    never closed before EOF (CommonMark: it swallows the rest of the document,
    hiding every later heading — a state render/check must not grade blind)."""
    unclosed_fence = None


def find_sections(text):
    """All level-2 sections as Section(start, body_start, end, canonical
    title), per the DECLARED canonicalization rule in this file's header:
    - ATX `##` headings with 0-3 leading spaces; trailing CR / trailing
      whitespace / ATX closing hashes canonicalized out of the title
    - a BOM at byte 0 is transparent to structure (a heading at byte 1 is
      found; the BOM byte is preserved on write)
    - heading-shaped lines inside fenced code blocks (``` / ~~~, CommonMark
      open/close matching) are CONTENT, never sections; per CommonMark §4.5 a
      BACKTICK fence's info string may not contain a backtick — such a line
      is NOT a fence opener
    `####` demoted headings do NOT open a section. A section runs to the next
    recognized heading or EOF. Returns a SectionList; .unclosed_fence records
    a fence still open at EOF."""
    base = 1 if text.startswith("﻿") else 0
    heads = []          # (line_start_abs, line_end_abs_excl_newline, title)
    offset = base
    fence = None        # (char, min_len) while inside a fenced block
    fence_line = None   # 1-based line number of the open fence
    line_no = 0
    for ln in text[base:].splitlines(keepends=True):
        line_no += 1
        content = ln[:-1] if ln.endswith("\n") else ln   # keeps a trailing \r
        if fence is not None:
            m = FENCE_CLOSE_RE.match(content)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1]:
                fence, fence_line = None, None
        else:
            m = FENCE_OPEN_RE.match(content)
            # CommonMark §4.5: a backtick-fence info string cannot contain a
            # backtick — such a line is ordinary content, not an opener.
            if m and not (m.group(1)[0] == "`" and "`" in content[m.end():]):
                fence, fence_line = (m.group(1)[0], len(m.group(1))), line_no
            else:
                hm = H2_LINE_RE.match(content)
                if hm:
                    heads.append((offset, offset + len(content), canon_title(hm.group(1))))
        offset += len(ln)
    out = SectionList()
    for i, (start, line_end, title) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        body_start = min(line_end + 1, len(text))  # past the newline if any
        out.append(Section(start, body_start, end, title))
    if fence is not None:
        out.unclosed_fence = (fence_line, fence[0], fence[1])
    return out


def classify(text):
    """(sections, dispatch_surfaces, rendered_zaps, legacy_zaps).
    Dispatch surface = canonical title matching /^next step\\b/i — casing,
    indent, and suffix variants ALL count (whitelist-rule intent)."""
    secs = find_sections(text)
    dispatch = [s for s in secs if NEXT_STEP_CANON_RE.match(s.title)]
    rendered = [s for s in secs if s.title == RENDERED_ZAP_TITLE]
    legacy = [s for s in secs if LEGACY_ZAP_TITLE_RE.match(s.title)
              and s.title != RENDERED_ZAP_TITLE]
    return secs, dispatch, rendered, legacy


def _nonfenced_section_lines(text, sec):
    """Yield each physical line of the section body that is NOT inside a fenced
    code block, applying the SAME CommonMark open/close + backtick-info rule
    find_sections uses for structure (PC-1: footer recognition must share
    find_sections' fence policy — a footer-shaped line quoted inside a ``` /
    ~~~ block is documentation, never a stamp). Fence state starts CLOSED: a
    recognized section heading cannot sit inside an open fence, so the body
    begins outside any fence. A fence still open at the section end is handled
    upstream (render/check refuse an unclosed fence)."""
    fence = None
    for content in text[sec.body_start:sec.end].splitlines():
        if fence is not None:
            m = FENCE_CLOSE_RE.match(content)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1]:
                fence = None
            continue
        m = FENCE_OPEN_RE.match(content)
        if m and not (m.group(1)[0] == "`" and "`" in content[m.end():]):
            fence = (m.group(1)[0], len(m.group(1)))
            continue
        yield content


def section_footer_lines(text, sec):
    """(clean_matches, attempt_count) over the NON-FENCED physical lines of the
    section. A CLEAN footer is FOOTER_RE.fullmatch on the stripped line; an
    ATTEMPT is any stripped line that structurally opens as a v1 footer
    (FOOTER_ATTEMPT_RE) — clean or corrupted. Counting attempts (not only
    clean matches) is the PC-1 close for a real footer disqualified by a
    trailing edit: fullmatch alone would drop it and silently bind a separate
    appended lookalike; the attempt count makes that tampering visible so the
    caller can refuse. Fenced lines are excluded (documentation, not stamps)."""
    clean, attempts = [], 0
    for content in _nonfenced_section_lines(text, sec):
        s = content.strip()
        if FOOTER_ATTEMPT_RE.match(s):
            attempts += 1
            m = FOOTER_RE.fullmatch(s)
            if m:
                clean.append(m)
    return clean, attempts


def section_footer(text, sec):
    """STRUCTURAL footer recognition (the unique-in-section rule plus the PC-1
    close):
    the footer is the UNIQUE, CLEAN, NON-FENCED v1-footer line of the given
    section — never bound by position (the pre-cure last-non-blank-line rule
    let an appended lookalike BECOME the footer, and let one benign appended
    line un-render the head) and never fence-blind (PC-1: a fenced footer
    quote is not a stamp). Returns the match, or None when the section carries
    no footer-attempt line at all. REFUSED (exit 2, ambiguous/tampered stamp —
    never graded, never certified) when either:
      * two or more footer-attempt lines are present (an appended lookalike
        never becomes the footer, and never silently un-renders the head), or
      * a single footer-attempt line is not a clean fullmatch (a real footer
        corrupted by a trailing edit — recognition must not fall through to a
        different appended lookalike or certify a mangled stamp).
    A footer-shaped line inside a fenced block or anywhere outside the section
    is documentation/prose, inert. --adopt never calls this on an ambiguous
    head (demotion is its named recovery), so the refusal is always the
    strict/check grade, and --adopt always recovers."""
    clean, attempts = section_footer_lines(text, sec)
    if attempts > 1 or (attempts == 1 and not clean):
        raise SystemExit_(RC_REFUSED,
                          f"⛔ REFUSED — ambiguous/tampered stamp: {attempts} footer-shaped line(s) "
                          f"in the Next Step section, {len(clean)} of them a clean v1 footer. Cannot "
                          f"certify which line is the rendered footer (an appended or trailing-edited "
                          f"lookalike never becomes the footer). No write performed. Recovery: --adopt "
                          f"demotes the section byte-intact and regenerates the pair.")
    return clean[0] if clean else None


def scoped_footer(text):
    """(match, section) for THE canonical dispatch section's footer, or
    (None, None). Raises RC_REFUSED if more than one dispatch surface."""
    _secs, dispatch, _r, _l = classify(text)
    if len(dispatch) > 1:
        raise SystemExit_(RC_REFUSED,
                          f"⛔ REFUSED — {len(dispatch)} dispatch surfaces (canonical census); "
                          f"exactly one is allowed. Run render/--adopt to resolve.")
    if not dispatch:
        return None, None
    return section_footer(text, dispatch[0]), dispatch[0]


# ------------------------------------------------------------------- sources -
def derive_sources(ws: Path):
    """[(rel, Path)] for every plan file and lane file, sorted, forward-slash
    rel paths. These are the ONLY inputs of the rendering and exactly the set
    stamped into the footer. Paths carrying whitespace OR a comma (the v1
    source separator) are REFUSED — the grammar cannot express them."""
    srcs = []
    for sub, pat in (("channel", "*.md"), ("plans", "*.plan.yaml")):
        d = ws / sub
        if d.is_dir():
            for p in sorted(d.glob(pat)):
                # ⛔ CANARY PROBES ARE NOT SOURCES. The watcher mesh writes
                # `*_CANARY-DO-NOT-ACT-CANARY-<ts>.md` into channel/ and rotates
                # them out within minutes. `channel/*.md` matches them, so a
                # canary present at render time got STAMPED into the footer —
                # and then self-deleted, leaving a stamped source missing from
                # disk. Both halves of the footer-staleness leg then fire: a
                # canary arriving after a render reads as "new source not in
                # footer", and its deletion reads as "stamped but missing". The
                # result is a GUARANTEED stale-head refusal for every seat that
                # wakes inside a canary window, for a reason that has nothing to
                # do with that seat's state. The window is short: a canary
                # arrives and then removes itself minutes later.
                #
                # The marker is the sentinel's ACTUAL string, deliberately NOT a
                # bare "CANARY" substring. Canonical definition + the full
                # two-directional failure analysis lives at
                # tools/dashboard/parse.py (does not ship in this repo),
                # in ::is_canary_lane; the literal is
                # duplicated here rather than imported so this tool stays
                # standalone in workspaces with no dashboard, and the two are
                # PINNED EQUAL by a control (the standing precedent for a
                # literal deliberately duplicated across two modules).
                # A broad substring would silently drop a REAL lane such as
                # `orch_to_builder_topic_<date>.md`, which is the
                # unsurvivable direction. (discipline: emitter and verifier are one grammar)
                if CANARY_MARKER in p.name:
                    continue
                # Ops alert flags — see ALERT_PREFIX. Anchored, so a real lane
                # can never be dropped; covers every producer in the family
                # including any that never adopted the _FAILING suffix.
                if p.name.startswith(ALERT_PREFIX):
                    continue
                rel = f"{sub}/{p.name}"
                if SRC_DELIM_RE.search(rel):
                    raise SystemExit_(RC_REFUSED,
                                      f"⛔ REFUSED — source path contains whitespace or ',' (v1 footer "
                                      f"delimiter), cannot stamp v1 footer: {rel}")
                srcs.append((rel, p))
    return srcs


def require_adopted(ws: Path):
    """Stream B wake contract (wake.md step 6): a workspace with no
    plans/ directory has NOT adopted the ledger — rendering an adopted-shape
    head for it would certify the wrong state."""
    if not (ws / "plans").is_dir():
        raise SystemExit_(RC_REFUSED,
                          f"⛔ REFUSED — no plans/ directory under {ws}: ledger not adopted "
                          f"(stream B wake 6c-only contract). render_head renders adopted "
                          f"workspaces only; adopt the plans/ ledger first.")


def _lane_sort_key(p: Path):
    """Chronological key for a lane file: the date embedded in its filename
    (lanes rotate by date), primary; full filename breaks same-date ties; a
    dateless lane falls back to its mtime. NEVER the bare filename alone — a
    lexical filename sort is SENDER-MAJOR (a lane named `builder_…` sorts
    before `owner_…` regardless of date), so `entries[-1]` reports whatever the
    filename sort happened to place last, which can be a stale id (cross-stream
    finding routed from stream B: OLD reports the EARLIER id when the true
    chronological tail is the LATER one). Mirrors stream B's `_lane_sort_key`."""
    m = LANE_DATE_RE.search(p.name)
    if m:
        return (m.group(1), p.name)
    # `utcfromtimestamp` is deprecated and SCHEDULED FOR REMOVAL; at removal this
    # raises AttributeError at head-render time for every seat at once, on a path
    # the fallback exercises on EVERY render.
    # Behaviour-preserving: verified identical on every fallback-path file
    # in the corpus it was measured against.
    #
    # ⚠ IT PRESERVES A SEMANTIC MISMATCH IT DID NOT CREATE, said here rather than
    # silently fixed, because changing a sort key is a shape change, not a cure
    # (discipline: shape change is adjudication). The `m.group(1)` branch above reads a date
    # out of a LOCAL-dated filename; this branch derives one in UTC. On some
    # files the two bases disagree by a day (those written late in the local
    # day, where the UTC date has already rolled over). Routed,
    # not decided here.
    return (datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d"),
            p.name)


def _lane_family(name: str):
    """The `<sender>_to_<recipient>` family of a lane FILENAME.

    Lanes rotate by date (`<family>_<YYYY-MM-DD>.md`), so the family is the
    stem with any trailing date stripped. SHARED by the emitter and the F8
    verifier — one grammar, so a family can never be computed two ways.
    """
    stem = name[:-3] if name.endswith(".md") else name
    m = LANE_DATE_RE.search(stem)
    if m and stem.endswith(m.group(1)):
        stem = stem[: m.start()].rstrip("_")
    return stem


def _lane_recipient(family: str):
    """Recipient seat of a lane family, normalized; None if not a direction."""
    if "_to_" not in family:
        return None
    return norm_seat(family.rsplit("_to_", 1)[1])


class LaneScan(dict):
    """{(family, prefix): [...]} plus .blind_lanes — the lanes whose scan is
    TRUNCATED by an unclosed fence (F6). Carried as an attribute on the
    result for the same reason SectionList carries .unclosed_fence: the
    diagnostic belongs to the scan, and a caller that ignores it should have
    to ignore it EXPLICITLY rather than by never being told.

    Each element is (lane_filename, opening_line_no, fence_text).
    """
    blind_lanes = ()


def _lane_scan(ws: Path):
    """{prefix: [(num, rel), ...]} in CHRONOLOGICAL order across all
    channel/*.md (files ordered by embedded date via _lane_sort_key, entries
    in append order within each file), with mirrored/echoed ids DEDUPED to
    their FIRST (origin) occurrence. So entries[-1] is the genuinely-newest id
    (not whatever a sender-major filename sort placed last) and every id has
    ONE authoritative position for the tick entries-behind count. One shared
    scan backs both lane_entries and lane_tails so they can never disagree.
    Mirrors stream B's lane_entries dedup exactly (cross-stream fix)."""
    raw, blind = {}, []
    ch = ws / "channel"
    if ch.is_dir():
        for lane in sorted(ch.glob("*.md"), key=_lane_sort_key):
            rel = f"channel/{lane.name}"
            # Headings come from find_sections() — the module's ONE declared
            # H2 grammar (fence-aware, 0-3 space indent, `####` excluded).
            # Scanning raw text with a heading-shaped regex is what let
            # fenced examples and body sub-headings count as entries.
            secs = find_sections(lane.read_bytes().decode("utf-8"))
            # F6: an unclosed fence swallows every LATER heading
            # (CommonMark), so the scan goes BLIND past it and that lane's
            # tail silently becomes whatever preceded the fence. Recorded
            # here, ACTED ON by the callers — because the right response
            # differs by caller and this scan does not know which it serves.
            if secs.unclosed_fence is not None:
                fch, min_len = secs.unclosed_fence[1], secs.unclosed_fence[2]
                blind.append((lane.name, secs.unclosed_fence[0], fch * min_len))
            for sec in secs:
                # .match(), never .search(): the anchor in ENTRY_ID_RE only
                # binds if the match must start at the title's beginning.
                # match_entry_id applies BOTH arms in order, per the governing ruling; it is
                # .match()-only on both, so the anchor argument above is intact.
                m = match_entry_id(sec.title)
                if not m:
                    continue
                # D2 cure: key by (FAMILY, prefix). A shared id prefix is a
                # SENDER's numbering space, not a delivery channel — traffic
                # addressed to another recipient is not this head's tail.
                raw.setdefault((_lane_family(lane.name), m.group(1)), []).append(
                    (int(m.group(2)), rel))
    out = LaneScan()
    out.blind_lanes = tuple(blind)
    for key, entries in raw.items():
        seen, deduped = set(), []
        for num, rel in entries:
            if num in seen:
                continue          # mirror/echo of an already-seen origin
            seen.add(num)
            deduped.append((num, rel))
        out[key] = deduped
    return out


def lane_entries(ws: Path):
    """{prefix: [n, ...]} chronological + deduped (see _lane_scan). The tick
    entries-behind leg counts positions in this list, so the chronological
    ordering and the mirror dedup are load-bearing: a lexical filename sort or
    a live echo would mis-locate the recorded tail (cross-stream fix)."""
    scan = _lane_scan(ws)
    out = LaneScan((key, [n for n, _rel in entries]) for key, entries in scan.items())
    # F6: the diagnostic rides through to the tick verifier, which reports it
    # as a PROBLEM rather than refusing — see check().
    out.blind_lanes = scan.blind_lanes
    return out


def lane_tails(ws: Path, seat=None):
    """{prefix: (n, rel)} — the TRUE chronological tail per prefix (the newest
    origin id from _lane_scan) and the lane it originates in. With
    chronological+deduped ordering the recorded tail is `behind==0` at render
    time by construction, and an old id echoed into a newer lane can neither
    displace the true tail nor grade fresh from the late echo."""
    scan = _lane_scan(ws)
    out = {key: (entries[-1][0], entries[-1][1])
           for key, entries in scan.items() if entries}
    # -- F6: refuse to MINT a tail claim over a lane the scan cannot see ----
    # Asymmetric with the tick verifier ONE FUNCTION DOWN, deliberately: this
    # is the emitter, and it is about to write a tail into a head that every
    # later tick grades as truth. A knowingly-short tail written here is the
    # silent wrong tail this whole cure exists to remove. check() only GRADES
    # a claim that already exists, so there it degrades to a loud `problems`
    # line — the same shape as the `channel lane unreadable` leg beside it.
    # Fail closed where the false claim is CREATED; report where it is READ.
    #
    # SCOPED to this seat's inbound families, and that scoping is the point:
    # channel lanes are append-only files written by OTHER seats, so an
    # unscoped refusal would let any one seat's malformed entry kill every
    # other seat's render fleet-wide. Under D2 an out-of-scope lane cannot
    # reach this head's tails at all, so there is nothing to refuse about.
    # (The module refuses unscoped on the ROLE file — that is the seat's OWN
    # file, with no cross-seat coupling. Different blast radius, different
    # rule.) seat=None means the scope is UNKNOWN, so it fails closed on any.
    want_r = norm_seat(seat) if seat is not None else None
    offend = [b for b in scan.blind_lanes
              if want_r is None or _lane_recipient(_lane_family(b[0])) == want_r]
    if offend:
        det = "; ".join(f"channel/{n} (fence {f!r} opened line {ln})" for n, ln, f in offend)
        raise SystemExit_(RC_REFUSED,
                          f"⛔ REFUSED — unclosed code fence hides every later entry heading "
                          f"in {len(offend)} inbound lane(s): {det}. A tail derived past it "
                          f"would be silently SHORT, and this head would then be graded as "
                          f"truth on every tick. Close the fence, then re-render.")
    if seat is None:
        return out
    # Seat-scoped: a head cites what was said TO this seat. Reporting another
    # recipient's tail is the defect this cure exists for (a builder head
    # printed an orch_to_owner id as its own tail).
    want = norm_seat(seat)
    # ⛔ NO FALLBACK. An earlier draft returned `scoped or out`, reasoning
    # that a seat with no inbound lane should not render a head with no
    # tails. That was backwards, and review ranked it the top silent
    # wrong-tail path: when `scoped` is empty the fallback hands that seat
    # EVERY family in the workspace — which is D2 exactly, reproduced for
    # precisely the seat whose empty inbound set should have been the
    # signal. An empty result IS the honest answer; the next-step line
    # already renders it as "none", and the guard's degradation path is
    # where a seat with no inbound lane belongs.
    return {k: v for k, v in out.items() if _lane_recipient(k[0]) == want}


# -------------------------------------------------------------------- ledger -
# Seat-resolution contract (stream B wake.md step 4 / digest 6b — ONE
# normalization contract with resolve_role/render_digest):
# legacy aliases normalize, canonical seats (owner/builder/orchestrator/
# creator) self-resolve, anything else passes through unchanged (an unknown
# seat matches no bound seat — never silently adopted).
# F8 — `orch` → orchestrator is the THIRD legacy alias the wake protocol
# declares (step 4, tier 3), and it was missing from this map. It was INERT
# until this cure: nothing here ever compared a seat name against a LANE
# name, so the gap could not fire. D2's seat-scoping makes it load-bearing,
# and it fails SILENTLY in the worst available way — lane families
# addressed to the orchestrator are conventionally named `*_to_orch`, so
# norm_seat("orch") != "orchestrator" emptied that seat's tail set outright
# and its head re-rendered with ZERO lane tails at rc=0. An empty tail set
# is byte-identical to LEG D's legitimate "no inbound lane" answer, so the
# affected seat would have been left with no lane-tail comparator at all,
# and nothing would have said so.
# Found by re-rendering the LIVE heads in a staging copy, not by reading.
#
# Digest side (norm_seat is ONE contract, shared with render_digest): no
# live plan uses `orch` as a seat while other rows say `orchestrator` — so the
# change is inert there today. It aligns this module with the protocol's
# alias list instead of leaving a second, shorter one beside it.
SEAT_ALIASES = {"engine": "owner", "helper": "builder", "orch": "orchestrator"}


def norm_seat(seat):
    return SEAT_ALIASES.get(seat, seat)


def flat(v):
    """Flatten ledger prose to ONE physical line before interpolation:
    schema-valid multiline desc/question/rule/action can never mint a
    physical heading (or fence) line inside a rendered section. The ⏎ marker
    makes the collapse visible rather than silent."""
    if v is None:
        return ""
    return " ⏎ ".join(part.strip() for part in str(v).replace("\r", "").split("\n"))


def prose(entry, canonical, fallback="desc"):
    """Resolve a ledger prose field for RENDERING (the P0 prose-drop cure).

    PLAN_SCHEMA names `question` on gates and `rule` on constraints; a large
    part of the live ledger writes the prose under `desc` instead. Reading
    only the canonical name and passing the miss through `flat()` — which
    maps None to "" — rendered those rows with an EMPTY body, and an empty
    tail reads as "this row has no text" rather than "the text was dropped".
    That is silent falsification of the surface a waking seat dispatches from.

    Fall back, but NEVER silently: a divergent row is MARKED so normalizing
    the ledger stays visible work instead of being papered over by the
    renderer. Missing under BOTH names is a loud defect, never an empty
    string. Returns already-flattened text.
    """
    v = entry.get(canonical)
    if v is not None:
        return flat(v)
    v = entry.get(fallback)
    if v is not None:
        return (f"{flat(v)}  [!! schema-divergent: prose read from "
                f"`{fallback}`; schema field is `{canonical}`]")
    return (f"!! PROSE MISSING (neither `{canonical}` nor `{fallback}` "
            f"present) — ledger defect, not empty prose")


def load_open_plans(ws: Path):
    out = []
    plans = ws / "plans"
    if plans.is_dir():
        planfiles = sorted(plans.glob("*.plan.yaml"))
        if planfiles and yaml is None:
            raise SystemExit_(RC_ERROR,
                              "\u26d4 ERROR - this workspace has plans/ but "
                              "PyYAML is not installed; the ledger cannot be "
                              "read. Install PyYAML (the one non-stdlib "
                              "prerequisite).")
        for p in planfiles:
            try:
                data = yaml.safe_load(p.read_bytes().decode("utf-8"))
            except _YAML_ERROR as e:
                raise SystemExit_(RC_ERROR,
                                  f"⛔ ERROR — plan YAML failed to parse: plans/{p.name}: "
                                  + str(e).splitlines()[0])
            if data is not None and not isinstance(data, dict):
                # valid YAML, wrong top-level shape (list/str/int): the most
                # likely hand-authored malformation — refuse per the exit
                # contract, never a raw AttributeError traceback
                raise SystemExit_(RC_ERROR,
                                  f"⛔ ERROR — plan top-level is not a YAML mapping "
                                  f"(got {type(data).__name__}): plans/{p.name}; schema_version-1 "
                                  f"plans are mappings (schema_version-1 contract)")
            if data and data.get("state") == "open":
                out.append(data)
    return out


def constraint_live(c, gates_by_id, now):
    until = c.get("until")
    if until is None or until == "close":
        return True
    if isinstance(until, str) and until.startswith("gate:"):
        g = gates_by_id.get(until[5:])
        return g is None or g.get("ruled") is None
    try:
        return datetime.fromisoformat(str(until)) > now
    except (ValueError, TypeError):
        return True  # unparseable/naive expiry stays visible, never silently dropped


def precondition_met(pid_map, ref, now):
    kind, obj = pid_map.get(ref, (None, None))
    if kind == "step":
        return obj.get("status") == "done"
    if kind == "gate":
        return obj.get("ruled") is not None
    if kind == "clock":
        if obj.get("fired") is not None:
            return True
        try:
            return datetime.fromisoformat(str(obj["fires_at"])) <= now
        except (ValueError, TypeError, KeyError):
            return False
    return False  # unknown reference: never treat as satisfied


def seat_digest(ws: Path, seat: str, now):
    """Typed digest for the bound seat. Same seat-scoping semantics as stream
    B's render_digest (REQUIRED step owner — no owner_seat fallback; one-hop
    gates; clocks/constraints by plan ownership; OVERDUE marking); grammar is
    this renderer's own. Seat names compare NORMALIZED through norm_seat (the
    frozen schema admits engine/helper aliases and the digest must not go
    blind on them). A step missing its required `owner` is a schema defect
    rendered as a loud DEFECT line in EVERY seat's digest — never guessed
    from owner_seat, never dropped, never dispatched (the renderer half of
    that contract).
    Every interpolated ledger value passes through flat() — one physical line.
    Returns (plan_ids, lines, actions) where actions feeds the Next Step
    derivation."""
    plan_ids, lines = [], []
    overdue, in_progress, ready, blocked_gates = [], [], [], []
    nseat = norm_seat(seat)
    for plan in load_open_plans(ws):
        pid = flat(plan.get("project_id", "?"))
        plan_ids.append(pid)
        plan_owned = norm_seat(plan.get("owner_seat")) == nseat
        pid_map = {}
        for s in plan.get("steps") or []:
            pid_map[s["id"]] = ("step", s)
        gates = plan.get("gates") or []
        for g in gates:
            pid_map[g["id"]] = ("gate", g)
        for k in plan.get("clocks") or []:
            pid_map[k["id"]] = ("clock", k)
        gates_by_id = {g["id"]: g for g in gates}
        seat_step_ids = set()
        for s in plan.get("steps") or []:
            owner = s.get("owner")
            if owner is None or (isinstance(owner, str) and owner.strip() == ""):
                # schema defect (steps[].owner is REQUIRED by the plan schema):
                # surfaced loudly in every seat's digest, never guessed from
                # owner_seat, never dispatched. PC-8: an EMPTY or whitespace
                # owner is the same defect as a missing one — pre-cure the
                # falsy `or owner_seat` fallback at least kept it visible to
                # the plan owner; the `is None`-only DEFECT silently dropped it
                # fleet-wide. (A non-empty but unresolvable/typo'd owner is a
                # different case — it names no bound seat and stays out of every
                # digest by design; a known open item.)
                lines.append(f"- step {flat(s['id'])} [{pid}] DEFECT — no owner "
                             f"(schema requires one)")
                continue
            if norm_seat(owner) != nseat:
                continue
            seat_step_ids.add(s["id"])
            st = s.get("status")
            if st in ("pending", "in-progress", "blocked"):
                lines.append(f"- step {flat(s['id'])} [{pid}] {flat(st)} — {flat(s.get('desc', ''))}")
                if st == "in-progress":
                    in_progress.append((pid, s))
                elif st == "pending" and all(
                        precondition_met(pid_map, r, now) for r in (s.get("preconditions") or [])):
                    ready.append((pid, s))
        for g in gates:
            if g.get("ruled") is None and (
                    plan_owned or set(g.get("unblocks") or []) & seat_step_ids):
                unb = flat(",".join(str(u) for u in (g.get("unblocks") or [])))
                lines.append(f"- gate {flat(g['id'])} [{pid}] unruled — {prose(g, 'question')} → unblocks {unb}")
                blocked_gates.append((pid, g))
        if plan_owned:
            for k in plan.get("clocks") or []:
                if k.get("fired") is not None:
                    continue
                # PC-9: an unparseable or NAIVE fires_at previously set
                # over=False SILENTLY — OVERDUE is rung 1 of the dispatch
                # ladder, so a naive/garbled ledger clock was permanently
                # demoted out of dispatch with no signal (the footer grammar
                # enforces the offset on --now/NOW.txt but the LEDGER input was
                # unguarded). It is now marked VISIBLY rather than dropped.
                try:
                    fires = datetime.fromisoformat(str(k["fires_at"]))
                    if fires.tzinfo is None:
                        raise ValueError("naive fires_at (no UTC offset)")
                    over = fires <= now
                    mark = " OVERDUE" if over else ""
                except (ValueError, TypeError):
                    over = False
                    mark = (" ⚠ UNGRADEABLE fires_at (unparseable or naive — cannot "
                            "compute OVERDUE; fix the ledger)")
                lines.append(f"- clock {flat(k['id'])} [{pid}] {flat(k['fires_at'])} {flat(k.get('kind', ''))}{mark} — {flat(k.get('action', ''))}")
                if over:
                    overdue.append((pid, k))
            for c in plan.get("constraints") or []:
                if constraint_live(c, gates_by_id, now):
                    # P0: `c.get('rule','')` rendered EVERY
                    # live constraint with an EMPTY body here — see prose().
                    body = prose(c, "rule")
                    # The enforcement check (deferred, does not ship here) skips any
                    # constraint whose
                    # `blocks` is not a dict, so one without it can never fire.
                    # Inert prose must not render like a configured guard.
                    blocks = c.get("blocks")
                    enf = ("" if isinstance(blocks, dict) and blocks
                           else " ⚠ ENFORCEMENT=NONE (no `blocks` key — "
                                "nothing enforces it; advisory prose only)")
                    lines.append(f"- constraint {flat(c['id'])} [{pid}] until {flat(c.get('until'))}{enf} — {body}")
    return plan_ids, lines, {"overdue": overdue, "in_progress": in_progress,
                             "ready": ready, "gates": blocked_gates}


def derive_next_step(seat, tails, actions):
    """Deterministic dispatch derivation. The priority order is fixed and is
    the ORDER OF THE BRANCHES BELOW — it was previously cited to a bare
    `DESIGN.md`, which resolves in this repo to `docs/DESIGN.md`, a file
    that does not specify it. This function IS the specification for the
    order; no shipping document defines it. Always cites the CURRENT lane
    tails so the wake 6c
    comparator sees fresh ids by construction."""
    if actions["overdue"]:
        pid, k = min(actions["overdue"], key=lambda x: str(x[1]["fires_at"]))
        head = (f"Handle OVERDUE clock {flat(k['id'])} [{pid}] (fired {flat(k['fires_at'])}): "
                f"{flat(k.get('action', ''))}")
    elif actions["in_progress"]:
        pid, s = actions["in_progress"][0]
        head = f"Finish step {flat(s['id'])} [{pid}] — {flat(s.get('desc', ''))} (verify: done_when before flipping status)"
    elif actions["ready"]:
        pid, s = actions["ready"][0]
        head = f"Start step {flat(s['id'])} [{pid}] — {flat(s.get('desc', ''))} (preconditions satisfied at render)"
    elif actions["gates"]:
        pid, g = actions["gates"][0]
        head = (f"Parked on gate {flat(g['id'])} [{pid}] — {prose(g, 'question')} "
                f"(present to ruler; waking never opens a gate)")
    else:
        head = f"No open ledger work for seat {seat} — re-derive from the lane tails below."
    tail_str = ", ".join(f"{fam} {p}-{n}"
                         for (fam, p), (n, _rel) in sorted(tails.items())) or "none"
    return [head, f"Lane tails at render: {tail_str}."]


# ------------------------------------------------------------------ renderer -
GEN_NOTE = ("<!-- rendered by render_head v1 — do not hand-edit; volatile facts "
            "derive from plans/ + channel/; judgment belongs in ## Standing judgment -->")


def assert_generated(section_text):
    """Per PHYSICAL LINE of the composed output: no line after the intended
    heading may open a heading or a fence. Belt over flat()'s braces."""
    for ln in section_text.split("\n")[1:]:
        assert not re.match(r"^ {0,3}#", ln) and not FENCE_OPEN_RE.match(ln), \
            f"generated physical line would open a structural surface: {ln!r}"


def build_rendered_sections(ws, role, now):
    """Returns (zap_text, make_ns) where make_ns(iso) -> the Next Step
    section text carrying a footer stamped rendered_at=<iso> over ONE shared
    source-mtime snapshot (so idempotence comparison can re-stamp without
    re-statting)."""
    sources = derive_sources(ws)
    if not sources:
        raise SystemExit_(RC_REFUSED,
                          "⛔ REFUSED — nothing to render from: no plans/*.plan.yaml and no channel/*.md under the workspace.")
    tails = lane_tails(ws, role)
    plan_ids, digest_lines, actions = seat_digest(ws, role, now)
    zap = ["## ⚡ working state (rendered)", GEN_NOTE, f"- seat: {role}",
           f"- open plans: {len(plan_ids)}" + (f" — {', '.join(plan_ids)}" if plan_ids else "")]
    zap += digest_lines
    for (_fam, p), (n, rel) in sorted(tails.items()):
        # Line format UNCHANGED — `rel` already identifies the family, so the
        # F8 verifier reads it back without a second grammar.
        zap.append(f"- lane tail {p}-{n} @ {rel}")
    src_str = ",".join(f"{rel}@{int(p.stat().st_mtime)}" for rel, p in sources)
    ns_body = derive_next_step(role, tails, actions)
    # Emission guard: no generated line other than the real
    # footer may CARRY a footer-shaped token — the current joint consumer
    # (stream B) binds FIRST match in the head body, so a ledger value that
    # renders a valid footer token would hand /sleep a forged stamp. Refuse
    # the input rather than emit a file the joint grammar misreads.
    for ln in zap[1:] + ns_body:
        if FOOTER_RE.search(ln):
            raise SystemExit_(RC_REFUSED,
                              f"⛔ REFUSED — a ledger/lane value renders a footer-shaped token into "
                              f"generated prose (the joint consumer binds first-match and would trust "
                              f"it as a stamp). Sanitize the value: {ln[:120]!r}")
    zap_text = "\n".join(zap) + "\n"

    # Lane-tail STAMP token (the optional `tails=` field of the v1 footer
    # grammar declared in this module's header):
    # the digest of the EXACT tail-line string this render emits, excluding
    # the line terminator, computed from the same in-memory string that goes
    # into the section — never from a re-read, so the emitter and any
    # verifier cannot diverge through a second measurement. The token is what
    # lets a wake EXEMPT the tail line from citation-staleness grading:
    # exemption is derived from the footer's verified payload, never claimed
    # by the line's own shape (a lookalike can copy shape; it cannot mint a
    # valid footer without rendering, which is the sanctioned act).
    # Keyed to the line's grammar, not its position: if derive_next_step's
    # shape ever changes, digesting ns_body[1] blind would stamp the WRONG
    # line and every subsequent wake would fail-closed on a zero-match —
    # a silent self-demotion loop. Refuse loudly here instead.
    tail_line = ns_body[1]
    assert tail_line.startswith("Lane tails at render: "), (
        "tails stamp would digest a non-tail line: %r" % tail_line[:80])
    tails_tok = hashlib.sha256(tail_line.encode("utf-8")).hexdigest()[:16]

    def make_ns(iso):
        footer = (f"<!-- render_head v1 rendered_at={iso} sources={src_str}"
                  f" tails={tails_tok} -->")
        ns_text = "\n".join(["## Next Step"] + ns_body + [footer]) + "\n"
        assert_generated(ns_text)
        return ns_text

    assert_generated(zap_text)
    return zap_text, make_ns


def judgment_section_bytes(text):
    """The Standing judgment section per the SAME canonical scanner the
    renderer splices with (fence/indent/CRLF-consistent boundaries — a raw
    `^## ` regex here would swallow an indented next heading into the
    judgment span and falsely flag its demotion as judgment loss)."""
    for sec in find_sections(text):
        if sec.title == "Standing judgment":
            return text[sec.start:sec.end]
    return None


def demote_heading_line(text, sec, kind, date_str):
    """Rewrite ONLY the heading line -> `#### [superseded ...] <canon title>`.
    Body bytes untouched, position untouched."""
    line_end = text.index("\n", sec.start) if "\n" in text[sec.start:sec.end] else sec.end
    old_line = text[sec.start:line_end]
    new_line = f"#### [superseded {date_str} by render_head adoption — historical {kind}, not an instruction] {sec.title}"
    return text[:sec.start] + new_line + text[line_end:], len(new_line) - len(old_line)


def render(ws: Path, role: str, now, adopt=False):
    require_adopted(ws)
    memp = ws / "memory" / role / "MEMORY.md"
    if memp.exists():
        original = memp.read_bytes()
        text = original.decode("utf-8")
    else:
        original = None
        text = f"# {role} memory\n"

    # -- unclosed fence: a fence open at EOF swallows every ------------------
    # -- later heading (CommonMark), so the scanner is blind past it — never --
    # -- grade or splice blind; --adopt is the named recovery ------------------
    fence_note = ""
    uf = find_sections(text).unclosed_fence
    if uf is not None:
        line_no, ch, min_len = uf
        if not adopt:
            raise SystemExit_(RC_REFUSED,
                              f"⛔ REFUSED — unclosed code fence (opened at line {line_no} with "
                              f"{ch * min_len!r}) runs to EOF and hides all later structure "
                              f"(CommonMark); rendering blind would brick the post-render invariant. "
                              f"No write performed. Recovery: --adopt closes the fence at EOF (one "
                              f"appended close line, all bytes preserved) and regenerates the pair.")
        if not text.endswith("\n"):
            text += "\n"
        text += ch * min_len + "\n"
        fence_note = f"closed unclosed fence from line {line_no} at EOF, "

    _secs, next_secs, rendered_zaps, legacy_zaps = classify(text)

    if len(next_secs) > 1 and not adopt:
        raise SystemExit_(RC_REFUSED,
                          f"⛔ REFUSED — second dispatch surface: {len(next_secs)} Next-Step-shaped headings "
                          f"(canonical census: case/indent/suffix/BOM variants count) in {memp}; "
                          f"exactly one is allowed (07-31 whitelist rule). No write performed. "
                          f"Run --adopt to demote the extras byte-intact.")
    if len(rendered_zaps) > 1 and not adopt:
        raise SystemExit_(RC_REFUSED,
                          f"⛔ REFUSED — {len(rendered_zaps)} rendered ⚡ sections in {memp}; corrupt state. "
                          f"No write performed. Run --adopt to demote them byte-intact.")
    if rendered_zaps and not next_secs and not adopt:
        raise SystemExit_(RC_REFUSED,
                          f"⛔ REFUSED — rendered ⚡ present but no dispatch surface in {memp} "
                          f"(a generated '## Next Step' was hand-demoted or lost); splicing here "
                          f"would overwrite bytes nested in the ⚡ section. RECOVERY: run --adopt "
                          f"to demote the stale rendered block byte-intact and regenerate the pair. "
                          f"No write performed.")
    if len(next_secs) == 1 and not adopt:
        sec = next_secs[0]
        if section_footer(text, sec) is None and text[sec.body_start:sec.end].strip():
            raise SystemExit_(RC_REFUSED,
                              f"⛔ REFUSED — hand-authored Next Step (no render_head footer as its last "
                              f"line) in {memp}; re-run with --adopt to demote it byte-intact before "
                              f"rendering. No write performed.")

    old_judgment = judgment_section_bytes(text)
    zap_text, make_ns = build_rendered_sections(ws, role, now)
    date_str = now.date().isoformat()

    def assemble(ns_text):
        """Pure assembly of the candidate text from the ORIGINAL text +
        precomputed section offsets (called twice for the scoped-idempotence
        comparison; must not share mutated state)."""
        if adopt:
            # Demote every dispatch/legacy-volatile/rendered heading IN PLACE
            # (bodies verbatim), then append the single rendered pair at EOF.
            # Re-running --adopt on an adopted file re-demotes the generated
            # pair and appends a fresh one (safe; footers inside #### bodies
            # are out of scope for footer recognition).
            t = text
            for sec in sorted(next_secs + legacy_zaps + rendered_zaps,
                              key=lambda s: s.start, reverse=True):
                kind = "next step" if NEXT_STEP_CANON_RE.match(sec.title) else "working state"
                t, _delta = demote_heading_line(t, sec, kind, date_str)
            if not t.endswith("\n"):
                t += "\n"
            return t + "\n" + zap_text + "\n" + ns_text
        edits = []  # (start, end, replacement)
        if rendered_zaps:
            edits.append((rendered_zaps[0].start, rendered_zaps[0].end, zap_text + "\n"))
        if next_secs:
            edits.append((next_secs[0].start, next_secs[0].end, ns_text))
        t = text
        for start, end, rep in sorted(edits, reverse=True):
            t = t[:start] + rep + t[end:]
        if not rendered_zaps and not next_secs:
            if not t.endswith("\n"):
                t += "\n"
            t = t + "\n" + zap_text + "\n" + ns_text
        elif not rendered_zaps:
            sec = next(s for s in find_sections(t) if NEXT_STEP_CANON_RE.match(s.title))
            t = t[:sec.start] + zap_text + "\n" + t[sec.start:]
        # (rendered ⚡ present + no dispatch surface is REFUSED above with a
        # named --adopt recovery — a splice here would swallow nested bytes)
        return t

    new_text = assemble(make_ns(now.isoformat()))

    # -- post-render assertions (scoped; single surface; single ⚡; judgment) -
    _fs, final_next, final_zaps, _fl = classify(new_text)
    assert len(final_next) == 1, f"post-render invariant broken: {len(final_next)} dispatch surfaces"
    assert len(final_zaps) == 1, f"post-render invariant broken: {len(final_zaps)} rendered ⚡ sections"
    assert section_footer(new_text, final_next[0]) is not None, \
        "post-render invariant broken: generated Next Step carries no scoped footer"
    if old_judgment is not None:
        if adopt or not (next_secs and rendered_zaps):
            # adoption / first render may append separators AFTER a trailing
            # judgment section; the judgment BYTES must still survive verbatim
            assert old_judgment in new_text, "render lost Standing judgment bytes"
        else:
            assert judgment_section_bytes(new_text) == old_judgment, \
                "render modified the Standing judgment section"

    # -- idempotence: SCOPED — only the generated footer's rendered_at is ----
    # -- neutralized (rebuild the candidate with the OLD stamp and compare ---
    # -- byte-exact; any other difference, including a rendered_at-shaped ----
    # -- string in ledger prose, forces a write) -----------------------------
    if original is not None:
        old_m = (section_footer(text, next_secs[0])
                 if len(next_secs) == 1 and not adopt else None)
        if old_m is not None and not adopt:
            if assemble(make_ns(old_m.group(1))) == text:
                print(f"CURRENT — {memp} already renders this ledger state; no write.")
                return RC_OK
        elif new_text == text:
            print(f"CURRENT — {memp} already renders this ledger state; no write.")
            return RC_OK
    memp.parent.mkdir(parents=True, exist_ok=True)
    # The atomic-write rule, at extended scope: the role file is read at
    # every wake — write_bytes truncates first, so a wake racing this render reads
    # a torn head. Same-dir temp + os.replace, the ruled method.
    tmp = memp.with_name(memp.name + ".renderhead.tmp")
    tmp.write_bytes(new_text.encode("utf-8"))
    os.replace(tmp, memp)
    print(f"RENDERED — {memp} ({'adopted, ' if adopt else ''}{fence_note}1 footer, 1 dispatch surface).")
    return RC_OK


# ---------------------------------------------------------------- comparator -
def check(ws: Path, role: str, tick=False):
    memp = ws / "memory" / role / "MEMORY.md"
    if not memp.exists():
        print(f"⛔ ERROR — no role file at {memp}")
        return RC_ERROR
    text = memp.read_bytes().decode("utf-8")
    secs0 = find_sections(text)
    if secs0.unclosed_fence is not None:
        line_no, ch, min_len = secs0.unclosed_fence
        raise SystemExit_(RC_REFUSED,
                          f"⛔ REFUSED — unclosed code fence (opened at line {line_no} with "
                          f"{ch * min_len!r}) runs to EOF and hides all later structure "
                          f"(CommonMark); cannot bind a dispatch surface to grade — refusing, "
                          f"not certifying, not silently downgrading to UNRENDERED. "
                          f"Recovery: --adopt closes the fence at EOF and regenerates the pair.")
    m, _sec = scoped_footer(text)   # SCOPED: decoy footers in prose are inert
    if not m:
        print(f"F8 UNRENDERED — no render_head footer on the Next Step section of {memp}; "
              f"F3 hand-head comparators (wake 6c / sleep hand-head gate) apply instead.")
        return RC_UNRENDERED
    stamped = {}
    try:
        for src in m.group(2).split(","):
            rel, ep = src.rsplit("@", 1)
            stamped[rel] = int(ep)
    except ValueError:
        raise SystemExit_(RC_ERROR,
                          f"⛔ ERROR — footer parse error in {memp}: sources token "
                          f"{m.group(2)!r} does not split as <rel>@<epoch>[,...]")
    problems = []
    if not (ws / "plans").is_dir():
        problems.append("no plans/ directory — ledger not adopted (wake 6c contract) "
                        "yet the head carries a rendered footer")
    # PC-2 footer↔⚡ invariant: a stamped Next Step footer is only ever emitted
    # alongside a `## ⚡ working state (rendered)` section (they are rendered as
    # one pair). If that section was retitled, demoted, or deleted while the
    # footer stayed valid, the tick entries-behind leg would scan ZERO lane
    # tails and pass VACUOUSLY (running-max/(discipline: vacuity cannot attribute)) — a
    # measured regression the tick-scoping cure introduced. A footer with no
    # census-recognized rendered ⚡ is head drift, not freshness, in EITHER
    # grade: the head no longer corresponds to a render this tool produced.
    if not [s for s in secs0 if s.title == RENDERED_ZAP_TITLE]:
        problems.append("stamped Next Step footer present but no "
                        f"'## {RENDERED_ZAP_TITLE}' section (retitled/demoted/deleted) — "
                        "head drift; the tick lane-tail leg cannot be evaluated and "
                        "freshness cannot be certified (regenerate with render_head)")
    for rel, ep in stamped.items():
        p = ws / rel
        try:
            st = p.stat()
        except FileNotFoundError:
            problems.append(f"stamped source missing from disk: {rel}")
            continue
        except OSError as e:
            problems.append(f"stamped source un-statable: {rel} ({type(e).__name__})")
            continue
        try:
            with open(p, "rb") as fh:   # fail CLOSED on unreadable, both grades
                fh.read(1)
        except OSError as e:
            problems.append(f"stamped source unreadable: {rel} ({type(e).__name__})")
            continue
        actual = int(st.st_mtime)
        if tick:
            if actual - ep > TICK_MAX_AGE_S:
                problems.append(f"{rel} lags render by {(actual - ep) // 3600}h (>24h)")
            elif actual < ep:
                problems.append(f"{rel} mtime regressed below the stamp ({actual} < {ep}) — "
                                f"backdated/restored source is never fresh")
        elif actual != ep:
            problems.append(f"{rel} changed after render (mtime {actual} != stamped {ep})")
    for rel, _p in derive_sources(ws):
        if rel not in stamped:
            problems.append(f"new source not in footer: {rel}")
    if tick:
        try:
            lanes = lane_entries(ws)
        except (OSError, UnicodeDecodeError) as e:
            problems.append(f"channel lane unreadable ({type(e).__name__}) — tail legs not evaluated")
        else:
            # F6: a blind lane makes the entries-behind arithmetic run over a
            # TRUNCATED sequence — the count is wrong with no parse error. Not
            # scoped by recipient here (unlike the emitter): by the time a head
            # exists, whatever it cites is already in scope, and a `behind`
            # number computed from a short lane is unsound whichever seat owns
            # it. Reported, never raised — check() grades an existing claim.
            for _n, _ln, _f in getattr(lanes, "blind_lanes", ()):
                problems.append(
                    f"channel/{_n} has an unclosed fence ({_f!r} opened line {_ln}) — "
                    f"every later entry heading is invisible, so any entries-behind "
                    f"count over that lane is UNDER-counted, not merely unverified")
            # Tick-scoping cure: lane-tail lines are read ONLY from the census-
            # recognized rendered ⚡ section(s) — a demoted #### body's stale
            # `- lane tail` history (which --adopt rightly preserves) must
            # never feed the entries-behind leg.
            zaps = [s for s in secs0 if s.title == RENDERED_ZAP_TITLE]
            tail_src = "\n".join(text[s.body_start:s.end] for s in zaps)
            for tm in LANE_TAIL_RE.finditer(tail_src):
                prefix, num = tm.group(1), int(tm.group(2))
                # D2 cure, verifier half: the family comes from the lane path
                # this record ALREADY carries (group 3) via the SAME
                # _lane_family() the emitter used. Without this the `behind`
                # arithmetic compares a per-family tail against a per-prefix
                # sequence — no parse error, just wrong math.
                fam = _lane_family(tm.group(3).rsplit("/", 1)[-1])
                # F7 — the verifier half of the SEAT scoping, and it is not
                # decoration. Without it a head that records another
                # recipient's family — D2 exactly, and what every pre-cure
                # head in the fleet contains — grades rc=0 GREEN: the id IS
                # the newest in the family it names, so `behind` is 0.
                # Consequence at landing: those heads are never asked to
                # re-render and the fleet does NOT self-heal. Measured, not
                # reasoned (LEG J): a builder head carrying
                # `ORCH-NNNN @ channel/<sender>_to_<recipient>_…` graded 0 until this.
                # Emitter and verifier are one grammar: lane_tails() REFUSES
                # to write a cross-family tail, so check() must refuse to
                # accept one.
                if _lane_recipient(fam) != norm_seat(role):
                    problems.append(
                        f"recorded lane tail {prefix}-{num} belongs to lane family "
                        f"{fam}, which is not addressed to {norm_seat(role)} — a head "
                        f"citing another recipient's traffic as its own tail is stale "
                        f"by construction (re-render)")
                    continue
                entries = lanes.get((fam, prefix))
                if not entries or num not in entries:
                    problems.append(
                        f"recorded lane tail {prefix}-{num} not found in lane family {fam}")
                    continue
                behind = len(entries) - 1 - entries.index(num)
                if behind > TICK_MAX_ENTRIES:
                    problems.append(
                        f"lane {fam}/{prefix} advanced {behind} entries past "
                        f"recorded tail {prefix}-{num} (>{TICK_MAX_ENTRIES})")
    if problems:
        print(("⚠ F8 STALE [tick] — " if tick else "⚠ F8 STALE — ") + "; ".join(problems))
        return RC_STALE
    print(f"F8 CURRENT — {len(stamped)} sources fresh ({'tick' if tick else 'strict'} mode).")
    return RC_OK


# ---------------------------------------------------------------------- main -
def main():
    ap = argparse.ArgumentParser(description="render_head v1")
    ap.add_argument("workspace")
    ap.add_argument("role")
    ap.add_argument("--now", help="ISO datetime override (testing); default: NOW.txt if present, else wall clock")
    ap.add_argument("--adopt", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--tick", action="store_true")
    args = ap.parse_args()
    ws = Path(args.workspace).resolve()
    try:
        if args.now:
            now = datetime.fromisoformat(args.now)
        # NOW.txt is an OPTIONAL workspace-level clock override: a file
        # `<workspace>/NOW.txt` holding a single ISO-8601 datetime WITH a UTC
        # offset. When present (and --now was not passed) it supplies "now"
        # for the whole run, so a workspace can be rendered or graded against
        # a pinned instant — tests, replays, and batch renders that must all
        # share one timestamp — without threading --now through every call.
        # Absent, the local wall clock is used. A naive value is refused
        # below with the same message as a naive --now.
        elif (ws / "NOW.txt").is_file():
            now = datetime.fromisoformat((ws / "NOW.txt").read_bytes().decode("utf-8").strip())
        else:
            now = datetime.now().astimezone()
        if now.tzinfo is None:
            raise SystemExit_(RC_ERROR,
                              "⛔ ERROR — naive --now/NOW.txt (no UTC offset): the footer <ISO> "
                              "grammar requires an offset (e.g. 2026-08-01T10:00-04:00)")
        if args.check:
            return check(ws, args.role, tick=args.tick)
        return render(ws, args.role, now, adopt=args.adopt)
    except SystemExit_ as e:
        print(e.msg)
        return e.code
    except AssertionError as e:
        print(f"⛔ ERROR — post-render invariant: {e}")
        return RC_ERROR
    except UnicodeDecodeError as e:
        print(f"⛔ ERROR — invalid UTF-8 ({e.reason} at byte {e.start}) in a source or role file")
        return RC_ERROR
    except _YAML_ERROR as e:
        print("⛔ ERROR — plan YAML failed to parse: " + str(e).splitlines()[0])
        return RC_ERROR
    except OSError as e:
        print(f"⛔ ERROR — I/O failure: {e}")
        return RC_ERROR
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        # AttributeError belt: wrong-shaped
        # ledger data reaching .get()/attribute access maps to the contract,
        # never a raw traceback (the top-level plan shape is also validated
        # with its own named message in load_open_plans).
        print(f"⛔ ERROR — {type(e).__name__}: {e}")
        return RC_ERROR


if __name__ == "__main__":
    sys.exit(main())
