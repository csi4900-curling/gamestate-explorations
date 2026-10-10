"""Embed T11 cross-view observations in the trajectory-accuracy demo.

Run after regenerating the base trajectory-accuracy page. The video starts at
source time 2260 s; the observations in cross-view/results.json use source time.
"""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "trajectory-accuracy" / "index.html"
SCRIPT = ROOT / "trajectory-accuracy" / "two-camera-live.js"
SOURCE = ROOT / "cross-view" / "results.json"
CLIP_START_S = 2260.0


def main() -> None:
    source = json.loads(SOURCE.read_text())
    throw = next(row for row in source["throws"] if row["id"] == "T11")

    def compact(row):
        return {
            "t": round(row["time_s"] - CLIP_START_S, 3),
            "world": row["world_m"],
            "pixel": row["pixel"],
            "provisional": row.get("scope") == "range_expanded_diagnostic",
        }

    departure = [compact(p) for p in throw["departure"]]
    arrival = [compact(p) for p in throw["display_arrival"]]
    assert len(departure) == 31 and len(arrival) == 29
    assert departure[-1]["t"] == arrival[0]["t"] == 46.7
    data = {
        "tee": source["configuration"]["tee_distance_m"],
        "hog": source["configuration"]["hog_from_tee_m"],
        "departure": departure,
        "arrival": arrival,
        "handoff": {
            "t": 46.7,
            "left": departure[-1]["world"],
            "right": arrival[0]["world"],
        },
    }
    js = SCRIPT.read_text()
    new_assignment = "const T11_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";"
    js, n = re.subn(r"const T11_DATA = .*?;", lambda _: new_assignment, js, count=1)
    assert n == 1
    SCRIPT.write_text(js)

    html = PAGE.read_text()
    old_intro = 'Un premier segment mesuré : arrivée de la pierre jaune du lancer 11. La courbe utilise les positions enregistrées à 2 Hz. Les croix rouges sont des lectures manuelles à 1 Hz. Le repère violet indique la position du balai observée à 15 s, projetée sur la glace sous hypothèse de contact. Il reste affiché pendant le lancer : référence de visée, pas destination confirmée.'
    new_intro = 'Le lancer T11 est observé par les deux caméras. La première visualisation montre leurs trajectoires enregistrées et synchronisées avec la vidéo ; l’audit de précision plus bas concerne seulement la caméra d’arrivée.'
    html = html.replace(old_intro, new_intro)
    stylesheet = '<link rel="stylesheet" href="two-camera-live.css">'
    if stylesheet not in html:
        html = html.replace("</style>", "</style>" + stylesheet, 1)
    section = '''<div class="two-camera-live">
<h2>Trajectoires mesurées, synchronisées avec la vidéo</h2>
<p>Les positions de la caméra de départ et de la caméra d’arrivée sont tracées dans le même repère <em>nominal</em>. Les chemins pâles montrent tous les points enregistrés ; les traits colorés montrent les points atteints au temps de lecture. Aucun trait ne relie artificiellement les deux vues.</p>
<div class="two-camera-legend"><span style="--swatch:#08766e">Départ, 31 points</span><span style="--swatch:#b86d18">Arrivée lointaine provisoire, 15 points</span><span style="--swatch:#ba4d34">Arrivée proche, 14 points</span></div>
<div class="two-camera-grid"><div><div class="two-camera-video"><video id="two-camera-video" controls preload="metadata" src="../continuous/clip.mp4"></video><canvas id="two-camera-overlay" width="1920" height="1080"></canvas></div><div class="two-camera-controls"><button data-t11-seek="43.5">Départ</button><button data-t11-seek="46.7">Raccord</button><button data-t11-seek="50">Arrivée lointaine</button><button data-t11-seek="54">Près de la maison</button><span id="two-camera-status"></span></div></div><canvas id="two-camera-rink" width="420" height="720" aria-label="Positions observées par les deux caméras sur la piste entière"></canvas></div>
<p class="two-camera-note">Au raccord à 46,7 s, les deux projections simultanées diffèrent de 0,61 m le long de la piste. La ligne violette pointillée montre cet écart entre estimations ; ce n’est pas un trajet mesuré. L’identité de la pierre et la géométrie lointaine restent provisoires.</p>
</div>'''
    if 'class="two-camera-live"' not in html:
        assert '<div class="joined">' in html
        html = html.replace('<div class="joined">', section + '<div class="joined">', 1)
    audit_heading = '<h2>Audit de précision : caméra d’arrivée seulement</h2><p>La courbe de cet audit utilise les positions enregistrées à 2 Hz ; les croix rouges sont des lectures manuelles à 1 Hz. Le repère violet indique la position du balai à 15 s sous une hypothèse de contact avec la glace.</p>'
    if audit_heading not in html:
        html = html.replace('</div><section><div><div class="video-wrap">', '</div>' + audit_heading + '<section><div><div class="video-wrap">', 1)
    html = html.replace('<button onclick="v.currentTime=43.5;v.play()">Voir la première caméra</button> ', '')
    script_tag = '<script src="two-camera-live.js"></script>'
    if script_tag not in html:
        html = html.replace("</html>", script_tag + "</html>", 1)
    PAGE.write_text(html)


if __name__ == "__main__":
    main()
