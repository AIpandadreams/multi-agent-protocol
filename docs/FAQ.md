# FAQ

**Do I need three agents?**
The default is three (`3agent.local`) — orchestrator + owner + builder,
with the orchestrator as your single point of contact. Want it more
compact? Run with a **dual-role owner** (`2agent.local`): the owner absorbs
the orchestrator's interface and intake duties and you talk to it directly.
You can split the role back out any time ([CONFIGURATIONS.md](CONFIGURATIONS.md)
has the path — nothing restamps).

**Do I need Codex?**
You need an *independent reviewer* — that's a protocol requirement, not a
vendor pick. Codex is the worked example (`tools/reviewer_poller.py`); any
second-vendor CLI, or a Claude session on a model different from the
author's, satisfies the contract. What's forbidden is the author's own
model instance reviewing its own work.

**Why a separate workspace repo? Can't the agents just use my project repo?**
The coordination record has different integrity rules than your code:
append-only files, per-role subtree ownership, monotonic counters, a CI
that exists to protect *history* rather than correctness. Mixing that into
your work repo pollutes both. The workspace is cheap — one `new_project.py`
run — and your project repo stays clean.

**What do /sleep and /wake actually do?**
`/sleep`: checkpoint the role's memory (with an exact `## Next Step`),
commit + push, print a change log and a one-line handover, declare the
session safe to close. `/wake <role>`: run the role's START_SESSION
contract in a fresh session — bind, verify integrity, read the ⚡
working-state block, report the resume point. Together they make sessions
disposable: no context pasting, no "where were we".

**What happens if a session dies without /sleep?**
The discipline is checkpoint-after-every-shipped-unit, so the loss is
bounded to the unit in flight. The next `/wake` reads the last checkpoint,
notices the gap against the channel/git state, and reports it rather than
papering over it. (This is tested — see [DESIGN.md](DESIGN.md).)

**Can the orchestrator approve things for me?**
Never on its own authority — it carries bytes, not permission. With
PROXY_AUTH off (the default) it brings decisions to you and you approve in
whichever session acts. With PROXY_AUTH on, your *recorded verbatim words*
travel to workers as validated log events for enumerated gate classes
only — and the irreversible/outward super-classes (outward-facing/publish
actions, email SEND, new-money/new-recipient financial actions, destructive
operations on another party's artifacts, canonical-repo merges, and changes to
PROXY_AUTH / gates / embargoes / the protocol) are first-hand-only in every
configuration.

**Does this send my data anywhere?**
No. No telemetry, no network calls beyond the git remotes you configure.
The tools are plain Python; the "protocol" is markdown files your agents
read.

**Which models should I use?**
Whatever your budget likes — `MODELS.md` in each workspace has five
presets and takes overrides per role. The one hard rule: the reviewer is
never the author's model instance.

**Windows only?**
No — paths and examples are OS-neutral; Claude Code and the Python tools
run anywhere. Some unattended-heartbeat recipes are written
scheduled-task-first because that's where they've run longest; cron
equivalents are one-liners.

**Where's the cloud version?**
Shipped. Peers on separate machines (or a live session plus a scheduled
cloud twin) coordinate over a git remote via the `git-sync` transport —
stamp a `2agent.git-sync` / `3agent.git-sync` workspace and read
[transports/git-sync.md](../transports/git-sync.md) +
[CLOUD.md](CLOUD.md). CLOUD.md is deliberately honest about the hosted-cloud
host class and the platform surface its automerge recipe depends on.

**Can I change the protocol for my deployment?**
Bind anything bindable (that's most things: cadences, models, gates,
duties). For the protocol files themselves, the self-improvement loop
applies: reviewed PR, human merge, version bump — the point of the
exercise is that *agents* can't quietly rewrite their own rules; you can
do what you like in your fork.
