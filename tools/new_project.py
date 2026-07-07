#!/usr/bin/env python3
"""Stamp a dedicated per-project agent workspace (PROTOCOL v2.6).

Creates the "dedicated, not generic" instantiation: a workspace directory
(intended to become its own private repo) holding bindings, channel skeleton,
per-role memory, MODELS.md, and instantiated start-session files. The skills
themselves stay in the multi-agent-protocol repo (installed via plugin
marketplace).

Usage:
  python tools/new_project.py --name myproject --dest path/to/myproject-ws \
      --profile 3agent.local --owner-side engine --builder-side builder \
      [--principal "Your Name"] [--no-orchestrator] [--wizard] [--git-init] \
      [--plugin-install {marketplace,manual}]

Add --wizard for an interactive PRE-STAMP walkthrough (topology -> side names ->
principal -> repo -> reviewer -> a grouped {{FILL}} walk -> git-init ->
plugin-install) that renders the resolved BINDINGS in one pass; it is skipped
automatically when stdin is not an interactive terminal, so unattended stamps
never hang. --git-init makes the fresh workspace a git repo (non-fatal);
--plugin-install {marketplace,manual} chooses how the stamped
.claude/settings.json installs the plugin — `manual` omits the marketplace
blocks for a hand-copied ~/.claude install. `--no-orchestrator` is a deprecated
alias for `--profile 2agent.local` (a dual-role-owner workspace).
"""
import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Canonical role order (SIDE_NAMES are positional against this) and each
# role's DEFAULT side name — the argparse defaults below. A ROLE_ALIASES row
# entry (and a README "(as ...)" note) is emitted only for a side whose name
# was CHANGED from its default, so an all-defaults stamp stays byte-identical
# to pre-ROLE_ALIASES stamps (owner/builder keep their canonical names; the
# orchestrator's conventional short name `orch` is its default, not a rename).
CANONICAL_ROLE_ORDER = ["owner", "builder", "orchestrator"]
DEFAULT_SIDE_NAME = {"owner": "owner", "builder": "builder", "orchestrator": "orch"}

BINDINGS_TEMPLATE = """# BINDINGS — {name} agent workspace [PROTOCOL v2.6]

Instantiated {date} from the multi-agent-protocol repo (profile: {profile}).
Slot glossary: plugins/agent-protocol/skills/agent-core/references/binding-slots.md

| slot | value |
|---|---|
| PROJECT | {name} |
| PROFILE | {profile} |
| TRANSPORT | {transport} |
{remote_row}| SIDE_NAMES | {side_names} |
{alias_row}| CANONICAL_REPO | {{{{FILL: work repo path + remote + branch}}}} |
| CHANNEL | channel/ (repo-relative; this workspace repo) |
| MEMORY | memory/<role>/ (repo-relative) |
| REVIEWER | {{{{FILL: per side — mechanism + model}}}} |
| PRINCIPAL | {principal} |
| PINNED_RESOURCES | {{{{FILL: exact IDs/paths, or "none"}}}} |
| SHARED_ARTIFACTS | none (add per agent-core conditions if needed) |
| SIGNING | {{{{FILL: gpg-local / webflow-api / sign-on-merge}}}} |
| SECRETS | none committed — git credentials/tokens live in the host env or platform connector only, never here |
| HEARTBEAT | {{{{FILL: per role, offset}}}} |
| AUTONOMY | semi-autonomous (dial: attended / semi-autonomous / standing-duties / never-idle) |
| WATCHER | {{{{FILL: per-role monitor + lane list + cadence, or "none" — required if AUTONOMY = never-idle}}}} |
| MODEL | see MODELS.md (active preset + overrides) |
| EMBARGOES / GATES | {{{{FILL: standing list + size tripwire}}}} |
| PROTOCOL_VERSION | v2.6 |
{orch_slots}"""

ORCH_SLOTS = """| FLAVOR | {{FILL: global-pa or project:<name>}} |
| PROXY_AUTH | off (default — only the principal, directly in the orchestrator session, may change this; if on, list ONLY enumerated reversible/internal gate classes plus explicit exclusions. The irreversible/outward super-classes — outward-facing/publish actions, email SEND, new-money/new-recipient financial actions, destructive operations on another party's artifacts, canonical-repo merges, and changes to PROXY_AUTH / gates / embargoes / the protocol — are never listable or relayable) |
| AUTH_PROVENANCE | {{FILL: per-role-identity (+ commit .auth-provenance.json mapping role->author email; CI enforces) / single-identity (trust-based; principal acceptance recorded here)}} |
| TASKQUEUE | TASKQUEUE.md (this workspace) |
| SESSION_REGISTRY | memory/orchestrator/session-registry.md |
| COST_LEDGER | memory/orchestrator/cost-ledger.md |
| ESCALATION | {{FILL: matrix + quiet hours}} |
| DUTIES | {{FILL: standing duty list}} |
| TICKS | {{FILL: idle cadence / active-window cadence}} |
"""

README_TEMPLATE = """# {name} — dedicated agent workspace

Stamped from github.com/AIpandadreams/multi-agent-protocol on {date}.
Roles: {roles}. Profile: {profile}.

- `BINDINGS.md` — fill every {{{{FILL}}}} before first session.
- `channel/` — the inter-agent channel (filename grammar in agent-core).
- `memory/<role>/` — each role's persistent memory + auth-log.md.
- `MODELS.md` — live model matrix (presets + overrides).
- `start/` — instantiated per-role START_SESSION files; each session follows
  its own at every session boundary.
- `.claude/settings.json` — installs the agent-protocol plugin at session
  start.
"""

AUTH_LOG_VALIDATOR = r'''#!/usr/bin/env python3
"""Auth-log chain validator [PROTOCOL v2.6] — mechanical enforcement of the
exactly-one-landed-CONSUMED audit rule (proxy-auth-core.md) over every
memory/<role>/auth-log.md in this workspace:

  - no duplicate CONSUMED for the same consumption id (relay id or
    grant-id[/D<k>]) — a second CONSUMED for the same id is a violation
  - a relayed CONSUMED (id contains /R) must follow a COMPLETE RECEIVED
    block for that relay id in the SAME log — the consume must come after
    the block's source: provenance line, not merely after its header
  - a RECEIVED block must reference a relay id actually RELAY-SENT in some
    log (fabricated relays fail) and must carry a source: provenance line
  - RELAY-SENT only for grants defined in the SAME log; direct CONSUMED
    only of grants defined in the SAME log (unknown ids fail — nothing is
    consumable that was never granted)
  - relay and direct spends of the SAME grant TOGETHER never exceed its
    scope (a grant spent once by relay and once directly is a double-spend)

This is the CI layer; the reviewer's semantic audit (words in scope, gate
class on the list, provenance) remains on top. Run from the workspace root.
Exit 0 clean, 1 on violation. Stamped by new_project.py — edit upstream.
"""
import re
import sys
from pathlib import Path

GRANT_RE = re.compile(r"^## GRANT (\S+)")
SCOPE_RE = re.compile(r"^scope:\s*(single|batch-(\d+))")
RELAY_RE = re.compile(r"^RELAY-SENT (\S+) relay=(\S+)")
RECV_RE = re.compile(r"^relay-id:\s*(\S+)")
CONS_RE = re.compile(r"^CONSUMED (\S+)")


RECV_HEAD_RE = re.compile(r"^## RECEIVED ")
SOURCE_RE = re.compile(r"^source:\s*\S+")


def parse_log(log: Path) -> dict:
    d = {"log": log, "grants": {}, "relays": {}, "received": {},
         "consumed": {}, "direct": {}, "cons_lines": []}
    cur = None
    in_recv = None  # relay id of the RECEIVED block being read
    for n, line in enumerate(
            log.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if RECV_HEAD_RE.match(line):
            cur, in_recv = None, "PENDING"
            continue
        m = GRANT_RE.match(line)
        if m:
            cur, in_recv = m.group(1), None
            d["grants"][cur] = 1
            continue
        if line.startswith("## "):
            # any other heading closes an open RECEIVED block so a later
            # source:/CONSUMED cannot be mis-attributed to it
            in_recv = None
        m = SCOPE_RE.match(line)
        if m and cur:
            d["grants"][cur] = int(m.group(2)) if m.group(2) else 1
            continue
        m = RELAY_RE.match(line)
        if m:
            d["relays"].setdefault(m.group(1), set()).add(m.group(2))
            continue
        m = RECV_RE.match(line)
        if m and in_recv is not None:
            in_recv = m.group(1)
            d["received"][in_recv] = {"line": n, "has_source": False,
                                      "source_line": None}
            continue
        if SOURCE_RE.match(line) and in_recv and in_recv != "PENDING":
            d["received"][in_recv]["has_source"] = True
            d["received"][in_recv]["source_line"] = n
            continue
        m = CONS_RE.match(line)
        if m:
            cid = m.group(1)
            d["consumed"][cid] = d["consumed"].get(cid, 0) + 1
            d["cons_lines"].append((cid, n))
            if "/R" not in cid:
                d["direct"].setdefault(cid.split("/")[0], set()).add(cid)
    return d


def check(parsed: list, bad: list) -> None:
    # global sets: every relay id actually SENT, anywhere — and every
    # consumption id, anywhere: exactly-one CONSUMED holds ACROSS logs
    # (the same relay consumed in two different roles' logs is a double
    # spend, not two local singles)
    all_sent = set()
    global_consumed = {}
    for d in parsed:
        for rids in d["relays"].values():
            all_sent |= rids
        for cid, _ in d["cons_lines"]:
            global_consumed.setdefault(cid, []).append(d["log"])
    for cid, where in sorted(global_consumed.items()):
        if len(where) > 1:
            locs = ", ".join(sorted({str(w) for w in where}))
            bad.append(f"duplicate CONSUMED {cid} - {len(where)} events "
                       f"across: {locs} (exactly-one landed CONSUMED per "
                       "action, global)")
    for d in parsed:
        log = d["log"]
        for cid, n in d["cons_lines"]:
            if "/R" in cid:
                rec = d["received"].get(cid)
                if rec is None:
                    bad.append(f"{log}:{n}: CONSUMED {cid} has no RECEIVED "
                               "block in this log (record before reserve)")
                elif rec["source_line"] is not None and n < rec["source_line"]:
                    bad.append(f"{log}:{n}: CONSUMED {cid} appears before its "
                               "RECEIVED provenance completes (source: at line "
                               f"{rec['source_line']}) — record before reserve")
            elif cid.split("/")[0] not in d["grants"]:
                bad.append(f"{log}:{n}: direct CONSUMED {cid} of a grant not "
                           "defined in this log (direct consumes live in the "
                           "granting session's own log)")
        for gid, rids in d["relays"].items():
            if gid not in d["grants"]:
                bad.append(f"{log}: RELAY-SENT for unknown grant {gid} "
                           "(relays are appended only to the granting log)")
        for rid, info in d["received"].items():
            if rid not in all_sent:
                bad.append(f"{log}:{info['line']}: RECEIVED {rid} matches no "
                           "RELAY-SENT in any log (fabricated relay)")
            if not info["has_source"]:
                bad.append(f"{log}:{info['line']}: RECEIVED {rid} lacks a "
                           "source: provenance line")
        # Combined scope: relay + direct spends of the SAME grant together may
        # not exceed its scope — a single grant spent once by relay AND once
        # directly is a double-spend that the separate per-kind checks missed.
        for gid, scope in d["grants"].items():
            nrelay = len(d["relays"].get(gid, set()))
            ndirect = len(d["direct"].get(gid, set()))
            if nrelay + ndirect > scope:
                bad.append(f"{log}: grant {gid} scope {scope} but "
                           f"{nrelay + ndirect} spends "
                           f"({nrelay} relay + {ndirect} direct)")


def main() -> int:
    logs = sorted(Path("memory").glob("*/auth-log.md"))
    if not logs:
        print("auth-log validator: no logs found (nothing to check)")
        return 0
    bad: list = []
    check([parse_log(log) for log in logs], bad)
    if bad:
        print("auth-log chain violations:")
        print("\n".join(bad))
        return 1
    print(f"auth-log validator: {len(logs)} log(s) clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

INTEGRITY_WORKFLOW = """name: workspace-integrity
on:
  push:
  pull_request:
jobs:
  integrity:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: auth-log append-only
        run: |
          BASE="${{ github.event.before }}"
          if [ -z "$BASE" ] || ! git cat-file -e "$BASE" 2>/dev/null; then
            BASE=$(git rev-parse HEAD~1 2>/dev/null || echo "")
          fi
          if [ -n "$BASE" ]; then
            REMOVED=$(git diff "$BASE"..HEAD -- 'memory/*/auth-log.md' | grep '^-' | grep -v '^---' || true)
            if [ -n "$REMOVED" ]; then
              echo "auth-log.md is append-only; lines were removed or edited:"
              echo "$REMOVED"
              exit 1
            fi
          fi
      - name: auth-log provenance (no mixed-path auth commits)
        run: |
          BASE="${{ github.event.before }}"
          if [ -z "$BASE" ] || ! git cat-file -e "$BASE" 2>/dev/null; then
            BASE=$(git rev-parse HEAD~1 2>/dev/null || echo "")
          fi
          if [ -n "$BASE" ]; then
            for C in $(git rev-list "$BASE"..HEAD); do
              LOGS=$(git diff-tree --no-commit-id --name-only -r "$C" | grep -E '^memory/[^/]+/auth-log\\.md$' || true)
              [ -z "$LOGS" ] && continue
              ROLE=$(echo "$LOGS" | head -1 | cut -d/ -f2)
              BAD=$(git diff-tree --no-commit-id --name-only -r "$C" | grep -v "^memory/$ROLE/" || true)
              if [ -n "$BAD" ] || [ "$(echo "$LOGS" | cut -d/ -f2 | sort -u | wc -l)" -gt 1 ]; then
                echo "commit $C touches $ROLE's auth-log together with other paths:"
                echo "$BAD"
                echo "auth-log events must ride commits confined to their own memory/<role>/ subtree (proxy-auth-core §Provenance)"
                exit 1
              fi
              if [ -f .auth-provenance.json ]; then
                WANT=$(python3 -c "import json,sys; print(json.load(open('.auth-provenance.json')).get(sys.argv[1],''))" "$ROLE")
                GOT=$(git log -1 --format=%ae "$C")
                if [ -z "$WANT" ]; then
                  echo "per-role-identity mode: no bound identity for role '$ROLE' in .auth-provenance.json (commit $C)"
                  exit 1
                fi
                if [ "$GOT" != "$WANT" ]; then
                  echo "commit $C appends to $ROLE's auth-log but author '$GOT' is not the bound identity '$WANT' (proxy-auth-core §Provenance)"
                  echo "NOTE: author email is a weak signal (spoofable) — per-role deploy keys / branch-ruleset ownership are the hard layer"
                  exit 1
                fi
              fi
            done
          fi
      - name: auth-provenance map sanity (unique role identities)
        run: |
          [ -f .auth-provenance.json ] || { echo "no .auth-provenance.json (single-identity mode)"; exit 0; }
          python3 - <<'EOF'
          import json, sys
          m = json.load(open(".auth-provenance.json"))
          ids = [v for v in m.values() if v]
          if len(ids) != len(set(ids)):
              print(".auth-provenance.json: role identities must be UNIQUE -"
                    " a shared identity defeats per-role provenance")
              sys.exit(1)
          print(f"provenance map: {len(ids)} unique role identities")
          EOF
      - name: auth-log chain validation (exactly-one CONSUMED)
        run: python3 tools/validate_auth_log.py
      - name: channel append-only
        run: |
          BASE="${{ github.event.before }}"
          if [ -z "$BASE" ] || ! git cat-file -e "$BASE" 2>/dev/null; then
            BASE=$(git rev-parse HEAD~1 2>/dev/null || echo "")
          fi
          if [ -n "$BASE" ]; then
            REMOVED=$(git diff "$BASE"..HEAD -- 'channel/*.md' | grep '^-' | grep -v '^---' || true)
            if [ -n "$REMOVED" ]; then
              echo "channel files only ever gain lines; lines were removed or edited:"
              echo "$REMOVED"
              exit 1
            fi
          fi
      - name: CHANNEL_STATE monotonic
        run: |
          [ -f CHANNEL_STATE.json ] || { echo "no CHANNEL_STATE.json (ok)"; exit 0; }
          BASE="${{ github.event.before }}"
          if [ -z "$BASE" ] || ! git cat-file -e "$BASE" 2>/dev/null; then
            BASE=$(git rev-parse HEAD~1 2>/dev/null || echo "")
          fi
          OLD=""
          if [ -n "$BASE" ]; then
            OLD=$(git show "$BASE":CHANNEL_STATE.json 2>/dev/null || echo "")
          fi
          python3 - "$OLD" <<'EOF'
          import json, sys
          new = json.load(open("CHANNEL_STATE.json"))  # must parse
          old_raw = sys.argv[1]
          if not old_raw.strip():
              print("CHANNEL_STATE.json valid (no prior version)")
              sys.exit(0)
          old = json.loads(old_raw)
          def walk(o, n, path=""):
              if isinstance(o, dict):
                  if not isinstance(n, dict):
                      print(f"CHANNEL_STATE{path}: object became {type(n).__name__}")
                      sys.exit(1)
                  for k in o:
                      if k not in n:
                          print(f"CHANNEL_STATE{path}.{k}: key REMOVED (state is forward-only)")
                          sys.exit(1)
                      walk(o[k], n[k], f"{path}.{k}")
              elif isinstance(o, int) and not isinstance(o, bool):
                  if not isinstance(n, int) or isinstance(n, bool):
                      print(f"CHANNEL_STATE{path}: integer became {type(n).__name__} (type reset bypass)")
                      sys.exit(1)
                  if n < o:
                      print(f"CHANNEL_STATE{path}: counter went BACKWARD {o} -> {n}")
                      sys.exit(1)
          walk(old, new)
          print("CHANNEL_STATE.json valid and monotonic")
          EOF
      - name: secret scan
        run: |
          python3 - <<'EOF'
          import re, subprocess, sys
          pats = [r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"\\bAKIA[0-9A-Z]{16}\\b",
                  r"\\bghp_[A-Za-z0-9]{36}\\b", r"\\bgithub_pat_[A-Za-z0-9_]{22,}\\b",
                  r"\\bsk-[A-Za-z0-9_-]{20,}\\b", r"\\bsbp_[a-f0-9]{40}\\b",
                  r"\\beyJhbGciOiJ[A-Za-z0-9_.-]{40,}"]
          files = subprocess.run(["git", "ls-files"], capture_output=True,
                                 text=True).stdout.split()
          bad = []
          for f in files:
              try:
                  t = open(f, encoding="utf-8", errors="ignore").read()
              except (IsADirectoryError, OSError):
                  continue
              for p in pats:
                  if re.search(p, t):
                      bad.append(f"{f}: matches {p}")
          if bad:
              print("possible secrets committed:")
              print("\\n".join(bad))
              sys.exit(1)
          print("secret scan clean")
          EOF
      - name: protected paths (no state-branch PR touches governance files)
        if: github.event_name == 'pull_request' && startsWith(github.head_ref, 'state/')
        run: |
          # git-sync reservation-class publishing rides state/** branches; those
          # branches carry channel/auth-log/state ONLY. A PR from state/** that
          # also edits governance surfaces (bindings, CI, the auth validator,
          # the provenance map, the model matrix) is a privilege-escalation
          # shape — fail loudly. Inert on every non-state-branch PR.
          BAD=$(git diff --name-only "origin/${{ github.base_ref }}"...HEAD \
            | grep -E '^(BINDINGS\\.md|MODELS\\.md|\\.auth-provenance\\.json|\\.github/workflows/|tools/validate_auth_log\\.py)' || true)
          if [ -n "$BAD" ]; then
            echo "PR from state branch '${{ github.head_ref }}' edits protected governance paths:"
            echo "$BAD"
            echo "state/** branches carry channel + auth-log + state only; governance changes land through a normal branch"
            exit 1
          fi
          echo "protected-path guard clean"
"""

# unattended wakes stall on permission prompts they cannot answer —
# pre-approve exactly the git/gh surface the channel loop needs
_PERMISSIONS_ALLOW = [
    "Bash(git status:*)", "Bash(git log:*)", "Bash(git diff:*)",
    "Bash(git show:*)", "Bash(git fetch:*)", "Bash(git pull:*)",
    "Bash(git add:*)", "Bash(git commit:*)", "Bash(git push:*)",
    "Bash(git checkout:*)", "Bash(git switch:*)",
    "Bash(git branch:*)", "Bash(git rev-parse:*)",
    "Bash(git merge-base:*)", "Bash(gh pr create:*)",
    "Bash(gh pr view:*)", "Bash(gh pr list:*)",
    "Bash(gh run list:*)", "Bash(gh run view:*)",
    "Bash(python tools/validate_auth_log.py)",
    # the in-workspace hygiene self-check (SELF-CHECK MODE copy)
    "Bash(python tools/conformance_check.py:*)",
]

PLUGIN_MODES = ("marketplace", "manual")


def build_settings(plugin_mode="marketplace"):
    """The stamped `.claude/settings.json` dict.

    `marketplace` (default) registers the plugin marketplace and enables the
    plugin so a session opened in the workspace installs it automatically.
    `manual` OMITS both blocks (C/D-7): the operator installs the skills into
    their own `~/.claude` by hand, and the workspace must NOT also try to pull
    the marketplace plugin (which would double-install / fight the manual copy).
    Either way the git/gh permission allowlist is stamped."""
    settings = {}
    if plugin_mode == "marketplace":
        settings["extraKnownMarketplaces"] = {
            "multi-agent-protocol": {
                "source": {
                    "source": "github",
                    "repo": "AIpandadreams/multi-agent-protocol",
                }
            },
        }
        settings["enabledPlugins"] = ["agent-protocol@multi-agent-protocol"]
    settings["permissions"] = {"allow": list(_PERMISSIONS_ALLOW)}
    return settings


FILL_RE = re.compile(r"\{\{FILL:([^}]*)\}\}")


PROFILE_CHOICES = ["2agent.local", "3agent.local",
                   "2agent.git-sync", "3agent.git-sync"]

# An operator can DEFER a slot in the wizard instead of answering it: typing the
# defer token stamps a {{DEFERRED: …}} marker distinct from an untouched
# {{FILL}}. Conformance treats DEFERRED as a deliberate "later", not a slot
# nobody has looked at.
DEFER_TOKEN = "defer"

# A side (display) name feeds the `<from>_to_<to>_<date>` channel filename, so
# it must match this charset — underscore in particular is FORBIDDEN because it
# is that grammar's separator. The wizard rejects a bad name AT ENTRY (rather
# than letting conformance catch it post-stamp).
SIDE_CHARSET_RE = re.compile(r"^[A-Za-z0-9-]+$")

# The remaining {{FILL}} slots the wizard walks AFTER the preflight, grouped so
# the operator fills the load-bearing ones on day one and is offered an easy
# "defer" on the rest (addressing the "{{FILL}} wall" — most are postponeable).
# CANONICAL_REPO / REVIEWER / PRINCIPAL are handled in the preflight already.
DAY_ONE_SLOTS = [
    ("EMBARGOES / GATES", "standing must-ask-first list + size tripwire"),
    ("SIGNING", "gpg-local / webflow-api / sign-on-merge"),
]
DEFERRABLE_SLOTS = [
    ("PINNED_RESOURCES", "exact IDs/paths the agents may touch, or 'none'"),
    ("HEARTBEAT", "per-role check-in cadence + offset"),
    ("WATCHER", "per-role monitor + lanes + cadence (required if never-idle)"),
]
# Orchestrator-only slots are deferrable too (a 2-agent stamp never has them).
DEFERRABLE_ORCH_SLOTS = [
    ("FLAVOR", "global-pa or project:<name>"),
    ("AUTH_PROVENANCE", "per-role-identity / single-identity"),
    ("ESCALATION", "matrix + quiet hours"),
    ("DUTIES", "standing duty list"),
    ("TICKS", "idle cadence / active-window cadence"),
]


def resolve_topology(profile, no_orchestrator):
    """Resolve (profile, roles) from raw --profile (or None) + --no-orchestrator.

    C3 fix: `--no-orchestrator` is a DEPRECATED alias for a 2-agent (dual-role
    owner) workspace. Combining it with an explicit 3-agent profile is a hard
    error — that pairing used to stamp owner+builder while writing
    PROFILE=3agent.local, which conformance rightly BLOCKs. A 2agent.git-sync
    selection is preserved.
    """
    if no_orchestrator:
        if profile is not None and profile.startswith("3agent"):
            raise ValueError(
                f"--no-orchestrator conflicts with --profile {profile}: "
                "--no-orchestrator forces a 2-agent (dual-role owner) "
                "workspace. Pick one. (--no-orchestrator is a deprecated alias "
                "for --profile 2agent.local.)")
        resolved = (profile if profile and profile.startswith("2agent")
                    else "2agent.local")
    else:
        resolved = profile if profile is not None else "3agent.local"
    roles = ["owner", "builder"]
    if resolved.startswith("3agent"):
        roles.append("orchestrator")
    return resolved, roles


def apply_slot_answers(bindings_text, answers):
    """Splice wizard answers into named slot rows of the rendered BINDINGS.

    `answers` maps a SLOT name -> answer string, or the DEFER_TOKEN sentinel to
    stamp a {{DEFERRED: <original hint>}} marker in place of the slot's
    {{FILL}}. A slot absent from `answers`, or given an empty answer, is left as
    {{FILL}} for later. Rows are matched by their leading `| SLOT |`, never by
    value, so two slots sharing placeholder text can't be confused.
    """
    if not answers:
        return bindings_text
    lines = bindings_text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped.startswith("|"):
            continue
        cells = stripped.split("|")
        if len(cells) < 3:
            continue
        slot = cells[1].strip()
        if slot not in answers:
            continue
        m = FILL_RE.search(line)
        if not m:
            continue
        ans = answers[slot]
        if ans == DEFER_TOKEN:
            hint = m.group(1).strip()
            repl = "{{DEFERRED: " + hint + "}}" if hint else "{{DEFERRED}}"
        elif ans:
            repl = ans
        else:
            continue
        lines[i] = line[:m.start()] + repl + line[m.end():]
    return "".join(lines)


def _ask(prompt, default, input_fn):
    """One wizard question with an echoed default; empty input takes the default."""
    shown = f" [{default}]" if default not in (None, "") else ""
    try:
        ans = input_fn(f"{prompt}{shown}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        return default
    return ans or default


def _ask_yesno(prompt, default_yes, input_fn):
    d = "Y/n" if default_yes else "y/N"
    ans = _ask(f"{prompt} [{d}]", "", input_fn).strip().lower()
    if not ans:
        return default_yes
    return ans[0] == "y"


def _ask_side_name(role, default, input_fn):
    """Ask for a side display name, REJECTING an illegal one at entry.

    A side name flows into channel filenames, so it must be [A-Za-z0-9-]
    (underscore is the filename separator — forbidden). On a bad answer we
    explain and re-prompt rather than stamp a workspace conformance will
    later BLOCK. A bounded retry count keeps a piped/hostile input_fn from
    looping forever — it falls back to the default with a note."""
    for _ in range(5):
        name = _ask(f"Display name for the {role} side", default, input_fn)
        if SIDE_CHARSET_RE.match(name):
            return name
        why = ("'_' is the channel-filename separator"
               if "_" in name else "only letters, digits and '-' are allowed")
        print(f"  ! '{name}' is not a legal side name ({why}). Try again.")
    print(f"  ! too many invalid attempts — using the default '{default}'.")
    return default


def walk_fill_slots(roles, input_fn, slot_answers):
    """Walk the remaining {{FILL}} slots after the preflight, in two groups.

    Day-one slots default to `defer` but are worth answering now; deferrable
    slots default to `defer` outright. Any slot the operator leaves at the
    default is recorded as DEFER_TOKEN (→ {{DEFERRED}}); a typed value is kept
    verbatim. Answers are written into `slot_answers` (never overwriting a
    preflight answer). Mutates and returns `slot_answers`."""
    groups = [("day-one (fill these first)", DAY_ONE_SLOTS),
              ("deferrable (Enter to postpone)", DEFERRABLE_SLOTS)]
    if "orchestrator" in roles:
        groups.append(("orchestrator (deferrable)", DEFERRABLE_ORCH_SLOTS))
    for label, slots in groups:
        print(f"\n  — {label} —")
        for slot, hint in slots:
            if slot in slot_answers:
                continue  # a preflight answer wins
            ans = _ask(f"{slot} ({hint})", DEFER_TOKEN, input_fn)
            slot_answers[slot] = ans if ans else DEFER_TOKEN
    return slot_answers


def wizard_preflight(input_fn=None, which_fn=None, seed=None):
    """Interactive PRE-STAMP walkthrough → a resolved config dict.

    Order: topology (roles + transport) → side names → principal → repo →
    reviewer (probes PATH for a CLI) → grouped {{FILL}} walk → git-init →
    plugin-install. `input_fn` and `which_fn` are injectable so tests can drive
    it without a TTY. Both use a None sentinel resolved to the live builtin at
    CALL time — a bare `input_fn=input` default would capture the builtin at
    import, so a caller (or test) that later swaps `builtins.input` wouldn't be
    seen.

    `seed` (typically the parsed argparse args) PRE-FILLS each question's
    DEFAULT, so a flag the operator already passed just needs Enter to accept —
    flags seed, the wizard confirms. Reads: profile, no_orchestrator,
    owner_side/builder_side/orch_side, principal, plugin_install. Returns:
      {profile, roles, role_side, principal, slot_answers, git_init,
       plugin_mode}
    slot_answers carries CANONICAL_REPO / REVIEWER + the walked slots (values or
    DEFER_TOKEN).
    """
    if input_fn is None:
        input_fn = input
    if which_fn is None:
        which_fn = shutil.which

    def _seed(attr, fallback=None):
        return getattr(seed, attr, fallback) if seed is not None else fallback

    print("\n— new workspace wizard —")
    print("Answer each question; press Enter for the default. Type "
          f"'{DEFER_TOKEN}' on a slot to record it as {{{{DEFERRED}}}} for later.\n")

    # 1. topology — defaults seeded from --profile / --no-orchestrator
    seed_profile = _seed("profile")
    if seed_profile:
        three_default = seed_profile.startswith("3agent")
        gitsync_default = seed_profile.endswith("git-sync")
    else:
        three_default = not bool(_seed("no_orchestrator", False))
        gitsync_default = False
    three = _ask_yesno("Run a separate orchestrator? (3-agent; No = dual-role "
                       "owner / 2-agent)", three_default, input_fn)
    gitsync = _ask_yesno("Do the agents run on SEPARATE machines? "
                         "(git-sync transport; No = one shared filesystem)",
                         gitsync_default, input_fn)
    profile = ("3agent" if three else "2agent") + (".git-sync" if gitsync
                                                   else ".local")
    roles = ["owner", "builder"] + (["orchestrator"] if three else [])

    # 2. side names (validated at entry — underscore / bad charset rejected;
    #    seeded from --owner-side / --builder-side / --orch-side)
    seed_side = {"owner": _seed("owner_side", DEFAULT_SIDE_NAME["owner"]),
                 "builder": _seed("builder_side", DEFAULT_SIDE_NAME["builder"]),
                 "orchestrator": _seed("orch_side",
                                       DEFAULT_SIDE_NAME["orchestrator"])}
    role_side = {}
    for role in CANONICAL_ROLE_ORDER:
        if role not in roles:
            role_side[role] = DEFAULT_SIDE_NAME[role]
            continue
        # never seed an illegal default (a bad --*-side flag) into the prompt.
        cand = seed_side.get(role) or DEFAULT_SIDE_NAME[role]
        default = cand if SIDE_CHARSET_RE.match(cand) else DEFAULT_SIDE_NAME[role]
        role_side[role] = _ask_side_name(role, default, input_fn)

    # 3. principal — seeded from --principal (unless still the FILL sentinel)
    principal = _ask("Principal's name (the human who holds the gates)",
                     _seed("principal", "{{FILL: principal's name}}"), input_fn)

    # 4. repo
    slot_answers = {}
    repo = _ask("CANONICAL_REPO — the project repo the agents work on "
                "(path + remote + branch)", DEFER_TOKEN, input_fn)
    slot_answers["CANONICAL_REPO"] = repo

    # 5. reviewer (probe PATH)
    probe = which_fn("codex")
    if probe:
        suggest = "codex CLI via tools/reviewer_poller.py, model default"
        print(f"  (found a 'codex' CLI on PATH — suggested REVIEWER: {suggest})")
    else:
        suggest = DEFER_TOKEN
        print("  (no 'codex' CLI on PATH — a different-model Claude session is "
              "the documented fallback reviewer)")
    reviewer = _ask("REVIEWER — who reviews each side's work (type 'none' to "
                    "run without one)", suggest, input_fn)
    if reviewer.strip().lower() == "none":
        print("  ! REVIEWER = none. Independent cross-vendor review is the "
              "protocol's single biggest quality lever — running without it "
              "means no gate catches a bad round. Bind one as soon as you can "
              "(a different-model Claude session is a fine fallback).")
    slot_answers["REVIEWER"] = reviewer

    # 6. the remaining {{FILL}} walk (day-one vs deferrable), then git + plugin
    walk_fill_slots(roles, input_fn, slot_answers)

    git_init = _ask_yesno("Initialize the workspace as a git repo now?",
                          True, input_fn)
    manual_default = _seed("plugin_install", "marketplace") == "manual"
    manual = _ask_yesno("Install skills MANUALLY (copy into ~/.claude)? "
                        "No = marketplace plugin (recommended)", manual_default,
                        input_fn)
    plugin_mode = "manual" if manual else "marketplace"

    return {"profile": profile, "roles": roles, "role_side": role_side,
            "principal": principal, "slot_answers": slot_answers,
            "git_init": git_init, "plugin_mode": plugin_mode}


def run_git_init(dest, name, timeout=30):
    """Make `dest` a git repo with one initial commit. Non-fatal: returns
    (ok, message); a failure (no git, no identity, timeout) never aborts the
    stamp — the workspace is already written, git is a convenience here."""
    steps = [["git", "init", "-b", "main"],
             ["git", "add", "-A"],
             ["git", "commit", "-m", f"stamp {name} workspace"]]
    try:
        for cmd in steps:
            r = subprocess.run(cmd, cwd=str(dest), capture_output=True,
                               text=True, timeout=timeout)
            if r.returncode != 0:
                return False, (f"`{' '.join(cmd)}` failed: "
                               + (r.stderr or r.stdout or "").strip())
        return True, "git repo initialized on main with an initial commit"
    except subprocess.TimeoutExpired:
        return False, f"git init exceeded {timeout}s — left un-initialized"
    except OSError as e:
        return False, f"git not runnable ({e}) — left un-initialized"


def stamp(name, dest, profile, roles, role_side, principal,
          slot_answers=None, plugin_mode="marketplace"):
    """Write a complete workspace at `dest`. Returns 0 on success, 1 if `dest`
    exists and is non-empty. Pure of argparse: callers (main / the wizard /
    adopt_project / tests) resolve the config first, then call this.
    `plugin_mode` (marketplace | manual) shapes .claude/settings.json."""
    dest = Path(dest)
    if dest.exists() and any(dest.iterdir()):
        print(f"refusing: {dest} exists and is not empty", file=sys.stderr)
        return 1

    # A principal of 'defer' (wizard defer, or `--principal defer`) becomes a
    # DEFERRED marker so conformance WARNs — never a literal 'defer' silently
    # stamped as the principal's name (Codex M3).
    if principal is not None and principal.strip().lower() == DEFER_TOKEN:
        principal = "{{DEFERRED: principal's name}}"

    orch = "orchestrator" in roles

    today = dt.date.today().isoformat()
    (dest / "channel").mkdir(parents=True)
    # The shared review-round ledger (review-core.md): one row per round, each
    # side appends only its own rows. Stamped on init so the channel dir is
    # tracked and START_SESSION's "read INDEX.md" step finds a well-formed file.
    (dest / "channel" / "INDEX.md").write_text(
        f"# REVIEW-ROUND LEDGER — {name} [PROTOCOL v2.6]\n\n"
        "Append-only. Each side appends ONLY its own rows. ROUND-TYPE is one of\n"
        "FREEZE / RESULTS / FIX-CONFIRMATION (see review-convergence.md).\n"
        "Rounds used vs budget: default 2-3 substantive rounds per artifact "
        "(overridable in the REVIEWER binding notes); budget exhausted without "
        "the reviewer's own convergence declaration escalates to the principal "
        "— never auto-loop.\n\n"
        "| round | side | ROUND-TYPE | request file | verdict file (how written) | "
        "verdict summary | actions taken | next round |\n"
        "|---|---|---|---|---|---|---|---|\n",
        encoding="utf-8")
    (dest / "start").mkdir()
    for role in roles:
        (dest / "memory" / role).mkdir(parents=True)
        # Orchestrator gets its own richer index below; owner/builder get the
        # standard ⚡ working-state block + an initial Next Step so a cold
        # /wake reads a well-formed state from the very first session.
        if role != "orchestrator":
            (dest / "memory" / role / "MEMORY.md").write_text(
                f"# {name} — {role} memory index\n\n"
                f"ROLE_LOCK: this workspace's {role.upper()} sessions only.\n\n"
                "## ⚡ working state\n"
                "last unit: none (fresh stamp — never run)\n"
                "next channel entry: 1 · per-peer last-seen: none\n"
                "next review round: 1 · in-flight units: none\n"
                "gated/parked queue: empty\n"
                f"next auth-record id: {role}-0001 · auth-log tail: header\n\n"
                "## Next Step\n"
                "First session on this workspace: resolve any unbound slots in\n"
                "BINDINGS.md (ask the principal once), confirm ROLE_LOCK, then\n"
                "poll the channel and pick up the first task. Overwrite this\n"
                "line with the concrete next action before /sleep.\n",
                encoding="utf-8")
        (dest / "memory" / role / "auth-log.md").write_text(
            f"# AUTH-RECORD — {name} / {role} [PROTOCOL v2.6]\n\n"
            "Append-only, event-sourced. Single-writer: this role's sessions\n"
            "only, only for words the principal spoke into this session (or\n"
            "a relay verified per proxy-auth-core.md when PROXY_AUTH is on).\n"
            "Normative schema: agent-core/references/proxy-auth-core.md in\n"
            "the multi-agent-protocol repo. Events are never edited or deleted;\n"
            "corrections are new events referencing old ids.\n",
            encoding="utf-8")

    if "orchestrator" in roles:
        (dest / "memory" / "orchestrator" / "MEMORY.md").write_text(
            f"# {name} — orchestrator memory index\n\n"
            f"ROLE_LOCK: this workspace's ORCHESTRATOR sessions only.\n\n"
            "## ⚡ working state\n"
            "last tick: none (never ticked)\n"
            "next TASKQUEUE id: T4\n"
            "next channel entry: 1 · per-peer last-seen: none\n"
            "next auth grant id: orchestrator-0001 · auth-log tail: header\n"
            "dispatch log: memory/orchestrator/dispatch-log.md\n"
            "in-flight dispatches: none\n"
            "briefings: last sent none · next due first-morning\n"
            "decision menu: 0 items\n"
            "active preset: balanced · ledger tail: header\n\n"
            "## Next Step\n"
            "First orchestrator session: resolve any unbound BINDINGS slots\n"
            "(PROXY_AUTH + EMBARGOES confirmed by the principal directly),\n"
            "confirm ROLE_LOCK, then greet the principal and drain TASKQUEUE.\n"
            "Overwrite this line with the concrete next action before /sleep.\n",
            encoding="utf-8")
        (dest / "memory" / "orchestrator" / "dispatch-log.md").write_text(
            f"# DISPATCH LOG — {name} [PROTOCOL v2.6]\n\n"
            "Append-only. One line per dispatch:\n"
            "| id | date | task ref | target role | model (rule) | status | result |\n"
            "|---|---|---|---|---|---|---|\n",
            encoding="utf-8")
        (dest / "TASKQUEUE.md").write_text(
            f"# TASKQUEUE — {name} [PROTOCOL v2.6]\n\n"
            "T1-T3 below are EXAMPLE standing duties seeded by the stamp —\n"
            "when filling BINDINGS, prune/replace them to match the DUTIES\n"
            "binding (a duty in the queue that is not in DUTIES, or vice\n"
            "versa, is a bookkeeping bug). Ids are consumed either way:\n"
            "the next new task is T4+ even if T1-T3 are pruned.\n\n"
            "| id | date | requester | task | status |\n"
            "|---|---|---|---|---|\n"
            f"| T1 | {today} | stamp | standing: morning briefing (recurring) | queued |\n"
            f"| T2 | {today} | stamp | standing: EOD report (recurring) | queued |\n"
            f"| T3 | {today} | stamp | standing: cost-ledger day rollup (recurring) | queued |\n",
            encoding="utf-8")
        (dest / "memory" / "orchestrator" / "session-registry.md").write_text(
            f"# SESSION_REGISTRY — {name}\n\n"
            "| role | workspace | session link/id | model | last seen | current unit |\n"
            "|---|---|---|---|---|---|\n",
            encoding="utf-8")
        (dest / "memory" / "orchestrator" / "cost-ledger.md").write_text(
            f"# COST_LEDGER — {name}\n\n"
            "| date | dispatch | role | model | rule (preset/override/escalation/downgrade) | est. tokens/cost |\n"
            "|---|---|---|---|---|---|\n",
            encoding="utf-8")

    side_parts = [role_side[r] for r in CANONICAL_ROLE_ORDER if r in roles]

    # ROLE_ALIASES row: only the sides whose name was CHANGED from the role's
    # default side name. All-defaults => empty string => byte-identical stamp.
    alias_pairs = [f"{role_side[r]}→{r}"
                   for r in CANONICAL_ROLE_ORDER
                   if r in roles and role_side[r] != DEFAULT_SIDE_NAME[r]]
    alias_row = (f"| ROLE_ALIASES | {', '.join(alias_pairs)} |\n"
                 if alias_pairs else "")

    # Transport binding: the `.git-sync` profiles bind the git-sync transport
    # and need a WORKSPACE_REMOTE row (FILL at instantiation); the `.local`
    # profiles bind local-fs and carry no remote row.
    transport = "git-sync" if profile.endswith("git-sync") else "local-fs"
    remote_row = ("| WORKSPACE_REMOTE | {{FILL: remote URL + default branch}} |\n"
                  if transport == "git-sync" else "")

    bindings_text = BINDINGS_TEMPLATE.format(
        name=name, date=today, profile=profile,
        transport=transport, remote_row=remote_row,
        dest=dest.as_posix(), side_names=" / ".join(side_parts),
        alias_row=alias_row,
        orch_slots=ORCH_SLOTS if orch else "", principal=principal)
    # Wizard answers (CANONICAL_REPO / REVIEWER / …) collected pre-stamp are
    # spliced in here; DEFER_TOKEN answers become {{DEFERRED}} markers.
    bindings_text = apply_slot_answers(bindings_text, slot_answers)
    (dest / "BINDINGS.md").write_text(bindings_text, encoding="utf-8")
    # README roles line names the display name when a side was renamed
    # (e.g. `owner (as "engine")`); an unchanged side shows just the role.
    roles_disp = [(f'{r} (as "{role_side[r]}")'
                   if role_side[r] != DEFAULT_SIDE_NAME[r] else r)
                  for r in CANONICAL_ROLE_ORDER if r in roles]
    (dest / "README.md").write_text(
        README_TEMPLATE.format(name=name, date=today,
                               roles=", ".join(roles_disp), profile=profile),
        encoding="utf-8")

    shutil.copy(ROOT / "profiles" / "MODELS.md", dest / "MODELS.md")

    start_src = {
        "owner": ROOT / "plugins/agent-protocol/skills/owner-engine-agent/references/START_SESSION.md",
        "builder": ROOT / "plugins/agent-protocol/skills/helper-builder-agent/references/START_SESSION.md",
        "orchestrator": ROOT / "plugins/agent-protocol/skills/orchestrator-agent/references/START_SESSION.md",
    }
    for role in roles:
        src = start_src.get(role)
        target = dest / "start" / f"START_SESSION.{role}.md"
        if src and src.is_file():
            shutil.copy(src, target)
        else:
            target.write_text(
                f"# START_SESSION — {role} [instantiate from the "
                f"orchestrator-agent skill when authored]\n", encoding="utf-8")

    claude_dir = dest / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text(
        json.dumps(build_settings(plugin_mode), indent=2) + "\n",
        encoding="utf-8")

    wf_dir = dest / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "integrity.yml").write_text(INTEGRITY_WORKFLOW, encoding="utf-8")
    (dest / "tools").mkdir()
    (dest / "tools" / "validate_auth_log.py").write_text(
        AUTH_LOG_VALIDATOR, encoding="utf-8")

    # In-workspace conformance copy — a HYGIENE self-check, NOT a trust gate
    # (C2): running it from inside the workspace prints a SELF-CHECK MODE banner
    # because it is workspace-owned code. A mandatory provenance header (C/D-5)
    # records where and when it was stamped; to vet an unfamiliar workspace, run
    # the protocol checkout's copy instead.
    conf_src = ROOT / "tools" / "conformance_check.py"
    if conf_src.is_file():
        header = ("# STAMPED COPY — multi-agent-protocol PROTOCOL v2.6 @ "
                  f"{today}. In-workspace HYGIENE SELF-CHECK (workspace-owned "
                  "code); for a trust decision run the protocol checkout's "
                  "copy against this workspace.\n")
        src_text = conf_src.read_text(encoding="utf-8")
        if src_text.startswith("#!"):
            nl = src_text.index("\n") + 1
            src_text = src_text[:nl] + header + src_text[nl:]
        else:
            src_text = header + src_text
        (dest / "tools" / "conformance_check.py").write_text(
            src_text, encoding="utf-8")

    print(f"stamped {name} at {dest} (roles: {', '.join(roles)})")
    return 0


def print_next_steps(name, dest, roles, git_ok, git_msg,
                     plugin_mode="marketplace"):
    """The post-stamp NEXT STEPS block: exactly what the operator does now.

    The plugin section matches `plugin_mode`: `marketplace` shows the two
    `/plugin` commands (and notes the stamped settings.json re-installs at
    session start); `manual` shows the copy-into-~/.claude instructions and
    notes that settings.json deliberately OMITS the marketplace blocks so the
    manual copy is authoritative (C/D-7)."""
    lead = "orchestrator" if "orchestrator" in roles else "owner"
    print("\n=== NEXT STEPS ===")
    n = 1
    print(f"{n}. Fill every {{{{FILL}}}} in {dest}/BINDINGS.md "
          "(CANONICAL_REPO, REVIEWER, EMBARGOES first). {{DEFERRED}} markers "
          "are ones you chose to postpone — resolve before relying on them.")
    n += 1
    if git_ok:
        print(f"{n}. Git: {git_msg}. Add a private remote and push so history "
              "is protected.")
    else:
        print(f"{n}. Make it a repo: `cd {dest} && git init -b main && "
              "git add -A && git commit -m \"stamp workspace\"`"
              + (f"  (auto git-init: {git_msg})" if git_msg else "")
              + ", then push to a private remote.")
    n += 1
    print(f"{n}. Sanity-check it — from your PROTOCOL CHECKOUT (trust copy): "
          f"`python tools/conformance_check.py --workspace {dest}`. A fresh "
          "stamp shows WARNs for unfilled slots; `--strict` should be clean "
          "once every slot is resolved.")
    n += 1
    print(f"{n}. Open a Claude Code session IN {dest} and `/wake {lead}`.")
    if plugin_mode == "manual":
        print("\n--- plugin install: MANUAL (settings.json omits the "
              "marketplace blocks) ---")
        print("  cp -r plugins/agent-protocol/skills/* ~/.claude/skills/")
        print("  cp plugins/agent-protocol/commands/*.md ~/.claude/commands/")
        print("  (run from your protocol checkout; your ~/.claude copy is the "
              "one that loads — the workspace won't also pull the marketplace "
              "plugin.)")
    else:
        print("\n--- plugin install: MARKETPLACE (once per machine) ---")
        print("  /plugin marketplace add AIpandadreams/multi-agent-protocol")
        print("  /plugin install agent-protocol@multi-agent-protocol")
        print("  (the stamped .claude/settings.json also installs it at "
              "session start.)")


def _print_adoption_appendix(name, dest, refusal=False):
    """Print adopt_project.adoption_checklist(). Called on TWO wizard paths:
    (1) after a NON-EMPTY-DEST REFUSAL (`refusal=True`) — the ACTUAL adopter,
    who already has a collaboration sitting in `dest` and needs the in-place
    path; and (2) after a SUCCESSFUL stamp (`refusal=False`) — a clearly
    OPTIONAL pointer for the rarer case of replacing an ad-hoc collaboration,
    ignorable otherwise. Loaded lazily to avoid a new_project<->adopt_project
    import cycle; silent if the tool is absent."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "adopt_project", ROOT / "tools" / "adopt_project.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception:
        return
    if refusal:
        print("\n--- that directory already has content — if you are ADOPTING "
              "an existing collaboration IN PLACE, here's how ---")
    else:
        print("\n--- OPTIONAL: only if this workspace REPLACES an existing "
              "ad-hoc collaboration — otherwise ignore ---")
    print(mod.adoption_checklist(f"{name} at {dest}"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Stamp a dedicated per-project agent workspace.")
    ap.add_argument("--name", required=True)
    ap.add_argument("--dest", required=True)
    # default None so resolve_topology can tell "not given" from an explicit
    # choice (needed for the --no-orchestrator C3 conflict check).
    ap.add_argument("--profile", default=None, choices=PROFILE_CHOICES)
    ap.add_argument("--owner-side", default="owner")
    ap.add_argument("--builder-side", default="builder")
    ap.add_argument("--orch-side", default="orch")
    ap.add_argument("--principal", default="{{FILL: principal's name}}")
    ap.add_argument("--no-orchestrator", action="store_true",
                    help="DEPRECATED alias for --profile 2agent.local "
                         "(dual-role owner); errors if combined with a 3agent "
                         "profile")
    ap.add_argument("--wizard", action="store_true",
                    help="interactive pre-stamp walkthrough (skipped if stdin "
                         "is not a TTY)")
    ap.add_argument("--git-init", action="store_true",
                    help="initialize the stamped workspace as a git repo "
                         "(non-fatal)")
    ap.add_argument("--plugin-install", choices=PLUGIN_MODES,
                    default="marketplace",
                    help="how the stamped .claude/settings.json installs the "
                         "plugin: 'marketplace' (default) registers + enables "
                         "it; 'manual' OMITS those blocks for a hand-copied "
                         "~/.claude install (C/D-7)")
    args = ap.parse_args()

    git_init = args.git_init
    plugin_mode = args.plugin_install
    slot_answers = {}

    if args.wizard and sys.stdin.isatty():
        cfg = wizard_preflight(seed=args)
        profile, roles = cfg["profile"], cfg["roles"]
        role_side = cfg["role_side"]
        principal = cfg["principal"]
        slot_answers = cfg["slot_answers"]
        git_init = cfg["git_init"]
        plugin_mode = cfg["plugin_mode"]
    else:
        if args.wizard:
            print("(--wizard ignored: stdin is not an interactive terminal)",
                  file=sys.stderr)
        try:
            profile, roles = resolve_topology(args.profile, args.no_orchestrator)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        role_side = {"owner": args.owner_side, "builder": args.builder_side,
                     "orchestrator": args.orch_side}
        principal = args.principal

    rc = stamp(args.name, args.dest, profile, roles, role_side, principal,
               slot_answers=slot_answers, plugin_mode=plugin_mode)
    if rc != 0:
        # A non-empty-dest refusal under the wizard is exactly the operator who
        # already has an ad-hoc collaboration there — point them at adopt-in-
        # place rather than leaving them stuck (C/D — adoption appendix).
        if args.wizard and sys.stdin.isatty():
            _print_adoption_appendix(args.name, args.dest, refusal=True)
        return rc

    git_ok, git_msg = (False, "")
    if git_init:
        git_ok, git_msg = run_git_init(Path(args.dest), args.name)
        if not git_ok:
            print(f"(git-init: {git_msg})", file=sys.stderr)

    print_next_steps(args.name, args.dest, roles, git_ok, git_msg, plugin_mode)
    if args.wizard and sys.stdin.isatty():
        _print_adoption_appendix(args.name, args.dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
