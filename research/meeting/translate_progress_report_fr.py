"""Render the supervisor report in French from its reviewed English source."""

import json
from pathlib import Path
import re

from bs4 import BeautifulSoup, Doctype

TRANSLATIONS = Path(__file__).with_name("progress_fr_translations.json")

OVERRIDES = {
    "Detection strategy": "Stratégie de détection",
    "Keep plausible throws, then filter false alarms.": "Garder les lancers plausibles, puis filtrer les fausses alertes.",
    "1 · Recall-oriented proposals": "1 · Propositions orientées vers le rappel",
    "Collect plausible moving-stone passages across camera layouts. Keep the raw candidates, including ones that may later be rejected.":
        "Recueillir les passages plausibles de pierres en mouvement malgré les changements de vue. Conserver les candidats bruts, même s'ils sont ensuite écartés.",
    "2 · Visual-context filter": "2 · Filtre de contexte visuel",
    "Confirm candidates using image context and motion. Reject lookalikes without discarding the underlying evidence.":
        "Confirmer les candidats grâce au contexte de l'image et au mouvement. Écarter les faux semblants sans supprimer les indices de départ.",
    "3 · Auditable decisions": "3 · Décisions vérifiables",
    "Save confirmed and withheld candidates in a review ledger. Score both missed throws and extra events on complete videos.":
        "Conserver les candidats confirmés et écartés dans un registre de vérification. Compter les lancers manqués et les événements en trop sur des vidéos complètes.",
    "Development evidence (TP/FP/FN):": "Résultats de développement (VP/FP/FN) :",
    "USA 19/20/1 raw → 19/1/1 filtered; Estonia 16/5/1 → 16/0/1; China 17/9/1 → 17/1/1. The filter cuts false alarms while retaining the raw matches on these excerpts.":
        "États-Unis : 19/20/1 brut → 19/1/1 filtré ; Estonie : 16/5/1 → 16/0/1 ; Chine : 17/9/1 → 17/1/1. Sur ces extraits, le filtre réduit les fausses alertes en conservant les appariements bruts.",
    "Each raw pool still misses one labelled passage. A filter cannot recover a throw absent from its proposal pool. These are exposed partial intervals with agent-made references, not independent full-match scores.":
        "Chaque liste brute manque encore un passage annoté. Un filtre ne peut pas retrouver un lancer absent de la liste de propositions. Ces résultats portent sur des extraits déjà étudiés avec des références préparées par l'agent, pas sur des parties entières évaluées indépendamment.",
    "Inspect the two-stage audit ↗": "Examiner l'audit en deux étapes ↗",
    "“Our direction is a high-recall proposal stage followed by a visual-context filter. On three development excerpts, the filter removes many false alarms while retaining the raw matches; each raw pool still misses one labelled passage. T11 also shows candidate trajectories in both cameras, with a 0.61-metre geometric disagreement at the handoff. Next we must improve proposal coverage and validate the full pipeline on independently labelled complete matches.”":
        "« Notre approche combine une première étape de propositions à fort rappel et un filtre de contexte visuel. Sur trois extraits de développement, le filtre retire beaucoup de fausses alertes tout en conservant les appariements bruts ; chaque liste brute manque encore un passage annoté. T11 montre aussi des trajectoires candidates dans les deux caméras, avec un désaccord géométrique de 0,61 m au raccord. La suite consiste à améliorer la couverture des propositions et à valider toute la chaîne sur des parties complètes annotées indépendamment. »",
    "Two-stage filter prototype:": "Prototype de filtre en deux étapes :",
    "Raw throw proposals now remain in a review ledger when a confirmation gate withholds them. On the exposed Estonia excerpt, the older speed cutoff withheld three labelled passages; one common image-context gate now retains them as automated candidates on that already studied video. This is a development diagnostic, not independent full-match scores.":
        "Les propositions de lancer restent dans un dossier de vérification lorsqu'un filtre ne les confirme pas. Sur l'extrait estonien déjà étudié, l'ancien seuil de vitesse avait écarté trois passages annotés ; une même règle de contexte les conserve maintenant comme candidats automatiques sur cette vidéo déjà étudiée. Il s'agit d'un diagnostic de développement, pas d'un score indépendant sur une partie entière.",
    "Open the three-video audit": "Ouvrir l'audit des trois vidéos",
    "Release timing:": "Moment du lâcher :",
    "The frozen moving-stone tracks begin 0.3–1.5 seconds before their virtual-line crossings (median 0.7 seconds). For T11, source-frame review first shows a clearly separable moving stone at 2303.433 s, the frozen track starts at 2303.500 s, and the line is crossed at 2303.956 s. Separation from the delivery device is hidden by the player and remains unknown.":
        "Les suivis figés des pierres en mouvement commencent 0,3 à 1,5 s avant le franchissement de la ligne virtuelle (médiane : 0,7 s). Pour T11, l'examen des images montre une pierre mobile clairement séparée à 2 303,433 s ; le suivi figé commence à 2 303,500 s et la ligne est franchie à 2 303,956 s. La séparation d'avec le dispositif de lancer est masquée par l'athlète et reste inconnue.",
    "Inspect all 16 onsets": "Examiner les 16 débuts de suivi",
    "Selected retrospective source-frame audit: first visible motion is a better review anchor than the later line crossing, but it is not the physical release time.":
        "Vérification rétrospective de quelques images source : le premier mouvement visible situe mieux le début de la séquence à examiner que la ligne franchie plus tard, sans mesurer le lâcher physique.",
    "Meeting guide": "À présenter",
    "The four points to report.": "Les quatre points à présenter.",
    "If time is short, use this page. The technical sections below support each claim.":
        "Si le temps manque, cette page suffit. Les sections suivantes apportent les éléments de preuve et les limites.",
    "1 · Goal": "1 · Objectif",
    "Detect every delivered stone": "Détecter chaque lancer",
    "Segment a whole broadcast into throw events, then reconstruct observed paths and stone positions. High precision and recall on complete, independently labelled videos are the target.":
        "Découper une partie entière en lancers, puis reconstruire les trajets observés et les positions des pierres. L'objectif est une précision et un rappel élevés sur des vidéos complètes annotées indépendamment.",
    "2 · Demonstration": "2 · Démonstration",
    "One end already works": "Une manche fonctionne déjà",
    "On the Canada–Korea development end, 16 of 16 internally prepared passage windows match. T11 shows 31 departure and 29 receiving positions after a targeted range extension. Both views contain a candidate at 46.7 s, but their nominal longitudinal positions differ by 0.61 m.":
        "Sur la manche Canada–Corée utilisée pour le développement, les 16 fenêtres de passage préparées en interne correspondent aux détections. Pour T11, nous montrons 31 positions au départ et 29 à l’arrivée après élargissement ciblé de la zone projetée. Les deux vues contiennent une proposition à 46,7 s, mais leurs positions longitudinales nominales diffèrent de 0,61 m.",
    "3 · Transfer": "3 · Transfert",
    "Generalisation is the problem": "La généralisation échoue encore",
    "Canada–USA reaches 19 matched passages, one extra and one missed coarse window on 18.5 minutes. Estonia misses four. A 2022 full-match run produces 142 candidates for 128 official shots. These scores do not prove full-match event F1.":
        "Canada–États-Unis : 19 passages appariés, un candidat supplémentaire et une fenêtre manquée sur 18,5 minutes. En Estonie, quatre lancers sont manqués. Sur une partie de 2022 : 142 candidats pour 128 lancers officiels. Aucun de ces chiffres ne démontre un F1 des lancers sur une partie entière.",
    "4 · Decision": "4 · Décision",
    "Choose the next validation": "Choisir la prochaine validation",
    "Agree on the target broadcast family and an exhaustive independent reference for whole matches. Then prioritise camera-aware stone identity and test precision and recall before simulation or coaching.":
        "Choisir le type de diffusion visé et une référence indépendante et exhaustive pour des parties entières. Ensuite, améliorer le suivi de la pierre entre caméras et mesurer précision et rappel avant la simulation ou l'analyse pour l'entraînement.",
    "Say this in about one minute": "À dire en une minute environ",
    "“We built a prototype that finds stone passages and links observations across two cameras. On one development end it found all 16 marked passages, but the camera link and physical path are still provisional. Our first same-format transfer scored 19 matches, one extra and one missed passage on a short extract; other videos show missed throws and excess candidates. The next step is a complete, independently labelled evaluation and a detector that follows the stone through changing camera views.”":
        "« Nous avons construit un prototype qui détecte les passages des pierres et relie des observations prises par deux caméras. Sur une manche de développement, il retrouve les 16 passages repérés, mais l'identité entre caméras et la trajectoire physique restent provisoires. Sur un court extrait d'une autre vidéo du même type, nous obtenons 19 appariements, un candidat en trop et un passage manqué. D'autres vidéos révèlent davantage de lancers manqués ou de candidats supplémentaires. Il faut maintenant évaluer des parties entières avec une référence indépendante et suivre la pierre malgré les changements de caméra. »",
    "Keep the claim precise:": "Préciser la portée des chiffres :",
    "16/16 is one development end; 0.950 F1 is a short same-family timing check against agent-prepared windows; 142 versus 128 is an excess-candidate count, not a full-match F1. Exact release and continuous physical trajectory are not validated.":
        "16/16 concerne une seule manche de développement ; le F1 de 0,950 mesure la concordance temporelle sur un court extrait du même type de diffusion, avec des fenêtres préparées par l'agent ; 142 contre 128 signale un excès de candidats, pas un F1 sur la partie entière. L'instant exact du lâcher et la trajectoire physique continue ne sont pas validés.",
    "Show the demonstration": "Montrer la démonstration",
    "T11 in two cameras ↗": "T11 dans deux caméras ↗",
    "Show the measured score": "Montrer le score mesuré",
    "Canada–USA 19/1/1 ↗": "Canada–États-Unis 19/1/1 ↗",
    "Show the failure": "Montrer la limite",
    "Canada–Norway 2022 ↗": "Canada–Norvège 2022 ↗",
    "T11 has 31 departure positions and 29 receiving positions, including 15 provisional far-range points. Both cameras show a candidate at 46.7 s, with a 0.61 m nominal longitudinal and 0.09 m lateral disagreement. The cross-camera identity and physical coordinates remain provisional.":
        "T11 comporte 31 positions au départ et 29 à l'arrivée, dont 15 points lointains provisoires. Les deux caméras montrent une proposition à 46,7 s, avec un écart nominal de 0,61 m longitudinalement et de 0,09 m latéralement. L'identité entre caméras et les coordonnées physiques restent provisoires.",
    "Open the interactive two-camera trajectory ↗":
        "Explorer la trajectoire interactive à deux caméras ↗",
    "Curling video project | Supervisor progress briefing":
        "Projet d'analyse vidéo du curling | Bilan pour la réunion de supervision",
    "Evidence": "Résultats",
    "Latest transfer": "Essai sur une autre partie",
    "Speaker notes": "Notes de présentation",
    "Large type": "Texte agrandi",
    "From curling video": "De la vidéo de curling",
    "to": "aux",
    "grounded game events.": "événements de jeu fondés sur l'image.",
    "Research prototype": "Prototype de recherche",
    "Reproducible evidence pipeline": "Chaîne d'analyse reproductible",
    "Independent full-match F1 pending": "F1 indépendant sur une partie entière : à mesurer",
    "Our target system": "Notre objectif",
    "Video → throw → board → coaching":
        "Vidéo → lancer → état des pierres → analyse pour l'entraînement",
    "Executive snapshot": "L'essentiel",
    "The Canada–Korea end-three video shows stone passages and one partial arrival trajectory in a single recording. The remaining challenge is making that chain reliable across complete matches and camera layouts.":
        "Dans une même vidéo de la troisième manche Canada–Corée, nous détectons les passages des pierres et suivons une partie de la trajectoire d'arrivée. Il reste à rendre cette chaîne fiable sur des parties entières et d'autres dispositifs de caméra.",
    "Presentation length: about 8 minutes · All evidence and images are embedded for offline viewing; demo links use the project folder.":
        "Durée prévue : environ 8 minutes · Les résultats et les images sont intégrés au rapport pour une consultation hors ligne ; les démonstrations nécessitent le dossier du projet.",
    "Open with the useful outcome: we have a real pipeline and viewable artifacts. Then state the limit early: strong partial-window results do not yet prove a robust full-match throw detector.":
        "Commencer par le résultat concret : une chaîne d'analyse et des démonstrations consultables. Préciser aussitôt la limite : de bons résultats sur de courts extraits ne prouvent pas la fiabilité sur une partie entière.",
    "Built enough to demonstrate; not enough to claim automation at scale.":
        "Une démonstration fonctionne ; la fiabilité à grande échelle reste à prouver.",
    "What works": "Ce qui fonctionne",
    "Evidence-rich throw candidates": "Lancers candidats reliés aux images source",
    "Video, colour motion, camera cuts and delayed scoreboard changes flow into an ordered ledger with links back to the source.":
        "Les indices tirés de la vidéo, le mouvement des pierres colorées, les changements de caméra et les mises à jour différées du compteur alimentent une liste chronologique reliée aux images source.",
    "Best partial transfer": "Meilleur essai sur un extrait distinct",
    "0.95 timing F1": "F1 temporel : 0,95",
    "Canada–USA 2024: 19 correct, one extra, one missed coarse window over 18.5 minutes. This is a same-production, agent-authored reference.":
        "Canada–États-Unis 2024 : 19 passages concordants, un candidat supplémentaire et un passage manqué sur 18,5 minutes. La référence a été préparée par l'agent sur une vidéo du même type de production.",
    "Main gap": "Limite principale",
    "Full-match reliability": "Fiabilité sur une partie entière",
    "The new Canada–Norway 2022 transfer produces excess candidates and colour conflicts. No independent complete-recording precision/recall exists yet.":
        "L'essai Canada–Norvège 2022 produit trop de candidats et des conflits de couleur. La précision et le rappel sur une partie entière n'ont pas encore été mesurés avec une référence indépendante.",
    "The honest status:": "État réel :",
    "not been met": "n'est pas encore atteint",
    "a source-specific research prototype with useful event and board evidence. The 0.95 precision and 0.95 recall acceptance gate on complete, independently referenced recordings has":
        "un prototype de recherche adapté à certaines vidéos, avec des indices utiles sur les lancers et l'état des pierres. Le critère d'acceptation — précision et rappel d'au moins 0,95 sur des parties entières avec référence indépendante —",
    "Avoid calling the 0.95 result overall accuracy. It measures timing agreement on a short same-family interval against coarse windows prepared by the developing agent.":
        "Ne pas présenter le résultat de 0,95 comme la précision globale du système : il mesure la concordance temporelle sur un court extrait, avec des fenêtres approximatives préparées par l'agent qui développait le détecteur.",
    "One recording through the pipeline": "Une même vidéo, du début à la fin de la chaîne",
    "Canada–Korea 2024: detect a passage, then inspect its arrival.":
        "Canada–Corée 2024 : détecter le passage d'une pierre, puis observer son arrivée.",
    "Event detection": "Détection des passages",
    "For the meeting, follow one 18.5-minute end-three video from a virtual-line stone-passage detector to a partial receiving-view trajectory. This is the strongest coherent demonstration of the intended workflow, with its uncertainty shown beside each output.":
        "Pour la réunion, suivre un seul extrait de 18,5 minutes de la troisième manche : du passage d'une pierre devant une ligne virtuelle jusqu'à sa trajectoire partielle dans la vue d'arrivée. C'est notre démonstration la plus cohérente de la chaîne envisagée, avec l'incertitude associée à chaque résultat.",
    "All 16 coarse, internally prepared passage windows matched one-to-one, with no extra candidate in this same end. The virtual line marks stone passage, not physical release.":
        "Les 16 fenêtres de passage approximatives préparées en interne correspondent chacune à une détection, sans candidat supplémentaire dans cette manche. La ligne virtuelle marque le passage de la pierre, pas l'instant physique du lâcher.",
    "One arrival": "Une arrivée suivie",
    "The yellow stone has an observed receiving-camera path and a provisional settled point. The link across the camera cut uses colour, timing and motion; physical identity is not verified.":
        "Nous observons une partie du trajet d'une pierre jaune dans la caméra d'arrivée et proposons une position d'arrêt. Le rapprochement avec la vue de départ repose sur la couleur, le temps et le mouvement ; l'identité de la pierre à travers la coupe n'est pas vérifiée.",
    "Trajectory check": "Vérification de la trajectoire",
    "Retrospective RMSE on four manually read moving points. Both sides share calibration; this does not measure centimetre accuracy on the ice.":
        "Écart quadratique moyen rétrospectif sur quatre positions lues manuellement pendant le mouvement. Les deux séries utilisent le même étalonnage : ce chiffre ne mesure pas la précision physique en centimètres sur la glace.",
    "This is one development end and one selected arrival trajectory. The eight later passages were checked after the detector was frozen, but still share the recording and internally prepared reference. The middle of the throw, cross-view identity, complete board and physical accuracy remain unverified.":
        "Il s'agit d'une seule manche de développement et d'une trajectoire d'arrivée choisie. Les huit derniers passages ont été évalués après le gel du détecteur, mais sur la même vidéo et avec une référence préparée en interne. Le milieu du lancer, l'identité entre caméras, l'état complet des pierres et la précision physique restent à valider.",
    "Scope:": "Portée de ce résultat :",
    "Start here": "Commencer ici",
    "Sixteen passage detections ↗": "Seize passages détectés ↗",
    "Follow the stone": "Suivre la pierre",
    "Inspect both cameras": "Examiner les deux caméras",
    "Camera-local stone tracks and registration status.":
        "Suivis propres à chaque caméra et état du recalage des images.",
    "Lead with this one recording: the line crossing is a practical event anchor, T11 demonstrates a partial receiving path, and the missing cross-camera identity is the research gap. Then use the transfer table to show why the same result cannot yet be claimed for arbitrary match video.":
        "Commencer par cette vidéo : le franchissement de la ligne donne un repère temporel pratique ; T11 montre une partie du trajet à l'arrivée ; l'identité entre caméras reste inconnue. Montrer ensuite les essais sur d'autres vidéos pour expliquer pourquoi ce résultat ne se généralise pas encore.",
    "What exists today": "Ce qui a été construit",
    "One pipeline, with explicit uncertainty at each stage.":
        "Une chaîne d'analyse qui conserve l'incertitude à chaque étape.",
    "Ingest + view routing": "Lecture vidéo et choix de la vue",
    "Reads full videos, detects cuts and routes known layouts. Unknown spans remain gaps.":
        "Lit les vidéos, détecte les changements de plan et reconnaît certaines dispositions de caméras. Les passages non reconnus restent explicitement manquants.",
    "Stone evidence": "Détection des pierres",
    "Colour caps, learned boxes, local tracks and image-to-ice calibration.":
        "Détection des poignées colorées, boîtes apprises, suivis locaux et projection de l'image vers la glace.",
    "Throw candidates": "Lancers candidats",
    "Early-view passages, cross-view motion and counter-linked event windows.":
        "Passages observés près du départ, mouvement vu après les coupes et fenêtres associées au compteur TV.",
    "Game-state observations": "Observations de l'état du jeu",
    "Stable partial boards from selected overhead frames, compared with official diagrams.":
        "États partiels des pierres observés dans certaines vues de dessus, puis comparés aux diagrammes officiels.",
    "Validated trajectories": "Trajectoires validées",
    "Physical stone identity, exact phase boundaries and calibrated continuous paths.":
        "Identité physique des pierres, instants exacts des phases du lancer et trajectoires continues calibrées.",
    "Coaching agent": "Assistant d'analyse pour l'entraînement",
    "Simulation and grounded feedback only after events and states are reliable.":
        "Simulation et conseils fondés sur la vidéo, une fois les lancers et les états du jeu fiabilisés.",
    "Existing cross-view prototype: one yellow stone shown before and after the broadcast camera handoff. This is a proposed link, not independently proven identity.":
        "Prototype à deux vues : une pierre jaune apparaît avant et après un changement de caméra. Le lien est proposé, mais son identité physique n'est pas validée indépendamment.",
    "Working artifacts": "Démonstrations et données disponibles",
    "One-end demo with 16 detected passages and 16 provisional two-view links.":
        "Démonstration sur une manche : 16 passages détectés et 16 rapprochements provisoires entre deux vues.",
    "Full-source event ledger with candidate windows, colour status, counter links and explicit gaps.":
        "Liste des événements candidats sur les vidéos complètes, avec fenêtres temporelles, provenance des couleurs, liens au compteur et lacunes explicites.",
    "Source-linked official shot and board references for evaluation.":
        "Références officielles des lancers et des positions des pierres, reliées aux vidéos pour l'évaluation.",
    "Interactive cross-view, segment and board evidence viewers.":
        "Visionneuses interactives des deux caméras, des segments et des positions des pierres.",
    "Complete throw boundaries and continuous physical trajectories.":
        "Limites exactes de chaque lancer et trajectoires physiques continues.",
    "Validated game states, simulations and grounded coaching.":
        "États du jeu validés, simulations et conseils fondés sur les observations.",
    "Use the cross-view image as a 30-second demo. Point out the broadcast cut: we cannot claim we saw the stone continuously through that gap.":
        "Montrer pendant 30 secondes l'exemple à deux caméras. Signaler la coupe : nous n'avons pas observé la pierre sans interruption pendant ce passage.",
    "Measured evidence": "Résultats mesurés",
    "Promising intervals, visible transfer failures.":
        "Un résultat prometteur sur la vidéo initiale, puis des échecs de transfert.",
    "The table keeps scoring method and scope beside each number. It is deliberately not a leaderboard of interchangeable F1 scores.":
        "Chaque chiffre est accompagné de sa méthode de mesure et de sa portée. Les différents scores F1 ne sont pas directement interchangeables.",
    "Experiment": "Expérience",
    "Result": "Résultat",
    "What it establishes": "Ce que cela montre",
    "Limit": "Limite",
    "Calibrated body localisation is feasible on chosen views.":
        "La localisation calibrée du corps des pierres est possible dans certaines vues choisies.",
    "Manual calibration and diagram references; not an unseen-video rate.":
        "Étalonnage manuel et comparaison aux diagrammes ; ce n'est pas un taux mesuré sur une vidéo inconnue.",
    "18.5-minute frozen transfer": "Essai figé sur 18,5 minutes",
    "Timing F1 0.950": "F1 temporel : 0,950",
    "Timing F1 0.867": "F1 temporel : 0,867",
    "Coarse agent-authored windows; not a full match.":
        "Fenêtres temporelles approximatives préparées par l'agent ; ce n'est pas une partie entière.",
    "Earlier frozen transfer": "Essai figé précédent",
    "Fixed pixel-speed and virtual-line rules lose real throws.":
        "Les seuils fixes de vitesse dans l'image et la ligne virtuelle manquent de vrais lancers.",
    "Partial interval; same-family coarse reference.":
        "Extrait partiel ; référence approximative issue d'une vidéo du même type.",
    "New full-match transfer": "Nouvel essai sur une partie entière",
    "128 official shots": "128 lancers officiels",
    "Counter linkage reaches 100 readable updates, but the ledger has excess candidates.":
        "Cent candidats sont associés à une mise à jour lisible du compteur TV, mais la liste contient trop de candidats.",
    "No official video release times; no full-match event F1.":
        "Les résultats officiels ne donnent pas l'instant du lâcher dans la vidéo ; aucun F1 de lancer sur la partie entière.",
    "Adjacent-view pairing": "Association entre plans vidéo successifs",
    "Norway end 3 → end 4": "Norvège, manche 3 → manche 4",
    "Norway end 4 → end 6": "Norvège, manche 4 → manche 6",
    "End 4: 10/12": "Manche 4 : 10/12",
    "Only 6 colour-concordant": "Seulement 6 couleurs concordantes",
    "Delayed counter proxy covers 12/16 throws; same-match development, not physical event F1.":
        "Le compteur différé n'offre une référence indirecte que pour 12 des 16 lancers ; développement sur la même partie, sans F1 physique des événements.",
    "Mirrored early line": "Ligne virtuelle des deux côtés",
    "19 partition cues": "19 indices de franchissement",
    "10/12 counter colours": "10/12 couleurs concordantes avec le compteur",
    "Fixed line failed on end 5; delayed counter proxy, not physical event F1.":
        "Une ligne fixe a échoué en manche 5 ; le compteur différé n'est qu'une référence indirecte, pas un F1 des lancers réels.",
    "Held-stone cue": "Indice de pierre tenue avant le lancer",
    "Norway end 6 development → first end 7 transfer":
        "Norvège, développement sur la manche 6 → premier essai sur la manche 7",
    "End 7: 10/12": "Manche 7 : 10/12",
    "14 candidates; 10/10 paired colours agree":
        "14 candidats ; les 10 couleurs appariées concordent",
    "End-six correction was postscore; end-seven counter coverage is 12/16 and same-match. No physical event F1.":
        "La correction en manche 6 est rétrospective ; le compteur ne couvre que 12 des 16 lancers de la manche 7, dans la même partie. Aucun F1 des lancers réels.",
    "Early-line first end-8 transfer": "Premier essai de la ligne précoce en manche 8",
    "Norway end 8; tie-break frozen after end 7":
        "Norvège, manche 8 ; règle de départage figée après la manche 7",
    "8/9 counter pairs": "8/9 associations au compteur",
    "16 candidates; 7/8 paired colours agree":
        "16 candidats ; 7 des 8 couleurs appariées concordent",
    "Only 9/16 official deliveries have clean counters; 8 visual candidates are unpaired. No physical event F1.":
        "Seuls 9 des 16 lancers officiels ont une lecture fiable du compteur ; 8 candidats visuels restent sans association. Aucun F1 des lancers réels.",
    "Non-origin motion fallback": "Détection de secours hors vue de départ",
    "Norway end 7 development → two other recordings":
        "Développement sur la manche 7 de Norvège → deux autres vidéos",
    "End 7 / Slovakia / Switzerland candidates":
        "Candidats en Norvège, Slovaquie et Suisse",
    "Cross-recording check": "Vérification sur d'autres vidéos",
    "Full China track-quality audit": "Audit du suivi sur la partie Chine entière",
    "All 102 existing cap-corroborated camera windows":
        "Les 102 plans où le mouvement d'une poignée de pierre avait été corroboré",
    "15/102 supported": "15/102 avec cet indice supplémentaire",
    "42 visually ambiguous-colour abstentions":
        "42 abstentions faute de couleur visuelle claire",
    "Colour provenance in China ledger":
        "Origine des couleurs dans la liste des candidats Chine",
    "112 existing event candidates": "112 candidats déjà recensés",
    "39 counter-derived": "39 couleurs déduites du compteur",
    "Both visual colours supported; 3 still unresolved":
        "Les deux couleurs restent possibles ; 3 cas non résolus",
    "Provenance audit": "Audit de l'origine des couleurs",
    "Official-sequence diagnostic": "Diagnostic de l'ordre officiel des lancers",
    "Audit only, all three exposed 2022 recordings":
        "Audit uniquement, sur trois vidéos de 2022 déjà examinées",
    "15 candidates / 10 official slots":
        "15 candidats écartés / 10 lancers officiels sans association",
    "Persistent skip or gap in every minimum-cost alignment":
        "Écarts présents dans tous les alignements de coût minimal",
    "Four source-frame reviews": "Quatre vérifications des images source",
    "25-case queue": "Liste de 25 cas à examiner",
    "sequence audit data": "données de l'audit de séquence",
    "Receiving-view recall lead": "Piste d'un lancer manqué dans la vue d'arrivée",
    "Selected China end-one gap": "Cas choisi : première manche Chine",
    "Visible red travel / 0 accepted tracks":
        "Pierre rouge en mouvement / aucun suivi accepté",
    "Cut at 915.4 s": "Changement de plan à 915,4 s",
    "Source frames and diagnostic": "Images source et diagnostic",
    "China S593 colour check": "Vérification de la couleur : Chine S593",
    "Selected end-eight sensitivity": "Analyse choisie : huitième manche",
    "8 to 4 edit cost": "Coût d'alignement : de 8 à 4",
    "Red ledger versus yellow source cues":
        "Liste rouge, indices jaunes dans la vidéo",
    "sensitivity data": "données de sensibilité",
    "Three exposed 2022 recordings": "Trois vidéos de 2022 déjà examinées",
    "359 candidates / 349 official shots":
        "359 candidats / 349 lancers officiels",
    "300 distinct counter-anchored slots":
        "300 lancers officiels distincts associés au compteur",
    "Slot audit": "Audit de couverture des lancers",
    "Full unassigned-shot source scan":
        "Analyse de tous les plans vidéo non attribués",
    "1,351 camera shots": "1 351 plans vidéo",
    "8 raw cues; 4 ice-supported":
        "8 indices bruts ; 4 corroborés sur la glace",
    "China frames": "Images de la partie Chine",
    "Integrated event evidence handoff":
        "Dossier d'indices associé à chaque événement",
    "Additive v3 candidate union": "Liste v3 enrichie des candidats",
    "359 event records": "359 fiches d'événement",
    "113 release cues; 18 two-view colour agreements":
        "113 indices près du lâcher ; 18 accords de couleur entre deux vues",
    "Handoff and limits": "Dossier et limites",
    "Outside-union origin-cue discovery":
        "Indices de départ trouvés hors de la liste initiale",
    "2 rescue proposals": "2 propositions de récupération",
    "71 origin-like shots scanned; 3 raw cues":
        "71 plans ressemblant à des vues de départ analysés ; 3 indices bruts",
    "V2 review method": "Méthode de vérification v2",
    "Frame panel": "Planche d'images",
    "Ice-context ambiguity tie-break":
        "Départage selon la présence de glace autour de la pierre",
    "Three exposed 2022 recordings, then Norway":
        "Trois vidéos de 2022 déjà examinées, puis Norvège",
    "Study": "Étude",
    "Audit": "Audit",
    "Source audit": "Audit des images source",
    "Source frames": "Images source",
    "Official-shot slot coverage proxy": "Couverture indirecte des lancers officiels",
    "Public stone-box clips": "Extraits publics annotés avec des boîtes de pierres",
    "Temporal boards": "États des pierres à différents instants",
    "Adjacent video boards": "États des pierres dans des plans vidéo successifs",
    "Latest full-match case study": "Essai récent sur une partie entière",
    "Canada–Norway 2022 shows the current bottleneck.":
        "Canada–Norvège 2022 révèle le principal obstacle.",
    "From events to game state": "Des événements à l'état du jeu",
    "We have reference states and partial video states. The gap is explicit.":
        "Nous avons des états de référence et des états vidéo partiels. Ce qui manque est identifié.",
    "Simulation readiness": "Prêt pour la simulation ?",
    "Not yet": "Pas encore",
    "Concrete next milestones": "Prochaines étapes concrètes",
    "Raise reliability before adding interpretation.":
        "Fiabiliser les observations avant de les interpréter.",
    "Track the stone, not just its colour": "Suivre la pierre, pas seulement sa couleur",
    "Resolve event sequence": "Résoudre la séquence des lancers",
    "Prove the detector": "Valider le détecteur",
    "Build grounded state + replay": "Reconstruire l'état du jeu et rejouer les coups",
    "Acceptance gate": "Critère d'acceptation",
    "What the team can decide tomorrow": "Décision à prendre en équipe",
    "Prioritise the target use case": "Choisir le cas d'usage prioritaire",
    "Show, then discuss": "Démontrer, puis discuter",
    "A practical 8-minute meeting path.": "Déroulé proposé : huit minutes.",
    "Two sentences to use": "Deux phrases à dire",
    "Full-match viewer": "Visionneuse de parties entières",
    "Cross-view stone evidence ↗": "Pierres observées par deux caméras ↗",
    "Throw segments ↗": "Segments de lancer ↗",
    "Board-state audit ↗": "Audit de l'état des pierres ↗",
    "Evidence and qualifications": "Sources et limites",
    "Sources a reviewer can inspect.": "Sources vérifiables par l'équipe.",
    "What is not independently proven": "Ce qui n'est pas validé indépendamment",
}

ATTRIBUTE_TRANSLATIONS = {
    "T11 source frames before and after the moving yellow stone becomes visible, while the player hides physical release.":
        "Images source de T11 avant et après l'apparition de la pierre jaune en mouvement, tandis que l'athlète masque le lâcher physique.",
    "T11: departure and receiving camera trajectories overlap in time but differ by 0.61 metres at the same frame.":
        "T11 : trajectoires des deux caméras se chevauchant dans le temps mais présentant un écart de 0,61 m dans la même image.",
    "Four real source frames show a yellow stone in departure and receiving camera views, with observed image points below.":
        "Quatre images source montrent une pierre jaune dans les vues de départ et d'arrivée, avec ses positions observées au-dessous.",
    "Canada–Norway second-end broadcast frame with a yellow delivery stone in the lower central ice and red-clothed people elsewhere.":
        "Image de la deuxième manche Canada–Norvège : pierre jaune en cours de lancer au centre bas de la glace et personnes vêtues de rouge ailleurs.",
    "Two pairs of China broadcast frames show camera views changing within camera-shot windows S123 and S519.":
        "Deux paires d'images de la partie Chine montrent un changement de caméra dans les plans S123 et S519.",
}

# Longer technical passages are edited by index against the frozen source-text
# inventory. This keeps the exact figures and the distinction between a visual
# cue, a delayed scoreboard proxy, and an independently validated throw.
INDEX_OVERRIDES = {
    13: "Nous savions détecter les 16 passages de pierre dans une manche Canada–Corée et suivre partiellement une arrivée. Aujourd'hui, nous avons étendu le détecteur à d'autres vidéos, directions de lancer et configurations de caméra : il ne se généralise pas encore. Les échecs de transfert révèlent les points à résoudre avant de promettre une segmentation fiable des parties entières.",
    18: "Commencer par le résultat qui fonctionne, puis montrer les essais d'extension et leurs échecs. Les bons scores sur de courts extraits ne démontrent pas encore un détecteur de lancers fiable sur une partie entière.",
    90: "Nous avons étendu le détecteur à de nouvelles vidéos : plusieurs essais ont échoué.",
    0: "html",
    2: "VIDÉO DE CURLING / AVANCEMENT DU PROJET",
    9: "Réunion avec le superviseur et l'équipe · 9 octobre 2026 · 10 h",
    21: "Chaque étape doit reposer sur des images observables, une incertitude explicite et une évaluation.",
    52: "Examiner T11 dans la vidéo continue de la troisième manche.",
    55: "Positions observées, relevés manuels et limites de la mesure.",
    57: "Extrait de 90 secondes à deux caméras ↗",
    97: "Images de développement choisies",
    98: "à moins de 10 cm",
    105: "Le détecteur de passages en vue précoce donne un résultat encourageant sur un autre extrait du même type de diffusion.",
    149: "Diagnostic du mouvement",
    150: "Diagnostic du suivi",
    324: "Prochaines étapes concrètes",
    325: "Fiabiliser les observations avant de les interpréter.",
    326: "Suivre la pierre, pas seulement sa couleur",
    327: "Reconnaître la pierre tenue et son départ avant la coupe, déterminer le côté actif du lancer, écarter joueurs et incrustations TV, puis conserver l'incertitude entre les vues.",
    328: "Résoudre l'ordre des lancers",
    329: "Associer chaque candidat à au plus un lancer officiel, tenir compte de la manche et traiter le compteur comme un indice différé ; conserver explicitement les conflits et les lancers hors champ.",
    330: "Valider le détecteur",
    331: "Figer les règles sur les vidéos de développement, puis évaluer des parties entières encore jamais examinées, issues des deux types de production, avec des annotations indépendantes et exhaustives.",
    332: "Reconstruire l'état du jeu et rejouer les coups",
    333: "Relier les états stables des pierres, calibrer les coordonnées sur la glace, conserver les lacunes des trajectoires, puis tester une simulation 2D/3D et des résumés pour l'entraînement.",
    334: "Critère d'acceptation",
    335: "Précision ≥ 0,95 et rappel ≥ 0,95",
    336: "Pour chaque partie complète tenue à l'écart, avec une tolérance temporelle fixée avant l'évaluation, un compte explicite des erreurs de couleur, des périodes sans lancer et de la couverture totale. Le F1 sera aussi indiqué, mais ne doit pas masquer une précision ou un rappel insuffisants.",
    337: "Décision à prendre en équipe",
    338: "Choisir le cas d'usage prioritaire",
    339: "Quel format de diffusion et quelle question d'entraînement sont prioritaires ? Quelles sources peuvent fournir des références indépendantes pour les lancers et les positions d'arrêt ? Cela fixe la cible d'évaluation avant de nouveaux réglages.",
    340: "Proposer pour le prochain cycle la reconnaissance de la pierre tenue, l'identité des événements et une évaluation indépendante, puis la reconstruction de l'état du jeu. La simulation viendra ensuite, à partir d'états mesurés.",
    341: "Démontrer, puis discuter",
    342: "Déroulé proposé : huit minutes.",
    343: "1 minute :",
    344: "présenter l'objectif et le stade actuel du prototype.",
    345: "2 minutes :",
    346: "montrer T11 dans Canada–Corée : le passage détecté, la trajectoire à l'arrivée et la lacune créée par la coupe.",
    347: "montrer le tableau des transferts mesurés et l'échec Canada–Norvège.",
    348: "montrer les observations partielles de l'état des pierres.",
    349: "convenir de la prochaine cible d'évaluation et répartir les responsabilités.",
    350: "Deux phrases à dire",
    351: "« Dans une manche Canada–Corée, nous avons retrouvé les 16 passages de pierres annotés et suivi partiellement une arrivée dans la seconde caméra. Le défi est de prouver qu'il s'agit de la même pierre et de mesurer précision et rappel sur des parties entières différentes. »",
    352: "« Le dernier essai sur une partie entière montre l'écart actuel : 142 candidats provisoires pour 128 lancers officiels, avec des conflits de couleur même quand les instants concordent avec le compteur TV. »",
    353: "Visionneuse de parties entières",
    354: "Examiner 359 fenêtres d'événements provisoires ↗",
    355: "Trois vidéos source. Rechercher TRAVEL-B02 pour le cas de mouvement à l'arrivée, SOURCE-S392 ou SOURCE-S216 pour les indices de lâcher visibles seulement dans la source, ou Chine B26. Ces extraits sont des fenêtres de vérification, pas des segments de lancer physiques validés.",
    356: "Démo 1",
    357: "Pierres observées par deux caméras ↗",
    358: "Visionneuse à deux caméras sur une manche ; examiner T11 et les autres associations proposées.",
    359: "Démo 2",
    360: "Segments de lancer ↗",
    361: "Seize fenêtres de vérification entre passages successifs, avec des trajectoires partielles.",
    362: "Preuve 3",
    363: "Audit de l'état des pierres ↗",
    364: "Diagrammes officiels et essai d'états partiels reconstruits depuis la vidéo.",
    365: "Le rapport fonctionne hors ligne. Les liens vers les démonstrations locales exigent que ce fichier HTML reste à la racine du projet avec les données et vidéos associées ; les sources officielles externes exigent Internet.",
    366: "Sources et limites",
    367: "Sources vérifiables par l'équipe.",
    368: "Protocole d'évaluation des événements",
    369: "Critère d'acceptation et définitions des scores",
    370: "Résultat figé Canada–États-Unis",
    371: "Échec de l'essai figé Canada–Estonie",
    372: "Provenance des données Canada–Norvège 2022",
    373: "Plan de transfert préalable et empreintes des fichiers",
    374: "Audit de la première exécution, lisible par machine",
    375: "Interprétation",
    376: "Rediffusion officielle",
    377: "Document officiel des résultats",
    378: "Indices sur l'état du jeu et la géométrie",
    379: "Audits des références et du transfert des positions des pierres",
    380: "Rapport sur la localisation des pierres",
    381: "Visionneuse à deux caméras",
    382: "Ce qui n'est pas validé indépendamment",
    383: "Aucun horodatage exhaustif et indépendant des lancers sur une partie entière ; aucun instant de lâcher validé ; aucune identité de pierre fiable à travers toutes les coupes ; aucune séquence complète des positions tirée de la vidéo ; aucune trajectoire vérifiée physiquement ; aucune mesure de qualité des simulations ou des conseils d'entraînement. La vidéo réservée de Wetzikon reste hors du développement.",
    384: "Préparé pour la réunion du 9 octobre 2026 avec le superviseur et l'équipe.",
    385: "README du projet",
    386: "Protocole d'évaluation",
    387: "Notes du présentateur : touche N · Grandes lettres : touche L · Impression / PDF : bouton en haut ou Ctrl/Cmd+P.",
    282: "Nous avons figé les modèles et les règles avant d'analyser une nouvelle partie, puis comparé les résultats à l'ordre officiel des 128 lancers et aux mises à jour différées du compteur TV. Une",
    283: "manche",
    284: "comprend ici 16 lancers ; cette partie comporte huit manches. Le compteur à l'écran affiche le nombre de pierres restantes et change souvent après le lancer. Le document officiel ne fournit pas les instants de lâcher dans la vidéo.",
    285: "Lancers officiels numérotés",
    286: "Candidats vidéo provisoires",
    287: "Mises à jour lisibles du compteur associées",
    288: "Candidats sans association au compteur",
    289: "La manche entièrement couverte par le compteur",
    290: "La manche 2 comporte 16 mises à jour fiables du compteur. Le détecteur de mouvement des poignées colorées propose 16 événements ; 15 concordent temporellement avec le compteur différé. Pourtant, seuls neuf appariements ont la bonne couleur connue : quatre couleurs s'opposent au compteur et deux restent visuellement inconnues. Un lancer officiel et un candidat ne sont pas appariés.",
    291: "Appariements temporels",
    292: "Couleurs connues concordantes",
    293: "Conflits de couleur",
    294: "Ces chiffres comparent les candidats à un compteur différé ; ils ne mesurent pas indépendamment la précision ou le rappel des lancers physiques. La règle figée de récupération des pierres tenues n'a ajouté aucun événement dans 32 fenêtres admissibles.",
    295: "Image source examinée après le score, à 23 min 12 s : une pierre jaune en cours de lancer est visible. La règle de mouvement des couleurs peut aussi trouver des suivis rouges ailleurs ; l'association temporelle et l'identité des objets doivent progresser.",
    296: "Coupes possibles manquées par le seuil prudent : à 1 606,0 s et 7 029,4 s, la diffusion change de caméra à l'intérieur des plans déjà découpés. Un diagnostic sur toute la source propose 58 coupes supplémentaires dans 55 plans chinois, contre six en Suisse ; 29 propositions chinoises se trouvent dans un intervalle où une poignée est déjà suivie. La recherche suisse réagit aussi à des changements visuels qui ne sont pas des coupes : ce sont des cas à vérifier, pas des coupes confirmées. Le recalage de l'arrière-plan échoue sur les 64 paires proposées, y compris les fausses coupes suisses. La même règle propose dix coupes en Norvège et 17 en Slovaquie ; l'analyse temporelle en classe respectivement sept et 13 comme changements brusques, tout en manquant certains fondus visibles.",
    297: "Examiner l'audit",
    298: "Dernier essai :",
    299: "en manche 7 de Norvège, la ligne précoce orientée et l'indice figé de pierre tenue trouvent 14 candidats colorés, dont 10 associés aux 12 mises à jour fiables du compteur différé. Les dix couleurs associées concordent, mais deux événements soutenus par le compteur sont manqués et quatre candidats restent sans association. Il s'agit d'une référence indirecte sur la même partie, pas d'un F1 des lancers physiques. Auparavant, un filtre spatial de glace conservait du mouvement dans seulement 52 des 114 fenêtres confirmées par une poignée : trop de pertes pour un veto strict. En manche 8, un critère de qualité du passage figé n'a rien changé ; la règle initiale associe 8 des 9 compteurs fiables, avec un conflit de couleur.",
    300: "Le chiffre 142 n'est pas un score F1. La liste provisoire dépasse de 14 le nombre officiel de lancers : elle ne représente donc pas encore un événement net par lancer. Le compteur est différé et peut être associé au mauvais mouvement.",
    303: "Références officielles",
    304: "Diagrammes officiels des lancers numérotés dans quatre parties de Pékin 2022 : 349 pour les trois premières parties étudiées, plus 128 états Canada–Norvège. Ce sont des observations de référence, pas des reconstructions à partir de la vidéo.",
    305: "Essai de reconstruction depuis la vidéo",
    306: "états partiels des pierres",
    307: "L'échantillon initial de 15 lancers produit sept états partiels et 22 pierres dont les positions concordent. Une recherche ciblée dans les plans voisins ajoute deux états et quatre pierres, ainsi que deux transitions locales observées. La couverture reste sélective.",
    310: "Il manque encore les coordonnées physiques, l'identité persistante des pierres, les instants fiables d'arrêt et les trajectoires continues. Une simulation 3D ou un assistant d'entraînement inventerait sinon des faits.",
    311: "Export de données déjà construit :",
    312: "neuf états partiels tirés de la vidéo et 26 observations de pierres sont exportés avec les empreintes des sources, les intervalles temporels et des coordonnées sans unité dans la maison. L'extension suisse de la manche 2 ajoute deux transitions locales ; les trois états produits dans cette recherche ciblée de cinq lancers concordent rétrospectivement avec les diagrammes officiels. Le premier essai Canada–Chine avec la même règle donne deux états partiels et aucun complet sur cinq lancers. Dans des essais chinois ultérieurs choisis, les points de contact des pierres correspondent à 3/3 symboles sous l'hypothèse d'une orientation de caméra inversée de 180° ; une fusion provisoire des vues de dessus et larges du plan précédent atteint aussi 3/3. Ces essais ne modifient pas le score du premier transfert. La règle figée sur les vues larges trouve d'abord 1/2 pierre suisse ; une correction rétrospective de l'anneau bleu atteint 2/2. L'emblème asymétrique peint au centre de la maison indique indépendamment une inversion de 180° dans 12/12 paires d'images choisies, en Chine comme en Suisse. Dans cette orientation indiquée par l'image, le recouvrement des points de contact entre vues vaut 1/1 en Chine et 2/2 en Suisse ; la fusion chinoise de trois pierres n'est pas intégrée à l'export. Dans cinq fenêtres slovaques prévues à l'avance, la règle révisée ne trouve que des images larges isolées et aucun suivi stable. Les détecteurs actuels de maison n'acceptent aucune des 57 images norvégiennes échantillonnées dans la vue de lancer : l'emblème ne permet donc pas encore d'orienter la détection précoce. La couverture, la continuité temporelle et la projection géométrique ne sont pas validées indépendamment. Tous les états exportés restent incomplets ou inconnus depuis la vidéo, et impropres à la simulation. Ni l'identité de la pierre lancée ni une transition physique de l'état du jeu ne sont établies.",
    313: "Examiner l'analyse de couverture",
    314: "Dossier d'indices par événement",
    315: "21 des 112 candidats chinois présentent une coupe possible traversant le suivi d'une poignée",
    316: "Le nouvel export conserve, pour chaque événement, la provenance de la couleur (vidéo ou compteur), puis signale les changements de vue internes possibles et les suivis qui les traversent. Quatorze autres candidats présentent une coupe possible sans suivi traversant ; aucune coupe n'est proposée pour 77 candidats à ce seuil. Aucun cas ne possède une identité physique vérifiée, un instant exact de lâcher, une trajectoire continue ou un état prêt pour la simulation.",
    317: "Examiner le dossier",
    318: "Couverture des événements par les états des pierres :",
    319: "Sur huit fenêtres chinoises déjà choisies pour examiner l'état des pierres, cinq contiennent un état partiel. L'ancienne liste associée au compteur couvre les huit, mais seuls trois des cinq cas avec état figurent dans la nouvelle liste de 112 candidats fondée sur le mouvement des poignées. L'un des cas absents comporte un ancien conflit de couleur. Son absence ne signifie pas qu'aucun lancer n'a eu lieu ; partager un compteur ne vérifie pas non plus la pierre lancée. Un indice de pierre tenue sur la glace propose une récupération provisoire pour B57. À l'arrivée, un autre indice montre un mouvement jaune possible pour B26 après la mise à jour du compteur, sans résoudre le lâcher ni la transition des pierres. Sur les trois vidéos de 2022 déjà examinées, cette règle propose trois ajouts en Chine et aucun en Suisse ni en Slovaquie. Dix-sept des 29 propositions fondées sur le mouvement arrivent après un candidat déjà visible ; 13 paires ont des couleurs contradictoires. La règle actuelle associe 21 compteurs à des candidats existants sans en augmenter le nombre, ce qui révèle 16 conflits de couleur. Une liste dédoublonnée distincte compte 117, 123 et 116 candidats provisoires. Les cinq fenêtres chinoises avec état ont maintenant un candidat associé au compteur ; seul B26 présente un recouvrement entre images de l'état et mouvement observé. Ce sont des liens de suivi des sources, pas des transitions physiques vérifiées.",
    320: "Examiner la liste fusionnée",
    322: "dossier des états des pierres",
    323: "Les diagrammes officiels permettent de vérifier une future reconstruction. Les injecter directement dans une simulation contournerait le problème de reconstruction depuis la vidéo. Les résultats tirés des images sont prometteurs, mais choisis et incomplets.",
    222: "La glace visible distingue une vue de lancer suisse d'un gros plan ; la même règle s'abstient face à l'ambiguïté norvégienne.",
    223: "Un indice sur le type de vue ne démontre pas l'identité de la pierre lancée et n'a pas été transformé en décision de lancer.",
    224: "Diagnostic chronologique du compteur",
    225: "Quatre vidéos de 2022 déjà examinées",
    226: "3 propositions uniques sur 10",
    227: "6 associations existantes contradictoires",
    228: "La mise à jour précédente du compteur TV départage trois attributions ambiguës aux plans, dont Norvège B69 → S389. L'examen des images soutient ce choix norvégien.",
    229: "Le compteur TV peut être mis à jour après le lancer suivant : six associations existantes contredisent l'ordre proposé. La liste des événements et le F1 des lancers physiques ne changent pas.",
    230: "Audit de l'ordre indiqué par le compteur",
    231: "4 propositions uniques sur 11",
    232: "3 inversions d'associations existantes",
    233: "Les associations voisines au compteur limitent les plans possibles. Une recherche de pierre tenue dans la vidéo trouve du jaune dans les deux nouveaux plans slovaques proposés pour des compteurs rouges ; l'audit figé après coupe classe l'un comme jaune et s'abstient sur l'autre.",
    234: "Aucune des deux nouvelles associations n'a été ajoutée. Un indice de lâcher plus fort dans le même plan apparaît dans 3 des 13 plans concurrents, dont S411 jaune et S374 rouge, mais la lecture brute du compteur fluctue autour de B80/B81. Couleur et ordre ne prouvent ni l'identité entre caméras ni un gain de F1.",
    235: "Fiabilité de lecture du compteur brut",
    236: "58/400 avec fiabilité élevée",
    237: "420 mises à jour brutes produites",
    238: "Seules 58 mises à jour lisibles avant et après le changement présentent un soutien exact d'au moins 0,75 pour les deux états ; l'icône lue sur une seconde fluctue souvent.",
    239: "Un seuil strict de stabilité éliminerait une grande partie des indices fournis par le compteur différé. Ces chiffres mesurent la couverture du lecteur de compteur, pas la précision des lancers physiques.",
    240: "Transfert de l'indice de lâcher dans une même vue",
    241: "Trois listes de candidats de parties entières déjà examinées",
    242: "111 indices dans 356 plans candidats",
    243: "Suisse : 45 ; Chine : 32 ; Slovaquie : 34",
    244: "La recherche de pierre tenue puis mise en mouvement fournit des instants reliés aux images source. Limiter la recherche aux plans déclarés retire Suisse B48 et retrouve Chine B57 ; la recherche large initiale comptait aussi 111 indices, mais sur d'autres cas. Les couleurs concordent avec la liste dans 101 cas, s'opposent dans deux et restent inconnues dans huit.",
    245: "Les 31,2 % mesurent la couverture des candidats, pas le rappel des lancers physiques. Le passage d'une poignée colorée ne prouve ni l'identité entre caméras ni l'instant exact du lâcher.",
    246: "Association des couleurs entre deux vues",
    247: "Indice strict après coupe et passage dans la vue de départ",
    248: "16 accords entre indices vidéo",
    249: "4 couleurs inconnues dans la liste ; 1 conflit",
    250: "En Chine, S593 montre du jaune au départ et à l'arrivée, alors que la liste indique rouge ; le suivi dans la vue d'arrivée commence 0,6 s après la coupe.",
    251: "Aucun des 16 suivis ne dispose d'un recalage fiable de l'arrière-plan. Pour S593, après exclusion de la pierre jaune, il ne reste que sept points d'arrière-plan suivis ; abaisser le seuil d'ajustement serait risqué. La liste principale conserve le rouge en attendant vérification.",
    252: "Transmission des indices",
    253: "Lien du lâcher à l'état des pierres",
    254: "Neuf états partiels tirés de la vidéo",
    255: "1/9 lié à un indice de lâcher limité au plan",
    256: "9/9 liés provisoirement au compteur",
    257: "Dans le plan de départ B57 en Chine, la recherche limitée au plan trouve un seul passage de pierre rouge tenue puis mise en mouvement à 3 459,8 s. La recherche large sur plusieurs plans en trouvait deux et s'abstenait ; les huit autres liens aux états des pierres n'ont toujours pas d'indice unique.",
    258: "Pour B57, l'indice de départ, le mouvement à l'arrivée et l'état partiel ultérieur forment une chaîne temporelle provisoire par l'intermédiaire du compteur différé. Ils ne vérifient ni l'identité de la pierre lancée ni une transition physique de l'état du jeu. Ce chiffre mesure la couverture, pas le rappel des lancers.",
    259: "Extraits publics avec boîtes autour des pierres",
    260: "20 extraits tenus à l'écart, 985 images annotées",
    261: "F1 : 0,681 → 0,859",
    262: "Amélioration sur 18/20 extraits",
    263: "Le réentraînement du modèle de détection locale des pierres réduit les fausses boîtes tout en conservant la plupart des vraies pierres.",
    264: "Le résultat est mitigé sur les vues latérales télévisées ; le modèle n'a pas été adopté. Les ensembles d'extraits peuvent partager des images source ; aucun score de détection des lancers.",
    265: "Jeu de données",
    266: "États des pierres à différents instants",
    267: "15 plans choisis et associés au compteur",
    268: "7 états partiels des pierres",
    269: "22/22 pierres trouvées concordent ; 5 états complets",
    270: "Dans certaines vues de dessus choisies, la vidéo permet d'observer des positions de pierres stables en 2D.",
    271: "Huit plans ne produisent aucun état ; l'échantillon de développement est choisi.",
    272: "États des pierres dans des plans voisins",
    273: "Développement suisse → premier essai en Chine",
    274: "États complets : 3 → 0 ; 2 transitions locales en Suisse",
    275: "Des états consécutifs peuvent être reconstruits dans une vue suisse favorable. Les gros plans chinois ne montrent qu'une pierre ; des essais ultérieurs sur des vues larges trouvent les points de contact des pierres et une fusion provisoire de trois pierres.",
    276: "Résultats sur des fenêtres choisies de cinq lancers, pas des taux généraux. La normalisation elliptique simple place 1 des 3 centres de poignées dans la tolérance ; les points de contact des pierres et la fusion de deux vues atteignent chacun 3/3 sous une hypothèse d'orientation de caméra à 180°, dans une analyse rétrospective. Le premier essai suisse conserve 1/2 pierre visible ; une correction rétrospective de l'anneau bleu atteint 2/2. L'emblème peint au centre de la maison indique indépendamment une inversion de 180° dans les exemples chinois et suisses. Cinq fenêtres slovaques figées ne donnent aucun suivi stable des contacts en vue large. Les détecteurs actuels de maison ne trouvent aucun logo exploitable sur 57 images norvégiennes prises dans la vue de lancer ; cette piste n'a donc pas amélioré la détection des lancers. Ces états ne sont pas prêts pour la simulation.",
    277: "Transfert",
    278: "VP = lancer apparié ; FP = candidat supplémentaire ; FN = lancer manqué. Le F1 combine précision et rappel. Les scores fondés sur des références différentes ne sont pas directement comparables.",
    279: "Le meilleur essai de transfert est Canada–États-Unis 2024, mais les échecs comptent autant : quatre lancers sont manqués en Estonie et la vidéo de 2022 exige une autre méthode. L'association de plans voisins se trompe sur la couleur en manche 4. La ligne virtuelle fixe échoue quand la direction de lancer s'inverse ; même après adaptation, elle manque des pierres tenues au départ. Le score de 0,859 concerne les boîtes autour des pierres dans des extraits publics, pas la détection des lancers.",
    122: "L'association des vues de départ et d'arrivée réduit les doublons, mais peut encore suivre la mauvaise pierre ou manquer des mises à jour du compteur.",
    129: "Une ligne déplacée selon le sens du mouvement gère les deux directions de lancer ; les pierres tenues immobiles et les coupes précoces restent difficiles.",
    135: "La pierre tenue ou en mouvement près du lanceur peut corriger certaines couleurs, mais la règle figée n'a corrigé aucune couleur et n'a récupéré aucun événement supplémentaire associé au compteur en manche 7.",
    141: "La ligne suit le sens du mouvement, mais le nouveau critère de qualité du passage n'a rien changé ; une couleur reste en conflit avec le compteur.",
    146: "Un mouvement de même couleur dans les plans voisins peut signaler une vue de lancer rejetée, mais réagit aussi à des mouvements sans rapport. Une vérification rétrospective des phases écarte trois indices suisses. Figée puis appliquée à l'intégralité de la vidéo chinoise, la règle produit deux candidats sur 630 plans ; les deux figuraient déjà dans la liste des événements.",
    147: "Un candidat chinois contredit la couleur du compteur associé ; aucun nouveau plan de lancer n'est récupéré. Dans S123, une vérification ciblée trouve un mouvement relatif à la caméra, mais un seul saut d'association représente 96,9 % du trajet du suivi principal. S519 n'a pas de paire d'images permettant un recalage fiable. D'éventuelles coupes internes restent sous le seuil figé. Un panoramique suisse choisi produit 11 étapes de mouvement, mais un résidu relatif à la caméra de 7,3 px au maximum : la continuité du suivi ne suffit pas à l'écarter. La correction des phases suisses est rétrospective. Sans référence indépendante ni F1 des lancers, cette règle n'est pas intégrée au détecteur.",
    156: "Le mouvement de plusieurs poignées, associé à un déplacement relatif à la caméra, apporte parfois un indice utile ; la plupart des fenêtres candidates ne présentent cependant pas ces deux indices.",
    157: "Après correction d'une différence de suivi propre à l'audit, seuls 12 des 43 cas à couleur connue associés à un compteur différé présentent ces deux indices. En faire une condition obligatoire rejetterait les 31 autres. Il s'agit de couverture de la chaîne, non de rappel indépendant des lancers ; cette vidéo était déjà connue.",
    163: "La liste fusionnée attribuait déjà une couleur issue du compteur différé à 39 des 42 candidats dont la couleur visuelle était ambiguë. Le nouvel export indique si la couleur vient de la vidéo, du compteur, des deux ou d'aucun des deux.",
    164: "Dix autres candidats reçoivent une couleur du compteur sans candidat visuel corroboré. L'association au compteur dépend d'un mouvement voisin ; elle ne prouve ni l'identité de la pierre lancée ni le F1 des événements.",
    170: "En fixant 275 associations fiables au compteur, la comparaison de l'ordre et des couleurs place 330 candidats sur le même lancer officiel dans tous les alignements optimaux. Les 15 candidats écartés et les 10 lancers officiels sans candidat forment une liste de vérification ciblée. Quatre candidats écartés conservent pourtant un indice distinct de lancer dans la vidéo source : on ne peut donc pas les supprimer en bloc.",
    171: "La séquence officielle et le coût d'alignement sont des diagnostics rétrospectifs, ni des annotations indépendantes des lancers physiques ni des entrées du détecteur en fonctionnement.",
    179: "Entre deux fenêtres candidates, la diffusion montre la préparation d'un lancer chinois, puis un gros plan qui masque le lâcher, puis une pierre rouge qui avance vers la maison. La recherche de passage dans la vue de départ et le détecteur strict après coupe s'abstiennent tous deux.",
    180: "Le lancer officiel E01-S14 a motivé cette inspection rétrospective ; l'association au lancer physique et l'identité entre caméras ne sont pas vérifiées. C'est une piste pour un lancer manqué, pas un faux négatif mesuré.",
    186: "La liste attribue le rouge à S593, alors que l'indice au départ et le suivi à l'arrivée indiquent le jaune. Modifier uniquement cette couleur associe S593 au lancer officiel E08-S13 dans l'unique alignement de coût minimal.",
    187: "Cela suggère une correction provisoire de la couleur d'après les images, sans vérifier l'identité de la pierre entre caméras ni améliorer un F1 mesuré. La liste figée des candidats reste inchangée.",
    194: "Sur trois parties, 308 candidats associés au compteur couvrent 300 lancers officiels distincts. Quarante-neuf lancers officiels n'ont aucun candidat associé au compteur ; six en ont plusieurs. La partie Chine compte 125 candidats pour 125 lancers officiels, mais 11 lancers restent sans candidat associé au compteur.",
    195: "Des événements vidéo sans association peuvent couvrir ces lancers, et la lecture du compteur peut fluctuer. C'est un diagnostic de couverture indirect, pas une mesure de précision, de rappel ou de F1 des lancers physiques.",
    200: "Les quatre indices corroborés se trouvent dans des plans rejetés par le modèle de vue de départ. Trois cas suisses précèdent immédiatement des candidats rouges existants ou montrent du mouvement près de la maison. En Chine, S28 montre une pierre rouge en mouvement à l'arrivée après S27, plan de départ possible sans attribution ; le compteur rouge brut B02 suit à 383 s.",
    201: "Cette vérification rétrospective propose pour B02 un candidat fondé uniquement sur le mouvement à l'arrivée, ajouté provisoirement à une liste distincte de 359 événements. Le déclenchement dans cette vue n'est pas l'heure du lâcher, et l'identité physique reste inconnue.",
    208: "Chaque candidat dispose maintenant d'une fiche réunissant l'indice de lâcher dans le plan source, l'indice à l'arrivée, la fenêtre de vérification et tout lien vers un état partiel des pierres. Neuf événements ont un lien vers cet état ; seul B57 en Chine possède à la fois un indice de lâcher et ce lien. B02 montre une pierre rouge en mouvement à l'arrivée sans indice de lâcher visible.",
    209: "Les instants physiques du lâcher, les identités persistantes des pierres, les temps d'arrêt et les trajectoires continues restent inconnus. Aucun événement n'est prêt pour la simulation ; les neuf liens aux états des pierres reposent sur le compteur.",
    214: "S392 en Suisse et S216 en Chine montrent chacun une pierre rouge tenue puis mise en mouvement, absente de la liste figée de 356 candidats. Après une coupe vérifiée, chacun présente un suivi strict d'une pierre rouge dans la vue d'arrivée. Un gros plan suisse déclenche aussi l'indice brut, mais échoue au contrôle existant de présence sur la glace.",
    215: "Le recalage du mouvement de caméra reste non résolu dans les deux vues d'arrivée. Ce sont des pistes de lancers manqués visibles dans les images, pas des lancers annotés indépendamment ni un F1 mesuré. Une liste enrichie de 358 candidats les inclut provisoirement, sans association aux lancers officiels ni affirmation sur l'identité physique.",
}
_source_nodes = list(json.loads(TRANSLATIONS.read_text()))
OVERRIDES.update({_source_nodes[index]: value for index, value in INDEX_OVERRIDES.items()})


def translate_html(source):
    mapping = json.loads(TRANSLATIONS.read_text())
    soup = BeautifulSoup(source, "html.parser")
    soup.html["lang"] = "fr"
    missing = set()
    for node in list(soup.find_all(string=True)):
        if isinstance(node, Doctype) or node.parent.name in ("script", "style"):
            continue
        raw = str(node)
        key = raw.strip()
        if not key or not re.search("[A-Za-z]", key):
            continue
        translated = OVERRIDES.get(key, mapping.get(key))
        if translated is None:
            missing.add(key)
            continue
        prefix = raw[:len(raw) - len(raw.lstrip())]
        suffix = raw[len(raw.rstrip()):]
        node.replace_with(prefix + translated + suffix)
    for image in soup.find_all("img", alt=True):
        image["alt"] = ATTRIBUTE_TRANSLATIONS[image["alt"]]
    if missing:
        raise ValueError(f"Untranslated report text: {sorted(missing)[:8]}")
    return str(soup)
