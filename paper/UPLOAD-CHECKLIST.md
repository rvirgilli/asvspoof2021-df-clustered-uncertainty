# M1 upload checklist — prepared 14 September 2026

**Status: internal repair and payload binding completed; publication is pending the author's instruction.** No manuscript source or PDF was modified or rebuilt. No existing public repository file, commit, local tag or remote tag was changed. `release-prep/` contains only the small replacement files and proposed manifest; it is not a copied release tree.

**Current reader mismatch.** A fresh HTTPS retrieval at 2026-09-14T16:39:19.312147+00:00 returned the 23,009-byte supplement with computed SHA-256 `e46b8b86b232d44307cf39fbbb474a1dbefc33f7607d0052b669255b98447d5b`. The cited repository is <https://github.com/rvirgilli/asvspoof2021-df-clustered-uncertainty>; the exact tag to update is **`icassp2027-submission`**. Remote tag object `9a8abe9c06a8b611f4ec22c95762db6068449647` currently peels to commit `a751672c14bb529c5dc2803b5abe994d6313c380`; both object identifiers were independently recomputed from available Git objects and agree with `git ls-remote`.

A reader fetching that tag receives the September 10 supplement: S4 and S5 survive, including the full-table RawNet2–CQCC-GMM row, but the new S2 worked example is absent and S8 still has working-repository paths and the archived-original witness hash where the public-file distinction is needed. Its manuscript, PDF and figure also predate this candidate. Publishing only S2, or moving the tag back to closure, would leave part of the mismatch unresolved. The observations in this checklist describe preparation time; a later publication must have a separate dated publication record.

**Repair and scope.** The final supplement retains S1–S7, including the new S2 example, and preserves the approved SpoofCeleb chronology and ASVspoof 5 prose byte for byte. S8 restores repository-root paths, public JSON selectors, the point-only extract and explicit legacy-field exclusion, and separate public/original witness hashes. Original standalone files that are not distributed in the public tree are named and distinguished from the released embedded payloads; re-serializing an embedded object cannot authenticate its original file hash. The receipt records fresh hashes of the public artifacts and the recoverable originals read in place.

As auditor of record, I explicitly confirm continued scope for exactly “The reversing sign also holds at distinct-score boundaries (supplement, Sec.~S5).” and the identified XLSR-Mamba minus XLS-R+SLS witness in the final receipt-bound source, supplied PDF and repaired supplement. S5, the pair, masses, sign, original sweep and adjacent limitations remain intact. This confirmation includes the final bindings and the prepared guard/generator adaptations as regression evidence; it approves no other scientific claim or revision. The original interpretation and lapse conditions in `APPROVAL-EXTENSION.md` remain operative. Any later payload change requires new hashes, rerun applicable checks and explicit scope confirmation.

The September 9 round-6 whole-release PASS, exact-PDF audit, deterministic-build result, academic/public byte identity, 161-member release-verifier PASS, historical 46/46 guard run, and prior delivery/publication claims **do not carry forward**. They identify earlier bytes. September 13 and September 14 scope confirmations cover only the specified sentence/witness; neither authorizes a whole-release or exact-PDF claim for changed bytes. The fresh guard results below apply only to their recorded inputs. The five nonblocking debts and lack of independent historical timing attestation remain. No fresh witness reconstruction, scientific audit, scoring run, bootstrap or manuscript build was performed.

**Files to publish.** `RELEASE-RECEIPT-FINAL.json` → `release_members` is the exhaustive file list, with a freshly computed SHA-256, byte count and `prepared_source` for each member. Retain every unchanged public member listed there. Apply these replacements/additions as individual files:

| Prepared source | Public destination |
|---|---|
| `main.tex`, `main.pdf` | `paper/main.tex`, `paper/main.pdf` |
| `SUPPLEMENT.md` | `paper/SUPPLEMENT.md` |
| `figs/forest.pdf`, `figs/floor.pdf` | `paper/figs/forest.pdf`, `paper/figs/floor.pdf` |
| `refs.bib`, `spconf.sty`, `IEEEbib.bst` | same names under `paper/` |
| `semantic_obligations.json` | `paper/semantic_obligations.json` |
| `release-prep/paper/figures_m1.py` | `paper/figures_m1.py` |
| `release-prep/code/check_numbers.py` | `code/check_numbers.py` |
| `release-prep/paper/test_semantic_guards.py` | `paper/test_semantic_guards.py` |
| `release-prep/code/verify_final_receipt.py` | `code/verify_final_receipt.py` |
| `release-prep/README.md`, `release-prep/paper/README.md` | `README.md`, `paper/README.md` |
| The eight `release-validation/*.stdout.txt` / `*.stderr.txt` guard logs listed in the receipt | same names under `paper/release-validation/` |
| `UPLOAD-CHECKLIST.md`, `RELEASE-RECEIPT-FINAL.json` | same names under `paper/` |
| `release-prep/MANIFEST.json` | `MANIFEST.json` |

The supplied academic guards and generator remain unchanged and are separately bound as validation inputs. The **prepared public** number checker retains the existing public artifact adapters, ports the current abstract/table and witness checks, and permits explicit roots for read-only preparation checks. Its mutation test permits explicit paper/checker paths. The public generator differs from the supplied generator only by resolving inputs to `derived/` instead of the absent `paper/exp/`; its three result inputs and provenance sidecar already exist and are bound in the receipt. The unused floor figure remains a dependency of the two-figure generator. Do not copy the academic guards over the public paths, substitute the old public checker, or regenerate the receipt-bound PDF/figures during staging. The old public checker fails against this manuscript's updated abstract and table.

**Fresh guard outputs after the supplement edit.** Both the supplied guards and prepared public guards exited 0. Both number checkers printed:

```text
OK — scientific contract passes: matched trial/PW results, complete system and pair tables, coverage boundaries, source weighting, SpoofCeleb/ASV5 checks, and all caveats are artifact-bound.
```

The supplied mutation suite reported:

```text
test_every_registered_deletion_fails_its_named_guard (test_semantic_guards.SemanticGuardMutationTests.test_every_registered_deletion_fails_its_named_guard) ... ok

----------------------------------------------------------------------
Ran 1 test in 2.932s

OK
```

The prepared public mutation suite reported:

```text
test_every_registered_deletion_fails_its_named_guard (release-prep.paper.test_semantic_guards.SemanticGuardMutationTests.test_every_registered_deletion_fails_its_named_guard) ... ok

----------------------------------------------------------------------
Ran 1 test in 2.960s

OK
```

Each suite is one test with 46 obligation subtests: every registered deletion failed its named guard. The exact stdout/stderr files, commands and input bindings are in the receipt. These are fresh runs, not inherited closure results. The existing 161-member public manifest was also checked by recomputing every member's digest and length, with no mismatches; that manifest belongs to the old release. The separate proposed manifest binds the prepared member set and final receipt. `verify_final_receipt.py` checks those files in place without copying trees. No full `verify_release.py` run is claimed for an assembled replacement Git release; that integrated check remains part of the publication procedure below.

**Prepared publication procedure — do not execute without the author's instruction.** Set `PACKAGE` to this delivered workspace and `PUBLIC_REPO` to the existing public checkout. Keep an independent copy of this small receipt for subsequent comparison. Confirm a clean checkout and re-read `git ls-remote` before staging; stop and reconcile if its tag or base differs from the observation above. Start a release branch at the observed base. Copy only entries whose `prepared_source.root` is `workspace` from their listed paths to their public destinations, followed by the receipt and proposed manifest. No tree copy, raw inputs, private archive, temporary files or log files outside the enumerated set belongs in the public release.

From that assembled repository, run:

```sh
unset M1_RELEASE_ROOT M1_PAPER_ROOT M1_CHECKER_PATH M1_TEX_PATH M1_SUPPLEMENT_PATH M1_REPO_ROOT
uv run --frozen python build_manifest.py
uv run --frozen python code/verify_final_receipt.py --receipt "$PACKAGE/RELEASE-RECEIPT-FINAL.json"
uv run --frozen python code/check_numbers.py
uv run --frozen python -m unittest -v paper/test_semantic_guards.py
uv run --frozen python verify_release.py
```

The regenerated manifest must equal the supplied proposed manifest as a JSON object and must enumerate every payload member plus the receipt, excluding only `MANIFEST.json` itself. Investigate any failure or extra member before committing. If changing a payload is necessary, issue a successor binding and scope confirmation; do not quietly edit this frozen receipt. Hash the resulting manifest and receipt for the publication record. Stage exactly the enumerated files, `paper/RELEASE-RECEIPT-FINAL.json` and `MANIFEST.json`, review the staged diff, then create the release commit. Record its actual commit ID; **the future commit and replacement tag object are currently unbound because neither exists**. Do not invent their IDs or reuse the old tag object.

Only after the author instructs publication, set `FINAL_COMMIT` to that verified commit and publish the branch/commit and annotated replacement tag. The old tag object below is a concurrency check; re-observe it immediately before pushing. A changed remote must be reconciled, not overwritten with an unconditional force:

```sh
git tag -f -a icassp2027-submission "$FINAL_COMMIT" -m 'M1 reconciled supplement and receipt-bound package, 2026-09-14'
git push origin HEAD:refs/heads/m1-reconciled-20260914
git push --force-with-lease=refs/tags/icassp2027-submission:9a8abe9c06a8b611f4ec22c95762db6068449647 origin refs/tags/icassp2027-submission:refs/tags/icassp2027-submission
```

Do not replace any published commit on an existing branch. The branch name above is for a new release branch; if it already exists, inspect it and choose a new name. Annotated tag creation changes a local reference, and both push commands are publication actions; none was executed for this preparation.

**What the updated tag must deliver and how to verify it.** It must fetch the receipt-bound current manuscript/PDF, six-pair figure and generator, current guards and all 46 obligations, the S2 example and repaired S8 supplement, all retained public evidence/plans, this checklist, the receipt and a complete updated manifest. The originals that were never separate public members remain explicitly distinguished from public bytes. The tag name alone is insufficient identification: record its replacement object ID and peeled commit in a separate dated publication record, together with newly computed receipt/manifest digests and the post-publication check output. This avoids circularly embedding a containing commit or a self-hash in the frozen receipt.

Read back both tag references and fetch into a **new local verification ref**, without replacing another user's local tag or checking out/copying a tree:

```sh
git ls-remote origin refs/tags/icassp2027-submission 'refs/tags/icassp2027-submission^{}'
git fetch --no-tags origin refs/tags/icassp2027-submission:refs/m1-verification/reconciled-20260914
FETCHED_COMMIT=$(git rev-parse 'refs/m1-verification/reconciled-20260914^{}')
uv run --frozen python "$PACKAGE/release-prep/code/verify_final_receipt.py" --public-root . --commit "$FETCHED_COMMIT" --receipt "$PACKAGE/RELEASE-RECEIPT-FINAL.json"
```

The fetched peeled commit must equal `FINAL_COMMIT`. The verifier compares **every Git member's bytes and length** with the retained receipt, confirms that the published receipt is itself identical to the retained one, checks the manifest, and rejects additional or missing Git paths. Also retrieve the tagged raw `paper/SUPPLEMENT.md` over HTTPS again and compute its SHA-256 and length; compare with the receipt's `release_members["paper/SUPPLEMENT.md"]`. Inspect that retrieved text for the S2 example, S8 repository-root locators and separate witness hashes. Record retrieval time, status and digest. A receipt fetched only from the same tag establishes internal consistency; comparison with the independently retained receipt establishes identity to this prepared package.

The planned manifest is an acyclic control file: it binds the final receipt, which binds the payload and this checklist. The receipt does not bind itself or that containing manifest. Their final digests can be computed with `sha256sum` and recorded alongside the actual publication commit. Historical whole-release, exact-PDF and publication claims remain historical even after these content checks pass.
