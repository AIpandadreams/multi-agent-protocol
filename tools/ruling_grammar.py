"""One definition of the PA1-RUL ruling-id grammar, in three DOCUMENTED tiers.

An orchestrator ruling / creator's one-grammar finding: three readers each carried a private
regex for the same id space — ops_digest_source (anchored ``\\d{3}``), register_sweep
(unanchored bytes ``\\d+``), open_rulings (prefix startswith) — so a grammar change
would have to land three times and would land once. This module does NOT collapse the
tiers: they are deliberately different instruments, and collapsing them would replay
the earlier tick defect (a strict filter silently DROPPING off-grammar rows that a
harvester must SEE and label). It names them, so each reader imports the tier it
means and the difference is a decision on record, not an accident of copy-paste.

  PREFIX    — the resolvability floor: cheapest test that a string is even in the id
              namespace. Use for routing/lookup floors (open_rulings' startswith).
  CANONICAL — full grammar, anchored, seat-scoped, exactly three digits. The GATE
              tier: use where an id is ADMITTED into a closed-vocabulary surface
              (ops digest FIELD_VOCAB). Off-grammar here must become a STATE, never
              free text and never a silent drop.
  HARVEST   — bytes, unanchored, ``\\d+``. The LABEL tier: use where ids are being
              collected from raw ledger bytes and an off-grammar id must be seen and
              LABELED, never filtered out (register_sweep's label-not-filter;
              ``HARVEST.fullmatch(rid)`` is the canonicality LABEL on a harvested id).

Cross-language twin: ``tools/intake_ops_digest.mjs`` carries a JS literal of
CANONICAL (``const RULING = /.../``) because it cannot import this module. The sync
leg in the ops-source controls (private workspace) asserts LITERAL
EQUALITY of the two pattern sources, so cross-language drift is a red, not a hope.
"""
import re

PREFIX = "PA1-RUL-"
CANONICAL = re.compile(r"^PA1-RUL-[a-z]+-\d{3}$")
HARVEST = re.compile(rb"PA1-RUL-[a-z]+-\d+")
