# Model Card — InduSense (modèle apprenant)

Les statuts autorisés sont `[mesuré]`, `[à produire]`, `[non mesuré]`,
`[à confirmer]` et `[benchmark externe]`. Toute ligne `[mesuré]` doit comporter
`preuve=chemin/relatif` vers un fichier local réel.

## 1. Niveau métier

- Finalité et utilisateurs : [à produire]
- Décision assistée, hors périmètre et supervision humaine : [à produire]
- Coût des erreurs : [à produire]

## 2. Niveau technique / maintenance

- Artefact et version : [à produire]
- Données, split temporel et empreinte : [à produire]
- Métriques et seuil : [à produire]
- MLflow run_id : [à produire]
- Signature I/O : [à produire]
- Coût comparé CPU, RAM, GPU, durée, latence et taille : [non mesuré]
- Limites, drift, réévaluation et responsable : [à produire]

## 3. Niveau conformité AI Act

- Finalité, personnes affectées et données utilisées : [à produire]
- Risques, transparence, journalisation et supervision : [à produire]
- Classification réglementaire : [à confirmer] à confirmer avec le référent conformité

## 4. Benchmark externe distinct

- Référence Marine — ne décrit pas mon modèle : [benchmark externe] XGBoost ; cible panne à 24 h ; seuil proche de 0,41 ; PR-AUC proche de 0,62 ; prévalence 16,6 %.
- Coût Marine — ne décrit pas mon modèle : [benchmark externe] frugal 202,6 s / 0,158 gCO2e ; lourd 612,8 s / 0,352 gCO2e.
