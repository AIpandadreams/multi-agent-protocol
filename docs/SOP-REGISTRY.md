# SOPs and the cross-team registry [PROTOCOL v2.6]

Standing Operating Procedures are **principal-ruled standing orders layered on
top of the protocol**. The protocol defines the invariant machinery (roles,
channel, review, gates); SOPs capture the principal's evolving operating
doctrine — reviewer-model pins, decision-presentation rules, overnight
expectations — without amending protocol text each time.

## Rules

1. **Master numbers, never renumbered.** An SOP gets the next free number at
   adoption and keeps it forever. Retire an SOP by marking it retired — its
   number is never reused.
2. **Provenance on every SOP.** Who ruled it, when, verbatim wording where
   possible, and the authorization/log reference if the deployment keeps one.
3. **Scope declared at adoption:** per-team or ALL-TEAMS. An ALL-TEAMS SOP
   carries the same number in every workspace by design; distribution runs
   through each team's principal-comms routing seat and is recorded.
4. **The registry file.** Every workspace carries an identical `SOPS.md` at
   its root: one table row per master number, per-team meaning, scope, and
   adoption date(s). Authoritative FULL text lives in each workspace's
   `BINDINGS.md` SOP addenda (or equivalent); the registry is the cross-team
   index. Update every copy in the same wave — a stale registry is worse than
   none.

## The collision lesson

In the originating deployment, two teams independently minted "SOP-2" and
"SOP-4" for DIFFERENT rules before a registry existed. The fix was NOT
renumbering (principal-dated adoptions stand as written): the collisions are
documented in the registry, and the standing rule is that any cross-team
artifact cites SOPs **team-qualified** ("t1-SOP-4", "t2-SOP-2"). A bare
number is valid only inside its own team's workspace.

Start the registry on day one and mint numbers from a single sequence, and
you never need this lesson.

## Registry row format

```markdown
| # | team A meaning | team B meaning | scope | adopted |
|---|---|---|---|---|
| SOP-3 | Fallback judge = <fixed model> ALWAYS; author==judge-model → fresh isolated session | same (adopted verbatim) | ALL TEAMS | <adoption date> (<auth-log ref>) |
```

## A generalized starter catalog

A worked catalog of eight battle-tested SOPs (principal-comms routing,
fan-out pre-flight gate, rolling decisions sheet, fixed fallback judge,
persistent wake monitors, end-of-turn honesty guard, overnight
queue-emptying, reviewer model pin, convergence-before-decisions,
external status-board sync) is in
[docs/CREATOR-SEAT-BOOTSTRAP.md](CREATOR-SEAT-BOOTSTRAP.md), Part 5. Adopt
what fits; the registry pattern above is the part every deployment should
keep regardless.
