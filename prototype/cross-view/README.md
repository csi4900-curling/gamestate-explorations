# Liaison des deux vues

Le [handoff de replay observé](OBSERVED-REPLAY-HANDOFF.md) exporte désormais les 16 lancers candidats en segments de caméra distincts, avec les lacunes et le désaccord T11 conservés explicitement. Ce format sert à visualiser les observations ; il ne constitue pas une trajectoire physique continue ni une simulation validée.

`index.html` fonctionne sans serveur, avec la vidéo locale. Les deux tracés sont affichés dans un repère de piste commun ; le vide entre observations n’est pas interpolé. Le viewer montre les traces complètes et ne dessine un cercle de position courante qu’à proximité d’un instant réellement observé.

## Géométrie

Chaque vue conserve sa propre homographie recalée sur l’image. Au départ, les timestamps de la piste existante sont réexaminés en 1080p : le détecteur de capuchon doit trouver une unique proposition de même couleur à proximité de la position 360p. Les points sans détection ou sans géométrie acceptée sont laissés indisponibles. La zone de recherche de départ est élargie à y = −18 m. Le code du détecteur est inchangé.

Après la correction de hauteur conditionnelle existante, le repère local est transformé :

- Départ : X = x ; Y = −y.
- Réception : X = x ; Y = 34,747 − y.

Origine au tee de départ. Les deux panneaux sont traités comme regardant dans le même sens de la piste, sans miroir, d’après leur disposition et le sens des déplacements. C’est une hypothèse source-spécifique explicite, pas une orientation retrouvée automatiquement par correspondances inter-caméras. Les dimensions viennent du diagramme page 5 de `feasibility/sources/Rules-2025.pdf` : distance nominale de 114 pieds / 34,747 m. Aucun relevé de la piste réelle. La précision géométrique au départ, loin des cercles de calibration, n’est pas évaluée indépendamment.

## Identité

L’horloge est celle du fichier composite. Un éventuel décalage de production entre panneaux n’a pas été mesuré. Une piste de réception candidate doit :

1. être de la même couleur et apparaître après le passage de départ, dans les 35 secondes ;
2. être observée traversant la hog line de réception vers la maison, avec mouvement entrant soutenu ;
3. avoir un temps et une progression longitudinale positifs par rapport à la dernière observation de départ ;
4. être l’unique candidate satisfaisant ces critères.

Cela écarte notamment la deuxième piste T08 apparue dans la maison : elle ne traverse pas la hog line en arrivant. Cette règle a été développée sur cette manche après inspection de T08 ; aucun résultat de généralisation n’est revendiqué. Les noms de pistes locaux restent différents ; l’identifiant du lancer relie les deux observations.

Les vitesses moyennes sur le vide sont des distances longitudinales nominales divisées par le temps, pas des mesures de vitesse instantanée ni une reconstruction de courbe. La lacune signifie « sans observations retenues par ce traitement », pas « invisible dans les images ».

**Correction T11 (audit ciblé du 8 octobre 2026).** La lacune de 5,8 s du traitement initial va de 2306,7 à 2312,5 s et reflète surtout la limite de la vue de réception (projection du capuchon limitée à y ≤ 6,401 m), pas une absence de pierre à l'image. En étendant provisoirement cette limite à y ≤ 22 m, avec le même détecteur et la même homographie recalée, on trouve une proposition jaune en mouvement dans la caméra de réception dès 2306,7 s (temps du clip 46,7 s), puis à chaque échantillon de 0,5 s jusqu'à l'entrée dans la zone d'origine. La dernière position de départ et la première position de réception ont donc le même timestamp dans cet essai. Leur écart longitudinal nominal est toutefois d'environ 0,61 m et l'écart latéral d'environ 0,09 m : cette continuité temporelle ne valide ni l'identité entre vues ni la précision métrique au loin. Le viewer affiche maintenant les deux trajectoires sans les aligner artificiellement. `display_arrival` dans `results.json` contient les 15 points lointains expérimentaux et les 14 points de réception initiaux ; `gap` conserve la valeur du traitement borné pour la provenance, et `expanded_handoff` décrit l'écart au même instant.

Reproduire cet audit isolé avec `feasibility/scripts/python.sh prototype/scripts/probe_t11_far_receiving.py` ; les points et limites sont conservés dans [`T11-far-receiving-probe.json`](T11-far-receiving-probe.json).

## Reproduction

```
feasibility/scripts/python.sh prototype/scripts/process_departure_geometry.py
feasibility/scripts/python.sh prototype/scripts/probe_t11_far_receiving.py
feasibility/scripts/python.sh prototype/scripts/build_cross_view.py
feasibility/scripts/python.sh prototype/scripts/render_cross_view_evidence.py
feasibility/scripts/python.sh -m unittest discover -s prototype/tests -v
feasibility/scripts/python.sh prototype/scripts/check_cross_view.py
```

Le traitement réutilise les observations déjà sauvegardées. Pour modifier les paramètres, conserver une copie du dossier puis recalculer les fichiers `Txx-departure.json` dans un dossier vide. `results.json` conserve les coordonnées, décisions et raisons de rejet ; `provenance.json` conserve les empreintes des entrées principales.

## Résultat

16 liens proposés, 499 positions conditionnelles de départ sur 513 observations. Les lacunes de 5,2 à 9,4 secondes décrivent le traitement initial borné ; elles ne prouvent pas que la pierre soit absente des images. Pour T11, l'audit élargi supprime la lacune temporelle échantillonnée, tout en révélant 0,61 m de désaccord longitudinal au raccord. Aucun lien validé par une référence indépendante. Les limites de précision des positions et de calibration restent distinctes du nombre de liens proposés.

Le tracé de réception s’arrête à la première stabilité visuelle candidate de la pierre livrée (5 observations sur 2 s), afin de ne pas prolonger arbitrairement l’épisode dans les réassociations après arrêt. `raw_arrival` conserve les observations ultérieures. Ce n’est pas une preuve de fin du lancer pour toutes les pierres.
