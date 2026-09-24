> ⛔ **THE EMITTER'S RENDERING OF `<iso>` IS NORMATIVE, not a library default (v10-round
> O5 — through v10 the `<RFC3339-EXACT>` grammar DESCRIBED the emitter while nothing
> CONSTRAINED it, and the verdict measured the naturally-chosen implementation
> non-conforming: Python `datetime.isoformat()` yields `…T12:00:00.123456-04:00` in the
> ordinary case but `…T12:00:00-04:00` when microseconds are exactly 0 — the fraction is
> ELIDED, the emitted marker matches no grammar row, the locator finds no boundary, and
> the LF-terminated line starting `<<CO-` is a pre-boundary EPOCH-CANDIDATE ANOMALY ⇒
> the lane refuses, permanently, on its very first envelope-era write, ~1 write in 10⁶):**
> the emitter renders `<iso>` as, exactly and always:
>
> - the local-time fields via the byte-exact pattern `%Y-%m-%dT%H:%M:%S.%f` — where
>   `%f` is **ALWAYS SIX fractional digits, zero-padded** (microsecond 0 renders
>   `.000000`, never elided, never shortened);
> - followed by the UTC offset rendered **separately** as sign (`+` or `-`), two
>   zero-padded hour digits, `:`, two zero-padded minute digits — **always numeric
>   `±HH:MM`, NEVER `Z`, never omitted** (a zero offset renders `+00:00`).
>
> Total emitted form: `YYYY-MM-DDTHH:MM:SS.ffffff±HH:MM` — 32 bytes, always, and every
> byte position's charset is fixed. **`datetime.isoformat()` is DOCUMENTED-UNSAFE for
> this rendering and MUST NOT be the implementation** (its fraction-elision at
> microsecond 0 is exactly the measured defect; `strftime('%f')` zero-pads and is safe
> for the fraction, and the offset is rendered by the rule above, not by `%z` — whose
> output omits the colon). The rendering rule and the `<RFC3339-EXACT>` grammar are the
> SAME 32-byte form stated from both ends — emitter and recognizer — so neither can
> drift without the other's row changing (this-seat (y), §10.2). **Battery obligation:
> one leg emits at a microsecond-0 instant (freeze the clock or construct the datetime)
> and asserts the §4.1e locator finds the boundary; one leg asserts the rendered form
> byte-matches `<RFC3339-EXACT>` across a sweep of instants including microsecond 0 and
> a negative-offset zone.**
