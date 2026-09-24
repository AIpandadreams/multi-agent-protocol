⛔ **THE LOCK, BUILD-SPECIFIED (v7-round C5 — v7 named no API, offset, extent, timeout or
failure behavior, while §3.2's own record shows the result is extent-dependent: a lock
ending at current EOF need not cover an append that begins at EOF):**

- **API:** `LockFileEx` on the §6.2 verified handle (the same handle that does the
  operation's I/O — the lock and the writes share one object), flags
  `LOCKFILE_EXCLUSIVE_LOCK | LOCKFILE_FAIL_IMMEDIATELY`. The Python binding is
  `msvcrt.locking` ONLY if the build proves it can express the region below; otherwise
  ctypes/`pywin32` `LockFileEx` directly — the REGION is normative, the binding is not.
- **Region:** offset `0`, length `0xFFFFFFFFFFFFFFFF` bytes. ⛔ **Pinned to the API's own
  DWORDs and to the mathematically matching interval (v8-round C9 — v7/v8 called this
  length "the half-open byte range `[0, 2^64)`", and a length of `2^64−1` starting at
  offset 0 denotes `[0, 2^64−1)`, one byte less; §10.2 repeated the same wrong interval):**
  the call is `LockFileEx(h, LOCKFILE_EXCLUSIVE_LOCK | LOCKFILE_FAIL_IMMEDIATELY, 0,
  nNumberOfBytesToLockLow = 0xFFFFFFFF, nNumberOfBytesToLockHigh = 0xFFFFFFFF, &ov)` with
  `ov.Offset = 0` and `ov.OffsetHigh = 0` — the two length DWORDs compose the 64-bit byte
  count `0xFFFFFFFFFFFFFFFF = 2^64−1`, so the locked interval is **`[0, 2^64−1)`**
  (`UnlockFileEx` names the identical four DWORDs). **That interval covers every legal
  append offset:** Win32 file sizes and offsets are signed 64-bit (`LARGE_INTEGER` — the
  contract of `SetFilePointerEx`/`GetFileSizeEx`), so no byte of any file can sit at an
  offset ≥ `2^63`, and `2^63 < 2^64−1` — the entire current file AND every future append
  offset lie strictly inside the region. A this-seat choice
  (§10.2) over lock-at-EOF-extent, for exactly §3.2's reason: an appender writes AT
  current EOF, so any extent that stops at EOF leaves the contested bytes unlocked. One
  huge constant region also makes acquire and release trivially symmetric.
