# Test de rectitude avant la ligne

Le protocole et son empreinte sont écrits avant le calcul. Entrée : pistes du détecteur de passages figé, sans retrait de points et sans nouveau réglage. Coordonnées originales 640 × 360. Les images 1080p servent à inspecter les points, pas à créer de nouvelles références indépendantes.

Trois mesures : distance orthogonale à la droite ajustée à tous les points ; distance à la droite entre première et dernière observation ; pour 8 pistes avec au moins 8 points, ajustement sur les deux premiers tiers puis évaluation des observations ultérieures. Les deux dernières mesures évitent de présenter uniquement le meilleur ajustement à tous les points. Aucune vitesse constante supposée.

Résultat : 11/16 pistes sous 1 pixel de déviation maximale à la droite des extrémités ; 14/16 sous 2 pixels ; maximum 2,376 pixels. Durée visible 0,3 à 1,5 seconde, médiane 0,7. Sur 8 pistes : RMSE médiane des points ultérieurs réservés 0,803 pixel. Pas une validation sur une autre vidéo.

Une homographie préserve les droites du plan. L’écart image mesure donc une non-colinéarité des observations, mais pas directement la courbure physique : quantification, occultations, forme du point détecté et éventuels mouvements de caméra restent confondus avec elle. Les erreurs d’annotation indépendante et la calibration de cette portion de piste ne sont pas mesurées. Aucun chiffre en cm et aucune validation du trajet depuis le lâcher.

Reproduction :

```
feasibility/scripts/python.sh prototype/scripts/audit_pre_gate.py
feasibility/scripts/python.sh prototype/scripts/render_pre_gate_evidence.py
feasibility/scripts/python.sh -m unittest discover -s prototype/tests -v
```

65 tests passent, notamment la conservation d’une droite sous transformation projective. Le viewer fonctionne directement depuis le fichier HTML, sans serveur. Chaque piste dispose des coordonnées exactes et de trois images source avec et sans marques.
