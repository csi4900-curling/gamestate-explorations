# Première vérification de trajectoire

Lancer T11, caméra de réception, segment visible seulement. Ouvrir index.html via le serveur local.

10 lectures manuelles approximatives sur la grille reference-sheet.jpg, dont 4 pendant le mouvement (54 à 57 s). Les prédictions avaient déjà été vues : audit rétrospectif, ni aveugle ni indépendant. Aucun réglage du détecteur.

RMSE des 4 points de mouvement : 1,16 pixel, 3,90 cm conditionnels. Les lectures manuelles ont une précision estimée de 2 pixels, non mesurée : ces résultats ne permettent donc pas de conclure à une précision subpixel. Même homographie et hauteur de 13,6 cm pour référence et prédiction. Aucune mesure indépendante de la précision physique de la projection.

Reste à valider : plusieurs lancers, couverture complète, changements de caméra, occlusions, identité et référence physique indépendante. Le résultat 16/16 de détection des passages ne valide pas ces aspects.

Reproduction : feasibility/scripts/python.sh prototype/scripts/audit_trajectory.py
Contrôle navigateur : 10 lignes, absence d’erreurs JavaScript et largeur mobile vérifiées.
