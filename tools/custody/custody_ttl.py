#!/usr/bin/env python3
"""The custody-lease TTL of record — ONE number, pinned once, with its lineage.

⛔ WHY A MODULE AND NOT AN ENV VAR. `git_guard.main()` reads CUSTODY_TTL_SECONDS and
refuses when it is unset, which is right for a CLI. It is wrong for a WIRED caller:
an env var is settable per-shell, per-schtask and per-seat, so the fleet could run six
different TTLs while every seat believed it ran "the" one, and no artifact would record
which number actually guarded which act. The TTL is a MEASURED parameter (design O-1) and
a measured parameter belongs in the tree next to its derivation, not in an environment.

⛔ THERE IS DELIBERATELY NO ENV OVERRIDE HERE. Adding one re-opens exactly what the
measurement closed: a number that can be changed without changing a file cannot be
reviewed, cannot be blamed, and cannot be shown to have been in force at the time of an
act [[measured-numbers-discipline]]. If this number must change, it changes here, in a
commit, with a new authority line below.

═══ LINEAGE (newest first) ═══

TTL_SECONDS = 1223.9   ADOPTED (2026-08-24) by the principal, by a fleet ruling relayed through the orchestrator.

  Derivation:  a rescreen workpaper in the private workspace
  Instrument:  a rescreen instrument in the private workspace (controls all pass, rc=0)
  Rule:        TTL = max(600, R8 x 2) = max(600, 612.0 x 2) = 1223.9 s

  The screened R8 parameter is 612.0 s, governed by session ba3ebd63 on 2026-08-23
  10:00:09 -> 10:10:21, class `blocked-in-tool` -- a PowerShell call in flight across the
  whole window. It is the first number in the ladder with a MECHANISM rather than a
  distribution tail: the top observations cluster at 612.0 / 611.2 / 606.7 s against the
  published 600 s Bash/PowerShell tool ceiling, which is the physical bound on how long a
  HEALTHY seat can be unable to emit.

  ⚠ It is BELOW the [1451 s, 24 h] band of an earlier ruling's condition (d), and the delivered number was an
  R8-stage figure where that ruling's condition (a) named the R7 stage. Both misses were reported as
  misses (in a seat report) and routed to the principal rather than resolved at this seat; he retired
  the band floor on provenance (the 1451 s figure was VACATED by a later ruling) and extended
  the pre-authorisation to the 4-stage ladder. This constant therefore stands on his
  ruling, not on the earlier ruling's conditions being met.

  ⚠ RESIDUAL, carried not smoothed (the adopting ruling's condition (f)): the attempt log witnesses
  only 4.3% of lost-emission windows where the transcript witnesses 86.3%, because an
  attempt row is written BY the emitter and a hook killed before python starts leaves
  none. A seat frozen longer than this TTL loses its lease while alive; the fail direction
  of a too-SHORT TTL is lease-cleared-while-alive, which is the unrecoverable one.

SUPERSEDED
  1451 s -- an earlier ruling (2026-08-16), VACATED (2026-08-24) by a later ruling: derived on an
  instrument whose R6/R7 stages were never run on the corrected predicate. Never in force
  at any wired caller; it was the TTL of record on paper only.
"""

# The number. Changing it is a commit, and it owes a new lineage block above.
TTL_SECONDS = 1223.9

# Standing posture at wiring, NOT a per-call knob (design E1248 s4, recorded at plan P8).
# A caller wired False is a RE-OPENING of the E1245 s3 conflation -- the state "emitter is
# not running" would again read as "no peers are live" -- and is graded as that, never as
# a configuration detail. Both wired callers pass this; neither exposes it.
REQUIRE_SELF_LEASE = True

# The adopting fleet ruling, relayed by the orchestrator. Cited by both callers in their refusal text so an
# operator who is blocked can find the ruling that blocked them without asking anyone.
AUTHORITY = "a principal ruling (2026-08-24)"
