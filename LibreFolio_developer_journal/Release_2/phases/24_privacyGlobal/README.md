# 24_privacyGlobal — privacy globale, «nascondi valori» (U2, SP15)

> Archiviata da `Phase_0/24_privacyGlobal/` il 2026-10-09, con un `mv` normale. La verifica d'archivio l'ha fatta I
> per conto di J, la cui sessione non esiste più: analisi e piani sono stati riallineati al codice di `dev_release2` a
> `3cceb4f90`.

Il workstream J ha costruito la privacy globale: uno store con il toggle nell'header, il mascheramento nei
formattatori (`maskable`), la classificazione dei siti pubblici e un gate che controlla i siti del denaro. Il Round 2
ha corretto quello che la review d'uso del 22/09 aveva trovato: simbolo della valuta, rischio, lotti, Broker e
quantità possedute.

| File | Descrizione | Stato |
|---|---|---|
| `analysis-phase00PrivacyGlobal.md` | Analisi preliminare: contratto, primitive, store, decisioni D1–D7. Non è un piano | ✅ Eseguita per intero dai due round |
| `plan-phase00PrivacyGlobalRound1-MaskingCore.prompt.md` | Round 1, nucleo di mascheramento: passi 1–4 e 6–8 | ✅ Completato il 2026-09-22; passo 5 (`SensitiveValue`) sospeso per decisione misurata, non un buco |
| `plan-phase00PrivacyGlobalRound2-PostReview.prompt.md` | Round 2, correzioni dalla review d'uso del 22/09 | ✅ Completato il 2026-09-24, integrato col merge `2bbaa8db2` (2026-09-25) |

**Residuo tracciato:** la precisione del gate sui due rami di `shortMoney` e su `axisTickAmount` in
`PerformanceChart.svelte`. È rinviata a `Phase_0/38_postReleaseBacklog/README.md`, voce «I-05 · precisione del gate
privacy su PerformanceChart», con la proposta di fonderla con P4-11.

**Piano gemello:** il Round 8 dell'onboarding, `Phase_0/21_onboarding/plan-phase00OnboardingRound8-PostReview.prompt.md`
(cartella attiva al 2026-10-09), è nato dalla stessa review.
