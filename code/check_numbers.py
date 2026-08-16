"""Verify every asserted number in M1's main.tex against a NAMED artifact value.

M1 shipped `55fb37d` with no checker at all: zero presence assertions, zero value
assertions, no retired list. Every claim was unguarded and nothing fired on deletion
-- which is how compression silently dropped "on the four systems we can check" from
the conclusion and turned it into an overclaim, and how a per-pair MDE and a pair name
vanished from the resolution paragraph.

Four layers, because each catches what the others cannot:

1. VALUE   -- every literal names the exact JSON path it must equal. A number can
              only pass by being right about the thing it claims, never by matching
              some unrelated value elsewhere in the artifacts.
2. WINDOW  -- the literal must appear within N characters of a unique anchor, so a
              value cannot migrate elsewhere in the paper and still pass. The
              anchor's own uniqueness is asserted.
3. PRESENCE-- statements the paper is obliged to make. Anchored on the SECTION OR
              CLAUSE MARKER, never on a value: a document-wide value check passes
              when a row is deleted if that number appears anywhere else in the
              prose, so value checks cannot detect deletion. These can.
4. RETIRED -- formulations a correction removed must stay absent, so a withdrawn
              claim cannot creep back in a later edit.

Run: python3 check_numbers.py    (exit 1 on any failure)
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1] / "experiments/EXP-101-m1-campaign"
TEX_RAW = (HERE / "main.tex").read_text()
# Whether a number sits inside its own $...$ or shares a math block with its
# neighbour is typesetting, not content.
# Strip LaTeX comments first: the header comment records withdrawn formulations by
# name, and a RETIRED check must not fire on the note that documents the retirement.
TEX = re.sub(r"(?m)^%.*$", "", TEX_RAW)
TEX = TEX.replace("$", "").replace("\\,", "").replace("{,}", ",")

_FILES = ("selection", "organizer_test", "floor", "floor_ci", "scaling",
          "coverage_real", "contingency", "verdict_ci", "dgp_fit", "widths",
          "icc", "source")
SRC = {n: json.loads((EXP / f"results_{n}.json").read_text()) for n in _FILES}

SSL = {"XLSR-Mamba", "XLS-R+SLS", "XLSR-Conformer", "SSL-AASIST"}
SEL_PAIRS = SRC["selection"]["21df"]["pairs"]
failures = []


def get(path):
    """Resolve 'selection:21df.supt_critical_value' or 'x:a.b[2]' to its value."""
    file, rest = path.split(":", 1)
    node = SRC[file]
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", rest):
        if part.startswith("["):
            node = node[int(part[1:-1])]
        else:
            node = node[part]
    return node


def lit(x, nd=None):
    """Render a JSON number the way the paper prints it."""
    if nd is None:
        return str(x)
    s = f"{float(x):.{nd}f}"
    return s


def check_value(literal, path, nd=None, transform=None):
    """The literal must be in the tex AND equal the named artifact value."""
    want = get(path)
    if transform:
        want = transform(want)
    want_s = lit(want, nd)
    if literal != want_s:
        failures.append(f"VALUE  {path}: paper says {literal!r}, artifact gives {want_s!r}")
        return
    if not re.search(r"(?<![\d.])" + re.escape(literal) + r"(?![\d])", TEX):
        failures.append(f"VALUE  {path}: {literal!r} matches the artifact but is ABSENT from main.tex")


def check_window(literal, anchor, dist=260):
    if TEX.count(anchor) != 1:
        failures.append(f"WINDOW anchor {anchor!r} occurs {TEX.count(anchor)} times, need exactly 1")
        return
    i = TEX.index(anchor)
    seg = TEX[max(0, i - dist): i + dist + len(anchor)]
    if not re.search(r"(?<![\d.])" + re.escape(literal) + r"(?![\d])", seg):
        failures.append(f"WINDOW {literal!r} not within {dist} chars of {anchor!r}")


def check_presence(marker, why):
    if marker not in TEX:
        failures.append(f"PRESENT missing {marker!r} -- {why}")


def check_presence_re(pattern, why):
    """For obligations whose wording may legitimately change but whose content may not."""
    if not re.search(pattern, TEX, re.S):
        failures.append(f"PRESENT no match for {pattern!r} -- {why}")


def check_retired(pattern, why):
    if re.search(pattern, TEX):
        failures.append(f"RETIRED {pattern!r} reappeared -- {why}")


# --- 1. VALUE -------------------------------------------------------------
# Act 1: the reversal.
check_value("12.7", "organizer_test:pairs.B04 vs B01.z_iid", 1, abs)
check_value("5,162", "organizer_test:pairs.B04 vs B03.family_size_needed_to_lose_significance",
            transform=lambda v: f"{v:,}")
check_value("-9.27", "organizer_test:pairs.B04 vs B01.clustered_ci_simultaneous[0]", 2)
check_value("2.91", "organizer_test:pairs.B04 vs B01.clustered_ci_simultaneous[1]", 2)
check_value("3.18", "organizer_test:pairs.B04 vs B01.delta_eer_pts", 2, abs)

# Act 2: what the benchmark settles.
check_value("2.98", "selection:21df.supt_critical_value", 2)

# Block counts. Bare-integer searches are near-vacuous here ("16" occurs many times),
# so these are anchored. The within-SSL and within-baseline counts are spelled as
# English words in the prose: without an explicit check, SWAPPING THEM passes -- and
# that swap inverts the paper's central structural result.
_pe = get("verdict_ci:point_estimates")
check_window(str(_pe["cross"]), "cross-generation pairs resolve, which is")
# Spelled-out counts: without these, swapping the two within-block results passes.
_n_within = 28 - _pe["cross"]
_n_unres_within = _n_within - (_pe["within_ssl"] + _pe["within_baseline"])
for _phrase, _why in ((f"ten of twelve", "within-generation unresolved count"),
                      ("all six among the baselines", "the within-baseline block resolves none"),
                      ("the two that do, on gaps of", "the within-SSL block resolves exactly two")):
    if _phrase not in TEX:
        failures.append(f"VALUE  {_why}: expected {_phrase!r} in main.tex")
if (_n_within, _n_unres_within) != (12, 10):
    failures.append(f"VALUE  artifact gives {_n_unres_within} of {_n_within} within-generation "
                    f"pairs unresolved; main.tex says ten of twelve")
check_value("0.97", "floor_ci:pairs.XLSR-Mamba vs SSL-AASIST.gap", 2)
check_value("0.94", "floor_ci:pairs.XLS-R+SLS vs SSL-AASIST.gap", 2)

# Act 3: effective sample size and the floor.
check_value("3.9", "scaling:summary.width_ratio_all_28[0]", 1)
check_value("11.1", "scaling:summary.width_ratio_all_28[1]", 1)
check_value("26", "scaling:summary.n_resolved_iid")
check_value("0.066", "floor:summary.total_clustered_variance_within_modern[0]", 3)
check_value("0.144", "floor:summary.total_clustered_variance_within_modern[1]", 3)
check_value("0.949", "floor:summary.total_clustered_variance_within_baseline[0]", 3)
check_value("5.164", "floor:summary.total_clustered_variance_within_baseline[1]", 3)
check_value("6", "floor_ci:summary.bootstrap_count_ci95[0]")
check_value("10", "floor_ci:summary.bootstrap_count_ci95[1]")
check_value("99.3", "floor_ci:summary.p_at_least_6_of_10", 1, lambda v: v * 100)

# Coverage.
def nolead(v):
    return f"{float(v):.3f}".lstrip("0")


# The paper renders these twice: as percentages in Experiments and as bare
# decimals in Limitations. Both renderings are checked against the same key.
# Only the renderings the paper actually uses are required: the i.i.d. figure
# appears as a percentage in Experiments and never as a bare decimal.
for _dec, _p, _forms in ((".160", "coverage_real:iid.coverage", ("16",)),
                         (".955", "coverage_real:twoway.coverage", ("95.5", ".955")),
                         (".965", "coverage_real:jackknife.coverage", ("96.5", ".965"))):
    if nolead(get(_p)) != _dec:
        failures.append(f"VALUE  {_p}: paper says {_dec!r}, artifact gives {nolead(get(_p))!r}")
        continue
    for _form in _forms:
        if not re.search(r"(?<![\d.])" + re.escape(_form) + r"(?![\d])", TEX):
            failures.append(f"VALUE  {_p}: rendering {_form!r} absent from main.tex")

# The DGP fit behind the regime choice (the 22.8 that had no home).
check_value("18.2", "dgp_fit:regimes.high_icc_organizer.fitted_population_eer_pct[0]", 1)
check_value("22.8", "dgp_fit:regimes.high_icc_organizer.fitted_population_eer_pct[1]", 1)
check_value("22.4", "dgp_fit:regimes.high_icc_organizer.real_pooled_eer_pct[0]", 1)
check_value("23.5", "dgp_fit:regimes.high_icc_organizer.real_pooled_eer_pct[1]", 1)
check_value("0.27", "dgp_fit:regimes.low_eer_sota.fitted_population_eer_pct[0]", 2)
check_value("0.06", "dgp_fit:regimes.low_eer_sota.fitted_population_eer_pct[1]", 2)

# Derived quantities the paper states as ranges: recomputed here, not looked up,
# so a change in the underlying pairs breaks the check rather than the claim.
_hw = {}
for k, v in SRC["selection"]["21df"]["pairs"].items():
    a, b = k.split(" vs ")
    blk = "cross" if (a in SSL) != (b in SSL) else ("ssl" if a in SSL else "base")
    _hw.setdefault(blk, []).append((v["ci_pointwise"][1] - v["ci_pointwise"][0]) / 2)
_all_hw = [h for v in _hw.values() for h in v]
# The within-baseline endpoint 2.00 was dropped from the prose in a length pass; the
# 0.45--4.64 span it sits inside is still asserted, so the claim is still guarded.
for lo_hi, vals in (("0.45", [min(_all_hw)]), ("4.64", [max(_all_hw)])):
    if f"{vals[0]:.2f}" != lo_hi:
        failures.append(f"VALUE  half-width {lo_hi} != recomputed {vals[0]:.2f}")
    elif lo_hi not in TEX:
        failures.append(f"VALUE  half-width {lo_hi} absent from main.tex")

# From the unrounded per-pair components. Reading the 3dp summary values instead
# gives 78.2 and would flag the correct "79" as wrong.
_tot = {b: [v["V_spk"] + v["V_att"] for v in SRC["floor"]["pairs"].values()
            if v["block"] == b] for b in ("within-modern", "within-baseline")}
_ratios = (min(_tot["within-baseline"]) / max(_tot["within-modern"]),
           max(_tot["within-baseline"]) / min(_tot["within-modern"]))
if f"{_ratios[0]:.1f}" != "6.6" or round(_ratios[1]) != 79:
    failures.append(f"VALUE  block variance ratio 6.6--79 != recomputed "
                    f"{_ratios[0]:.1f}--{_ratios[1]:.0f}")
elif "6.6--79" not in TEX:
    failures.append("VALUE  '6.6--79' absent from main.tex")

# The studentized margins: the paper's primary evidence since the F4 rewrite.
check_value("3.21", "verdict_ci:margin_by_block.cross.min", 2)
check_value("4.28", "verdict_ci:margin_by_block.cross.max", 2)
check_value("1.06", "verdict_ci:studentized_margin_point_estimate.XLSR-Mamba vs SSL-AASIST", 2)
check_value("1.12", "verdict_ci:studentized_margin_point_estimate.XLS-R+SLS vs SSL-AASIST", 2)
# "0.04--0.60" is the range over the TEN UNRESOLVED pairs, which span both
# within-blocks -- not one block's range. Recomputed from the per-pair margins and
# the campaign's resolved flags so it cannot drift from either.
_marg = get("verdict_ci:studentized_margin_point_estimate")
_unres = [v for k, v in _marg.items()
          if not (SEL_PAIRS.get(k) or SEL_PAIRS[" vs ".join(k.split(" vs ")[::-1])])["resolved_simultaneous"]]
if len(_unres) != 10:
    failures.append(f"VALUE  expected 10 unresolved pairs, found {len(_unres)}")
for _lit, _val in (("0.04", min(_unres)), ("0.60", max(_unres))):
    if f"{_val:.2f}" != _lit:
        failures.append(f"VALUE  unresolved-margin bound {_lit} != recomputed {_val:.2f}")
    elif _lit not in TEX:
        failures.append(f"VALUE  unresolved-margin bound {_lit} absent from main.tex")


# The direction of the asymmetry is a claim, not a number: assert it from the artifact
# so the paper cannot say "highest within SSL" while the data says lowest.
_bb = get("verdict_ci:se_inflation_diagnostic.by_block")
# The paper's claim is now the pct_inflated form: within SSL the inflation is the
# LEAST FREQUENT of the three blocks, which is what rules out a mean-inflation
# explanation for the within-SSL collapse. Assert that from the artifact.
if _bb["within_ssl"]["pct_inflated"] >= min(_bb["cross"]["pct_inflated"],
                                            _bb["within_baseline"]["pct_inflated"]):
    failures.append("VALUE  within-SSL inflation is no longer the least frequent; the "
                    "'cannot be a mean-inflation effect' claim in main.tex must be restated")

# Table 1, cell by cell against results_selection.json. Three things a naive
# per-row check misses, all mutation-proven: ROW ORDER (swapping two rows passes),
# BLOCK GROUPING (moving a baseline row above the midrule passes), and the BOLD
# MARKERS -- which encode the resolution verdict, i.e. the one cell content carrying
# the paper's central structural claim. Bold is therefore matched, not stripped.
_SHORT = {"XLSR-Mamba": "XLSR-Mamba", "XLS-R+SLS": "XLS-R+SLS", "XLSR-Conformer": "XLSR-Conf",
          "SSL-AASIST": "SSL-AAS", "RawNet2": "RawNet2", "LFCC-LCNN": "LFCC-LCNN",
          "LFCC-GMM": "LFCC-GMM", "CQCC-GMM": "CQCC-GMM"}
_ORDER = ["XLSR-Mamba", "XLS-R+SLS", "XLSR-Conformer", "SSL-AASIST",
          "RawNet2", "LFCC-LCNN", "LFCC-GMM", "CQCC-GMM"]
_body = TEX_RAW[TEX_RAW.index("\\label{tab:pairs}"):TEX_RAW.index("\\end{tabular}")]
_expected, _prev_ssl = [], None
for _i, _a in enumerate(_ORDER):
    for _b in _ORDER[_i + 1:]:
        if (_a in SSL) != (_b in SSL):
            continue
        _v = SEL_PAIRS.get(f"{_a} vs {_b}") or SEL_PAIRS[f"{_b} vs {_a}"]
        _hw = (_v["ci_pointwise"][1] - _v["ci_pointwise"][0]) / 2
        _gap = f"{abs(_v['delta_eer_pts']):.3f}"
        # Bold iff the pair resolves: the caption says so, so it is a checked claim.
        if _v["resolved_simultaneous"]:
            _gap = r"\textbf{" + _gap + "}"
        _expected.append((_a in SSL, _SHORT[_a], _SHORT[_b], _gap,
                          f"{_hw:.3f}", f"{2.802 * _v['boot_sd']:.3f}"))
if len(_expected) != 12:
    failures.append(f"TABLE  expected 12 within-generation rows, built {len(_expected)}")

# Walk the printed rows in order and require them to match the artifact's order.
_printed = [ln for ln in _body.split("\n") if "&" in ln and "\\\\" in ln]
_printed = [ln for ln in _printed if not ln.strip().startswith("pair")]
if len(_printed) != len(_expected):
    failures.append(f"TABLE  {len(_printed)} data rows printed, {len(_expected)} expected")
else:
    for _k, (_row, _exp) in enumerate(zip(_printed, _expected)):
        _cells = [c.strip() for c in _row.replace("\\\\", "").split("&")]
        _want = [_exp[1], _exp[2], _exp[3], _exp[4], _exp[5]]
        if _cells != _want:
            failures.append(f"TABLE  row {_k+1} is {_cells} but the artifact gives {_want} "
                            f"(order, values and bold are all checked)")
# Block grouping: the six SSL rows must all precede the midrule, the six baseline rows follow.
_mid = _body.index("\\midrule", _body.index("\\midrule") + 1) if _body.count("\\midrule") > 1 else -1
if _mid < 0:
    failures.append("TABLE  the block-separating \\midrule is missing")
else:
    _above = _body[:_mid]
    for _is_ssl, _a, _b, *_ in _expected:
        _in_above = f"{_a} & {_b}" in _above
        if _in_above != _is_ssl:
            failures.append(f"TABLE  {_a}/{_b} is on the wrong side of the block midrule")

# Kish design effect: predicted from the ICCs, so both inputs and the prediction bind.
import math as _math
_icc = [v["speaker_icc_bona"]["icc"] for v in SRC["icc"]["21df"].values() if "speaker_icc_bona" in v]
_n0s = {round(v["speaker_icc_bona"]["n0"], 2) for v in SRC["icc"]["21df"].values() if "speaker_icc_bona" in v}
if len(_n0s) != 1:
    failures.append(f"VALUE  speaker_icc_bona n0 is not unique: {_n0s}")
_n0 = _n0s.pop()
if f"{_n0:.1f}" != "159.2":
    failures.append(f"VALUE  n0 159.2 != recomputed {_n0:.1f}")
for _lit, _val in (("5.0", _math.sqrt(1 + (_n0 - 1) * min(_icc))),
                   ("11.1", _math.sqrt(1 + (_n0 - 1) * max(_icc)))):
    if f"{_val:.1f}" != _lit:
        failures.append(f"VALUE  design-effect bound {_lit} != recomputed {_val:.1f}")
    elif _lit not in TEX:
        failures.append(f"VALUE  design-effect bound {_lit} absent from main.tex")

# Leave-one-corpus-out: the paper claims the cross-generation block is invariant to
# provenance and that both within-SSL resolutions are not. Both halves bound here.
_loco = SRC["source"]["leave_one_corpus_out"]
_xflip = [f for f in _loco["verdict_flips_vs_full_data"]
          if (f["pair"].split(" vs ")[0] in SSL) != (f["pair"].split(" vs ")[1] in SSL)]
if _xflip:
    failures.append(f"VALUE  {len(_xflip)} cross-generation verdict(s) flip under "
                    f"leave-one-corpus-out; main.tex says all 16 are unchanged")
_ssl_fell = {f["pair"] for f in _loco["verdict_flips_vs_full_data"]
             if f["full_data"] and not f["refit"]}
if len(_ssl_fell) != 2:
    failures.append(f"VALUE  {len(_ssl_fell)} resolved verdict(s) fall under "
                    f"leave-one-corpus-out; main.tex says both within-SSL resolutions do")

# Permutation null on the corpus share: the analytic expectation and the tested claim.
_pn = SRC["source"]["permutation_null"]
if f"{100 * _pn['analytic_expected_share_under_no_effect']:.1f}" != "2.2":
    failures.append("VALUE  permutation null expectation is no longer 2.2%")
elif "2.2" not in TEX:
    failures.append("VALUE  permutation null expectation 2.2 absent from main.tex")
if _pn["n_pairs_p_below_0.05"] != len(_pn["pairs"]):
    failures.append(f"VALUE  only {_pn['n_pairs_p_below_0.05']}/{len(_pn['pairs'])} pairs "
                    f"exceed the permutation null at p<0.05; main.tex says every one")

# --- 2. WINDOW ------------------------------------------------------------
check_window("12.7", "survives their test most emphatically")
check_window("5,162", "would need a family of")
check_window("2.98", "the sup-t critical value")
check_window("99.3", "six or more in")
check_window("0.27", "but not low-EER ones")
check_window(".945", "all consistent with nominal")
check_window("3.21", "The studentized margins state it directly")

# --- 3. PRESENCE (markers, never values) ----------------------------------
# Wording may change; the scope restriction may not. Without it, "none survives"
# reads as the totality of the 2021 analysis, which tested every submitted pair.
check_presence_re(r"the four organizer baselines (?:with public scores|whose scores are public)|the four systems we can check",
                  "conclusion scope; without it 'none survives' reads as the whole 2021 analysis")
check_presence("fall below their own detectable effect",
               "F5/M4: a reader must be able to check gaps against their own MDE; the "
               "per-pair figures now live in Table 1, whose rows are checked above")
check_presence("no cell-level agreement", "H4: the withdrawal must be stated, not merely implied")
check_presence("which we treat as inadmissible",
               "say WHY the published count is not given, or a reader re-derives it and wonders")
check_presence("At least six of the ten unresolved pairs",
               "must lead with six; leading with eight lets a skimmer take the withdrawn count")
check_presence("\\textbf{Scope.}", "pool caveat; Limitations refers back to it")
check_presence("cannot speak for submissions whose scores were never released", "pool scope")
check_presence("studentized", "F4: the margins are the primary evidence, not the bootstrap")
check_presence("self-supervised systems occupy",
               "the rank-interval statement, which is where SSL systems are named in full")
check_presence("speaker and attack cluster counts",
               "the two named cluster units, in a paper whose thesis is the cluster unit")
check_presence("not established on this evaluation set", "scope of 'unresolved'")
check_presence("loosest step of 0.05", "Holm step value; without it the arithmetic is uncheckable")
check_presence("journal version of the 2021 overview \\cite{asvspoof21journal}",
               "R8: the premise names three texts and this one carried no citation")
check_presence("which is arithmetic rather than a finding",
               "the cross-generation separation must not be dressed as a structural discovery")
check_presence("verified by Monte Carlo", "coverage targets the model's own delta, not the real one")
check_presence("subsampling flattens a fitted exponent", "must disclaim the fitted exponent")
check_presence("because the field has moved",
               "M6: observe the organizers' redesign rather than prescribe to them")
check_presence("Poh, Martin and Bengio", "M7: the nearest antecedent must be engaged, not listed")
check_presence("conditional on that exchangeability",
               "the estimand must be named and the result stated as conditional on it: "
               "93 speakers and 110 attacks are not a probability sample")
check_presence("We release an audit package",
               "the release sentence must point at something a reader can open")
check_presence("adding attacks alone",
               "the attack-budget claim holds the observed effect and speaker pool fixed")
# The lapse claim now lives only in the abstract and S1, each naming its sources; the
# universal form stays retired below.
# The two procedures agreeing on all 28 is what makes the conjunction rule harmless;
# asserted from the artifact so the claim cannot outlive the fact.
_dis = [k for k, v in SEL_PAIRS.items()
        if (not (v["ci_simultaneous"][0] <= 0 <= v["ci_simultaneous"][1]))
        != (not (v["ci_jackknife"][0] <= 0 <= v["ci_jackknife"][1]))]
if _dis:
    failures.append(f"VALUE  bootstrap and jackknife disagree on {len(_dis)} pair(s) "
                    f"({_dis[:3]}); main.tex says they agree on all 28")
check_presence("they agree on all 28 pairs",
               "the conjunction rule does no work only if both variants agree everywhere")
check_presence("our reconstruction",
               "five separations is our reconstruction, not the published matrix's count")
check_presence("adds a calibration study instead",
               "the lapse claim must name what replaced it rather than claim a census")
check_presence("not whether two systems differ",
               "M5: the calibration-study rebuttal must be in the paper, not the response")
check_presence("source corpora", "M1: the source-corpus decomposition must be disclosed")
check_presence("Permuting speaker labels",
               "the corpus share must be a tested claim, not a description: 3 corpora is 2 df")
check_presence("design-effect approximation",
               "the width ratio must be placed by the ICC as well as measured; it is an\n                approximation here, not an identity -- EER is a thresholded functional on\n                two crossed factors with cluster sizes from 8 to 355")
check_presence("anti-conservative", "M1: the direction the corpus finding cuts against us")
check_presence("three methods with different failure modes",
               "the convergence of margins, block counts and provenance refits is the "
               "robustness claim; reporting only the strongest reads as one fragile result")
check_presence("Dropping each corpus in turn",
               "the anti-conservatism must be bounded by refits, not conceded as a direction")
check_presence("attack interaction divided by",
               "M3: the jackknife's upward bias on the floor, biased toward our own conclusion")
check_presence("737", "M6: the organizers' redesign is the observation that replaces the prescription")
check_presence("110 to 16", "M6: attacks were cut while speakers were multiplied")
check_presence("The latter subject is our focus",
               "Poh explicitly sets aside the case this paper is in; the quote is the defence")
check_presence("dyadic", "Fogliato advises against two-level bootstraps for a different dependence structure")
check_presence("the shared decision threshold",
               "m2: without the mechanism, the per-speaker EER spread looks to contradict the floor")
_icc = [v["speaker_icc_bona"]["icc"] for v in SRC["icc"]["21df"].values() if "speaker_icc_bona" in v]
for _lit, _val in (("0.15", min(_icc)), ("0.77", max(_icc))):
    if f"{_val:.2f}" != _lit:
        failures.append(f"VALUE  bona-fide speaker ICC bound {_lit} != recomputed {_val:.2f}")
    elif _lit not in TEX:
        failures.append(f"VALUE  bona-fide speaker ICC bound {_lit} absent from main.tex")

# --- 4. RETIRED -----------------------------------------------------------
check_retired(r"cell for cell", "H4: cell-level agreement was withdrawn (pixel read)")
check_retired(r"S\^\{-", "fitted speaker exponent withdrawn (finite-population flattening)")
check_retired(r"halving a clustered interval", "halving prescription withdrawn (extrapolation)")
check_retired(r"four to seven times the speakers", "same")
check_retired(r"A\^\{-0\.2\}|A\^-0\.2", "attack power law withdrawn (identity, not a finding)")
check_retired(r"two to three times the return", "denominator was the withdrawn attack exponent")
check_retired(r"6\.6--21", "mixed a min-ratio with a median-ratio")
check_retired(r"factor of seven", "not derivable from the endpoints it attached to")
check_retired(r"eight of the ten unresolved", "superseded by 'at least six'")
check_retired(r"agree to within 2\\%", "measured 2.96% on one pair")
check_retired(r"pigeonhole correction(?! is)", "the pigeonhole variant is withdrawn")
check_retired(r"3\.7--11\.2", "superseded by the artifact's [3.9, 11.1]")
check_retired(r"common across blocks|one common bias",
              "the bias is NOT common across blocks; this formulation was withdrawn")
check_retired(r"tab:blocks", "the block-count table was replaced by the per-pair table")
check_retired(r"collect speakers, not attack", "M6: the prescription is withdrawn in favour of observation")
check_retired(r"attack conditions?\b", "the organizers reserve 'conditions' for the codec conditions C1-C9")
check_retired(r"nothing replaced it", "M5: refutable -- ASVspoof 5 adds a calibration study")
check_retired(r"(?:the published test|2021 analysis's) five separations",
              "five is OUR reconstruction under the independent form; the paper disclaims "
              "cell-level agreement with the published matrix, so it cannot also report its count")
check_retired(r"beats the previous best",
              "the historical sequence is not established by a four-system public-score pool")
check_retired(r"[Ee]ffective sample size is set by",
              "governed by, not set by: EER is a nonlinear two-sided functional")
check_retired(r"certif(?:y|ied|ication)", "withdrawn twice: R=200 checks robustness, it does not certify")
check_retired(r"no attack budget closes", "narrowed: adding attacks alone, at the observed effect, this speaker pool")
check_retired(r"every margin (?:claimed )?since is untested", "not a census; name the audited sources")
check_retired(r"Being an identity", "the design effect is an approximation here, not an identity")
check_retired(r"model-free", "the design-effect approximation is not model-free")
# Enumerating wrong phrasings is brittle -- an earlier version of this check missed
# "largest". Assert the correct direction positively instead: the sentence must still
# say the within-SSL mean is the lowest, whatever words it uses around it.
check_presence_re(r"biased against resolving.{0,200}unevenly",
                  "the bootstrap bias and its unevenness across blocks must stay disclosed "
                  "even though the per-block figures now live only in the artifact")
check_retired(r"(?:highest|larger|largest|greatest|heavier|most) (?:mean )?(?:inflation )?within SSL",
              "within-SSL mean inflation is the LOWEST; the asymmetry is in the tail only")

# --- 5. BIBLIOGRAPHY ------------------------------------------------------
# Uncited entries are invisible: they do not appear in the rendered reference list,
# so a citation lost to a compression edit leaves the claim standing with its
# attribution silently detached and nothing fires. An external audit found nine such
# keys in this paper, two of them collateral losses from a restructure. Every key
# must therefore be cited or declared here.
BIB_RETAINED = set()  # keys deliberately kept in refs.bib without a citation
_bib = (HERE / "refs.bib").read_text()
_keys = set(re.findall(r"@\w+\{([^,]+),", _bib))
_cited = {k.strip() for m in re.findall(r"\\cite\{([^}]*)\}", TEX) for k in m.split(",")}
for _k in sorted(_keys - _cited - BIB_RETAINED):
    failures.append(f"BIB    {_k!r} is defined in refs.bib but never cited "
                    f"(restore the citation, delete the entry, or add it to BIB_RETAINED)")
for _k in sorted(_cited - _keys):
    failures.append(f"BIB    {_k!r} is cited but missing from refs.bib")

# --- 6. READER-FACING TEXT OUTSIDE main.tex --------------------------------
# Withdrawn terminology survived in two places no check reached: a figure axis label
# (rendered, and caught only by looking at the raster) and an artifact `note` field
# (read by anyone cross-checking the JSON). A whole-file scan of the sources is
# useless here -- it returns 21 hits of which 18 are this file matching its own
# RETIRED list, or the comments that *record* each withdrawal. So the scan is scoped
# to the two surfaces a reader actually sees, and skips lines documenting a fix.
_RENDERED = re.compile(r"set_(?:xlabel|ylabel|title)\(\s*([\"'])(.*?)\1|annotate\(\s*(?:f?[\"'])(.*?)[\"']")
_DOCUMENTING = re.compile(r"withdrawn|superseded|retired|NOT common|no longer", re.I)
_ARTIFACT_TEXT_KEYS = ("note", "reading", "why", "estimator", "method",
                       "measured_width_source", "point_estimate_check")

def _scan(label, text, patterns):
    for pat, why in patterns:
        for m in re.finditer(pat, text, re.I):
            line = text[:m.start()].count("\n")
            ctx = text.split("\n")[line]
            if _DOCUMENTING.search(ctx):
                continue
            failures.append(f"SURFACE {label}: {m.group()!r} -- {why}")

_RETIRED_TERMS = [(r"attack conditions?\b", "organizers reserve 'conditions' for codecs C1-C9"),
                  (r"collect speakers, not attack", "the prescription is withdrawn"),
                  (r"cell for cell", "cell-level agreement was withdrawn"),
                  (r"common across blocks", "the bias is not common across blocks")]

# (a) strings that can reach a rendered figure
_figsrc = (HERE / "figures_m1.py").read_text()
_rendered_strings = "\n".join(g for m in _RENDERED.finditer(_figsrc) for g in m.groups() if g)
_scan("figure label", _rendered_strings, _RETIRED_TERMS)

# (b) prose written INTO released artifacts
for _name in _FILES:
    def _texts(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in _ARTIFACT_TEXT_KEYS and isinstance(v, str):
                    yield v
                else:
                    yield from _texts(v)
        elif isinstance(node, list):
            for v in node:
                yield from _texts(v)
    _scan(f"results_{_name}.json", "\n".join(_texts(SRC[_name])), _RETIRED_TERMS)

# --- report ---------------------------------------------------------------
n = (len([l for l in open(__file__) if l.startswith("check_")]))
if failures:
    print(f"FAIL — {len(failures)} problem(s):\n")
    for f in failures:
        print("  " + f)
    sys.exit(1)
print(f"OK — all checks pass ({len(_FILES)} artifacts, "
      f"{len(_all_hw)} pairs recomputed).")
