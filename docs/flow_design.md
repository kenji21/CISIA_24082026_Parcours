# Design du flow M29–M30 — a completer

## Diagramme

```text
entree -> task ? -> task ? -> sortie ?
```

## Contrats des tasks

| Task | Entree | Sortie | Effet de bord | Retry | Cle d'idempotence |
|---|---|---|---|---|---|
| A completer | A completer | A completer | A completer | A completer | A completer |

## Preuves attendues

- Deux executions sur la meme fenetre ne dupliquent aucune ligne.
- Un echec intermediaire peut etre repris sans recommencer aveuglement.
- Chaque run porte un nom et des parametres retrouvables.
