#!/usr/bin/env python3
"""lane_id_check.py -- commissioned: 3-assertion id-space check over
lanes this seat writes.

Extractor grammars (grown by measured false-positives, not by design):
    ## ORCH → CREATOR — <PREFIX>-<n> [v2.7] · ...   (role-arrow long form)
    ## <PREFIX>-<n> · ...                     (anchored short form)
    ## <PREFIX>-<n>a — ...                    (letter-suffixed corrigendum)
`^## ` lines that are NEITHER role-arrow nor id-anchored are BODY headings
(sections inside entries) -- counted, never keyed. History: a one-grammar
extractor manufactured 5 false holes (short form, 2026-08-02 morning); the
`^## `=entry premise then manufactured 5 false DOUBLEs on the creator lane
family (an earlier review: prose id citations in section headers mis-keyed as entry
ids, suffixed corrigenda read as re-mints). Footer tokens like "next free:
<PREFIX>-<n+1>" are NOT headings (`^## ` gate) and are never read as the tail.

Assertions:
  (a) every id count == 1            -> report doubles
  (b) max - min + 1 == unique count  -> report each hole
  (c) tail id (last id-bearing heading in the last file) == max
                                     -> report phantom-tail

--known-hole <n> / --known-double <n> (repeatable) suppress documented
findings (e.g. a lane's documented hole and double).
Suppressed findings are printed as suppressed, not counted as failures.

Exit 0 clean (after suppressions), 1 with findings, 2 usage/no files.
"""

import argparse
import glob as globmod
import os
import re
import sys


def heading_position(line):
    """Portion of the heading line before the first middot or '['."""
    cut = len(line)
    for ch in ("·", "["):
        i = line.find(ch)
        if i != -1 and i < cut:
            cut = i
    return line[:cut]


# Entry-boundary premise (from an earlier review): `^## ` alone is NOT an entry -- older
# lanes use `## ` for section headers INSIDE entries, and a prose id citation
# there mis-keys as the entry's id (a silent MIS-KEY no ledger can catch,
# because nothing went unparsed). An ENTRY heading is only:
#   (1) role-arrow form: `## <CAPS ROLE> → <CAPS ROLE> ...` (id searched in
#       heading position; id-less ones -- broadcasts, commissions -- go to
#       the unkeyed ledger). The addressee token is OPTIONAL by construction
#       (only the pre-arrow roles are required), which is what keyed the
#       sixth heading form `## CREATOR -> <PREFIX>-<n> [v2.6] ...` -- a real signed
#       v2.6 entry, arrow straight to the id -- that a stricter grammar
#       ledgered instead (a later review; the one-heading 690/688 vs 689/687
#       census discrepancy).
#   (2) anchored short form: `## <PREFIX>-<n>[a-z]? ...` (the
#       id is anchored at heading start, never search()ed, so a citation
#       later in the line can never be read as the entry's id).
# Every other `## ` line is a BODY heading -- counted, never keyed.
ROLE_ARROW = re.compile(r"^## [A-Z0-9_]+(?: [A-Z0-9_]+)* (?:→|->) ")

# Fence opener/closer, CommonMark-aligned: a fence may be
# indented 0-3 spaces and still be a fence; at 4+ spaces it is an indented
# code block, NOT a fence, and treating it as one flips the state and skips
# REAL headings after it -- the deflation direction E800 §3 showed collides
# instead of skipping once next-id derivation rides this parser. The
# column-0-only predicate this replaces agreed with creator's lstrip()
# grammar on all 39 of today's fenced specimens ONLY because no indented
# fence exists in them yet -- untested, not absent. Mixed ```/~~~ toggling
# one shared state stays a deliberate approximation (both instruments share
# it; a mismatched-marker close is malformed input, caught as UNCLOSED).
FENCE = re.compile(r"^ {0,3}(?:```|~~~)")

# Recipient of an entry heading, for the BROADCAST carve-out (an orchestrator
# ruling): `-> ALL` is byte-identical in every recipient's lane BY DESIGN
# (a real broadcast is the measured specimen), so its repeats are one logical
# entry, not a collision.
RECIPIENT = re.compile(r"^## [A-Z0-9_]+(?: [A-Z0-9_]+)* (?:→|->) ([A-Z0-9_]+)")


def full_token(text, start, prefix, sep):
    """The WHOLE id token beginning at `start` -- `<PREFIX>-<n>-tick`, not `<PREFIX>-<n>`.

    The claim assert compares tokens by EXACT EQUALITY rather than by
    substring match, which is what gives it id-space prefix immunity
    (per an orchestrator ruling) without touching the shared extractor's `id_pat`.

    Why not a lookahead on id_pat instead (the obvious fix, measured and
    REJECTED 2026-08-05): `-[a-z]+` is ambiguous in this corpus. It is a
    distinct id in `<PREFIX>-<n>-owner` (a real entry-position id, the v2.6
    middot form at a line of an orch-to-owner lane) but ordinary prose
    hyphenation in `E899-as`, `E63-gate`, `<PREFIX>-<n>-era` -- all of which are
    citations OF `E899`/`E63`/`<PREFIX>-<n>`. A blanket lookahead would stop
    those from matching at all, converting a narrow false-POSITIVE into a
    broad false-NEGATIVE across every lane; and dropping the tick ids from
    id_pat would hide their numbers from --next-id's deflation guard, the
    exact collision that guard exists to refuse. Exact-token comparison
    needs neither change: it is local to the claim, so doubles/holes/
    next-id keep byte-identical behaviour.

    SUFFIX CLASS WIDENED (2026-08-05, from an orchestrator review). It was
    `-[a-z]+`, which cannot read `<PREFIX>-<n>-A` -- so the token truncated to
    `<PREFIX>-<n>` and the two symptoms were opposite: the audit binned the pair
    as one id (false DOUBLE), while the claim found no site for the FULL
    string and certified it FREE. Measured with a negative control: claiming
    `<PREFIX>-<n>-A` (which EXISTS in the fixture) and `<PREFIX>-<n>-Z` (which does NOT)
    returned byte-identical `CLAIM OK ... rc 0`. The path was never
    respecting the suffix; it was BLIND to it [[unknown-is-not-unparseable]].

    The widening does NOT reopen the ambiguity argued above. That argument
    is about a LOOKAHEAD on the shared `id_pat`, which runs over PROSE where
    `E899-as` / `<PREFIX>-<n>-era` are citations. `full_token` runs only at ENTRY
    POSITION, where a heading is an id and not a sentence, so admitting
    uppercase and digits adds forms (`-A`, `-R2`) without touching how any
    prose citation is read.
    """
    m = re.compile(
        re.escape(prefix) + re.escape(sep) + r"\d+[a-z]?(?:-[A-Za-z0-9]+)?"
    ).match(text, start)
    return m.group(0) if m else None


def extract_ids(files, prefix, sep="-"):
    """([(file, lineno, (num, suffix), title)], unkeyed, body_count, ...).

    unkeyed is the UNKEYED-HEADING LEDGER: every ENTRY heading
    (role-arrow form) yielding no id. Reported, NEVER fatal -- silent
    skipping is what manufactured the 5 false holes, but a fatal version
    would block on legitimately id-less entries (the ALL-SEATS broadcast is
    the measured false-positive). The author rules each ledger line as
    missed-grammar or legitimately-id-less.

    Ids are (number, suffix) pairs: `<PREFIX>-<n>a` is its own id,
    a corrigendum, not a second `<PREFIX>-<n>`. title is the heading text after
    the id, kept for the duplicate-class discriminator.

    sep is the prefix/number separator -- "-" for hyphenated lanes,
    "" for the owner lane's hyphenless E799 form (E801 §2: with the hyphen
    hard-coded, every owner heading was id-less to this grammar and the
    tool refused the whole lane -- safe direction, wrong coverage). The
    (?<![0-9A-Za-z]) guard keeps a bare prefix from matching inside a
    longer token (TORCH-5 / PHASE2).
    """
    # suffix limited to one letter; lookahead stops `<PREFIX>-<n>abc` half-matching
    id_body = re.escape(prefix) + re.escape(sep) + r"(\d+)([a-z]?)(?![0-9A-Za-z])"
    id_pat = re.compile(r"(?<![0-9A-Za-z])" + id_body)
    # ⛔⛔ THE REPEAT IS NOT COSMETIC TOLERANCE -- IT IS THE CURE FOR A
    #   FALSE-HOLE CLASS THIS FILE EXISTS TO PREVENT. A heading
    #   spelled `## ORCH-ORCH-<n>` (a body template `## ORCH-{{ID}}` filled with
    #   an already-prefixed id) matches NEITHER `short_pat` -- `^## ORCH-` then
    #   `\d+` meets a letter -- NOR `ROLE_ARROW`, so it fell through to
    #   `body_count` and vanished. Measured on the live corpus BEFORE this line
    #   was written: 72 such headings across `channel/orch_to_*.md`, and 67 of
    #   their ids were reported as HOLES that are in fact published. That is
    #   exactly the earlier false-hole defect -- a specimen set one grammar short
    #   -- in a new spelling. [[fixture-derived-from-the-subject-is-mutation-blind]]
    #
    # ⭐ THE REPEAT CANNOT WIDEN ANYTHING ELSE. It is anchored at `^## ` and
    #   every repetition must be this prefix's OWN `<prefix><sep>` token, so the
    #   only strings it newly admits are headings that open with this prefix
    #   spelled two or more times -- which is the defect, and nothing else. A
    #   citation cannot reach it (anchored), and a different prefix cannot
    #   (literal). Non-capturing, so `id_body`'s groups 1/2 keep their numbers;
    #   the id token's start is recovered from `m.start(1)` instead.
    #
    # ⚠ IT COUNTS THE ID *AND* NAMES THE SPELLING (see `doubled` below).
    #   Silently absorbing it would trade a false hole for an invisible defect,
    #   and the landed headings are NOT rewritable (orch ruled: do not rewrite
    #   any landed heading), so the finding is a non-fatal ledger line -- a
    #   counted finding would leave this audit permanently red with the only
    #   cure forbidden. New ones are stopped at the writer, in append_co.py.
    #   [[advisory-line-naming-an-absence-is-the-gate-firing]]
    short_pat = re.compile(
        r"^## (?:" + re.escape(prefix) + re.escape(sep) + r")*" + id_body)
    out = []
    unkeyed = []
    doubled = []
    # (fp, lineno, FULL token, title, recipient-or-None) at every
    # ENTRY-POSITION match site -- built in THIS loop, off THESE matches, so
    # the claim assert and the audit share ONE grammar rather than a second
    # counter drifting beside the first [[emitter-and-verifier-are-one-grammar]].
    entry_tokens = []
    body_count = 0
    fenced_skipped = 0
    fenced_prefix_hits = []
    unkeyed_prefix_hits = []
    for fp in files:
        in_fence = False
        with open(fp, "r", encoding="utf-8", errors="replace") as f:
            for lineno, line in enumerate(f, 1):
                # Fence state FIRST (E794): a heading QUOTED inside a
                # triple-backtick fence is evidence someone DISCUSSED an id,
                # not a definition of one -- and the quoting happens mostly
                # in id-adjudication entries, so a fence-blind auditor's
                # false-positive rate rises with its own use. Skips are
                # COUNTED, never silent (a silent skip trades a false
                # positive for an invisible omission).
                if FENCE.match(line):
                    in_fence = not in_fence
                    continue
                if not line.startswith("## "):
                    continue
                if in_fence:
                    fenced_skipped += 1
                    # E800 §5: a fenced heading carrying THIS prefix's id is
                    # the one skip class that can DEFLATE max -- recorded so
                    # --next-id can refuse rather than derive low and collide.
                    fm = id_pat.search(line)
                    if fm:
                        fenced_prefix_hits.append(
                            (fp, lineno, (int(fm.group(1)), fm.group(2))))
                    continue
                text = line.rstrip()
                rm = RECIPIENT.match(text)
                rcpt = rm.group(1) if rm else None
                m = short_pat.match(text)
                if m:
                    # The id token starts `len(prefix)+len(sep)` before the
                    # digits -- DERIVED, never the literal 3 this line used to
                    # pass, which was true only while the repeat was empty.
                    id_start = m.start(1) - len(prefix) - len(sep)
                    if id_start != 3:
                        doubled.append((fp, lineno, text[:120],
                                        (int(m.group(1)), m.group(2))))
                    out.append((fp, lineno, (int(m.group(1)), m.group(2)),
                                text[m.end():]))
                    entry_tokens.append((fp, lineno,
                                         full_token(text, id_start, prefix, sep),
                                         text[m.end():], rcpt))
                    continue
                if ROLE_ARROW.match(text):
                    m = id_pat.search(heading_position(text))
                    if m:
                        out.append((fp, lineno,
                                    (int(m.group(1)), m.group(2)),
                                    text[m.end():]))
                        entry_tokens.append(
                            (fp, lineno,
                             full_token(text, m.start(), prefix, sep),
                             text[m.end():], rcpt))
                    else:
                        # E801 §3: the parser's own grammar is a third
                        # container. The v2.6 seventh form puts the
                        # separator middot BEFORE the id (`## ORCH → OWNER
                        # · ORCH-<n> [v2.6] — …`), so heading_position()
                        # cuts the id out of the window and a real signed
                        # entry lands in the ledger with its own id
                        # invisible. Discriminator (owner-built, E801 §5):
                        # the id is in ENTRY POSITION iff it appears in the
                        # post-arrow segment BEFORE the first `[` -- a
                        # citation (`… [v2.6] - CORRECTION to ORCH-<n>`)
                        # sits after the bracket and must NOT fire, or
                        # every correction fails the wake shut.
                        # Segment = post-arrow text up to the first `[` or
                        # em-dash (the address block); and the text between
                        # the arrow and the id must be address-shaped (no
                        # lowercase prose), or `## A → B · ack ORCH-<n> …`
                        # style title citations fire. First cut of this
                        # discriminator cut only at `[` and marked 51 lines
                        # against owner's measured 12 -- bracketless
                        # headings degraded it to anywhere-in-line, the
                        # exact shape E801 §5 warned against.
                        am = ROLE_ARROW.match(text)
                        seg = text[am.end():]
                        for stop in ("[", "—"):
                            cut = seg.find(stop)
                            if cut != -1:
                                seg = seg[:cut]
                        pm = id_pat.search(seg)
                        if pm and re.search(r"[a-z]", seg[:pm.start()]):
                            pm = None
                        if pm:
                            unkeyed_prefix_hits.append(
                                (fp, lineno,
                                 (int(pm.group(1)), pm.group(2))))
                            # These ARE entries -- their id sits in entry
                            # position, the main grammar just cut it out
                            # (v2.6 middot form, E801 §3). Omitting them
                            # from the claim would read a TAKEN id as FREE:
                            # the one direction that MINTS a collision
                            # rather than merely blocking a free id.
                            entry_tokens.append(
                                (fp, lineno,
                                 full_token(text, am.end() + pm.start(),
                                            prefix, sep),
                                 text[am.end() + pm.end():], rcpt))
                        unkeyed.append((fp, lineno, text[:100],
                                        bool(pm)))
                    continue
                body_count += 1
        if in_fence:
            raise UnclosedFenceError(
                "%s ends INSIDE a code fence -- every heading after the "
                "tear is misclassified; refusing to report" % fp)
    return (out, unkeyed, body_count, fenced_skipped, fenced_prefix_hits,
            unkeyed_prefix_hits, entry_tokens, doubled)


class UnclosedFenceError(Exception):
    """A file ended inside a code fence -- the parser's world-model is torn
    and every heading after the tear is misclassified. Loud, never silent
    (ported from channel_id_collision_scan.py, the sibling that got this
    cure at 10:12:36 the same day this instrument was authored WITHOUT it
    -- owner E794: a fresh authoring never inherits, it has no parent to
    re-sync from)."""


def norm_title(t):
    """ASCII-alnum-only casefold: mojibake re-encodes of the same title
    (`Â·` vs `·`) normalise equal, so a re-APPEND (duplicate content) is
    separable from a re-MINT (one id spent on two distinct units) --
    merging them tells a reader to fix an id space when the
    actual defect was an encoding."""
    return "".join(c for c in t.lower() if c.isascii() and c.isalnum())


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--lane-glob", action="append", required=True,
                   help="glob for lane files (repeatable)")
    p.add_argument("--prefix", required=True, help="id prefix, e.g. OC or ORCH")
    p.add_argument("--sep", default="-",
                   help="prefix/number separator (default '-'; pass '' for "
                        "hyphenless lanes like owner's E799 form -- E801 §2)")
    p.add_argument("--known-hole", action="append", type=int, default=[],
                   help="documented hole id to suppress (repeatable)")
    p.add_argument("--known-double", action="append", type=int, default=[],
                   help="documented double id to suppress (repeatable)")
    p.add_argument("--covers", action="append", default=[],
                   help="glob defining the seat's FULL lane-file universe "
                        "(repeatable). Any file matching --covers that the "
                        "--lane-glob set did not scan is a COVERAGE finding "
                        "(an earlier fleet review: the generative defect behind false holes "
                        "was a specimen set one file short, not a regex -- "
                        "only this assertion proves the check looked where "
                        "the ids live).")
    p.add_argument("--next-id", action="store_true",
                   help="derive the next free id (max number + 1) for wake "
                        "dispatch. E800 §3: this promotes the tool from "
                        "auditor to collision-avoidance, where UNDER-report "
                        "collides instead of skipping -- so derivation FAILS "
                        "CLOSED (rc=2, no NEXT-ID line) on either deflation "
                        "hazard: a fenced heading carrying this prefix's own "
                        "id in the scanned set, or a --covers file the scan "
                        "missed. Partitioned on prefix, not on "
                        "fenced_skipped>0 (E800 §5): another seat's quoted id "
                        "is inert and must stay inert.")
    p.add_argument("--claim-id",
                   help="the SPECIFIC id about to be used, e.g. <PREFIX>-<n>. "
                        "Asserts it occupies exactly --claim-count entry "
                        "positions across the scanned lanes (a fleet ruling). "
                        "Complements --next-id, which only derives max+1 and "
                        "never checks that the derived id is actually free -- "
                        "and a seat resuming, filling a documented hole, or "
                        "hand-picking an id never goes through max+1 at all. "
                        "Compares WHOLE tokens: <PREFIX>-<n> does not match inside "
                        "<PREFIX>-<n>-tick. Forward-looking only -- it rules on the "
                        "id you pass, never on the lanes' existing doubles.")
    p.add_argument("--claim-count", type=int, default=0,
                   help="expected entry-position occurrences of --claim-id: "
                        "0 (default) = PRE-MINT, the id must be free; 1 = "
                        "POST-WRITE, the entry you just appended must be "
                        "there exactly once.")
    p.add_argument("--virgin-prefix", action="store_true",
                   help="assert DELIBERATELY that this prefix has no entries "
                        "yet, permitting a claim over an id space the scan "
                        "found no evidence for. Without it that state is "
                        "REFUSED (rc 2), because an unreadable space and an "
                        "unused one look identical from here and only one of "
                        "them makes a FREE verdict provable.")
    args = p.parse_args(argv)

    # Windows consoles default to cp1252; lane headings carry arrows and
    # middots. A ledger that crashes printing its subject is worse than the
    # silent skip it replaces -- degrade characters, never the run.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    files = []
    for g in args.lane_glob:
        files.extend(globmod.glob(g))
    files = sorted(dict.fromkeys(os.path.normpath(f) for f in files))
    if not files:
        sys.stderr.write("no files match the given globs\n")
        return 2

    def fid(num, suffix=""):
        return "%s%s%d%s" % (args.prefix, args.sep, num, suffix)

    try:
        (ids, unkeyed, body_count, fenced_skipped, fenced_prefix_hits,
         unkeyed_prefix_hits, entry_tokens, doubled) = extract_ids(
            files, args.prefix, args.sep)
    except UnclosedFenceError as e:
        sys.stderr.write("UNCLOSED FENCE: %s\n" % e)
        return 2
    # An empty id space is FATAL to the audit (it has nothing to audit) but
    # LEGITIMATE for a claim -- claiming the first id in a fresh lane, or a
    # lane whose entries are all the v2.6 middot form (their ids are cut out
    # by heading_position(), so `ids` is empty while entry_tokens is not).
    # Answering "is this id free?" with "no headings found" is the refusal
    # shape a gate must not take when the honest answer is available
    # [[gate-must-admit-the-honest-answer]].
    if not ids and not args.claim_id:
        sys.stderr.write("no %s%s<n> entry headings found in %d file(s)\n"
                         % (args.prefix, args.sep, len(files)))
        return 2

    # Entry-position id key, shared by the summary count and the doubles leg
    # so the header can never contradict the findings under it. Hoisted here
    # for that reason: when only the doubles leg was re-keyed,
    # the summary still said "unique ids: 2" over a set the findings treated
    # as 3 [[corroborating-figures-must-share-the-artifact]].
    def split_token(tok):
        m = re.match(re.escape(args.prefix) + re.escape(args.sep)
                     + r"(\d+)(.*)$", tok)
        return (int(m.group(1)), m.group(2)) if m else None

    key_at = {}
    for _fp, _ln, _tok, _ti, _rc in entry_tokens:
        if _tok:
            _k = split_token(_tok)
            if _k is not None:
                key_at[(_fp, _ln)] = _k

    def eff_key(f, ln, k):
        return key_at.get((f, ln), k)

    print("files (%d, filename order): %s" % (len(files), ", ".join(files)))
    for fp, ln, text, own_id in unkeyed:
        print("UNKEYED HEADING (ledger, non-fatal%s): %s:%d %s"
              % ("; OWN-PREFIX ID IN ENTRY POSITION -- seventh-form "
                 "candidate, invisible to the number line" if own_id else "",
                 fp, ln, text))
    # ⛔ NAMED, NOT ABSORBED. These ids ARE counted above (that is what stops
    #   the false holes); the line exists so the reader learns the spelling is
    #   wrong rather than inheriting a quietly-widened grammar.
    for fp, ln, text, k in doubled:
        print("DOUBLED-PREFIX HEADING (ledger, non-fatal): %s:%d %s%s%d is "
              "spelled with the prefix twice -- counted as an entry here, but "
              "invisible to any anchored `^## %s%s<digits>` reader: %s"
              % (fp, ln, args.prefix, args.sep, k[0], args.prefix, args.sep,
                 text))
    nums = sorted({k[0] for _, _, k, _ in ids})
    if ids:
        print("entry headings with %s ids: %d ; unique ids: %d (%d numbers, "
              "range %d..%d) ; unkeyed entries: %d ; body headings skipped: "
              "%d ; fenced_skipped: %d"
              % (args.prefix, len(ids),
                 len({eff_key(f, ln, k) for f, ln, k, _ in ids}),
                 len(nums), nums[0], nums[-1], len(unkeyed), body_count,
                 fenced_skipped))
    else:
        print("no %s%s<n> KEYED entry headings; %d entry-position token(s) "
              "seen -- claim only, audit legs skipped"
              % (args.prefix, args.sep, len(entry_tokens)))

    findings = []
    suppressed = []

    # (d) file coverage: the union asserted, not assumed
    missed = []
    if args.covers:
        universe = set()
        for g in args.covers:
            universe.update(os.path.normpath(f) for f in globmod.glob(g))
        missed = sorted(universe - set(files))
        for fp in missed:
            findings.append(
                "COVERAGE: %s matches --covers but was NOT scanned -- ids "
                "living there would read as holes" % fp)

    # (e) next-id derivation, fail-closed in the deflation direction only
    # (E800 §3-§5, E801 §3-§5). Doubles/holes/phantom-tail cannot lower
    # max, so audit findings do not block derivation. Three hazards CAN:
    # a fenced own-prefix heading, an unkeyed heading carrying its own id
    # in entry position (the seventh-form class), and an unscanned lane
    # file. The first two are VISIBLE TOKENS, so they refuse only when the
    # invisible id EXCEEDS the visible max -- an id at-or-below max cannot
    # move a max+1 derivation, and unconditional refusal would fail the
    # ORCH wake shut on 12 standing v2.6 headings forever (the
    # unusable-guard shape; same principle as h5's honest-answer arm).
    # Owner's E801 §3 applied this exact condition before reporting
    # zero-harm (268 < 1510). The unscanned file stays UNCONDITIONAL: its
    # population is unbounded, so no max comparison exists.
    if args.next_id and not ids:
        sys.stderr.write("NEXT-ID REFUSED (deflation hazard -- a low "
                         "derivation COLLIDES with a published entry): no "
                         "keyed id in the scanned set, so max is unknown\n")
        return 2
    if args.next_id:
        vis_max = nums[-1]
        refuse = []
        for fp, ln, k in fenced_prefix_hits:
            if k[0] > vis_max:
                refuse.append("fenced %s at %s:%d exceeds visible max %s" % (
                    fid(k[0], k[1]), fp, ln, fid(vis_max)))
        for fp, ln, k in unkeyed_prefix_hits:
            if k[0] > vis_max:
                refuse.append(
                    "unkeyed entry-position %s at %s:%d exceeds visible "
                    "max %s" % (fid(k[0], k[1]), fp, ln, fid(vis_max)))
        for fp in missed:
            refuse.append("unscanned lane file %s (population unbounded)"
                          % fp)
        if refuse:
            sys.stderr.write(
                "NEXT-ID REFUSED (deflation hazard -- a low derivation "
                "COLLIDES with a published entry): %s\n" % "; ".join(refuse))
            return 2
        print("NEXT-ID: %s (max %s over %d file(s); derivation is "
              "max+1, so audit findings below do not move it)"
              % (fid(vis_max + 1), fid(vis_max), len(files)))

    # (f) claim: is the id I am ABOUT TO USE free?
    # Returns rc 3, distinct from rc 1 -- "the id you asked for is taken"
    # demands a different action than "these lanes carry old doubles", and
    # a shared code would make the live historical duplicates
    # mask every claim verdict. Forward-only: it rules on --claim-id, never
    # on the lanes' standing collisions (their disposition is the principal's).
    if args.claim_id:
        # Fail CLOSED on an incomplete scan. "0 occurrences" is evidence of
        # FREE only if the search covered the whole universe; from a short
        # file set it is evidence of nothing, and acting on it MINTS the
        # collision this assert exists to prevent [[coverage-controls-vs-correctness-controls]].
        if missed:
            sys.stderr.write(
                "CLAIM REFUSED (%s): --covers names %d file(s) the scan did "
                "not read (%s) -- a FREE verdict is unprovable over an "
                "incomplete universe\n"
                % (args.claim_id, len(missed), ", ".join(missed)))
            return 2
        # The second leg. An UNREADABLE id space is not an EMPTY one, and
        # only one of those makes a FREE verdict provable. With no keyed id
        # AND no entry-position token, the scan has no evidence the space
        # exists: either the prefix is virgin (free is right) or the grammar
        # cannot see a populated space (free MINTS the collision). This tool
        # cannot tell those apart, so it must not answer -- `--next-id`
        # already refuses on exactly this state (the deflation guard below),
        # and the claim path certifying rc 0 instead is the more dangerous
        # half of the same hole [[lookup-failure-needs-own-outcome]].
        #
        # MEASURED, not hypothesised: `--prefix ENTRY --claim-id ENTRY-<n>`
        # printed the `## ... ENTRY <n> ...` heading as an UNKEYED ledger
        # line and then certified <n> free, because the lane writes the
        # space form and the keyed grammar reads only the hyphen form.
        #
        # `own_id` is NOT the discriminator here and using it would miss this
        # case: that flag asks whether the ENTRY-POSITION prefix is ours, and
        # in `## BUILDER -> OWNER - ENTRY <n>` the entry-position prefix is
        # BUILDER. Absence of evidence is the signal; the heading text is not.
        # Owner sharpened this leg: a bare "the keyed population
        # is non-zero" test still passes a space that is 2 keyed against 300
        # unkeyed. They proposed a RATIO; a ratio is a threshold on a
        # population, and a threshold is a hint, not a gate
        # [[imprecise-rule-is-a-hint-not-a-gate]] -- owner's own honest run
        # sat at 177/310, so any threshold strict enough to catch 2/300 would
        # have to be tuned against live data it would then also refuse.
        #
        # The decidable question is not how much of the space is readable but
        # whether THIS id could be hiding in the unreadable part, and that is
        # answerable per-claim with no threshold: a heading that carries OUR
        # prefix in ENTRY POSITION but did not parse as a keyed id is exactly
        # a place one of our ids can sit unseen. Measured before shipping --
        # 0 such headings over the live OB space, so this does not over-refuse
        # owner's accepted claim in that space.
        # ⛔ CORRECTED (2026-08-09; an orchestrator tick: seven days of rc=2 on the CO
        # lane, 19 collisions of the exact class this gate exists to prevent
        # landing behind it). The 4th field of an `unkeyed` row is `bool(pm)` --
        # TRUE means the SEVENTH-FORM PATH RECOVERED THE ID and appended it to
        # `entry_tokens` (see the recovery block above, which says in its own
        # comment "These ARE entries"). So `if own` selected exactly the
        # headings the reader CAN read, and refused on them.
        #
        # That is a stale guard, not a wrong idea: this refusal was written when
        # a seventh-form heading really was unreadable, and the recovery path
        # added later DISSOLVED the condition without retiring the check
        # [[prescribed-cure-may-already-be-in-place]]. The safety property is
        # untouched by this fix -- a recovered id is in `entry_tokens`, so a
        # claim against it still returns TAKEN. What changes is only that we no
        # longer refuse a verdict we are able to give.
        #
        # The genuine blind class survives and is what we now key on: our prefix
        # appears in the heading, but NEITHER the keyed grammar NOR the
        # seventh-form path could turn it into an id. That is a place one of our
        # ids can sit unseen, and it is the case the original comment describes.
        # ⚠ Bound, stated: `text` is truncated to 100 chars upstream, so a
        # prefix occurring past column 100 is not seen by this test.
        _pfx = re.compile(r"(?<![0-9A-Za-z])" + re.escape(args.prefix))
        _blind = [(fp, ln, text) for fp, ln, text, own in unkeyed
                  if (not own) and _pfx.search(text)]
        if _blind:
            sys.stderr.write(
                "CLAIM REFUSED (%s): %d entry-position heading(s) carry the "
                "%s prefix but did not parse as a keyed id, so this id could "
                "already exist in a form the reader cannot see -- e.g. %s. "
                "A FREE verdict is unprovable while any of them is "
                "unreadable.\n"
                % (args.claim_id, len(_blind), args.prefix,
                   "; ".join("%s:%d" % (f, l) for f, l, _ in _blind[:3])))
            return 2
        if not ids and not entry_tokens and not args.virgin_prefix:
            sys.stderr.write(
                "CLAIM REFUSED (%s): no %s%s<n> keyed id and no entry-position "
                "token in %d file(s) -- so this scan cannot distinguish a "
                "VIRGIN prefix from an id space its grammar cannot read, and "
                "only the first makes a FREE verdict provable. If the prefix "
                "really is unused, say so deliberately with --virgin-prefix.\n"
                % (args.claim_id, args.prefix, args.sep, len(files)))
            return 2
        sites = [t for t in entry_tokens if t[2] == args.claim_id]
        bcast = [t for t in sites if t[4] == "ALL"]
        other = [t for t in sites if t[4] != "ALL"]
        # Broadcast carve-out: one `-> ALL` entry is
        # mirrored into every recipient lane BY DESIGN, so its byte-equal
        # repeats are ONE logical occurrence. Equal normalised titles are
        # what make them the same entry rather than a re-mint that merely
        # happens to be addressed to ALL.
        collapsed = 0
        if bcast:
            collapsed = 1 if len({norm_title(t[3]) for t in bcast}) == 1 \
                else len(bcast)
        n = len(other) + collapsed
        for fp, ln, tok, _, rcpt in sites:
            print("  claim site: %s at %s:%d (recipient %s)"
                  % (tok, fp, ln, rcpt or "n/a"))
        if bcast and collapsed == 1:
            print("  broadcast carve-out: %d `-> ALL` mirrors of one entry "
                  "counted once" % len(bcast))
        if n != args.claim_count:
            print("CLAIM VIOLATION: %s occupies %d entry position(s) over "
                  "%d file(s); expected %d (%s)"
                  % (args.claim_id, n, len(files), args.claim_count,
                     "pre-mint: the id must be free"
                     if args.claim_count == 0
                     else "post-write: expected exactly %d"
                          % args.claim_count))
            return 3
        print("CLAIM OK: %s occupies %d entry position(s) over %d file(s), "
              "as expected" % (args.claim_id, n, len(files)))
        if not ids:
            return 0

    # (a) doubles -- keyed on the FULL (number, suffix) id; classed by title
    # (per an earlier review): all-equal normalised titles = DUPLICATE-CONTENT
    # (re-append, likely encoding), distinct titles = RE-MINT (id spent on
    # two different units). Suppression stays by NUMBER.
    #
    # RE-KEYED (2026-08-05, from an orchestrator review). The key was the
    # `(number, suffix)` pair produced by the shared `id_pat`, whose suffix is
    # a single lowercase letter -- so `<PREFIX>-<n>-A` keyed as `<PREFIX>-<n>` and the
    # pair reported a FALSE DOUBLE [RE-MINT]. The doubles leg is computed over
    # ENTRY POSITIONS only, which is exactly where `full_token` is safe (a
    # heading is an id, not a sentence), so the key now takes its suffix from
    # the entry-position token and falls back to the id_pat key wherever no
    # token was captured.
    #
    # `id_pat` is DELIBERATELY UNTOUCHED. It runs over PROSE, where `-[a-z]+`
    # is genuinely ambiguous (`E899-as`, `<PREFIX>-<n>-era` are citations OF those
    # ids), so widening it would trade a narrow false-POSITIVE here for a
    # broad false-NEGATIVE everywhere. Holes and --next-id therefore keep
    # byte-identical behaviour; only the doubles key moves.
    occ = {}
    for f, ln, k, title in ids:
        occ.setdefault(eff_key(f, ln, k), []).append((f, ln, title))
    for k in sorted(kk for kk, v in occ.items() if len(v) > 1):
        sites = occ[k]
        titles = {norm_title(t) for _, _, t in sites}
        klass = ("DUPLICATE-CONTENT (same title %dx -- re-append, "
                 "not an id-space defect)" % len(sites)
                 if len(titles) == 1 else "RE-MINT (distinct titles)")
        msg = "DOUBLE [%s]: %s appears %d times at %s" % (
            klass, fid(k[0], k[1]), len(sites),
            ", ".join("%s:%d" % (f, ln) for f, ln, _ in sites))
        (suppressed if k[0] in args.known_double else findings).append(msg)

    # (b) holes -- over the NUMBER line only (a suffixed corrigendum shares
    # its number with its parent and neither creates nor fills a hole)
    lo, hi = nums[0], nums[-1]
    if hi - lo + 1 != len(nums):
        present = set(nums)
        for i in range(lo, hi + 1):
            if i not in present:
                msg = "HOLE: %s missing (range %d..%d)" % (fid(i), lo, hi)
                (suppressed if i in args.known_hole else findings).append(msg)

    # (c) phantom-tail: last entry heading in the LAST file must carry max
    tail_file, tail_line, tail_key, _ = ids[-1]
    if tail_key[0] != hi:
        findings.append(
            "PHANTOM-TAIL: last heading id %s (%s:%d) != max %s "
            "-- the max id is not the lane tail"
            % (fid(tail_key[0], tail_key[1]), tail_file, tail_line,
               fid(hi)))

    for msg in suppressed:
        print("suppressed (documented): %s" % msg)
    if findings:
        for msg in findings:
            print(msg)
        print("RESULT: %d finding(s)" % len(findings))
        # In CLAIM mode the exit code answers the question the caller
        # ASKED -- "is this id free?" -- and the audit's findings are
        # printed but advisory. Otherwise the three LIVE duplicates
        # (three historical doubles) would return rc 1 on every CO claim
        # forever, so a caller gating on rc would refuse a perfectly free
        # id for an unrelated historical reason, and the only way to read
        # the real answer would be to parse stdout. Their disposition is
        # The principal's, and a forward-only assert must not be blocked on it.
        if args.claim_id:
            print("RESULT NOTE: rc reports the CLAIM (0 free/as-expected, "
                  "3 violation, 2 refused); the %d audit finding(s) above "
                  "are advisory in claim mode" % len(findings))
            return 0
        return 1
    print("RESULT: CLEAN (3/3 assertions hold%s)"
          % ("; %d documented finding(s) suppressed" % len(suppressed)
             if suppressed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
