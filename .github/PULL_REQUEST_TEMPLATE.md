<!-- For docs/tooling changes: describe + delete the block below. -->

AMENDMENT  <!-- required for changes under plugins/agent-protocol/ -->
problem:
artifact set:      <!-- EVERY file this change governs, including co-maintained
                        counterparts you did NOT need to edit (a doc and its rendered
                        twin, a schema and its generated types, a value that must agree
                        across two manifests). Twins fail as a pair. -->
omission search:   <!-- what should have changed under this amendment and did not?
                        "none — searched X, Y, Z" is valid; silence is not -->
files touched:     <!-- the subset of the artifact set you actually edited -->
principal-locked paths touched: none  <!-- see .github/CODEOWNERS; if not none, say which + why -->
version impact: none
fingerprint:   <!-- base + SET digest (a diff digest cannot pin unchanged twins;
                    --error-unmatch errors on an untracked member, and the pipefail
                    guard propagates that failure — sha256sum alone masks it, exit 0):
                    ( set -o pipefail; git rev-parse HEAD && git ls-files -s --error-unmatch -- <artifact set> | sha256sum ) -->

- [ ] `python tools/mirror_check.py` green
- [ ] `python -m unittest discover -s tests` green
- [ ] no personal data / machine paths / secrets introduced
