"""§4.1e THE PREVIEW BINDING — `pv`, `pv_mac`, and the under-lock comparison.

Constraints C29-C34 (blueprint §A.4), spec `v17:2130-2210`.

`/api/preview` is **PURE**: no lock, no write, no server-side record — the
binding carries the state INSTEAD of a session (C29, v17:2174-2175). Everything
the append needs to know about what the preview showed travels inside `pv`,
authenticated by `pv_mac`.

Order of checks at append time, pinned by §12 (v17:6060-6078) and restated here
because this module implements it:

1. **`pv_mac` FIRST.** A bad MAC is `400 binding-invalid`, **not**
   `PREVIEW_STALE` — a client cannot mint or alter a binding (C32,
   v17:2176-2179). Then `pv.n` / `pv.id` / `pv.ts` must match the request's.
2. **Under the lock**, in this order: `pv.lane_date` vs the execution-time ET
   date (ORDINARY appends only — a correction's lane is the sidecar's and is
   date-exempt), then existence/creation disposition, size, whole-prefix
   sha256, final byte, epoch presence. **ANY difference ⇒ release, close,
   `PREVIEW_STALE`** (C33, v17:2179-2190).
3. **THE EMISSION COMPARISON IS AN EXPLICIT STEP** — after the state-anchor
   compare and BEFORE the `INTENT` journal write and the `fh.write`: recompute
   the complete candidate emission and compare **BOTH** `len(emission) ==
   pv.emission_len` **AND** `sha256(emission) == pv.emission_sha256`. Either
   differing ⇒ release, close, `binding-invalid` — not `PREVIEW_STALE`, because
   the lane did not move; the request/binding pair is inconsistent (C34,
   v17:2191-2199).

The field list is exhaustive by construction, not a three-example list:
`size` + `prefix_sha256` subsume any byte change; `final_byte_is_lf` and
`epoch_present` are named separately because each independently changes the
emission bytes the preview showed.
"""

import hashlib
import hmac
import json

#: §4.1e v17:2144-2166 — the EXACT field set of `pv`. C30. Declared here with
#: its cite: `tools/d5_model/design_data.py` carries no `pv` schema (measured —
#: `OBJECT_SCHEMAS` has no `pv`/`preview_binding` member), so this is the one
#: site the field set is written, and every reader/writer below indexes it.
PV_FIELDS = (
    "v",
    "lane_date",
    "lane",
    "n",
    "id",
    "ts",
    "lane_present",
    "size",
    "prefix_sha256",
    "final_byte_is_lf",
    "epoch_present",
    "emission_sha256",
    "emission_len",
    "correction",
)

#: The `correction` block's field set (non-null ⇒ a correction preview).
PV_CORRECTION_FIELDS = (
    "torn_report",
    "ostart",
    "olen",
    "osha256",
    "start",
    "end",
    "sha256",
)

#: §4.1e v17:2167-2172 — the MAC's domain-separation prefix. `pv_mac` reuses
#: `id_key` under `"PVST\0"` so the two HMAC uses (id derivation, §4.1c/§8; and
#: this binding) cannot cross-answer. No third secret. C31.
PV_MAC_DOMAIN = b"PVST"

PV_VERSION = 1

#: The order the under-lock comparison runs in, pinned (C33). `lane_date` is
#: FIRST and is skipped for a correction; the rest bind a correction unchanged.
STATE_ANCHOR_FIELDS = (
    "lane_present",
    "size",
    "prefix_sha256",
    "final_byte_is_lf",
    "epoch_present",
)

#: Named refusal causes this module reports. §11.2's outcome vocabulary is
#: **OPEN by the design's own choice** (v19:2029 — "the ellipsis is the
#: author's"), so this tuple is NOT a closed enum and nothing here treats it as
#: one (C83, Q4).
CAUSE_BINDING_INVALID = "binding-invalid"
CAUSE_PREVIEW_STALE = "PREVIEW_STALE"
CAUSE_WRONG_ROUTE = "wrong-route"


class BindingRefused(Exception):
    """A refusal from the binding path; ``.cause`` always names it."""

    def __init__(self, cause, detail=None):
        super().__init__(f"{cause}: {detail!r}" if detail else cause)
        self.cause = cause
        self.detail = detail or {}


def canonical_json(obj):
    """§4.1e v17:2167-2172 — canonical-JSON = **UTF-8, sorted keys, no whitespace**.

    Pinned so the MAC has ONE byte form. ``ensure_ascii=False`` is required:
    "UTF-8" is the stated encoding, and ``json``'s default would emit `\\uXXXX`
    escapes instead — a different byte string for the same object.
    """
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def pv_mac(id_key_raw, pv):
    """`pv_mac := HMAC-SHA256(key = raw id_key bytes, "PVST" || 0x00 || canonical-JSON(pv))`.

    C31 (v17:2167-2172) and C16: the key is the **raw 32 bytes** hex-decoded
    from ``ops/write_path/id_key`` — keying with the 64 hex ASCII characters is
    a different key space and is wrong (the same trap §8 prints for the id).
    ``id_key`` is never transmitted.
    """
    if not isinstance(id_key_raw, (bytes, bytearray)):
        raise BindingRefused(
            CAUSE_BINDING_INVALID, {"reason": "id_key must be RAW bytes, not hex text"}
        )
    msg = PV_MAC_DOMAIN + b"\x00" + canonical_json(pv)
    return hmac.new(bytes(id_key_raw), msg, hashlib.sha256).hexdigest()


def build_pv(
    *,
    lane_date,
    lane,
    n,
    id_str,
    ts,
    lane_present,
    size,
    prefix_sha256,
    final_byte_is_lf,
    epoch_present,
    emission,
    correction=None,
):
    """Construct `pv` with EXACTLY the C30 field set — no more, no fewer.

    ``emission`` is the COMPLETE emission bytes (conditional LF, epoch marker,
    SUPERSEDES line on a correction, envelope, heading, body): `emission_len`
    and `emission_sha256` are derived from it here so the preview cannot show
    one thing and bind another.
    """
    if correction is not None:
        missing = [f for f in PV_CORRECTION_FIELDS if f not in correction]
        extra = [f for f in correction if f not in PV_CORRECTION_FIELDS]
        if missing or extra:
            raise BindingRefused(
                CAUSE_BINDING_INVALID,
                {"reason": "correction field set", "missing": missing, "extra": extra},
            )
    pv = {
        "v": PV_VERSION,
        "lane_date": lane_date,
        "lane": lane,
        "n": n,
        "id": id_str,
        "ts": ts,
        "lane_present": bool(lane_present),
        "size": int(size),
        "prefix_sha256": prefix_sha256,
        "final_byte_is_lf": bool(final_byte_is_lf),
        "epoch_present": bool(epoch_present),
        "emission_sha256": hashlib.sha256(emission).hexdigest(),
        "emission_len": len(emission),
        "correction": correction,
    }
    assert_pv_shape(pv)
    return pv


def assert_pv_shape(pv):
    """C30 — the field set is EXACT. A missing or extra field is a refusal,
    never a default (a defaulted binding field is a binding that attests
    something the preview never showed)."""
    if not isinstance(pv, dict):
        raise BindingRefused(CAUSE_BINDING_INVALID, {"reason": "pv is not an object"})
    missing = [f for f in PV_FIELDS if f not in pv]
    extra = [f for f in pv if f not in PV_FIELDS]
    if missing or extra:
        raise BindingRefused(
            CAUSE_BINDING_INVALID,
            {"reason": "pv field set", "missing": missing, "extra": extra},
        )
    if pv["v"] != PV_VERSION:
        # An unknown binding version is a named refusal, not a guess (§4.1a
        # property 4's posture applied to the binding).
        raise BindingRefused(
            CAUSE_BINDING_INVALID, {"reason": "pv version", "got": pv["v"]}
        )


def verify_pv_mac(id_key_raw, pv, presented_mac):
    """Step 1: verify the MAC FIRST, constant-time.

    C32 (v17:2176-2179): a bad MAC is ``binding-invalid``, **NOT**
    ``PREVIEW_STALE``. The two causes answer different questions and collapsing
    them would let a tampered binding read as an ordinary race.
    """
    assert_pv_shape(pv)
    expected = pv_mac(id_key_raw, pv)
    if not isinstance(presented_mac, str) or not hmac.compare_digest(
        expected, presented_mac
    ):
        raise BindingRefused(CAUSE_BINDING_INVALID, {"reason": "pv_mac"})


def verify_request_matches_pv(pv, *, n, id_str, ts):
    """C32's second half: after the MAC, `pv.n` / `pv.id` / `pv.ts` must match
    the request's. Constant-time comparison is not required here (these are not
    secrets) but a mismatch is still ``binding-invalid`` — the request/binding
    pair is inconsistent, which is a client defect, not a lane race."""
    for field, got in (("n", n), ("id", id_str), ("ts", ts)):
        if pv[field] != got:
            raise BindingRefused(
                CAUSE_BINDING_INVALID,
                {"reason": "pv/request mismatch", "field": field},
            )


def refuse_correction_on_append_route(pv):
    """C35 (§11.2 v17:5753, carried in v19 §S5.1a at v19:2016 under pin
    ``s11_2_append_route``): a `pv` whose `correction` block is **non-null is
    REFUSED on `/api/append`** — `400 wrong-route`. Correction bindings land
    only via `/api/append/correction`."""
    if pv.get("correction") is not None:
        raise BindingRefused(
            CAUSE_WRONG_ROUTE, {"reason": "correction binding on the append route"}
        )


def observe_lane_state(data, present, epoch_present):
    """The state anchor as observed from the bytes on disk, in ONE place, so
    preview-time and under-lock observation cannot drift apart
    [[emitter-and-verifier-are-one-grammar]].

    ``epoch_present`` is supplied by the §4.1e LOCATOR (C37) rather than
    recomputed here — the locator is the normative decider of "first epoch
    marker" and a substring scan is explicitly NOT it (v19:1397-1408).
    """
    return {
        "lane_present": bool(present),
        "size": len(data),
        "prefix_sha256": hashlib.sha256(data).hexdigest(),
        "final_byte_is_lf": bool(data) and data[-1:] == b"\n",
        "epoch_present": bool(epoch_present),
    }


def compare_state_anchor(pv, observed, *, execution_et_date, is_correction):
    """Step 2 — run **under the lock, on the verified handle**. C33.

    Order is normative: `lane_date` FIRST (ordinary appends only), then the
    five byte-state fields. ANY difference ⇒ the caller releases the lock,
    closes the handle, and refuses ``PREVIEW_STALE``.

    Returns the list of differing field names (empty ⇒ the anchor holds); the
    caller raises, so the lock-release path stays in one place.
    """
    diffs = []
    if not is_correction:
        # v17:2179-2186 — a rollover between preview and append is
        # PREVIEW_STALE. A CORRECTION is exempt from THIS comparison only
        # (its lane is the sidecar's, historical by design, C24); every byte
        # field below still binds it.
        if pv["lane_date"] != execution_et_date:
            diffs.append("lane_date")
    for field in STATE_ANCHOR_FIELDS:
        if pv[field] != observed[field]:
            diffs.append(field)
    return diffs


def compare_emission(pv, emission):
    """Step 3 — **the explicit emission comparison**. C34 (v17:2191-2199).

    BOTH comparisons, always: `len(emission) == pv.emission_len` AND
    `sha256(emission) == pv.emission_sha256`. Either differing ⇒
    ``binding-invalid``. Returns the list of differing names (empty ⇒ equal) so
    the caller owns the release-and-close path.
    """
    diffs = []
    if len(emission) != pv["emission_len"]:
        diffs.append("emission_len")
    if hashlib.sha256(emission).hexdigest() != pv["emission_sha256"]:
        diffs.append("emission_sha256")
    return diffs
