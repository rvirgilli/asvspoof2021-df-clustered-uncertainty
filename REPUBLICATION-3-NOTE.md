# Republication 3 assembly

The release starts from `886824e172a70cec4089e99173d5b0eddba460fe` and assembles
the audited merged manuscript, bibliography, semantic obligations, supplement,
figures, portable diagnostic drivers, regenerated evidence and both archives.
Public path adapters and unrelated campaign artifacts retain their public bytes.
The supplement is identical at the root and under `paper/`; its S4a–S4e evidence
JSON links resolve at both locations.

This is a local, two-commit preparation. The artifact commit precedes the final
manuscript locator and PDF build. Its inherited PDF is the predecessor submission,
not a build of the revised source. The subsequent submission commit binds the
paper to the artifact commit and contains the new PDF. No tag is moved, no commit
is amended after the paper is built, and this run performs no network writes.

The successor `paper/RELEASE-RECEIPT-FINAL.json` binds each payload member and
records both its historical receipt predecessor and the observed public base.
It excludes itself and `MANIFEST.json` to avoid circularity. The manifest binds
the receipt, and Git binds the complete manifest and tree. Earlier receipts and
validation directories describe their original revisions. Final local commit
identities and validation results are recorded in the external
`REPUBLICATION-3-RECEIPT.md`, marked ready-to-push.

The author's S5 correction retires the SNAP sentence fragment, which carried no
performance or scientific claim, and its withdrawal-only bibliography check.
The submission removes the withdrawn reference and its sentence-only semantic
obligation, while retaining identity perturbations, speaker-adversarial training,
speaker/synthesizer familiarity, and the fixed-score distinction. This is the
retirement of a sentence that carried no claim, not a weakening of a scientific
check. The artifact source retains the merged text until this authorized second
step; the submission records the final obligation count and exact retirement.
