## 8 ID SCHEME — one derivation, stated once, with a worked example

**v5's §8 contradicted §4.1c** — it kept `AE-<YYYYMMDDhhmmss><KKKKK>` with a 16-bit suffix
and said widening was "a cheap decision deferred to build", while §4.1c had already frozen a
64-bit server-derived suffix. Two implementers would have built two id schemes, and a freeze
cannot hand a live parameter to build time (opus v5 O7; codex v5 C3). **The single normative
derivation is §4.1c.** This section restates its grammar and gives the worked example; if
this section and §4.1c are ever again read to disagree, §4.1c governs.

**Grammar:** `AE-` + 14-digit ET timestamp (`YYYYMMDDhhmmss`, from the preview, so a retry
reproduces the id) + 20-digit zero-padded decimal rendering of the first 8 bytes
(big-endian) of `HMAC-SHA256(key, ts || 0x00 || n || 0x00 || P)` — where the key is the
**raw 32 bytes hex-decoded from the key file** (§4.1c — v6-round F9) and `n` is the
32-hex-character preview nonce (§4.1c — v6-round C15) — **`id_digits` is 34 digits, always,
and `AE-` appears exactly once, as §2.1's `id := "AE-" + id_digits` (v7-round F4)**
(`parse.py`'s `ENTRY_ID_RE` accepts any digit run, so the width is pinned here, by design,
not by the parser). The example block below is the executable check on both names — its
heading and envelope lines carry one `AE-` each.

**Worked example — computed at this authoring (Python `hashlib`/`hmac`), reproducible from
the stated inputs. The key below is the DOCUMENTATION example key and is never a production
value; `key_id` is the HEX-ENCODED FILE CONTENT of `ops/write_path/id_key` (v6-round F9's
label), i.e. `sha256("D5-doc-example-key")` rendered as hex — the HMAC is keyed with its 32
DECODED RAW BYTES, and keying with the 64 hex ASCII characters instead yields suffix
`16840684310111949085`, a different id space (both computed; the wrong reading is printed so
an implementer who lands on it recognizes where they are). The example nonce is the first 16
bytes of `sha256("D5-doc-example-nonce")`, hex-rendered:**

```
key_id  = 0c5ed0673e1697d8755883d65a25cc517e58cc90e518056ed84814327b65b905   (hex file content)
ts      = 20260813120000
n       = d69dc6cda7f599a982af5d3598337baa                                   (preview nonce)
gist    = Example ruling
body    = b"Approved as discussed.\n"          (B; len = 23, trailing LF counted — §4.1b)
P       = b"Example ruling\nApproved as discussed.\n"

msg     = b"20260813120000" + b"\x00" + b"d69dc6cda7f599a982af5d3598337baa" + b"\x00" + P
suffix  = 03028313533809327460                  (20 digits — note the REAL leading zero:
                                                 the raw integer is 3028313533809327460,
                                                 19 digits; the zero-pad is load-bearing
                                                 here, not decorative)
id      = AE-2026081312000003028313533809327460 (34 digits)
D       = ae6cff72accad8b01e563808dfde989113706bfbc1860c403639ac097ec029b7   (= sha256(B);
                                                 unchanged from v6 — D never depends on
                                                 ts, n, or gist)

emission:
<<CO-ENV v1 id=AE-2026081312000003028313533809327460 len=23 sha256=ae6cff72accad8b01e563808dfde989113706bfbc1860c403639ac097ec029b7
## AE-2026081312000003028313533809327460 — Example ruling
Approved as discussed.
>>CO-END v1 id=AE-2026081312000003028313533809327460 sha256=ae6cff72accad8b01e563808dfde989113706bfbc1860c403639ac097ec029b7
```

**Collision posture:** two writers colliding now need the same second AND the same 64 HMAC
bits under the same install key — and because the suffix is derived, not drawn, a colliding
id with a different body is `CONFLICT` (§4.1d row 4), which is a refusal, not a
misattribution. §4.1d row 2 (`DUPLICATE_ID`) covers the only remaining arrival path
(forgery/hand-copying) loudly.

**Key lifecycle:** `key_id` generation, storage, permissions and rotation are specified with
the token's at **§11.4** — they are different secrets with different rotation consequences,
and the design says so there.

---
## 11 TRANSPORT, AUTHN, AUTHZ — the contract v5 omitted (NEW)
