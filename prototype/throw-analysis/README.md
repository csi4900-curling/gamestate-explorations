# Lancers et intention : expérience continue

Ouvrir <http://127.0.0.1:8765/throw-analysis/> avec le serveur local du prototype.

## Résultat

Sur la séquence continue 27:30–46:00 de Canada–Corée 2024 (`aWXo6XeUFQw`), le détecteur retrouve les 16 passages de pierres annotés, sans événement supplémentaire. Les huit premiers ont servi au développement ; le code a été figé avant de produire les résultats des huit suivants. Ces derniers restent une vérification dans la même manche, avec le même équipement et le même annotateur IA, et non un test indépendant sur une autre partie.

La référence a été préparée avant le détecteur : vues d’ensemble de la séquence toutes les cinq secondes, puis images espacées d’une seconde autour des 16 lancers. Ces annotations exploratoires peuvent manquer des événements courts inhabituels. Chaque référence est un intervalle de 1 à 2 secondes pour le passage du centre visible de la pierre à travers y=60 dans l’image 640×360. **Ce n’est pas l’instant exact du lâcher.** Toutes les prédictions tombent dans ces intervalles ; cela ne signifie pas une erreur temporelle nulle.

Version initiale : 7/8 lancers de développement. Une pierre rouge sombre n’était pas détectée. Après élargissement du seuil de teinte/saturation rouge sur cet exemple de développement : 8/8. Code figé `stone-passage-v2`, puis 8/8 dans la seconde moitié. La première sortie est conservée dans `development-v1.json`.

## Méthode

`../throw_detection.py` cherche des composantes rouges/jaunes de taille compatible avec une pierre et une bande neutre sous la couleur. Association temporelle par affectation un-à-un avec prédiction de vitesse. Confirmation seulement après déplacement cohérent vers le haut de l’image, plusieurs observations et franchissement d’une ligne virtuelle. Les objets stationnaires, les déplacements inverses et les sauts ne satisfont pas ce critère.

L’inférence traite toute la période, à 10 Hz sur la copie locale 360p. Elle ne lit pas `reference.json`, n’impose pas 16 événements, ne force pas l’alternance des couleurs et ne connaît pas les heures des lancers. La vue de gauche, le sens de départ et la zone d’analyse sont configurés manuellement pour cette source. Ni la détection automatique des manches ni la sélection générale des caméras ne sont implémentées.

`../scripts/evaluate_throws.py` effectue un appariement temporel un-à-un dans les intervalles annotés élargis de deux secondes. Une prédiction non appariée est un faux positif ; une annotation non appariée est une omission. La couleur est évaluée après l’appariement, sans servir à masquer les erreurs. Les hachages de la référence et du code figé sont vérifiés.

## Balai et résultat du lancer

L’exemple du lancer 11 utilise l’extrait 1080p existant 37:40–39:10. `../target_analysis.py` repère une tête de balai orange verticale dans une région explicite de la vue d’arrivée. Il trouve 56 observations stables durant 27,5 secondes avant le passage. Ce n’est pas une reconnaissance générale du skip ni une compréhension automatique de son geste.

Le bas visible du balai est projeté par l’homographie de la glace **sous l’hypothèse qu’il touche la glace**. L’incertitude métrique n’est pas connue ; la dispersion en pixels ne la remplace pas.

Une nouvelle trajectoire jaune à l’arrivée est associée au lancer par la couleur, le mouvement entrant et une fenêtre temporelle de 35 secondes. L’association est provisoire ; les coordonnées des deux caméras ne sont pas fusionnées. La méthode propose une stabilisation de la pierre à 38:39 après deux secondes de faible mouvement. Elle signale également une proximité suivie du mouvement d’une autre pierre autour de 38:36, compatible avec une interaction. Cette logique a été développée sur cet exemple ; aucune performance générale de suivi, de collision ou de stabilisation n’est mesurée.

**Aucun score de réussite du lancer n’est produit.** La destination voulue n’est pas identifiée. Le balai tenu en place indique une ligne de visée, pas nécessairement une destination. Les instructions peuvent aussi concerner une pierre à éliminer et une réaction après impact. Source primaire : [Curling des Collines, Different Shots and Signals](https://curlingdescollines.ca/index.php/en/41-curling-info/300-different-shots-signals), consultée pendant l’expérience.

`../shot_intent.py` ne calcule une distance d’exécution que pour un placement ou une garde avec destination explicitement revue, preuves référencées, coordonnées dans le même repère et résultat stabilisé sans interaction détectée. Sinon, la mesure reste indisponible. Cette distance éventuelle évalue l’écart à une intention interprétée, et non la précision du système de vision ni un score officiel de curling.

Prochaine expérience : annoter de véritables gestes de destination, de visée et les cas ambigus avec une personne connaissant le curling ; évaluer la reconnaissance d’intention sur d’autres parties. Comparer la position finale pour les placements, et des critères adaptés aux collisions pour les sorties de pierre.

## Fichiers et reproduction

- `reference.json` et `reference.sha256` : annotations figées et protocole.
- `model-frozen.sha256` : code d’inférence figé après développement.
- `predictions.json` : événements et points réellement observés.
- `evaluation.json` : omissions, faux événements et appariements.
- `target-analysis.json` : candidats de balai et association à l’arrivée.
- `evidence/` : séquences inspectées, captures et exemples.
- `end3.mp4` : extrait local 1080p de la source, sans réencodage. Début source 1650 s, durée 1110,033 s.
- `clip-alignment.json` : comparaison de trois instants entre copie d’analyse et vidéo affichée ; meilleur décalage de 0 s parmi les décalages essayés de −0,2 à +0,2 s.

Depuis la racine du projet :

```sh
feasibility/scripts/python.sh prototype/scripts/detect_throws.py
feasibility/scripts/python.sh prototype/scripts/evaluate_throws.py
feasibility/scripts/python.sh prototype/scripts/analyse_throw_target.py
feasibility/scripts/python.sh prototype/scripts/build_throw_viewer.py
feasibility/scripts/python.sh -m unittest discover -s prototype/tests -v
feasibility/scripts/python.sh prototype/scripts/check_throw_browser.py
```

L’évaluation peut être reproduite avec la copie locale `prototype/sources/canada-korea-2024-360p.mp4`. L’analyse du balai utilise les artefacts existants `continuous/clip.mp4`, `rectification/timeline.json` et `body-localization/video-timeline.json`.

## Limites importantes

Pas de preuve de fiabilité générale, de compréhension automatique de la tactique, d’identité du joueur, d’instant exact de lâcher ou de précision physique des positions sur cette séquence. Les nouvelles vidéos, changements de sens, autres couleurs de balai, reprises, occultations et pierres déplacées à la main restent des cas à tester. Le téléversement générique conserve son comportement d’indexation. Les anciens résultats restent inchangés.
