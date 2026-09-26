# Segmentation par passages et suivi de réception

Ouvrir `index.html` directement. Le lecteur découpe la manche en 16 intervalles consultables et s’arrête à la limite du segment sélectionné. Aucune dépendance à un serveur pour la lecture.

## Méthode

1. Réutiliser les événements du détecteur de passage figé. Chaque intervalle commence à la ligne virtuelle et finit au passage suivant, ou à la fin de l’extrait. La période précédant le premier passage reste explicitement non attribuée.
2. Pour chaque événement, analyser la vue de réception à 2 Hz depuis 3 secondes avant le passage jusqu’à 45 secondes après, ou avant le passage suivant. Recaler chaque image sur la référence par SIFT et RANSAC ; rejeter la géométrie insuffisamment soutenue.
3. Appliquer le détecteur de pierres existant et sa correction de hauteur, sans modifier ses paramètres. Associer les observations avec le suivi existant.
4. Chercher une unique nouvelle piste de même couleur avec déplacement entrant soutenu dans les 35 secondes suivant le passage. Sinon, laisser l’association non résolue.
5. Chercher une stabilité de la pierre livrée pendant 2 secondes, puis une fenêtre de 2 secondes avec le même ensemble de pistes visibles et des déplacements de 3 pixels maximum. Ce dernier résultat est un candidat de stabilité visible, pas une fin physique validée : les pierres occultées ou manquées restent inconnues.

Les limites entre passages sont des limites de consultation et incluent l’attente. Elles ne sont pas présentées comme les instants exacts de fin du lancer. Les associations et fins candidates n’ont pas de référence indépendante complète. Le résultat historique 16/16 concerne uniquement les passages sur cette manche.

La trajectoire avant la ligne n’est pas reconstruite. Une droite exigerait au minimum une position de départ et une direction ; elle constituerait une hypothèse distincte des observations. Aucune liaison géométrique inventée entre les deux caméras.

## Reproduction

Depuis la racine du projet :

```
feasibility/scripts/python.sh prototype/scripts/process_throw_segments.py
feasibility/scripts/python.sh prototype/scripts/build_throw_segments.py
feasibility/scripts/python.sh prototype/scripts/review_segment_endpoints.py
feasibility/scripts/python.sh -m unittest discover -s prototype/tests -v
feasibility/scripts/python.sh prototype/scripts/check_throw_segments.py
```

Le traitement reprend les fichiers Txx.json déjà présents. Pour une nouvelle expérience, conserver les anciens résultats et utiliser un nouveau dossier, ou déplacer explicitement les fichiers avant de recalculer. Chaque Txx.json contient les observations, transformations acceptées/rejetées et résultats provisoires. `segments.csv` exporte les limites de consultation.

Contrôle visuel préliminaire : sur T04, une pierre déplacée peut sortir de la zone détectée alors que les autres paraissent stables. La stabilité des seules pistes visibles ne suffit donc pas à certifier la fin physique. Les triptyques `Txx-endpoint.jpg` montrent le contexte à −2, 0 et +2 secondes pour examiner ces candidats.

## Résultat de ce passage

16 segments de consultation ; 15 associations provisoires de réception ; 12 stabilités visibles candidates. T08 a deux pistes candidates : aucune attribution. T13, T14 et T16 ont une piste provisoire mais aucun arrêt trouvé dans la fenêtre analysée. Aucune fin physique n’est validée indépendamment. Les 60 tests passent.
