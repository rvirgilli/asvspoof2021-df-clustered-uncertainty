# Input data

The score files and the evaluation key are third-party releases and are **not redistributed here**.
The primary-layer inputs are listed below with the sha256 prefix, byte count and line count
recorded in `audit/audit.json:provenance`. The separate Arena layer is recorded under
`derived/results_arena.json:provenance`. A reader who obtains these files can confirm byte
identity with the inputs behind the reported numbers.

## Evaluation key

ASVspoof 2021 DeepFake keys & metadata package, `keys/DF/CM/trial_metadata.txt`.
Distributed by the ASVspoof challenge organisers.

| sha256 (first 16) | bytes | lines |
|---|---|---|
| `70e0e7d5964562cb` | 62,086,042 | 611,829 |

## Per-trial score files (eight systems)

| System | Source | File | sha256 (first 16) | bytes | lines |
|---|---|---|---|---|---|
| XLSR-Mamba | [XLSR-Mamba (Xiao & Das, IEEE SPL 2025; arXiv:2411.10027)](https://github.com/swagshaw/XLSR-Mamba) | `Scores/Bmamba3_LA_WCE_1e-06_ES144_NE12.txt` | `0698327cafdadec1` | 19,572,585 | 611,829 |
| XLS-R+SLS | [XLS-R + SLS (Zhang et al., ACM MM 2024)](https://github.com/QiShanZhang/SLSforASVspoof-2021-DF) | `scores/scores_DF.txt` | `b0c20e37bd67899f` | 20,649,210 | 611,829 |
| XLSR-Conformer | [XLSR-Conformer (Rosello et al., Interspeech 2023)](https://github.com/ErosRos/conformer-based-classifier-for-anti-spoofing) | `Scores/Scores_Best_DF_Fixed_size_train.txt` | `fd00e8ddb2838a9a` | 19,590,147 | 611,829 |
| SSL-AASIST | [SSL-AASIST (Tak et al., Odyssey 2022) — author release](https://github.com/TakHemlata/SSL_Anti-spoofing) | `Scores/DF/Scores_DF.txt` | `b58885aef1322f48` | 19,865,710 | 611,829 |
| RawNet2 | [ASVspoof 2021 organiser baseline](ASVspoof 2021 DF keys & metadata package) | `keys/DF/CM/RawNet2/score.txt` | `a9ac140df41ec063` | 20,698,884 | 611,829 |
| LFCC-LCNN | [ASVspoof 2021 organiser baseline](ASVspoof 2021 DF keys & metadata package) | `keys/DF/CM/LFCC-LCNN/score.txt` | `ae95b18160ab0132` | 14,991,540 | 611,829 |
| LFCC-GMM | [ASVspoof 2021 organiser baseline](ASVspoof 2021 DF keys & metadata package) | `keys/DF/CM/LFCC-GMM/score.txt` | `488c214482d5f4fb` | 13,733,217 | 611,829 |
| CQCC-GMM | [ASVspoof 2021 organiser baseline](ASVspoof 2021 DF keys & metadata package) | `keys/DF/CM/CQCC-GMM/score.txt` | `97e05bdbbbe67130` | 13,723,903 | 611,829 |

The four organiser baselines ship inside the ASVspoof 2021 DF keys package; the four
self-supervised systems are author releases from the repositories linked above.

## Speech DF Arena re-score layer (eleven systems)

These are complete per-trial ASVspoof 2021 DF re-score files from Speech DF Arena. They are
analyzed as a separate provenance stratum and are never pooled with the eight releases above.
Each file has 533,928 evaluation rows and lives under the slug shown relative to
`M1_ARENA_SCORES`.

| System | Relative file | sha256 |
|---|---|---|
| AASIST-Arena | `aasist/asvspoof_2021_df.txt` | `ffebeaa69c89077d7eb65fada708d86589fa4f4d08bebab7831432080d2bc50d` |
| HuBERT-ECAPA-Arena | `hubert_ecapa/asvspoof_2021_df.txt` | `e79e078f20d7a8844954298d0dfc29e4922ac524d7bcb139b64853193a715c0a` |
| RawGAT-ST-Arena | `rawgat_st/asvspoof_2021_df.txt` | `23aaa74ba4f6a8c46aaf31333d9a5e2035ea72fb494f08e22a629a98d9e4f9e3` |
| RawNet2-Arena | `rawnet_2/asvspoof_2021_df.txt` | `5bb4a74381088b474a5f29d130b98d9b2e5d3b209c4e696082feaf8a5cd01e0c` |
| Resemble-AI-Arena | `resemble_ai/asvspoof_2021_df.txt` | `00e43c8111f889112b214739b07805ea235db264a45e5e3ac8abca602f0b4d72` |
| TCM-ADD-Arena | `tcm_add/asvspoof_2021_df.txt` | `f00e15c37b619bae91a5c050c14f626850d91fc2b08bd13c259e4544e1ebc953` |
| Wav2Vec2-ECAPA-Arena | `wav2vec2_ecapa/asvspoof_2021_df.txt` | `e44ae756b27c4ff186f87ad84d4283072d2e017d963b2f8186bdb12e971f1e37` |
| WavLM-ECAPA-Arena | `wavlm_ecapa/asvspoof_2021_df.txt` | `76689404ece7dcb9c196634482e9a1e1430ec93d200532a4ea3a5213f228b978` |
| Whisper-MesoNet-Arena | `whisper_mesonet/asvspoof_2021_df.txt` | `2379439b3e66f114e894ae81a1f5cd0746a722e60d2d95ed567d7fc394363dbe` |
| XLS-R+SLS-Arena | `xlsr_sls/asvspoof_2021_df.txt` | `b8a65eb82080494bf02b5ba92c676603a7e117affe588e3a8ababe63ff5d8586` |
| XLSR-Mamba-Arena | `xlsr_mamba/asvspoof_2021_df.txt` | `2d32e1da093cd60cd437500bf0f9f2b557b53de47a17ea9fb749d725f76195c7` |

## Layout expected by the code

Set the relevant environment variables (defaults are in the named scripts):

| Variable | Points at |
|---|---|
| `M1_DATA_ROOT` | directory holding `DF-keys-full/` and `official-scores/` |
| `M1_SSL_AASIST_SCORES` | the SSL-AASIST `Scores_DF.txt` file |
| `M1_EXP001_SCORES` | reproduction scores directory (In-the-Wild rows only) |
| `M1_ARENA_SCORES` | directory containing the eleven Arena slug directories above |
| `M1_ARENA_RUN_ROOT` | NVMe checkpoint directory for resumable Arena bootstrap arrays |

All eight systems are scored on an identical trial-ID set; `audit/audit.json:intersection`
records the rule and the resulting count.
