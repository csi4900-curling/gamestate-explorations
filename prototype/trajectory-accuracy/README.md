# Première vérification de trajectoire

Lancer T11 : la première section de `index.html` montre maintenant les deux
trajectoires observées directement sur la vidéo et sur une piste entière,
synchronisées au temps de lecture. Les 31 points du départ et les 29 points
de l'arrivée viennent de `../cross-view/results.json`. Quinze points lointains
de l'arrivée sont provisoires. À 46,7 s, les deux projections simultanées
diffèrent de 0,61 m longitudinalement dans le repère nominal commun ; aucune
ligne ne les fusionne en une trajectoire physique. L'association de la pierre
et la géométrie restent provisoires.

La mesure de précision ci-dessous concerne uniquement le segment visible dans
la caméra de réception. Ouvrir `index.html` avec la vidéo locale.

Un encadré distingue maintenant trois instants de T11 : première pierre
clairement séparée dans les images source (2 303,433 s, inspection rétrospective),
premier point du suivi figé (2 303,500 s), et ligne virtuelle (2 303,956 s).
Le lâcher physique est masqué par l'athlète et demeure inconnu. Le fichier
`../throw-analysis/observed-onset-v1.json` donne, pour les 16 pistes, le premier
point du suivi et l'avance correspondante sur la ligne virtuelle.

10 lectures manuelles approximatives sur la grille reference-sheet.jpg, dont 4 pendant le mouvement (54 à 57 s). Les prédictions avaient déjà été vues : audit rétrospectif, ni aveugle ni indépendant. Aucun réglage du détecteur.

RMSE des 4 points de mouvement : 1,16 pixel, 3,90 cm conditionnels. Les lectures manuelles ont une précision estimée de 2 pixels, non mesurée : ces résultats ne permettent donc pas de conclure à une précision subpixel. Même homographie et hauteur de 13,6 cm pour référence et prédiction. Aucune mesure indépendante de la précision physique de la projection.

Reste à valider : plusieurs lancers, couverture complète, changements de caméra, occlusions, identité et référence physique indépendante. Le résultat 16/16 de détection des passages ne valide pas ces aspects.

Reproduction : `feasibility/scripts/python.sh prototype/scripts/audit_trajectory.py`.
Ce script appelle `prototype/scripts/build_two_camera_live.py`, qui intègre
les observations des deux caméras dans un JavaScript local pour que la page
fonctionne aussi en `file://`.
La figure commune est régénérée par
`python research/meeting/build_t11_joined_figure.py` depuis
`prototype/cross-view/results.json`. Le script d'audit réinsère ensuite la
figure dans la page générée.
Contrôle navigateur : la page et les trajectoires synchronisées ont été
ouvertes dans Chromium avec `file://`.

## Faisabilité de la mesure de rotation

Pour T11, la poignée de la pierre jaune est résolue dans la vue de réception
originale à 1 920 × 1 080 pixels. La [planche de 13 images](t11-handle-visibility.jpg)
échantillonne 2 312,50–2 315,50 s toutes les 0,25 s. Elle montre un changement
visible de la silhouette de la poignée pendant le mouvement : une mesure
**directe de l'orientation** pourrait donc être tentée sur cette portion.
Un signal de forme reproductible, la dispersion horizontale des pixels jaunes
dans la moitié haute d'un recadrage original de 64 × 64 pixels, passe de
6,5 px à 8,9 px puis 4,2 px et 8,7 px sur ces images. Il comprend aussi le
dessus de la pierre : ces variations ne sont ni des angles ni des tours.
La [provenance](t11-handle-visibility.json) fixe les images, coordonnées de
recadrage, empreintes du clip et du suivi, et le script de reproduction est
[`build_t11_spin_visibility.py`](../scripts/build_t11_spin_visibility.py).

Cette planche ne mesure ni angle ni nombre de tours. La caméra est latérale :
plusieurs angles physiques peuvent produire une silhouette semblable. Le
suivi à 2 Hz sert seulement à centrer les recadrages ; il ne donne pas la
rotation, et les trois secondes observées ne couvrent pas le lancer entier.
Une estimation du nombre total de tours exigerait un suivi d'orientation
image par image, la résolution des ambiguïtés de silhouette et la couverture
des segments masqués. Le champ `spin_revolution_count` reste donc inconnu dans
les sorties d'état et aucune simulation physique n'est déclarée prête.
