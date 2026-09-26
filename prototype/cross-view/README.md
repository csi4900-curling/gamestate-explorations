# Liaison des deux vues

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

Les vitesses moyennes sur le vide sont des distances longitudinales nominales divisées par le temps, pas des mesures de vitesse instantanée ni une reconstruction de courbe. La lacune signifie « sans observations enregistrées », pas nécessairement « invisible dans toutes les images ».

## Reproduction

```
feasibility/scripts/python.sh prototype/scripts/process_departure_geometry.py
feasibility/scripts/python.sh prototype/scripts/build_cross_view.py
feasibility/scripts/python.sh prototype/scripts/render_cross_view_evidence.py
feasibility/scripts/python.sh -m unittest discover -s prototype/tests -v
feasibility/scripts/python.sh prototype/scripts/check_cross_view.py
```

Le traitement réutilise les observations déjà sauvegardées. Pour modifier les paramètres, conserver une copie du dossier puis recalculer les fichiers `Txx-departure.json` dans un dossier vide. `results.json` conserve les coordonnées, décisions et raisons de rejet ; `provenance.json` conserve les empreintes des entrées principales.

## Résultat

16 liens proposés, 499 positions conditionnelles de départ sur 513 observations. Lacunes entre les deux pistes : 5,2 à 9,4 secondes. Aucun lien validé par une référence indépendante. Les 74 tests passent. Les limites de précision des positions et de calibration restent distinctes du nombre de liens proposés.

Le tracé de réception s’arrête à la première stabilité visuelle candidate de la pierre livrée (5 observations sur 2 s), afin de ne pas prolonger arbitrairement l’épisode dans les réassociations après arrêt. `raw_arrival` conserve les observations ultérieures. Ce n’est pas une preuve de fin du lancer pour toutes les pierres.
