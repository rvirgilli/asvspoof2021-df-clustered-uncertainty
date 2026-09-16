# Portable diagnostic evidence in republication 3

This revision assembles the audited `merged/` delivery. It includes both portable
producers, both original archives and the regenerated diagnostic and influence
JSONs. The earlier portability task stopped because its original requirement
was whole-file JSON byte identity. That historical failure remains a failure:
rerun timings, executable provenance and protected-file bindings changed.
The later merged delivery deliberately contains the rerun JSONs. This release
does not relabel the historical byte-identity gate as passed.

| Member | SHA-256 |
|---|---|
| `evidence/ABLATION-RESULTS.json` | `41ffd32fa5bd446e0f7777d0d6d70b93b0153779b432516783216558f58fa8a3` |
| `evidence/diagnostics.json` | `913b096bfe4f699743fe7b58b694c622ad9473df87cef35216880e91ef426dff` |
| `evidence/influence.json` | `b3508bdf13f0929e7e8c9532d65e9fedc31c3158334fdb7743a5787614592759` |
| `evidence/ABLATION-REPLICATES.npz` | `8b5ebce66140973f49b9fc08c544692811189214c9884358a08ef968ea68cf03` |
| `evidence/replicates.npz` | `3364e1d4eb6030ea538b1c92e831b2fb0eb79131f58e6796a868467a6f75e972` |
| `code/strategy_diagnostics.py` | `14c25cc62b89e2ae21acf0d9b53e05708495f3aaf746a9fb845b7a9275506b7a` |
| `code/strategy_influence.py` | `8c97a8df91782e4699effc55a8c5792095834e8cae00bb5f7dfe195e98b9a19c` |

The two archives are distinct: 604,405 bytes with two `(5000, 8)` arrays, and
5,220,806 bytes with eighteen `(5000, 8)` arrays. Their shared speaker-only and
attack-only arrays agree exactly. The supplied portability run reproduced all
720,000 diagnostic array values and the compressed diagnostic archive bytes.
Every statistical value in the two JSONs agrees with the original author run.
The regenerated evidence records its actual execution and provenance fields.

The release retains its public path adapters, historical audit envelopes and
raw-score acquisition boundary. It adds the merged checker's exact portable
producer and archive bindings; neither historical producer is accepted as an
alternative. The scientific changes additionally check the three SpoofCeleb
survivor identities and separate low-EER failures (16/24, 16/24, 11/24), while
retaining the common intersection of 11 cells.

The supplied `AUDIT-REVISE.md`, `TEXTFIX-NOTE.md`, original portability note and
merge-validation records remain source records in the assembly workspace.
Their computed bindings are retained in the successor receipt. Public commands
are in [REPRODUCE-DIAGNOSTICS.md](REPRODUCE-DIAGNOSTICS.md).
