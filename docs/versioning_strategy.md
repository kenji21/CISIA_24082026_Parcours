# Strategie de versioning — a completer en M24

| Objet | Source de verite | Identifiant/version | Stockage | Preuve de restauration |
|---|---|---|---|---|
| Code | A completer | A completer | Git | A completer |
| Donnees | A completer | A completer | DVC | A completer |
| Modele | A completer | A completer | DVC + MLflow | A completer |
| Secrets | A completer | Jamais dans Git | A completer | A completer |

## Questions a trancher

1. Quel commit produit quel modele ?
2. Quelle empreinte identifie le Gold utilise ?
3. Comment rejouer un run sans modifier `uv.lock` ?
4. Comment restaurer code, donnees et modele ensemble ?
