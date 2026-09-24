- **What runs on the worker, in order, per request (this list and §6.2's lifecycle are ONE
  order, stated twice and required to byte-agree — v7-round C4; the `journal INTENT` and
  emission-comparison steps are in the list — v7-round F9b, F9d/C2):** §1 gate clauses →
  §2.2 predicates → §2.4 consumer agreement (read-time tier suppressed — §2.4/§4.1j,
  v7-round F7) → §4.1d outcome scan → **open the §6.2 verified handle → §3.1
  lock (on that handle) → ⛔ RE-VERIFY THE COMPLETE STATE ANCHOR UNDER THE LOCK — the
  §4.1e binding comparison: `pv.lane_date` vs the execution-time ET date FIRST (ordinary
  appends; a correction's lane is the sidecar's and is date-exempt — v8-round C1), then
  existence/creation disposition, size, whole-prefix sha256,
  final byte, epoch presence (and, on a correction, the §4.1f span re-derivation against
  `pv.correction`), each against `pv`; ANY difference ⇒ release, close, `PREVIEW_STALE`**
  → **recompute the emission; compare `emission_len` + `emission_sha256` against `pv`;
  ≠ ⇒ release, close, `binding-invalid` (§4.1e)** → **journal `INTENT` (§13.2's exact
  placement)** → single `fh.write` → read-back (same handle) → lock release →
  post-write revalidation (§6.2) → journal transition (`INTENT → APPENDED`, or §4.1g's
  outcome) → **CLOSE the append handle → THEN** the custody stage **per the SELECTED §5.2
  trigger**, on its own separately-opened §6.2 handle.
