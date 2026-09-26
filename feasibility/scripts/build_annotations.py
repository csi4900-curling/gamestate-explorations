"""Manual visual annotations by the assistant, in the saved 960x540 review frames.
This script records observations, not predictions inferred from official positions.
L/R/T/B are intersections of ring boundaries with tee/centre lines, NOT ellipse extrema.
"""

import json
from pathlib import Path

r = Path(__file__).resolve().parents[1]
frames = []


def add(t, end, shot, fit, check, red, yellow, notes="", tier="overhead", excluded=None):
    frames.append(
        dict(
            id=f"t{t:03d}",
            timestamp_s=t,
            image=f"frames/t{t:03d}_960.png",
            original_image=f"frames/t{t:03d}.png",
            annotation_size=[960, 540],
            end=end,
            shot=shot,
            tier=tier,
            diagram_sign=1 if tier == "oblique" else -1,
            fit=fit,
            check=check,
            stones=[
                dict(id=f"{c}{j + 1}", colour=c, pixel=p)
                for c, ps in [("R", red), ("Y", yellow)]
                for j, p in enumerate(ps)
            ],
            notes=notes,
            excluded_stones=excluded or [],
        )
    )


add(
    100,
    1,
    3,
    {
        "oL": [259, 355],
        "oR": [690, 356],
        "oT": [475, 298],
        "oB": [475, 418],
        "wL": [331, 355],
        "wR": [618, 356],
    },
    {"wT": [475, 317], "wB": [475, 394], "rL": [401, 355], "rR": [549, 356]},
    [[475, 330], [526, 339]],
    [[446, 337], [461, 378], [475, 466]],
    "Oblique view. Stone body centres project above the ice plane; no height correction. All visible stones manually marked.",
    tier="oblique",
)
add(
    136,
    1,
    4,
    {
        "oL": [304, 362],
        "oR": [645, 365],
        "oT": [476, 195],
        "oB": [474, 536],
        "rL": [416, 363],
        "rR": [533, 364],
        "rT": [475, 305],
        "rB": [474, 422],
    },
    {"wL": [361, 363], "wR": [588, 364], "wT": [476, 250], "wB": [474, 479]},
    [[479, 355], [434, 384], [473, 410]],
    [[486, 274], [497, 386], [477, 56]],
    "After the draw, before the next broadcast cut; distant guard is an extrapolation check.",
)
add(
    148,
    1,
    9,
    {
        "rL": [345, 278],
        "rR": [607, 279],
        "rT": [479, 150],
        "rB": [475, 408],
        "wL": [219, 277],
        "wR": [732, 281],
    },
    {"wT": [479, 24], "wB": [472, 537], "oL": [84, 275], "oR": [868, 282]},
    [[416, 169], [458, 214], [492, 268], [475, 383]],
    [[502, 79], [354, 239], [416, 338], [526, 333]],
    "One Canadian stone remains on score graphic. Both guards outside crop. House layout is also almost unchanged from shot 8; exact shot indexing relies on broadcast context.",
)
add(
    194,
    2,
    9,
    {
        "oL": [263, 264],
        "oR": [697, 266],
        "oT": [480, 48],
        "oB": [478, 481],
        "rL": [406, 264],
        "rR": [554, 265],
        "rT": [480, 191],
    },
    {"wL": [335, 264], "wR": [624, 265], "wT": [480, 120], "wB": [480, 409]},
    [[414, 152], [544, 331]],
    [[214, 285], [214, 459], [526, 374]],
    "One yellow house stone is obscured by player. Wide lateral yellow stones are explicitly annotated; no invented occluded centres.",
)
add(
    231,
    2,
    10,
    {
        "oL": [98, 242],
        "oR": [862, 241],
        "rL": [352, 244],
        "rR": [608, 242],
        "rT": [480, 114],
        "rB": [480, 370],
    },
    {"wL": [229, 244], "wR": [731, 242], "wB": [480, 493]},
    [[362, 44], [637, 420]],
    [],
    "End already finished; adjacent frames 230/232 show the yellow stones being moved during clearance. Compare only the two stationary red stones with shot 10; this is a partial-board comparison.",
    excluded=[
        {
            "colour": "Y",
            "pixel": [542, 355],
            "reason": "moving during end clearance; confirmed with frames 230 and 232",
        },
        {
            "colour": "Y",
            "pixel": [489, 397],
            "reason": "moving during end clearance; confirmed with frames 230 and 232",
        },
    ],
)
add(
    309,
    4,
    9,
    {
        "oL": [82, 269],
        "oR": [878, 272],
        "rL": [347, 270],
        "rR": [614, 271],
        "rT": [480, 138],
        "rB": [480, 404],
    },
    {"wL": [218, 270], "wR": [742, 272], "wT": [480, 9], "wB": [479, 532]},
    [[191, 123], [218, 178], [902, 440]],
    [],
    "During shot 10: compare only the three stationary red stones to state after shot 9. Moving yellow shooter explicitly excluded; this is not a complete post-shot board.",
    excluded=[{"colour": "Y", "pixel": [428, 166], "reason": "moving shooter"}],
)
add(
    344,
    5,
    8,
    {
        "oL": [307, 343],
        "oT": [476, 179],
        "oB": [472, 513],
        "rL": [417, 343],
        "rR": [531, 345],
        "rB": [473, 401],
    },
    {"wL": [362, 343], "wR": [585, 345], "wT": [475, 234], "wB": [474, 456]},
    [[394, 344], [464, 329], [480, 347], [508, 307], [489, 460]],
    [[467, 294], [452, 366], [464, 393], [535, 462], [477, 43]],
    "End 5 after shot 8; five red and five yellow stones visible. Outer-right and inner-top intersections occluded, not used.",
)
add(
    398,
    6,
    8,
    {
        "oL": [160, 319],
        "oR": [798, 323],
        "oT": [481, 6],
        "rL": [373, 320],
        "rR": [588, 322],
        "wL": [269, 320],
        "wR": [690, 323],
    },
    {"wT": [480, 111], "wB": [478, 534]},
    [[464, 305], [429, 462]],
    [[495, 205], [382, 281], [431, 363], [489, 417], [546, 417]],
    "Close view after shot 8. Two withheld vertical landmarks only; two red guards outside crop. Broadcast count graphic has not yet updated.",
)
add(
    414,
    6,
    8,
    {
        "oL": [288, 366],
        "oR": [671, 367],
        "oT": [480, 178],
        "rL": [416, 366],
        "rR": [545, 367],
        "rT": [480, 302],
    },
    {"wL": [352, 366], "wR": [608, 368], "wT": [480, 240], "wB": [478, 496]},
    [[473, 31], [528, 145], [469, 357], [449, 453]],
    [[489, 296], [420, 343], [450, 393], [486, 425], [521, 425]],
    "Repeat observation of the SAME shot-8 board at a wider zoom, not an independent shot. Two red guards are extrapolation checks.",
)
add(
    449,
    6,
    9,
    {
        "oL": [287, 375],
        "oR": [673, 376],
        "oT": [479, 184],
        "rR": [546, 376],
        "wL": [351, 375],
        "wR": [608, 376],
    },
    {"wT": [480, 247], "wB": [478, 504]},
    [[471, 35], [527, 150], [450, 339], [470, 369], [449, 462]],
    [[489, 303], [414, 363], [450, 401], [486, 435], [522, 434]],
    "After Canadian final draw, one Swiss stone remains. Inner-left/top/bottom landmarks hidden by stones. Only two vertical withheld landmarks.",
)
add(
    469,
    6,
    10,
    {
        "oL": [224, 264],
        "oR": [737, 267],
        "oT": [480, 9],
        "oB": [478, 522],
        "rR": [567, 267],
        "rT": [480, 178],
    },
    {"wL": [310, 264], "wR": [650, 267], "wT": [480, 95], "wB": [478, 435]},
    [[596, 207], [468, 272], [440, 380]],
    [[489, 343], [534, 343]],
    "Final collision outcome is still settling; use for calibration only, NOT official-state error. Occlusion and moving stones prevent a clean post-shot observation.",
    excluded=[
        {"colour": "R", "pixel": [394, 360], "reason": "moving or identity uncertain"},
        {"colour": "Y", "pixel": [790, 45], "reason": "moving after collision"},
        {"colour": "Y", "pixel": [294, 501], "reason": "moving after collision"},
    ],
)
frames[-1]["pairing_status"] = "excluded_unsettled"
for f in frames:
    f.setdefault(
        "pairing_status",
        "partial_stationary" if f["timestamp_s"] in [231, 309] else "matched_visible_subset",
    )
obj = dict(
    schema_version=1,
    annotator="AI assistant, manual visual inspection; not independently double-annotated",
    pixel_convention="x right, y down; centres in saved 960x540 review image; original 1920x1080 is exactly 2x",
    world_convention="local origin at tee; x right in review image, y toward image bottom; transform to official diagram axes via diagram_sign",
    radii_m={"o": 1.829, "w": 1.219, "r": 0.610},
    geometry_source="https://worldcurling.org/wp-content/uploads/2025/08/Rules-2025.pdf",
    frames=frames,
)
(r / "annotations/manual.json").write_text(json.dumps(obj, indent=2) + "\n")
print("Saved", len(frames), "annotated frames")
