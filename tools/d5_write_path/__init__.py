"""DW1 — the D5 localhost write path.

Package marker only. Every module in this package imports the design's
enums/schemas/constants through ``model_import`` (the single ``sys.path`` shim
into ``tools/d5_model``); no member list, field set, manifest version, filename
form, cause name or health-item name is ever re-declared here.

Spec: the D5 write-path design, v19 (``D5_WRITE_PATH_DESIGN_v19.md``, in the private workspace)
(and its quarry ``…_v17.md`` for §§11.3-11.6, 12, 2.4, 4.1c-f, 13.1-13.3).
Bar:  the D5 acceptance test protocol, v19 (``ACCEPTANCE_TEST_PROTOCOL_v19.md``, in the private workspace).

Python 3.13, stdlib only. No I/O at import.
"""
