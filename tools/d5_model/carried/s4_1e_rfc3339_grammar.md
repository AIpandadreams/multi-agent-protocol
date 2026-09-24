> - **The boundary is the first LF-TERMINATED line in the file that byte-matches
>   `^<<CO-EPOCH v1 at=<RFC3339-EXACT>$` — where `<RFC3339-EXACT>` :=
>   `[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}[+\-][0-9]{2}:[0-9]{2}`,
>   the EXACT byte form the emitter renders `<iso>` in (⛔ TIGHTENED in v10, v9-round
>   O4/C1: v9's `[0-9T:+\-\.]+` accepted every truncation of a real marker past `at=`,
>   so a torn marker completed by any later LF became a grammar-valid boundary; under the
>   exact form every truncation is grammar-invalid) — AND begins at offset 0 or immediately after an
>   LF.** (The same regex as §4.1d's `EPOCH` row, restated here because THIS is its
>   anchoring: line-start = offset 0 or the byte after an LF on disk; line-end = a real LF
>   on disk. A byte-identical sequence sitting mid-line matches nothing.) The scan region
>   is `[boundary-LF offset + 1, EOF)`. No such line ⇒ no marker ⇒ the bootstrap rule's
>   empty scan region — with the torn-marker carve-out next.
