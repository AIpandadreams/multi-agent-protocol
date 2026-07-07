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
    action: str
    detail: Optional[str]
    # `action` values, and what each means for LOCAL state:
    #   pushed               push succeeded — remote advanced, nothing to redo.
    #   reservation-dropped  CONFIRMED contention on a reservation-class push:
    #                        the local CONSUMED was hard-reset away; re-verify
    #                        the grant from the new tip before reserving again.
    #   mixed-publish        caller bug — more than the single reservation
    #                        commit was ahead; NOTHING dropped, local intact.
    #   conflict             rebase hit a content conflict (a writer touched a
    #                        file it does not own); rebase aborted, local intact.
    #   lane-down            still rejected after max_attempts of CONFIRMED
    #                        contention; any rebase done is kept, nothing lost.
    #   transport-error      push was rejected AND the follow-up fetch failed
    #                        (network / auth / bad remote URL) — the reject
    #                        cause is unknown, so NOTHING was mutated locally.
    #   rejected-no-contention  push rejected but a successful fetch shows the
    #                        remote did NOT move — a server-side refusal
    #                        (protected branch, pre-receive hook, permissions),
    #                        not a lost race; NOTHING was mutated locally.


class PollResult(NamedTuple):
    fetched: bool
    new_commits: List[str]   # remote commits absent locally, oldest-first
    error: Optional[str]


def _git(repo, *args, check=False):
    """Run one git command in `repo`, capturing text output. check=False by
    default: the retry logic inspects returncodes rather than raising."""
    return subprocess.run(["git", *args], cwd=str(repo), check=check,
                          capture_output=True, text=True)


def _count_ahead(repo, target: str) -> int:
    """How many commits `target` (a tracking ref) has that local HEAD lacks.

    >0 means the remote genuinely moved ahead of us (real contention); 0 means
    it did not (a rejected push is then a server-side refusal, not a lost race);
    -1 means the count could not be determined (treat as: do not mutate)."""
    r = _git(repo, "rev-list", "--count", f"HEAD..{target}")
    if r.returncode != 0:
        return -1
    try:
        return int(r.stdout.strip())
    except ValueError:
        return -1


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

        # Push rejected. Before applying ANY class rule, establish WHY, because
        # the class rules mutate local state (reset/rebase) and must never fire
        # on a reject that is not concurrent contention.
        #
        # Step 1 — fetch. Use no branch arg so the clone's default refspec
        # updates the `<remote>/<branch>` tracking ref (`git fetch <remote>
        # <branch>` only moves FETCH_HEAD, leaving a stale tracking tip). If the
        # fetch ITSELF fails, the reject cause is unknowable (network / auth /
        # bad remote URL) — return a transport error and mutate NOTHING. This is
        # the bug the MAJOR finding caught: a broken remote used to fall through
        # to a hard-reset that destroyed the local reservation.
        fetch = _git(repo, "fetch", remote)
        if fetch.returncode != 0:
            return PublishResult(
                False, attempt, "transport-error",
                "push was rejected and the follow-up fetch also failed — the "
                "reject cause is unknown, so nothing was changed locally; "
                "resolve connectivity/credentials and retry. git said: "
                + (fetch.stderr or fetch.stdout or "").strip())
        target = f"{remote}/{branch}"

        # Step 2 — did the remote actually MOVE? A rejected push whose remote
        # tip we already contain is NOT a lost race (protected branch, a
        # pre-receive hook, or missing permissions); applying a class rule would
        # reset/rebase good local work for no reason. Return non-contention and
        # mutate NOTHING.
        remote_ahead = _count_ahead(repo, target)
        if remote_ahead < 0:
            return PublishResult(
                False, attempt, "transport-error",
                f"push rejected; could not determine whether {target} moved "
                "after fetch (rev-list failed) — nothing was changed locally")
        if remote_ahead == 0:
            return PublishResult(
                False, attempt, "rejected-no-contention",
                "push was rejected but the remote has not moved (no new commits "
                "to integrate) — this is a server-side refusal (protected "
                "branch, pre-receive hook, or permissions), not a lost race; "
                "nothing was changed locally. Resolve the refusal, then retry")

        # Confirmed contention: the remote moved. Now the class rules apply.
        if mode == "reservation":
            # Guard the drop: reservation commits publish ALONE (mixing
            # classes in one push is a caller bug per the transport spec). If
            # anything besides the single reservation commit is ahead, refuse
            # to reset — a blind --hard here would silently discard the extra
            # commits, and silent loss is worse than a loud caller error.
            count = _git(repo, "rev-list", "--count", f"{target}..HEAD")
            try:
                ahead = int(count.stdout.strip())
            except ValueError:
                ahead = -1
            if ahead != 1:
                return PublishResult(
                    False, attempt, "mixed-publish",
                    f"{ahead} local commit(s) ahead of {target} on a "
                    "reservation-class publish — reservation commits publish "
                    "ALONE; nothing was dropped. Separate the commits and "
                    "publish each under its own class")
            # DROP: discard the local reservation commit and re-verify from
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
