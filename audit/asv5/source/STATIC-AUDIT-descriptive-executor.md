# EXP-106 official-token correction — successor static audit

Date: **2026-08-17**  
Decision: **implementation candidate; independent closure required before rerun**

This audit succeeds the independently PASSed hot-merge audit solely because the
first real pre-outcome parser gate exposed the synthetic fixture's wrong
bona-fide `attack` token. No run contract, checkpoint, result, EER, detector
delta, perturbation replicate or band existed when the correction was made.

## Preserved artifact chain

- independently audited predecessor:
  `STATIC-AUDIT-descriptive-executor-hot-merge.md`, SHA-256
  `4ce84d67b336098ef8e8983571572accdc33f7ee086126fef1ede4ee2c5b7129`;
- Amendment 8, exact failure boundary and delimited correction:
  `2ec551c84f9011bc2cf571e782a2938d4ca798df2866a3d29f9c083f24cf4857`;
- unchanged merged score:
  `f49f1e90e9ae9e70383cbe6e73f26db577f234aded6c0083294ebf60a6085f51`;
- unchanged merged sidecar:
  `9b47673f0226cac0ef4946b132b5c42d4f03598ca63c0123514c8750bd22d390`;
- unchanged numerical core:
  `f7556f6585926931a639d2bc93f430811a91a6d3cc8b87f496f722f78eb521cc`;
- unchanged core tests:
  `d03a27e7984c087c0585601e460afb4a3734d74330e1af4d9de4b6e03a1d6e65`.

The prior independent auditor established exact 353,840 + 326,934 disjoint
coverage, full-manifest order, literal score-string preservation, scorer
identity and all real merge hashes. None changed.

## Corrected implementation

The production parser now requires the official protocol equivalence
`label == "bonafide"` iff `attack == "bonafide"`. The former comparison to
`attack == "-"` confused that field with `attack_condition`. The four synthetic
bona-fide rows now reproduce the official ten-column encoding, and a dedicated
mutation test rejects the old encoding.

- corrected analyzer:
  `fe1c01f0de9a4052ea950fbb62b519b3ca9d17928d6d6c94e593ed8be6afbe8e`;
- corrected integrated tests:
  `0b66a3bf8eb212d5e8d72666ef75efd1b49b53fd29cb53c5a40e05fad1a4d98c`;
- successor config:
  `98e718e70d2395294981cd7e16fd4f3244496ad49ab8e0af0fe943bbfd59e565`.

The successor config changes only the static-audit path relative to the
independently audited hot-merged config. The analyzer remains at the same path,
so the run contract will bind its corrected bytes and this successor audit.

## Synthetic evidence and boundary

The frozen Python 3.11 / NumPy 2.4.2 / Numba 0.64.0 environment passes **15/15**
combined tests: seven numerical-core and eight integrated executor tests,
including 5,000 replicates under every arm and the new literal-token mutation.

This correction cannot change the estimand or a numerical outcome except by
allowing the already frozen official protocol to pass its intended schema
gate. Real execution remains prohibited until the same independent merge
auditor reproduces this focused closure and changes this candidate decision to
PASS.
