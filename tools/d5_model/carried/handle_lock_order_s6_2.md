- **Read-handle lifecycle — THE ONE ORDER, stated here and repeated identically in §12
  (v7-round C4: v7's §6.2 closed the append handle before custody opened its own, while
  v7's §12 ran the custody stage before closing — mutually exclusive orders, and §12's
  makes custody's `FILE_APPEND_DATA` open fail on this handle's `FILE_SHARE_READ`-only
  share mode):** there is ONE handle per append operation, and it does all of that
  operation's I/O —
  open → post-open identity checks (below) → §3.1 byte-range lock **taken on this handle**
  → §4.1e binding re-read (`SetFilePointerEx(0)` + read to EOF, through this handle) →
  §4.1e emission recompute + compare → journal `INTENT` (§13.2) →
  single append `write` → read-back of the written span (same handle, seek to `pre_size`)
  → lock release → **post-write revalidation (below) → journal transition
  (`INTENT → APPENDED`, or the §4.1g outcome on failure) → CLOSE the append handle →
  ONLY THEN the custody stage, per the selected §5.2 trigger, on its OWN separately-opened
  handle** under this same contract (same access mask, same checks, same lock discipline).
  Custody's open happens strictly after this close, so the two handles never hold the
  share-mode exclusion at once — by ordering, not by luck. No read in this design is
  performed through a path-addressed re-open: every read after the identity checks goes
  through a handle those checks validated, which is what makes the checks worth running
  [[compare-at-the-point-of-difference]].
