# Input data

The score files and the evaluation key are third-party releases and are **not redistributed here**.
Each is listed below with the sha256 prefix, byte count and line count of the exact file used,
as recorded in `audit/audit.json:provenance`. A reader who obtains these files can confirm byte
identity with the inputs behind every number in the repository.

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

## Layout expected by the code

Set three environment variables (defaults in `code/m1_campaign.py`):

| Variable | Points at |
|---|---|
| `M1_DATA_ROOT` | directory holding `DF-keys-full/` and `official-scores/` |
| `M1_SSL_AASIST_SCORES` | the SSL-AASIST `Scores_DF.txt` file |
| `M1_EXP001_SCORES` | reproduction scores directory (In-the-Wild rows only) |

All eight systems are scored on an identical trial-ID set; `audit/audit.json:intersection`
records the rule and the resulting count.
