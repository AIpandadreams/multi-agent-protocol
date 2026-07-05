#!/usr/bin/env python3
"""Stamp a dedicated per-project agent workspace (PROTOCOL v2.5).

Creates the "dedicated, not generic" instantiation: a workspace directory
(intended to become its own private repo) holding bindings, channel skeleton,
per-role memory, MODELS.md, and instantiated start-session files. The skills
themselves stay in the multi-agent-protocol repo (installed via plugin
marketplace).

Usage:
  python tools/new_project.py --name myproject --dest path/to/myproject-ws \
      --profile 3agent.local --owner-side engine --builder-side builder \
      [--principal "Your Name"] [--no-orchestrator]
"""
import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BINDINGS_TEMPLATE = """# BINDINGS — {name} agent workspace [PROTOCOL v2.5]

Instantiated {date} from the multi-agent-protocol repo (profile: {profile}).
Slot glossary: plugins/agent-protocol/skills/agent-core/references/binding-slots.md

| slot | value |
|---|---|
| PROJECT | {name} |
| PROFILE | {profile} |
| SIDE_NAMES | {side_names} |
| CANONICAL_REPO | {{{{FILL: work repo path + remote + branch}}}} |
| CHANNEL | {dest}/channel/ (this workspace repo) |
| MEMORY | {dest}/memory/<role>/ |
| REVIEWER | {{{{FILL: per side — mechanism + model}}}} |
| PRINCIPAL | {principal} |
| PINNED_RESOURCES | {{{{FILL: exact IDs/paths, or "none"}}}} |
| SHARED_ARTIFACTS | none (add per agent-core conditions if needed) |
| SIGNING | {{{{FILL: gpg-local / webflow-api / sign-on-merge}}}} |
| HEARTBEAT | {{{{FILL: per role, offset}}}} |
| MODEL | see MODELS.md (active preset + overrides) |
| EMBARGOES / GATES | {{{{FILL: standing list + size tripwire}}}} |
| PROTOCOL_VERSION | v2.5 |
{orch_slots}"""

ORCH_SLOTS = """| FLAVOR | {{FILL: global-pa or project:<name>}} |
| PROXY_AUTH | off (default — only the principal, directly in the orchestrator session, may change this; if on, list ONLY enumerated reversible/internal gate classes plus explicit exclusions. The irreversible/outward super-classes — outward-facing/publish, email SEND, new-money/new-recipient, destructive-to-others, canonical-repo merge, PROXY_AUTH/gate/embargo/protocol changes — are never listable or relayable) |
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
"""Auth-log chain validator [PROTOCOL v2.5] — mechanical enforcement of the
exactly-one-landed-CONSUMED audit rule (proxy-auth-core.md) over every
memory/<role>/auth-log.md in this workspace:

  - no duplicate CONSUMED for the same consumption id (relay id or
    grant-id[/D<k>]) — a second CONSUMED for the same id is a violation
  - a relayed CONSUMED (id contains /R) must follow a RECEIVED block for
    that relay id in the SAME log
  - a RECEIVED block must reference a relay id actually RELAY-SENT in some
    log (fabricated relays fail) and must carry a source: provenance line
  - RELAY-SENT only for grants defined in the SAME log; direct CONSUMED
    only of grants defined in the SAME log (unknown ids fail — nothing is
    consumable that was never granted)
  - RELAY-SENT count per grant never exceeds the grant's scope
  - distinct direct CONSUMED ids per grant never exceed the grant's scope

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
            d["received"][in_recv] = {"line": n, "has_source": False}
            continue
        if SOURCE_RE.match(line) and in_recv and in_recv != "PENDING":
            d["received"][in_recv]["has_source"] = True
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
            locs = ", ".join(str(w) for w in where)
            bad.append(f"duplicate CONSUMED {cid} - {len(where)} events "
                       f"across: {locs} (exactly-one landed CONSUMED per "
                       "action, global)")
    for d in parsed:
        log = d["log"]
        for cid, n in d["cons_lines"]:
            if "/R" in cid:
                if cid not in d["received"]:
                    bad.append(f"{log}:{n}: CONSUMED {cid} has no RECEIVED "
                               "block in this log (record before reserve)")
            elif cid.split("/")[0] not in d["grants"]:
                bad.append(f"{log}:{n}: direct CONSUMED {cid} of a grant not "
                           "defined in this log (direct consumes live in the "
                           "granting session's own log)")
        for gid, rids in d["relays"].items():
            if gid not in d["grants"]:
                bad.append(f"{log}: RELAY-SENT for unknown grant {gid} "
                           "(relays are appended only to the granting log)")
            elif len(rids) > d["grants"][gid]:
                bad.append(f"{log}: grant {gid} scope {d['grants'][gid]} but "
                           f"{len(rids)} distinct RELAY-SENT ids")
        for rid, info in d["received"].items():
            if rid not in all_sent:
                bad.append(f"{log}:{info['line']}: RECEIVED {rid} matches no "
                           "RELAY-SENT in any log (fabricated relay)")
            if not info["has_source"]:
                bad.append(f"{log}:{info['line']}: RECEIVED {rid} lacks a "
                           "source: provenance line")
        for gid, cids in d["direct"].items():
            if gid in d["grants"] and len(cids) > d["grants"][gid]:
                bad.append(f"{log}: grant {gid} scope {d['grants'][gid]} but "
                           f"{len(cids)} distinct direct CONSUMED ids")


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
"""

SETTINGS_TEMPLATE = {
    "extraKnownMarketplaces": {
        "multi-agent-protocol": {
            "source": {
                "source": "github",
                "repo": "AIpandadreams/multi-agent-protocol",
            }
        },
    },
    "enabledPlugins": ["agent-protocol@multi-agent-protocol"],
    # unattended wakes stall on permission prompts they cannot answer —
    # pre-approve exactly the git/gh surface the channel loop needs
    "permissions": {
        "allow": [
            "Bash(git status:*)", "Bash(git log:*)", "Bash(git diff:*)",
            "Bash(git show:*)", "Bash(git fetch:*)", "Bash(git pull:*)",
            "Bash(git add:*)", "Bash(git commit:*)", "Bash(git push:*)",
            "Bash(git checkout:*)", "Bash(git switch:*)",
            "Bash(git branch:*)", "Bash(git rev-parse:*)",
            "Bash(git merge-base:*)", "Bash(gh pr create:*)",
            "Bash(gh pr view:*)", "Bash(gh pr list:*)",
            "Bash(gh run list:*)", "Bash(gh run view:*)",
            "Bash(python tools/validate_auth_log.py)",
        ]
    },
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--dest", required=True)
    ap.add_argument("--profile", default="3agent.local",
                    choices=["2agent.local", "3agent.local"])
    ap.add_argument("--owner-side", default="owner")
    ap.add_argument("--builder-side", default="builder")
    ap.add_argument("--orch-side", default="orch")
    ap.add_argument("--principal", default="{{FILL: principal's name}}")
    ap.add_argument("--no-orchestrator", action="store_true")
    args = ap.parse_args()

    dest = Path(args.dest)
    if dest.exists() and any(dest.iterdir()):
        print(f"refusing: {dest} exists and is not empty", file=sys.stderr)
        return 1

    roles = ["owner", "builder"]
    if not (args.no_orchestrator or args.profile.startswith("2agent")):
        roles.append("orchestrator")
    orch = "orchestrator" in roles

    today = dt.date.today().isoformat()
    (dest / "channel").mkdir(parents=True)
    (dest / "channel" / ".gitkeep").write_text("", encoding="utf-8")
    (dest / "start").mkdir()
    for role in roles:
        (dest / "memory" / role).mkdir(parents=True)
        # Orchestrator gets its own richer index below; owner/builder get the
        # standard ⚡ working-state block + an initial Next Step so a cold
        # /wake reads a well-formed state from the very first session.
        if role != "orchestrator":
            (dest / "memory" / role / "MEMORY.md").write_text(
                f"# {args.name} — {role} memory index\n\n"
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
            f"# AUTH-RECORD — {args.name} / {role} [PROTOCOL v2.5]\n\n"
            "Append-only, event-sourced. Single-writer: this role's sessions\n"
            "only, only for words the principal spoke into this session (or\n"
            "a relay verified per proxy-auth-core.md when PROXY_AUTH is on).\n"
            "Normative schema: agent-core/references/proxy-auth-core.md in\n"
            "the multi-agent-protocol repo. Events are never edited or deleted;\n"
            "corrections are new events referencing old ids.\n",
            encoding="utf-8")

    if "orchestrator" in roles:
        (dest / "memory" / "orchestrator" / "MEMORY.md").write_text(
            f"# {args.name} — orchestrator memory index\n\n"
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
            f"# DISPATCH LOG — {args.name} [PROTOCOL v2.5]\n\n"
            "Append-only. One line per dispatch:\n"
            "| id | date | task ref | target role | model (rule) | status | result |\n"
            "|---|---|---|---|---|---|---|\n",
            encoding="utf-8")
        (dest / "TASKQUEUE.md").write_text(
            f"# TASKQUEUE — {args.name} [PROTOCOL v2.5]\n\n"
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
            f"# SESSION_REGISTRY — {args.name}\n\n"
            "| role | workspace | session link/id | model | last seen | current unit |\n"
            "|---|---|---|---|---|---|\n",
            encoding="utf-8")
        (dest / "memory" / "orchestrator" / "cost-ledger.md").write_text(
            f"# COST_LEDGER — {args.name}\n\n"
            "| date | dispatch | role | model | rule (preset/override/escalation/downgrade) | est. tokens/cost |\n"
            "|---|---|---|---|---|---|\n",
            encoding="utf-8")

    side_parts = []
    if "owner" in roles:
        side_parts.append(args.owner_side)
    if "builder" in roles:
        side_parts.append(args.builder_side)
    if orch:
        side_parts.append(args.orch_side)
    (dest / "BINDINGS.md").write_text(
        BINDINGS_TEMPLATE.format(name=args.name, date=today,
                                 profile=args.profile, dest=dest.as_posix(),
                                 side_names=" / ".join(side_parts),
                                 orch_slots=ORCH_SLOTS if orch else "",
                                 principal=args.principal),
        encoding="utf-8")
    (dest / "README.md").write_text(
        README_TEMPLATE.format(name=args.name, date=today,
                               roles=", ".join(roles), profile=args.profile),
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
        json.dumps(SETTINGS_TEMPLATE, indent=2) + "\n", encoding="utf-8")

    wf_dir = dest / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "integrity.yml").write_text(INTEGRITY_WORKFLOW, encoding="utf-8")
    (dest / "tools").mkdir()
    (dest / "tools" / "validate_auth_log.py").write_text(
        AUTH_LOG_VALIDATOR, encoding="utf-8")

    print(f"stamped {args.name} at {dest} (roles: {', '.join(roles)})")
    print("next: fill every {{FILL}} in BINDINGS.md, git init + private "
          "remote, then run each role's first session.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
