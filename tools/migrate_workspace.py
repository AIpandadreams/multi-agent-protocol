#!/usr/bin/env python3
"""Migrate a stamped v2.6 workspace up to PROTOCOL v2.7 [PROTOCOL v2.7].

The version-migrate gap in the lifecycle family: `new_project.py` stamps a
FRESH workspace, `scale_workspace.py` grows a 2-agent workspace to 3, and
`adopt_project.py` adopts an ad-hoc collaboration — but nothing carries a LIVE
stamped workspace across a protocol-version bump. This tool does, for the one
supported hop v2.6 -> v2.7. (An earlier hop — v2.5 -> v2.6 — is served by the
checkout that carried it; a v2.5 workspace migrates in two steps, oldest hop
first.)

It follows `scale_workspace.py`'s contract exactly, because the same design line
applies: a tool may mutate a workspace's STRUCTURE mechanically, but the
principal-owned and agent-owned surfaces are NEVER rewritten by an installer.

WHAT IT DOES (mechanical, idempotent, reversible):
  - rewrites the workspace's PROTOCOL_VERSION binding row v2.6 -> v2.7
    STRUCTURALLY (matched by slot name, any inner spacing) so version detection
    and the rewrite can never disagree — it flips ONLY the version cell and
    preserves the row's spacing and any extra cells, dropping nothing
  - flips a `[PROTOCOL v2.6]` stamp -> `[PROTOCOL v2.7]` ONLY on a file's BANNER
    line — its title heading or docstring banner: the first content line, or
    the second when the first is a shebang (BINDINGS header, TASKQUEUE,
    START_SESSION files, the stamped validator copy). That banner is the SOLE
    place new_project.py emits a stamp.
  - EXCEPT append-only records: `memory/<role>/auth-log.md`,
    `memory/<role>/dispatch-log.md`, `memory/<role>/tick-log.md`, and
    `channel/*.md` are NEVER touched — their banner keeps the stamp of the
    version they were CREATED under. A record's banner is part of the record;
    rewriting it would remove a line from an append-only file and either trip
    the workspace's own integrity gates (auth-logs / channel — the v2.5->v2.6
    hop did exactly that and ate a red CI run) or race a live appender
    (dispatch/tick logs are written by scheduled tasks). conformance_check
    accepts a supported creation-version stamp on these files, so keeping the
    old banner is green, not a finding. EVERY kept record is REPORTED —
    including those carrying no old-version token — so the skip is exhaustive
    and auditable, never silent.
  - preserves each file's existing line endings exactly (no CRLF<->LF rewrite)

  Because the flip is confined to the banner line, the same literal token
  appearing anywhere else — inside a PROXY_AUTH/authority row, a memory-body
  heading or prose (e.g. an emitted packet's provenance line), or a fenced
  example of a stamp — is LEFT UNTOUCHED (a bare "v2.6" that is real content is
  likewise left alone). Every such left-untouched token is REPORTED, so the
  conservative skip is auditable rather than silent, and the operator confirms
  each is intended content (historical provenance, an authority note, a doc
  example) and not a real stamp. `conformance_check.py --strict` is the final
  gate.

WHAT IT DOES NOT DO (judgement — it PRINTS what to do, never does it):
  - it never edits PROXY_AUTH / EMBARGOES or any authority row — not even the
    version token inside one (a PROXY_AUTH change is first-hand-only). If the
    workspace's PROXY_AUTH predates v2.6's canonical super-class wording it
    prints the reword to apply by hand.
  - it never adds binding slots. v2.7 introduces NO new slots; the v2.6 slot
    family (TRANSPORT / WORKSPACE_REMOTE / SECRETS / AUTONOMY / WATCHER /
    ROLE_ALIASES) remains advisory — it prints any not yet present, flagged by
    whether they apply to this workspace's profile, so the principal adds the
    rows they want.
  - it never rewrites coordination state (channel rows, counters, memory) —
    carrying live state across a boundary is the agents' retrospective work.

Because it only rewrites version tokens, a migration reverts cleanly with a
single `git revert`. Pin-aware conformance means a not-yet-migrated workspace
stays green under a v2.7 checkout, so workspaces migrate independently, each at
its own freeze boundary.

Usage:
  python tools/migrate_workspace.py --workspace path/to/ws            # migrate
  python tools/migrate_workspace.py --workspace path/to/ws --dry-run  # preview

Idempotent: a second run finds v2.7 and does nothing. Exit 0 = migrated /
already-v2.7 / dry-run; 1 = not a v2.6 workspace (unknown version, or no
BINDINGS); 2 = usage error. A successful migration may still leave conformance
findings that need a hand-edit (the PROXY_AUTH reword, unfilled new slots) —
those are PRINTED, and the operator runs `conformance_check.py --strict` as the
final gate.
"""
import argparse
import importlib.util
import io
import re
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _load(mod_name, filename):
    spec = importlib.util.spec_from_file_location(mod_name, _HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# conformance_check carries the pieces we reuse rather than re-implement: the
# BINDINGS parser, the pinned-version reader, the canonical super-class list,
# and the post-migration conformance verify (the operator runs it with --strict
# as the final gate).
cc = _load("conformance_check", "conformance_check.py")

FROM_VER = "v2.6"
TO_VER = "v2.7"
STAMP_FROM = f"[PROTOCOL {FROM_VER}]"
STAMP_TO = f"[PROTOCOL {TO_VER}]"

SKIP_DIRS = {".git", "__pycache__", "node_modules"}
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pyc", ".zip", ".pdf"}

GUARD_CLAUSE = "never listable or relayable"

# A `[PROTOCOL vX.Y]` stamp is structural chrome, never content: new_project.py
# emits it ONLY on a file's banner — the title heading or docstring line that
# opens the file. So the flip is confined to the banner line (identified in
# _plan_file) AND that line must look like a heading/docstring banner (one of
# these prefixes). This excludes BINDINGS table rows (`|`), a memory-body
# heading or prose, and a fenced example — anywhere the same literal token would
# be authority or coordination content rather than the file's own stamp.
_STAMP_LINE_PREFIXES = ("#", "<!--", '"""', "'''")

# Split preserving the exact line terminators (\r\n / \r / \n) as separate
# capture groups, so a migrated file keeps whatever endings it had — no
# text-mode CRLF<->LF rewrite.
_LINE_SPLIT = re.compile(r"(\r\n|\r|\n)")

# The v2.6 slot family a workspace may still lack — printed as "consider
# adding", never stamped. v2.7 introduces NO new binding slots, so this list is
# unchanged across the v2.6 -> v2.7 hop. (name, one-line note, applicability):
# "always" = add on any workspace; "git-sync" = only when the transport is
# git-sync; "if-*" = a conditional the operator judges.
NEW_V26_SLOTS = [
    ("TRANSPORT", "name the transport explicitly (local-fs / git-sync)",
     "always"),
    ("WORKSPACE_REMOTE", "remote URL + branch", "git-sync"),
    ("SECRETS", "credential doctrine line", "git-sync"),
    ("AUTONOMY", "attended / semi-autonomous / standing-duties / never-idle",
     "always"),
    ("WATCHER", "per-role monitor + lanes + cadence", "if-never-idle"),
    ("ROLE_ALIASES", "display->role map", "if-renamed"),
]


def _is_git_sync(slots):
    """True if this workspace's transport is git-sync (by PROFILE or TRANSPORT)."""
    prof = (slots or {}).get("PROFILE", "")
    tr = (slots or {}).get("TRANSPORT", "")
    return prof.strip().endswith(".git-sync") or "git-sync" in tr


def _text_files(ws):
    for p in sorted(ws.rglob("*")):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in BINARY_EXT:
            continue
        yield p


def _is_append_only_record(ws, p):
    """True for append-only record families: auth-logs and channel files (held
    append-only by the workspace integrity gates) plus dispatch/tick logs
    (self-declared append-only, written by live scheduled tasks — rewriting one
    races a concurrent append). These keep their creation-version banner; the
    migrator never rewrites them."""
    rel = p.relative_to(ws).as_posix()
    if re.fullmatch(r"memory/[^/]+/(auth|dispatch|tick)-log\.md", rel):
        return True
    return rel.startswith("channel/") and rel.endswith(".md")


def _is_stamp_line(line):
    """Looks like a stamp banner: a heading or docstring/comment line (never a
    `|`-row or prose). Necessary but not sufficient — it must ALSO be the file's
    banner line (see _banner_index) to be flipped. A leading UTF-8 BOM is
    tolerated in DETECTION only (str.lstrip() does not strip U+FEFF — a
    BOM-prefixed real banner must not be misread as prose); the BOM byte itself
    is never rewritten."""
    return line.lstrip("﻿").lstrip().startswith(_STAMP_LINE_PREFIXES)


def _banner_index(segments):
    """Index into `segments` (from _LINE_SPLIT.split) of the file's banner
    content line — the first content line, or the second when the first is a
    shebang (`#!...`). new_project.py stamps only the banner, so only this line
    is eligible for the flip. Returns None if there is no banner content line."""
    if not segments:
        return None
    if segments[0].lstrip().startswith("#!"):
        return 2 if len(segments) > 2 else None
    return 0


def _pver_row_migrated(line):
    """If `line` (no terminator) is a `| PROTOCOL_VERSION | v2.6 | ... |` table
    row (any inner spacing, any extra trailing cells), return the same row with
    ONLY the version cell flipped v2.6 -> v2.7; else None. A structural match on
    the slot name + value cell, so whitespace-tolerant detection and the rewrite
    agree — and no other cell's content is ever normalized away or dropped."""
    parts = line.split("|")
    if len(parts) < 4 or parts[0].strip() or parts[-1].strip():
        return None
    if parts[1].strip() != "PROTOCOL_VERSION" or parts[2].strip() != FROM_VER:
        return None
    parts[2] = parts[2].replace(FROM_VER, TO_VER)  # flip the value cell in place
    return "|".join(parts)


def _plan_file(p):
    """Return (new_or_None, n_stamps, pver_flipped, skipped) for a file.
    `new_or_None` is None when the file needs no write. `skipped` counts stamp
    tokens left on non-banner lines (authority rows / memory bodies / fenced
    examples), surfaced so the conservative skip is auditable.

    The rewrite is line-structured, NOT a whole-file text.replace:
      - the stamp token is flipped ONLY on the file's BANNER line (its opening
        title heading / docstring), so the same literal token inside a
        PROXY_AUTH row, a memory-body heading or prose, or a fenced example is
        left untouched (and counted in `skipped`);
      - the PROTOCOL_VERSION row (BINDINGS.md only) is matched structurally and
        only its version cell is flipped (spacing + extra cells preserved);
      - line terminators are preserved exactly (read+write with newline="").
    """
    try:
        with p.open(encoding="utf-8", newline="") as f:
            text = f.read()
    except (UnicodeDecodeError, OSError):
        return None, 0, False, 0
    is_bindings = (p.name == "BINDINGS.md")
    segments = _LINE_SPLIT.split(text)  # [line, sep, line, sep, ..., line]
    banner = _banner_index(segments)
    n_stamps = 0
    pver_flipped = False
    skipped = 0
    for i in range(0, len(segments), 2):  # content lines only (even indices)
        seg = segments[i]
        c = seg.count(STAMP_FROM)
        if i == banner and _is_stamp_line(seg):
            if c:
                segments[i] = seg.replace(STAMP_FROM, STAMP_TO)
                n_stamps += c
            continue
        skipped += c  # token off the banner — left untouched, surfaced
        if is_bindings:
            migrated_row = _pver_row_migrated(seg)
            if migrated_row is not None:
                segments[i] = migrated_row
                pver_flipped = True
    new = "".join(segments)
    return (new if new != text else None), n_stamps, pver_flipped, skipped


def migrate(ws, dry_run=False):
    """Flip the version tokens across a v2.6 workspace. Pure of argparse.

    Returns a result dict: {status, ...}. status is one of
      'migrated' | 'dry-run' | 'already' | 'unsupported' | 'error'.
    'changed' is a list of (Path, n_stamps, pver_flipped) actually written
    (or that WOULD be written, under dry_run).
    """
    ws = Path(ws)
    slots = cc.parse_bindings(ws)
    if slots is None:
        return {"status": "error",
                "reason": f"no readable BINDINGS.md under {ws} (not a workspace?)"}
    pinned = cc.pinned_version(slots)
    if pinned == TO_VER:
        return {"status": "already", "version": TO_VER, "changed": []}
    if pinned != FROM_VER:
        return {"status": "unsupported", "version": pinned or "absent"}

    changed = []
    left = []
    records_kept = []
    for p in _text_files(ws):
        if _is_append_only_record(ws, p):
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                txt = ""
            # EVERY record is reported (n may be 0) — exhaustive, not filtered.
            records_kept.append((p, txt.count(STAMP_FROM)))
            continue  # append-only record — creation stamp kept, never rewritten
        new, n_stamps, pver_flipped, skipped = _plan_file(p)
        if skipped:
            left.append((p, skipped))
        if new is None:
            continue
        changed.append((p, n_stamps, pver_flipped))
        if not dry_run:
            with p.open("w", encoding="utf-8", newline="") as f:
                f.write(new)
    return {"status": "dry-run" if dry_run else "migrated",
            "version_from": FROM_VER, "version_to": TO_VER,
            "changed": changed, "left_untouched": left,
            "records_kept": records_kept}


def proxy_auth_gaps(slots):
    """The canonical super-class phrases (and the guard clause) that a present
    PROXY_AUTH slot is MISSING — empty if the slot is absent or already
    canonical. Reuses conformance_check.SUPER_CLASSES so the two never drift."""
    pa = (slots or {}).get("PROXY_AUTH", "")
    if not pa:
        return []
    gaps = [phrase for phrase in cc.SUPER_CLASSES if phrase not in pa]
    on = not pa.lstrip().lower().startswith("off")
    if on and GUARD_CLAUSE not in pa:
        gaps.append(f"guard clause '{GUARD_CLAUSE}'")
    return gaps


def print_manual_steps(ws, slots, roles):
    """Print the judgement steps the tool deliberately does NOT do."""
    print("\n=== MANUAL STEPS (the tool does not touch these) ===")

    # 1. PROXY_AUTH reword — authority, first-hand only.
    gaps = proxy_auth_gaps(slots)
    if gaps:
        print("\n1. PROXY_AUTH is present but predates v2.6's canonical "
              "super-class wording. Reword its EXCLUDED clause to name these "
              "verbatim (FIRST-HAND ONLY — a PROXY_AUTH change is never "
              "relayed/automated; draft for the principal, they commit):")
        for g in gaps:
            print(f"     - {g}")
        print("   Canonical wording lives in new_project.ORCH_SLOTS "
              "(the PROXY_AUTH row).")
    else:
        pa = (slots or {}).get("PROXY_AUTH", "")
        if pa:
            print("\n1. PROXY_AUTH already carries the canonical v2.6 wording — "
                  "no reword needed.")
        else:
            print("\n1. No PROXY_AUTH slot (no orchestrator) — nothing to reword.")

    # 2. New v2.6 slots to consider (advisory — none are required for a green
    #    conformance run). Flag each not-present slot by whether it APPLIES to
    #    this workspace's profile, so "which apply" is honest, not a blanket list.
    present = set(slots or {})
    git_sync = _is_git_sync(slots)
    add, na, cond = [], [], []
    for n, note, applic in NEW_V26_SLOTS:
        if n in present:
            continue
        if applic == "always":
            add.append((n, note))
        elif applic == "git-sync":
            (add if git_sync else na).append((n, note))
        elif applic == "if-never-idle":
            cond.append((n, note + " — only if this workspace runs never-idle"))
        elif applic == "if-renamed":
            cond.append((n, note + " — only if a side is renamed"))
    if add or cond:
        print("\n2. v2.6 binding slots not yet present (none are required for "
              "conformance; add the ones this deployment wants):")
        for n, note in add + cond:
            print(f"     - {n}: {note}")
    if na:
        print("   (not applicable to this local-fs workspace: "
              + ", ".join(n for n, _ in na) + ")")

    # 3. Coordination state — carried by the agents, never by this tool.
    print("\n3. Coordination STATE (channel rows, per-side counters, memory) is "
          "carried across the boundary BY THE ROLES as their own retrospective "
          "work — this tool rewrote none of it. Read the live channel tail and "
          "reconcile counters per docs/MIGRATION.md; never reset.")


def verify(ws):
    """Run the trusted conformance check against `ws`; return (code, output)."""
    saved = sys.argv
    out, err = io.StringIO(), io.StringIO()
    try:
        sys.argv = ["conformance_check.py", "--workspace", str(ws)]
        with redirect_stdout(out), redirect_stderr(err):
            code = cc.main()
    finally:
        sys.argv = saved
    return code, out.getvalue()


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", required=True,
                    help="workspace root to migrate v2.6 -> v2.7")
    ap.add_argument("--dry-run", action="store_true",
                    help="list what would change; write nothing")
    args = ap.parse_args()

    ws = Path(args.workspace)
    if not ws.is_dir():
        print(f"migrate: {ws} is not a directory", file=sys.stderr)
        return 2

    result = migrate(ws, dry_run=args.dry_run)
    status = result["status"]

    if status == "error":
        print(f"migrate: {result['reason']}", file=sys.stderr)
        return 1
    if status == "unsupported":
        print(f"migrate: workspace PROTOCOL_VERSION is '{result['version']}', "
              f"this tool only migrates {FROM_VER} -> {TO_VER}", file=sys.stderr)
        return 1
    if status == "already":
        print(f"migrate: {ws.name} is already {TO_VER} — nothing to do "
              "(idempotent no-op)")
        return 0

    changed = result["changed"]
    total_stamps = sum(n for _, n, _ in changed)
    verb = "would flip" if args.dry_run else "flipped"
    print(f"migrate: {ws.name} {FROM_VER} -> {TO_VER} — {verb} "
          f"{total_stamps} stamp(s) across {len(changed)} file(s)"
          + (" [DRY RUN — nothing written]" if args.dry_run else ""))
    for p, n, pver in sorted(changed, key=lambda t: str(t[0])):
        tag = " (+PROTOCOL_VERSION)" if pver else ""
        print(f"    {p.relative_to(ws).as_posix()}: {n} stamp(s){tag}")

    kept = result.get("records_kept", [])
    if kept:
        total_kept = sum(n for _, n in kept)
        with_tok = [(p, n) for p, n in kept if n]
        print(f"\n  append-only records kept as-is — ALL {len(kept)} record "
              f"file(s) skipped (auth/dispatch/tick logs + channel; creation "
              f"stamp kept, conformance accepts a supported one); "
              f"{total_kept} `{STAMP_FROM}` token(s) in {len(with_tok)} of them:")
        for p, n in sorted(with_tok, key=lambda t: str(t[0])):
            print(f"    {p.relative_to(ws).as_posix()}: {n}")
        no_tok = len(kept) - len(with_tok)
        if no_tok:
            print(f"    (+ {no_tok} record file(s) with no `{STAMP_FROM}` "
                  "token — skipped all the same)")

    left = result.get("left_untouched", [])
    if left:
        total_left = sum(n for _, n in left)
        print(f"\n  left untouched — {total_left} `{STAMP_FROM}` token(s) on "
              "non-stamp lines (authority rows / prose), deliberately NOT "
              "flipped; confirm each is intended content, not a stamp:")
        for p, n in sorted(left, key=lambda t: str(t[0])):
            print(f"    {p.relative_to(ws).as_posix()}: {n}")

    slots = cc.parse_bindings(ws)
    roles = cc.infer_roles(ws)
    print_manual_steps(ws, slots, roles)

    if not args.dry_run:
        print("\n=== CONFORMANCE (post-migration) ===")
        code, out = verify(ws)
        print(out.rstrip())
        if code != 0:
            print("\n(resolve the MANUAL STEPS above, then re-run "
                  "`conformance_check.py --workspace <ws> --strict` as the gate.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
