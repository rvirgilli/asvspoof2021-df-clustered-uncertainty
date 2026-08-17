"""M1 figures. Own file: paper/figures.py is shared with another line.

Fig 1 (forest): the six baseline pairs, published i.i.d. interval against ours.
Fig 2 (finite-A component): measured clustered-CI width vs number of attacks,
                with each pair's delete-speaker component at the observed A=110.
Palette: Okabe-Ito subset, CVD-validated; every series directly labelled.
System names match Table 1's abbreviations so a reader can cross-reference.
"""

import json
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
    "font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7,
    "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e6e6e6", "grid.linewidth": 0.5,
    "pdf.fonttype": 42,
})
COL = 3.45


def short(m):
    return m.replace("XLSR-Conformer", "XLSR-Conf").replace("SSL-AASIST", "SSL-AAS")


def fig_forest():
    """The six baseline pairs: the published i.i.d. verdict against ours."""
    org = json.load(open(EXP / "results_organizer_test.json"))["pairs"]
    fig, ax = plt.subplots(figsize=(COL, 1.20))
    order = sorted(org, key=lambda k: abs(org[k]["delta_eer_pts"]))
    for i, k in enumerate(order):
        v = org[k]
        d = v["delta_eer_pts"]
        se = abs(d / v["z_iid"]) if v["z_iid"] else 0.0
        lo_i, hi_i = d - 1.96 * se, d + 1.96 * se
        lo_c, hi_c = v["clustered_ci_simultaneous"]
        y = i + 1
        ax.plot([lo_c, hi_c], [y, y], color=BLUE, lw=3.4, solid_capstyle="round",
                alpha=0.5, zorder=1)
        ax.plot([lo_i, hi_i], [y, y], color=VERM, lw=3.4, solid_capstyle="butt", zorder=3)
        ax.plot([d], [y], "o", color="#222", ms=3.2, zorder=4)
        lab = "/".join(v["systems"].split(" vs "))
        ax.annotate(lab, (hi_c, y), textcoords="offset points", xytext=(3, 0),
                    fontsize=5.4, va="center", color="#333")
        ax.annotate(f"$z{{=}}{abs(v['z_iid']):.1f}$", (lo_c, y), textcoords="offset points",
                    xytext=(-3, 0), ha="right", fontsize=5.4, va="center", color=VERM)
    ax.axvline(0, color=GRAY, lw=0.9, ls=":")
    ax.set_ylim(0.35, len(order) + 0.9)
    ax.spines["left"].set_visible(False)
    ax.set_yticks([])
    ax.set_xlim(-12.5, 11.5)
    ax.set_xlabel("$\\Delta$EER (points), system A $-$ system B")
    ax.annotate("published i.i.d. interval", (-11.8, len(order) + 0.55), color=VERM, fontsize=6)
    ax.annotate("clustered (this work)", (0.6, len(order) + 0.55), color=BLUE, fontsize=6)
    fig.tight_layout(pad=0.4)
    fig.savefig(HERE / "figs/forest.pdf", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def fig_floor():
    r = json.load(open(EXP / "results_widths.json"))["pairs"]
    fl = json.load(open(EXP / "results_floor.json"))["pairs"]
    fig, ax = plt.subplots(figsize=(COL, 1.20))
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
