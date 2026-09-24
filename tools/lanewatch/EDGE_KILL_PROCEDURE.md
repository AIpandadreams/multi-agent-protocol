# Edge kill procedure — REVIEWED PROCEDURE for a SEAT to run

Commissioned by an orchestrator ruling ("a kill procedure that satisfies the PID rule"),
shaped by an earlier entry's constraint: **this lands as a reviewed procedure a seat
executes deliberately — never as something a control or the census executes.**
`watcher_census.py` has no kill path *as an absent capability*, and this file
does not change that: it is instructions for a human-supervised seat act.

## 0. Authority

- Killing an edge is a seat act at the seat that owns the affected lane(s).
  Killing an edge whose receipt names ANOTHER seat's role requires that seat's
  (or orch's) concurrence first — the receipt's `role=` says whose lane goes
  dark if this goes wrong.
- A `SURPLUS` verdict is a hygiene claim, not a kill order. `SURPLUS-HELD`
  and `CURRENT` edges are NOT kill candidates under this procedure at all —
  see step 2.

## 1. Preconditions (all of them, same sitting)

1. A **fresh census** (`python tools/lanewatch/watcher_census.py`), run within
   the last few minutes. Stale censuses name recycled pids — the pid.win
   namespace recycles, and the census's own receipt join had to learn that
   (control arm 20f).
2. The target pid appears as an edge in that census (persistent across both
   snapshots — a transient is not a target, it self-clears).
3. The target's identity is read from the census row — **the receipt, the
   member list, and the serving verdict — never reconstructed from memory or
   from a process-name listing.**

## 2. What may be killed

- **`SURPLUS` only** (superseded AND the successor proven serving), or an
  edge orch/the principal has explicitly ruled dead by id.
- An edge that is any seat's **only serving arm** (`SERVING(obs)` naming its
  pid in the seat's `.hb`) must be **replaced first, killed second**:

  a. Arm the replacement watcher at the owning seat (normal SOP-4 arm).
  b. Verify the replacement: new `ARMED` line in `<seat>.chan.obs` with the
     NEW pid.win, and `<seat>.chan.hb` writer flips to (or alternates with)
     the new pid within ~3 poll intervals.
  c. Only then kill the old edge. The lane must never have zero serving
     watchers between the two acts — the ordering IS the procedure.

## 3. The kill (PID rule — verbatim discipline)

- **Exact PID from the edge's own receipt/census row. NEVER by process name,
  never by "looks stale".** Multiple agents and schtasks share this machine.
- PowerShell, not Git Bash (MSYS mangles `/PID`):

  ```powershell
  taskkill /PID <pid.win> /T /F
  ```

  `/T` is load-bearing: a watcher owns per-poll subshell children, and the
  tree flag takes them with it instead of orphaning them.
- One pid per command. No wildcard, no name filter, no loop over a listing.

## 4. Post-verification (the act is not done until this is)

1. Re-run the census. The killed pid must be GONE from both snapshots and the
   edge count must drop by exactly the expected number.
2. If the edge was a heartbeat writer: confirm `<seat>.chan.hb` is now written
   by the replacement pid (step 2b's pid), not frozen at the dead one — a
   frozen `.hb` will grade the seat DOWN at its next wake (SOP-4).
3. Record the act in the acting seat's lane entry: target pid, receipt line
   quoted, census timestamps (pre and post), and the replacement's ARMED line.

## 5. Known limits, stated

- The census's session attribution is UNREGISTERED for every edge until
  `arm_register.py register` is wired into the arm paths — so "whose session
  armed this" is currently answerable only from the receipt's `role=`, which
  names the SEAT, not the session. Do not infer session ownership from
  ancestry: parent-death is a constant across healthy and leaked edges
  (measured 5/5).
- `taskkill /T` kills the tree rooted at the pid; a subshell mid-poll dies
  with it. That is intended — but it is also why /T on a WRONG pid is worse
  than no /T. The exactness discipline in §3 is the mitigation.
