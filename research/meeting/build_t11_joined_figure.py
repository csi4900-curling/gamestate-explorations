"""Show both measured T11 camera trajectories and their nominal handoff error."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "prototype/cross-view/results.json"
OUTPUT = ROOT / "prototype/trajectory-accuracy/t11-joined-trajectory.png"


def build_figure():
    data = json.loads(SOURCE.read_text())
    shot = next(item for item in data["throws"] if item["id"] == "T11")
    departure, receiving = shot["departure"], shot["display_arrival"]
    handoff = shot["expanded_handoff"]
    assert len(departure) == 31 and len(receiving) == 29
    assert abs(handoff["sampled_gap_s"]) < 1e-6
    assert not shot["independently_verified_identity"]
    assert not shot["physical_accuracy_measured"]

    navy, teal, gold, coral = "#14313c", "#087f78", "#c88919", "#ad5148"
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig, (ice, timing) = plt.subplots(
        1, 2, figsize=(13.2, 6.0), gridspec_kw={"width_ratios": [0.76, 1.24]}
    )
    fig.patch.set_facecolor("#fffefa")
    for ax in (ice, timing):
        ax.set_facecolor("#fffefa")
        for spine in ax.spines.values():
            spine.set_color("#cbd9d7")
        ax.tick_params(colors="#52646b")

    ice.add_patch(
        Rectangle((-2.375, 0), 4.75, 34.747, fill=False, edgecolor="#93b6b7", linewidth=1.5)
    )
    for y in (0, 34.747):
        ice.add_patch(plt.Circle((0, y), 1.829, fill=False, edgecolor="#a5c5ce", linewidth=1.4))
    for points, colour in ((departure, teal), (receiving, gold)):
        xs = [point["world_m"][0] for point in points]
        ys = [point["world_m"][1] for point in points]
        ice.plot(xs, ys, color=colour, linewidth=2.7, marker="o", markersize=3.4, zorder=3)
    a, b = departure[-1], receiving[0]
    ice.plot(
        [a["world_m"][0], b["world_m"][0]],
        [a["world_m"][1], b["world_m"][1]],
        color=coral,
        linestyle="--",
        linewidth=1.6,
        zorder=4,
    )
    ice.scatter(
        [a["world_m"][0], b["world_m"][0]],
        [a["world_m"][1], b["world_m"][1]],
        s=85,
        c=[teal, gold],
        edgecolors="white",
        linewidths=1.5,
        zorder=5,
    )
    ice.annotate(
        "même image · 46,7 s\nécart Y = 0,61 m",
        xy=(b["world_m"][0], b["world_m"][1]),
        xytext=(0.5, 18.1),
        fontsize=10,
        color=coral,
        arrowprops={"arrowstyle": "->", "color": coral, "lw": 1.3},
    )
    ice.set_xlim(-2.8, 2.8)
    ice.set_ylim(5, 36.2)
    ice.set_xlabel("Position latérale nominale (m)", color=navy)
    ice.set_ylabel("Progression vers la maison (m)", color=navy)
    ice.set_title("Deux projections sur la piste", color=navy, loc="left", weight="bold")

    t0 = departure[0]["time_s"]
    for points, colour, label in (
        (departure, teal, "Départ · 31 positions"),
        (receiving, gold, "Réception · 29 positions, dont 15 lointaines"),
    ):
        timing.plot(
            [point["time_s"] - t0 for point in points],
            [point["world_m"][1] for point in points],
            color=colour,
            marker="o",
            markersize=3.7,
            linewidth=2.7,
            label=label,
            zorder=3,
        )
    at = a["time_s"] - t0
    timing.plot(
        [at, at],
        [a["world_m"][1], b["world_m"][1]],
        color=coral,
        linestyle="--",
        linewidth=1.8,
        zorder=5,
    )
    timing.scatter(
        [at, at],
        [a["world_m"][1], b["world_m"][1]],
        s=95,
        c=[teal, gold],
        edgecolors="white",
        linewidths=1.5,
        zorder=6,
    )
    timing.annotate(
        "Même instant, deux positions\nΔY = +0,61 m · ΔX = −0,09 m",
        xy=(at, b["world_m"][1]),
        xytext=(5.0, 19.6),
        color=coral,
        fontsize=10.5,
        weight="bold",
        arrowprops={"arrowstyle": "->", "color": coral, "lw": 1.3},
    )
    timing.set_xlim(-0.4, receiving[-1]["time_s"] - t0 + 0.5)
    timing.set_ylim(6, 36)
    timing.set_xlabel("Temps depuis la première observation (s)", color=navy)
    timing.set_ylabel("Progression vers la maison (m)", color=navy)
    timing.set_title("Positions enregistrées dans le temps", color=navy, loc="left", weight="bold")
    timing.legend(loc="lower right", frameon=False, fontsize=9.5)
    fig.suptitle(
        "T11 · les deux caméras se chevauchent, leurs positions divergent",
        x=0.055,
        y=0.985,
        ha="left",
        color=navy,
        fontsize=16.5,
        weight="bold",
    )
    fig.text(
        0.055,
        0.018,
        "Points lointains : projection expérimentale · association entre caméras provisoire · aucune précision physique validée",
        color="#52646b",
        fontsize=9.7,
    )
    fig.subplots_adjust(top=0.85, bottom=0.18, left=0.075, right=0.97, wspace=0.3)
    fig.savefig(OUTPUT, dpi=170, facecolor=fig.get_facecolor())
    plt.close(fig)
    return OUTPUT


if __name__ == "__main__":
    print(build_figure())
