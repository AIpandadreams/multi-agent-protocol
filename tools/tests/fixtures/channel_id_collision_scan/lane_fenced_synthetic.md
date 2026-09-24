<!-- FIXTURE - NOT A CHANNEL ENTRY. Source: SYNTHETIC (2026-08-03 arm-(b) repair).
     Derivation note: short-form orch headings (real mechanism, 9xxx synthetic ids) plus
     exactly ONE `## ` line inside a ``` fence, so the controls' INDEPENDENT fence state
     machine is exercised non-vacuously. The fenced line is deliberately ID-FREE - no
     ENTRY/ORCH/BO tokens and no digits at all - so it can never contribute to any
     per-prefix literal (the grain rule: fenced `^## ` lines feed ONLY the independent
     fence count, never the id literals).
     FROZEN: the arm-(b) literals in channel_id_collision_scan_controls.py are
     hand-derived from THIS byte content - do not edit without re-deriving them. -->

## SYN-9203 . 2026-01-07 . entry that quotes a heading shape

body before the fence:

```text
## fenced pseudo-heading - deliberately id-free
```

body after the fence.

## SYN-9204 . 2026-01-07 . second real entry

unique fixture body epsilon
