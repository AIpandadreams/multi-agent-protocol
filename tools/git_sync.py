#!/usr/bin/env python3
"""git-sync reference helper [PROTOCOL v2.6] — the retry policy, executable.

The git-sync transport (transports/git-sync.md) rebinds the channel verbs to git
operations. Two of them carry non-obvious retry rules that are easy to get wrong
by hand, so they live here as a small, stdlib-only, dependency-free reference:

  - publish(repo, mode=...) — push, and on a push reject do the RIGHT thing for
    the commit's class:
      * append      : fetch + rebase onto the new tip + re-push, bounded to
                      max_attempts. A rebase CONFLICT is not resolved — it is a
                      protocol-violation detector (a writer touched a file it
                      does not own), so publish aborts the rebase and reports it.
      * reservation : an auth-log CONSUMED event. On reject the loser DROPS the
                      reservation (hard-reset to the fetched tip) and reports
                      "re-verify" — it is NEVER carried through the rebase loop,
                      because rebasing a CONSUMED on top of a peer's could
                      double-spend the grant (proxy-auth-core.md).
  - poll(repo, ...) — fetch, then report the commits the remote has that the
    local checkout does not (fetch-before-act).

This is a REFERENCE, not a driver: it runs git and reports; it never resolves a
conflict, never force-pushes, never signs on your behalf. The caller stages and
commits the files it owns (by explicit path) before calling publish().

CLI (for a quick manual check; the library API is the real interface):
  python tools/git_sync.py poll    --repo path/to/clone --branch main
  python tools/git_sync.py publish --repo path/to/clone --branch main \\
      --mode append
"""
import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, NamedTuple, Optional


class PublishResult(NamedTuple):
    ok: bool
    attempts: int
    action: str          # pushed | reservation-dropped | conflict | lane-down
    detail: Optional[str]


class PollResult(NamedTuple):
    fetched: bool
    new_commits: List[str]   # remote commits absent locally, oldest-first
    error: Optional[str]


def _git(repo, *args, check=False):
    """Run one git command in `repo`, capturing text output. check=False by
    default: the retry logic inspects returncodes rather than raising."""
    return subprocess.run(["git", *args], cwd=str(repo), check=check,
                          capture_output=True, text=True)


def publish(repo, branch: str = "main", mode: str = "append",
            remote: str = "origin", max_attempts: int = 3) -> PublishResult:
    """Push the local branch, applying the class-specific reject rule.

    Preconditions: the caller has already committed the files it owns onto
    `branch` (APPEND). publish only handles the push + reject loop.
    """
    if mode not in ("append", "reservation"):
        raise ValueError(f"mode must be 'append' or 'reservation', got {mode!r}")

    for attempt in range(1, max_attempts + 1):
        push = _git(repo, "push", remote, branch)
        if push.returncode == 0:
            return PublishResult(True, attempt, "pushed", None)

        # Push rejected: the remote moved under us. Fetch the remote (no
        # branch arg, so the clone's default refspec updates the
        # `<remote>/<branch>` tracking ref — `git fetch <remote> <branch>` only
        # moves FETCH_HEAD and would leave us rebasing onto a stale tip).
        _git(repo, "fetch", remote)
        target = f"{remote}/{branch}"

        if mode == "reservation":
            # DROP: discard the local reservation commit(s) and re-verify from
            # the fetched tip. Never rebase a CONSUMED forward — that risks a
            # double-spend of the grant.
            _git(repo, "reset", "--hard", target)
            return PublishResult(
                False, attempt, "reservation-dropped",
                "grant may have been consumed by the peer — re-verify from the "
                "new tip before reserving again")

        # append: rebase our own commits onto the new tip, then retry the push.
        reb = _git(repo, "rebase", target)
        if reb.returncode != 0:
            _git(repo, "rebase", "--abort")
            return PublishResult(
                False, attempt, "conflict",
                "non-ff content conflict on rebase — DISCONTINUITY: a writer "
                "committed a file it does not own (each writer owns disjoint "
                "paths, so honest concurrent work never conflicts)")
        # rebase clean; loop and re-push

    return PublishResult(
        False, max_attempts, "lane-down",
        f"push still rejected after {max_attempts} attempts — mark the lane "
        "DOWN and escalate")


def poll(repo, branch: str = "main", remote: str = "origin",
         since: Optional[str] = None) -> PollResult:
    """Fetch, then list remote commits the local checkout lacks.

    `since` is the last-seen commit (a sha or ref); commits AFTER it on the
    remote branch are returned oldest-first. Defaults to local HEAD, so the
    result is "what the remote has that I don't".
    """
    # Fetch the remote (no branch arg) so the `<remote>/<branch>` tracking ref
    # is updated by the clone's default refspec — the comparison below reads it.
    fetch = _git(repo, "fetch", remote)
    if fetch.returncode != 0:
        return PollResult(False, [], (fetch.stderr or "fetch failed").strip())
    base = since or "HEAD"
    rev = _git(repo, "rev-list", "--reverse", f"{base}..{remote}/{branch}")
    shas = rev.stdout.split() if rev.returncode == 0 else []
    return PollResult(True, shas, None)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("publish", help="push with class-specific retry")
    pp.add_argument("--repo", required=True)
    pp.add_argument("--branch", default="main")
    pp.add_argument("--remote", default="origin")
    pp.add_argument("--mode", choices=["append", "reservation"],
                    default="append")
    pp.add_argument("--max-attempts", type=int, default=3)

    po = sub.add_parser("poll", help="fetch + report new remote commits")
    po.add_argument("--repo", required=True)
    po.add_argument("--branch", default="main")
    po.add_argument("--remote", default="origin")
    po.add_argument("--since", default=None)

    args = ap.parse_args()
    repo = Path(args.repo)
    if not (repo / ".git").exists():
        print(f"git_sync: {repo} is not a git checkout", file=sys.stderr)
        return 2

    if args.cmd == "publish":
        r = publish(repo, args.branch, args.mode, args.remote,
                    args.max_attempts)
        print(f"publish: ok={r.ok} action={r.action} attempts={r.attempts}")
        if r.detail:
            print(f"  {r.detail}")
        return 0 if r.ok else 1

    r = poll(repo, args.branch, args.remote, args.since)
    if not r.fetched:
        print(f"poll: fetch failed — {r.error}", file=sys.stderr)
        return 1
    print(f"poll: {len(r.new_commits)} new remote commit(s)")
    for sha in r.new_commits:
        print(f"  {sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
