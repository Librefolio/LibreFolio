# 19_yieldOnCost — colonna Yield on Cost (U3, primo incremento SP06)

> Archiviata da `Phase_0/19_yieldOnCost/` il 2026-10-09, con un `mv` normale. La verifica d'archivio l'ha fatta I per
> conto di H, la cui sessione non esiste più: il piano è stato riallineato al codice di `dev_release2` a `3cceb4f90`
> (§14, «Aggiornamento 2026-10-09»).

Il workstream H ha aggiunto lo Yield on Cost calcolato dal ledger delle transazioni: la colonna nelle tabelle delle
posizioni di Dashboard e Broker, con il suo tooltip e lo stato «non disponibile» distinto dal valore, più la pagina di
teoria in MkDocs. Commit `74afcebce`, ultimo commit del ramo `f092a194b`, integrato in `dev_release2` col merge
`d7d40c0ec` (2026-09-11).

| File | Descrizione | Stato |
|---|---|---|
| `plan-phase00YieldOnCost.prompt.md` | Piano H: Gate 0, contratto, implementazione, gate, review e walkthrough | ✅ Completato e integrato il 2026-09-11 |

**Residuo tracciato:** la pagina di teoria `yield-on-cost.en.md` non ha ancora le versioni it/fr/es. È rinviata a
`Phase_0/38_postReleaseBacklog/README.md`, voce «I-08 · debito di traduzione MkDocs», da fare con Aphra e solo su
richiesta del developer.
