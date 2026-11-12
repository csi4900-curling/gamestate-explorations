# Livrable de développement — suivi et rotation

Objectif de cette séance : nettoyer les scripts expérimentaux inutilisés, intégrer
un modèle de suivi amont réutilisable, et rendre vérifiables ses observations et
l'estimation des intervalles de rotation manquants. Ce document ne certifie pas
le pipeline complet.

## Ce qui doit être vérifié

- Même code et mêmes poids pour tous les clips ; initialisation et cadrage déclarés.
- Conservation des résultats précédents ; aucun résultat de développement présenté
  comme transfert indépendant.
- Lecture de la vidéo au bon instant, coordonnées du marqueur dans l'image source,
  identifiants des points et visibilité synchronisés, y compris les points perdus.
- Estimation de rotation uniquement entre fenêtres observées compatibles ; absence
  d'extrapolation arbitraire et conservation des ambiguïtés de nombre de tours.
- Test par masquage : les angles cachés ne participent jamais à l'ajustement.
- Distinction entre tests numériques, cohérence des sorties du modèle, examen visuel
  par l'agent, et précision physique mesurée indépendamment.
- Exécution de l'entrée publique avec l'ajout expérimental ; comparaison des
  événements, trajectoires et associations existants avant/après.

## Nettoyage

211 scripts spécifiques à des enregistrements, sans référence dans les sources
Python/shell/Nix/TOML/YAML examinées, ont été retirés du répertoire actif après
archivage et vérification des SHA-256. Les fichiers déjà modifiés par ailleurs
ont été exclus. Données, modèles, annotations et résultats antérieurs conservés.
Les scripts encore utilisés par d'autres composants sont restés en place.

Manifest : [cleanup-scripts-2026-10-22.json](cleanup-scripts-2026-10-22.json).
Pour reproduire une ancienne commande, restaurer son chemin depuis l'archive :

```bash
unzip docs/archive/recording-specific-leaf-scripts-2026-10-22.zip CHEMIN_ORIGINAL
```

## Composants

`prototype/spin/point_tracking.py` appelle les prédicteurs CoTracker3 amont sans
réimplémenter le réseau. Commit amont :
`82e02e8029753ad4ef13cf06be7f4fc5facdda4d`.
Poids officiels online/offline, environnement CPU séparé. Aucun entraînement
spécifique au curling n'a été effectué.

`prototype/spin/gaps.py` applique le modèle accepté : vitesse angulaire constante
par intervalle manquant. Les fenêtres visibles avant/après contraignent le nombre
de tours possibles. Si plusieurs solutions sont compatibles ou si les vitesses
sont incompatibles, l'intervalle reste inconnu. Les seuils sont des tolérances de
développement explicites, pas des intervalles de confiance calibrés.

`prototype/spin/pipeline.py` relie suivi, orientations, estimation, provenance et
rapport vidéo. Deux types d'initialisation : points choisis et déclarés, ou point
provenant automatiquement d'un segment déjà détecté. Un point de capuchon n'est
pas une orientation de poignée. La sélection automatique de repères de poignée
n'est pas implémentée.

L'entrée publique `run_throw_pipeline.py --spin-config ...` ajoute ce résultat
au candidat existant. Elle conserve les trajectoires précédentes : le suivi dense
n'est pas silencieusement substitué au pipeline de référence.

## Limites de la mesure

Les angles des expériences vidéo actuelles sont des orientations de paires de
points dans l'image, pas des angles physiques validés. Le compteur de révolutions
physiques reste `null`. Une homographie fournie serait identifiée comme géométrie
non validée ; aucune calibration manuelle nouvelle n'est utilisée ici.

La décision de visibilité du modèle n'est pas une probabilité de suivi correct.
Le prédicteur online utilise visibilité × confiance > 0,6 ; le prédicteur offline
utilise visibilité > 0,9. Comparer leur couverture n'est donc pas comparer deux
probabilités calibrées ni mesurer leur précision physique.

Les tests par masquage d'angles produits par CoTracker mesurent une cohérence avec
ces sorties, pas une vérité terrain indépendante. Une vitesse angulaire physique
constante ne donne généralement pas un angle image à vitesse constante sous
perspective : ces diagnostics ne valident ni ne réfutent l'hypothèse physique. Les examens de pixels par
l'agent sont identifiés comme tels, avec prédictions visibles.

## Installation et commandes

```bash
uv venv .venv-tracking --python .venv/bin/python
uv pip install --python .venv-tracking/bin/python torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
uv pip install --python .venv-tracking/bin/python -r requirements-tracking.txt
```

Poids officiels à télécharger depuis les liens du README CoTracker3 :
`models/cotracker3/scaled_online.pth` et `scaled_offline.pth`.
Les SHA-256 employés sont enregistrés dans chaque résultat.

```bash
CURLING_PYTHON="$PWD/.venv-tracking/bin/python" feasibility/scripts/python.sh \
  prototype/scripts/run_spin_analysis.py \
  --video prototype/continuous/clip.mp4 \
  --config validation/spin-development-2026-10-22/handle-config.json \
  --checkpoint models/cotracker3/scaled_online.pth \
  --output /tmp/nouveau-resultat-spin
```

Les configurations sont des données d'initialisation avec empreinte vidéo,
intervalle, cadrage, provenance et points. Elles ne contiennent pas de code ni de
règles différentes pour chaque vidéo. Les points manuels ne sont pas présentés
comme une détection automatique.

Les résultats mesurés et les liens de consultation sont regroupés dans
`validation/spin-development-2026-10-22/index.html` à la fin de la vérification.


Pour utiliser le modèle avec des angles déjà mesurés :

```bash
feasibility/scripts/python.sh -m prototype.spin.gaps \
  --input mesures-angulaires.json --output nouveau-resultat.json
```

Le fichier contient `provenance`, `coordinate_system`, puis `samples` avec
`time_s` et `angle_rad` (ou `null` si invisible). `config`, `known_breaks_s` et
`evaluation_masks_s` sont optionnels. Un exemple **synthétique**, explicitement
sans valeur de validation vidéo, est conservé dans
`validation/spin-development-2026-10-22/synthetic-angle-input.json`.

## Résultat de la séance

[Ouvrir le bilan et les exemples vidéo](../validation/spin-development-2026-10-22/index.html).
870 tests passent. Le suivi dense et le fonctionnement des lecteurs sont vérifiés sur trois segments de
Canada–Suède 2024 ; le suivi de poignée reste insuffisant pour compter les tours.
L'agrégat de référence reste identique dans les cinq exécutions comparées.

L'initialisation sans coordonnées manuelles est disponible avec
`run_throw_pipeline.py --track-candidate R01-S01:1`. Le point vient du segment
existant, avec conversion des coordonnées normalisées 640×360 en pixels source.
Le cadrage est celui du panneau gauche ou droit selon le segment. Aucun nouveau
repère de calibration n'est demandé. L'intervalle automatique reste celui du
segment existant ; le cas prolongé de 13 secondes utilise un intervalle explicite.

`--tracking-cache RESULTAT_JSON` permet de réutiliser les prédictions amont
uniquement lorsque vidéo, configuration, poids, mode, code de l'adaptateur,
fichier de points et horodatages correspondent. Le temps d'inférence conservé
est identifié comme appartenant à l'exécution originale.

La projection ajoutée réutilise une calibration acceptée de l'agrégat et le
recalage existant `camera_geometry.transfer`. Elle ne refait pas une calibration
de la patinoire. Cela ne supprime pas encore les calibrages de l'ancien pipeline.
Les sorties demeurent des projections conditionnelles de points du capuchon.


La dernière exécution fraîche de l’entrée publique traite 45 s de source en
433,2 s, dont 410,2 s de suivi neuronal sur 346 images et 12,5 s de projection.
Aucun résultat de pipeline n’était réutilisé dans cette exécution. Les cinq
régressions sur cache ne doivent pas être confondues avec cette mesure.

Le modèle de hauteur existant est réutilisé une fois à l’ancrage, puis transporté
par le recalage d’image. Les projections brutes restent accessibles. Le cas
automatique échoue à construire le modèle caméra (0/346 points corrigés), alors
que l’intervalle prolongé produit 390/390 points corrigés conditionnellement.
L’ancrage de calibration change de seulement 0,5 s : cette instabilité est un
résultat défavorable, pas une validation géométrique. L’écart brut/corrigé atteint
1,24 m ; ce n’est pas une erreur mesurée par rapport à une vérité terrain.

Les deux cas supplémentaires, choisis avant leurs résultats, donnent 406/406
et 55/55 points disponibles. Les revues de 15 et 8 images par l’agent, prédictions
visibles, ne sont ni des annotations indépendantes ni une précision de 100 %.
La comparaison entre trackers de pierres concurrents, l’identité entre caméras,
la précision métrique et l’évaluation sur match complet restent à faire.
