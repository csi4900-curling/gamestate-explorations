"""Keep the two-camera T11 context on the trajectory-accuracy demo page."""

from pathlib import Path


PAGE = Path(__file__).resolve().parents[1] / "trajectory-accuracy/index.html"

JOINED = """<div class="joined"><h2>T11 dans les deux caméras</h2><p>La caméra de départ fournit 31 positions ; la caméra d’arrivée en fournit 29, dont 15 points lointains obtenus avec une limite de projection élargie. Les deux trajectoires sont affichées sans les forcer à se rejoindre. À 46,7 s, les deux vues donnent une position dans la même image, mais leurs coordonnées longitudinales nominales diffèrent de 0,61 m. Cette discordance est à expliquer avant toute reconstruction physique. <a href="../cross-view/README.md">Méthode et données de l’audit</a>.</p><figure><img src="t11-joined-trajectory.png" alt="Trajectoire T11 : positions des deux caméras dans le même repère nominal et écart de 0,61 m au même instant."><figcaption>Association de la pierre entre caméras et géométrie physique provisoires. Les 1,16 px de RMSE ci-dessous concernent uniquement quatre points en mouvement dans la caméra d’arrivée. <a href="../cross-view/index.html">Ouvrir la vue interactive à deux caméras</a>.</figcaption></figure></div>"""
RELEASE = """<div class="release-panel"><h2>Quand la pierre est-elle lâchée ?</h2><p>Sur T11, cet instant est caché par l’athlète. La première pierre clairement séparée et déjà en mouvement apparaît vers <b>2 303,433 s</b> dans un examen rétrospectif des images. Le suivi automatique commence à <b>2 303,500 s</b>, puis la ligne virtuelle est franchie à <b>2 303,956 s</b>. Le temps exact du lâcher physique reste <b>inconnu</b> ; aucun de ces repères ne doit être présenté comme tel.</p><figure><img src="../throw-analysis/T11-release-visibility.jpg" alt="Images de T11 autour de l’apparition de la pierre, du premier suivi et du franchissement de la ligne virtuelle."><figcaption>Images source autour de la première observation. <a href="../throw-analysis/observed-onset-v1.json">Voir les 16 premiers instants de suivi</a> : ils précèdent la ligne virtuelle de 0,3 à 1,5 s, sans mesurer le lâcher.</figcaption></figure></div>"""


def augment_html(html):
    if 'class="joined"' not in html:
        old_title = "<h1>Le lancer, vu du dessus</h1>"
        assert old_title in html
        html = html.replace(old_title, "<h1>T11 : deux caméras, une trajectoire proposée</h1>", 1)
        marker = '<section><div><div class="video-wrap">'
        assert marker in html
        html = html.replace(marker, JOINED + marker, 1)
        old_button = '<button onclick="v.currentTime=53;v.play()">Revoir l’arrivée</button>'
        assert old_button in html
        html = html.replace(
            old_button,
            '<button onclick="v.currentTime=43.5;v.play()">Voir la première caméra</button> '
            + old_button,
            1,
        )
        css_end = "</style>"
        assert css_end in html
        html = html.replace(
            css_end,
            ".joined{margin:26px 0 32px;padding:22px;background:white;border:1px solid #d7e4e0;border-radius:14px}"
            ".joined h2{margin:0 0 8px}.joined p{margin:0 0 14px}"
            ".joined figure{margin:0}.joined img{display:block;width:100%;height:auto;border-radius:8px}"
            ".joined figcaption{font-size:14px;line-height:1.5;color:#47615d;margin-top:8px}"
            ".joined a{color:#086d73}"
            "button{margin:0 6px 6px 0}" + css_end,
            1,
        )
    if 'class="release-panel"' not in html:
        assert 'class="joined"' in html
        marker = '<section><div><div class="video-wrap">'
        assert marker in html
        html = html.replace(marker, RELEASE + marker, 1)
        html = html.replace(
            "</style>",
            ".release-panel{margin:0 0 32px;padding:22px;background:#fffaf6;border:1px solid #eadbd0;border-left:4px solid #b75e4c;border-radius:10px}"
            ".release-panel h2{margin:0 0 8px}.release-panel p{margin:0 0 14px}"
            ".release-panel figure{margin:0}.release-panel img{display:block;width:100%;height:auto;border-radius:8px}"
            ".release-panel figcaption{font-size:14px;line-height:1.5;color:#47615d;margin-top:8px}"
            "</style>",
            1,
        )
    # Keep previously generated pages current when this helper is rerun.
    return html.replace(
        "Quand la pierre quitte-t-elle la main ?", "Quand la pierre est-elle lâchée ?"
    )


def main():
    if not PAGE.with_name("t11-joined-trajectory.png").exists():
        raise FileNotFoundError("Build the joined T11 figure first")
    if not (PAGE.parent.parent / "throw-analysis/T11-release-visibility.jpg").exists():
        raise FileNotFoundError("Build the observed-onset evidence first")
    PAGE.write_text(augment_html(PAGE.read_text()))
    print(PAGE)


if __name__ == "__main__":
    main()
