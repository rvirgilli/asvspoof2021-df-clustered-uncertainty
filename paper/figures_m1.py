"""M1 figures. Own file: paper/figures.py is shared with another line.

Fig 1 (forest): all six within-SSL pairs, matched simultaneous trial-i.i.d. and
                speaker-attack procedure bands from the full 28-pair family.
Fig 2 (finite-A component): measured clustered-CI width vs number of attacks,
                with each pair's delete-speaker component at the observed A=110.
Palette: Okabe-Ito subset, CVD-validated; every series directly labelled.
System names match Table 1's abbreviations so a reader can cross-reference.
"""

import hashlib
import json
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
EXP = HERE.parent / "derived"
BLUE, VERM, GRAY = "#0072B2", "#D55E00", "#6e6e6e"
SSL = {"XLSR-Mamba", "XLS-R+SLS", "XLSR-Conformer", "SSL-AASIST"}

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 9, "axes.labelsize": 9,
    "xtick.labelsize": 9, "ytick.labelsize": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e6e6e6", "grid.linewidth": 0.5,
    "pdf.fonttype": 42,
})
COL = 86 / 25.4  # spconf: (178 mm text width - 6 mm gutter) / 2


def short(m):
    return m.replace("XLSR-Conformer", "XLSR-Conf").replace("SSL-AASIST", "SSL-AAS")


def fig_forest():
    """Show the complete modern cohort, without recalibrating a six-pair family."""
    source = EXP / "results_matched_iid.json"
    matched = json.loads(source.read_text())
    seal = json.loads((EXP / "results_matched_iid.provenance.json").read_text())
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != seal["sha256"][source.name]:
        raise ValueError("Matched-result file does not match its provenance seal")
    iid = matched["iid"]["pairs"]
    speaker_attack = matched["speaker_attack"]["pairs"]
    family = [f"{a} vs {b}" for a, b in combinations(matched["systems"], 2)]
    if set(iid) != set(family) or set(speaker_attack) != set(family):
        raise ValueError("Both arms must contain the full matched comparison family")
    # Keep the artifact's system order; do not select rows by separation or gap.
    order = [p for p in family if set(p.split(" vs ")) <= SSL]
    if len(order) != len(list(combinations(SSL, 2))):
        raise ValueError("A within-SSL comparison is missing; do not approximate it")
    fig, ax = plt.subplots(figsize=(COL, 2.60))
    # Fixed page box at the actual column width: no tight-bbox resizing of fonts.
    fig.subplots_adjust(left=0.080, right=0.950, bottom=0.19, top=0.80)
    for i, pair in enumerate(order):
        d = iid[pair]["delta_eer_pts"]
        if d != speaker_attack[pair]["delta_eer_pts"]:
            raise ValueError(f"Unmatched point estimates: {pair}")
        lo_i, hi_i = iid[pair]["simultaneous"]
        lo_c, hi_c = speaker_attack[pair]["simultaneous"]
        for arm, lo, hi in ((iid, lo_i, hi_i), (speaker_attack, lo_c, hi_c)):
            if not lo <= d <= hi or arm[pair]["resolved_simultaneous"] != (lo > 0 or hi < 0):
                raise ValueError(f"Inconsistent estimate, band or indicator: {pair}")
        y = len(order) - i
        ax.plot([lo_c, hi_c], [y, y], color=BLUE, lw=1.5, zorder=1)
        ax.plot([lo_c, hi_c], [y, y], linestyle="none", marker="|", color=BLUE,
                ms=5, markeredgewidth=1.1, zorder=2)
        ax.plot([lo_i, hi_i], [y, y], color=VERM, lw=3.2, solid_capstyle="butt", zorder=3)
        ax.plot([d], [y], "o", color="#222", ms=3.2, zorder=4)
        ax.annotate(pair.replace(" vs ", " − "), (0, y), xycoords=("axes fraction", "data"),
                    textcoords="offset points", xytext=(0, 4), fontsize=9,
                    va="bottom", ha="left", color="#333")
        ax.annotate(f"{d:.3f}".replace("-", "−"), (1, y),
                    xycoords=("axes fraction", "data"), textcoords="offset points",
                    xytext=(0, 4), fontsize=9, va="bottom", ha="right", color="#222")
    ax.axvline(0, color=GRAY, lw=0.9, ls=":")
    ax.set_ylim(0.45, len(order) + 0.55)
    ax.spines["left"].set_visible(False)
    ax.set_yticks([])
    # Display coordinates only; every estimate and endpoint above is read verbatim.
    endpoints = [x for p in order for arm in (iid, speaker_attack)
                 for x in arm[p]["simultaneous"]]
    tick_step = 0.5
    lo = np.floor(min(endpoints) / tick_step) * tick_step
    hi = np.ceil(max(endpoints) / tick_step) * tick_step
    ax.set_xlim(lo, hi)
    ax.set_xticks(np.arange(lo, hi + tick_step / 2, tick_step))
    ax.set_xlabel("ΔEER (percentage points), A − B", labelpad=3)
    for y, color, width, label in (
        (0.956, VERM, 3.2, "trial-i.i.d. simultaneous"),
        (0.890, BLUE, 1.5, "speaker-attack simultaneous"),
    ):
        fig.add_artist(plt.Line2D([0.065, 0.16], [y, y], transform=fig.transFigure,
                                  color=color, lw=width, solid_capstyle="butt"))
        fig.text(0.185, y, label, color=color, fontsize=9, va="center")
    fig.savefig(HERE / "figs/forest.pdf")
    plt.close(fig)


def fig_floor():
    r = json.load(open(EXP / "results_widths.json"))["pairs"]
    fl = json.load(open(EXP / "results_floor.json"))["pairs"]
    fig, ax = plt.subplots(figsize=(COL, 2.25))
    order = sorted(r, key=lambda k: -r[k]["by_A"]["10"]["mean_width_pts"])
    labpos = {0: (5, 4), 1: (5, 5), 2: (5, -9)}   # at the right end of each curve
    for j, k in enumerate(order):
        v = r[k]
        A = sorted(int(a) for a in v["by_A"])
        w = [v["by_A"][str(a)]["mean_width_pts"] for a in A]
        sd = [v["by_A"][str(a)]["width_sd"] or 0 for a in A]
        c = VERM if v["era"] == "organizer-era" else BLUE
        ax.errorbar(A, w, yerr=sd, color=c, lw=1.5, marker="o", ms=2.6,
                    capsize=1.5, elinewidth=0.8, alpha=1.0 if j != 2 else 0.75)
        component = fl[k]["finite_A_speaker_component_width_pts"]
        ax.plot([88, 130], [component, component], color=c, lw=0.9,
                ls=(0, (4, 2)), alpha=0.85)
        lab = " vs ".join(short(x) for x in k.split(" vs "))
        ax.annotate(lab, (A[-1], w[-1]), textcoords="offset points",
                    xytext=labpos[j], fontsize=5.7, color=c, va="center")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks([10, 20, 40, 80, 110])
    ax.set_xticklabels([10, 20, 40, 80, 110])
    ax.set_yticks([1, 2, 5, 10])
    ax.set_yticklabels([1, 2, 5, 10])
    ax.minorticks_off()
    ax.set_xlim(8.8, 260)
    ax.set_ylim(0.70, None)  # room for the lowest finite-A component marker
    ax.set_xlabel("attacks $A$ in the evaluation set")
    ax.set_ylabel("clustered CI width (pts)")
    fig.tight_layout(pad=0.4)
    fig.savefig(HERE / "figs/floor.pdf", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


if __name__ == "__main__":
    fig_forest()
    fig_floor()
    print("wrote figs/forest.pdf, figs/floor.pdf")
