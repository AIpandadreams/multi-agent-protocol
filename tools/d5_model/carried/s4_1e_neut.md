> - **A FINAL UNTERMINATED LINE whose bytes begin with `<<CO-EPOCH` — or are any non-empty
>   prefix of the literal `<<CO-EPOCH v1 at=` (a tear can cut anywhere, including inside
>   the token; extending O1's named `<<CO-EPOCH`-prefix case down to one byte is a
>   this-seat choice, §10.2 — over-triggering refuses loudly, under-triggering reads a
>   tear as clean absence) — is NOT a marker AND is NOT pre-epoch content: it is itself an
>   UNSETTLED fragment.** The locator reports it (`torn_epoch_fragment`, offset + length),
>   the lane is UNSETTLED regardless of the (empty) scan region, and the outcome procedure
>   returns `TORN_ORPHAN_TAIL` naming that span — **a tear inside the first envelope-era
>   write's own epoch line REFUSES; it is never read as clean absence** (row 8 `ABSENT` is
>   unreachable while the fragment stands), which restores the guarantee §4.1d states
>   twice on the one input v8 broke it for. **The journal consequence is fixed at the same
>   stroke: §7.1c's reconciliation of that first write's `INTENT` sees `TORN_ORPHAN_TAIL`
>   and ESCALATES — the record never transitions to terminal `ABORTED` ("the intent never
>   landed") while the write's own torn bytes sit on disk.** The §4.1f exit applies as
>   everywhere: the fragment gets its §13.3 sidecar and its correction — whose emission
>   FIRST NEUTRALIZES the torn line (the NEUT rule, next bullet) and then re-carries the
>   epoch marker, since the lane still has no valid LF-terminated one (⛔ v9-round O4:
>   v9's bare re-carry COMPLETED the torn line into a grammar-valid marker with its own
>   leading LF, and FIRST-MATCH then anchored the boundary on the torn artifact).
> - ⛔ **THE NEUTRALIZING TOKEN — exact bytes, normative (v9-round O4; the opus verdict
>   MEASURED that under v9's charset grammar every truncation of the marker past `at=`
>   remained grammar-valid once LF-terminated — so the repair's own leading LF minted a
>   SECOND valid epoch line, the locator anchored on the TORN one, the fresh marker fell
>   into the scan region as a MALFORMED span, and the correction's superseded span was
>   stranded pre-epoch: the lane was permanently UNSETTLED by its own repair):** when
>   the span being answered by a correction ends in ⛔ **a FINAL UNTERMINATED LINE whose
>   bytes begin with `<<CO-EPOCH` — or are any non-empty prefix of the literal
>   `<<CO-EPOCH v1 at=`** (the torn-marker carve-out above — ⛔ **the trigger text is now
>   BYTE-IDENTICAL to that carve-out's text, v15, v14-round Q11: v14's trigger read only
>   "matching any non-empty prefix of `<<CO-EPOCH v1 at=`" while the carve-out it cites by
>   name reads "begins with `<<CO-EPOCH` **OR** any non-empty prefix of …", so A TEAR
>   INSIDE THE RENDERED TIMESTAMP SATISFIED THE CARVE-OUT AND NOT THE TRIGGER. Opus
>   confirmed both readings settle to the same SAFE outcome — no proper prefix of a valid
>   rendering is itself grammar-valid under the fixed-width `<RFC3339-EXACT>` form, so the
>   tear is recognized either way — making this a BUILDABILITY defect rather than a safety
>   one. But the two readings EMIT DIFFERENT BYTES on a preview-exact-bytes path, which is
>   the one place this design cannot afford two readings. The condition is written ONCE,
>   above, and QUOTED here** [[emitter-and-verifier-are-one-grammar]]), the
>   correction's emission begins with the exact bytes **`<<CO-EPOCH-NEUT v1`** followed
>   by LF — IN PLACE of the bare conditional LF — and only then the fresh epoch marker.
>   The completed line (torn residue + token) can complete NO reserved grammar: the
>   token's letters sit outside the tightened EPOCH timestamp charset wherever the tear
>   cut, its own first bytes `<<CO-` mean §2.2 rule 1 refuses it in any gated body, and
>   it is deliberately given no §4.1d grammar row (fused, it is pre-boundary content
>   covered by the correction's superseded span; bare, it can land only by hand and
>   reads RESERVED-MALFORMED — loud). **The token and its LF land INSIDE the superseded
>   span** — §4.1f step 2's arithmetic and the expanded-span `sha256` carry them, so
>   (a1) verifies over the neutralized bytes and the pre-boundary EPOCH-CANDIDATE
>   ANOMALY below is contained in a landed VALID-SUPERSESSION span, settling it.
>   **Battery obligation: tear the marker at EVERY byte offset; after the one
>   correction, assert exactly ONE boundary (the fresh marker) and row 8 `ABSENT`.**
