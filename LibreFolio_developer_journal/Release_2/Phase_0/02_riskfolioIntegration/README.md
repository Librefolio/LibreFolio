# Risk Analysis — ripianificazione

**Data apertura**: 16 Settembre 2026
**Stato**: 🟡 analisi chiusa · pianificazione da scrivere
**Premessa**: il sottosistema Risk è **rilasciato in beta** con un banner su ogni vista.

---

## Perché questa cartella è stata svuotata

La prima campagna Risk (Luglio 2026) ha prodotto un backend completo e auditato e
**21 documenti di piano**, ma il frontend si è fermato al **26% della catena G6**
(work item 7 di 23). Il rilascio è avvenuto comunque, coprendo le viste incomplete con
un banner beta.

L'analisi del 16 Settembre 2026 ha stabilito che il problema non è la qualità del
backend né la resa grafica, ma **l'assenza di una domanda guida**: i piani rispondevano
a *«quali strumenti di rischio esistono?»* invece che a *«quale decisione deve prendere
l'utente?»*. Senza quella domanda ogni metrica pesa uguale, le implementi tutte, la UI
diventa una lista e l'utente non sa dove guardare.

Il materiale precedente **non è stato cancellato**: è in
[`_archive-backendFirst-G0G6/`](./_archive-backendFirst-G0G6/) e resta la fonte
autoritativa per il **contratto matematico**, le **evidenze di benchmark** e le
**decisioni di architettura backend**, che restano tutte valide.

Ciò che è superato è la **pianificazione frontend** (catena G6) e la **gerarchia di
priorità fra le metriche**.

---

## Ordine di lettura

| # | Documento | Contenuto |
|---|---|---|
| 0 | [`00-analisi-stato-attuale.md`](./00-analisi-stato-attuale.md) | Inventario **verificato sul codice** di cosa esiste davvero, dove, e quanto del piano è stato eseguito. |
| 1 | [`01-tesi-e-quattro-domande.md`](./01-tesi-e-quattro-domande.md) | **La direzione.** Tesi guida, i quattro livelli di domanda, la regola dei pesi. Fonte di ogni decisione successiva. |
| 2 | [`02-verdetti-per-strumento.md`](./02-verdetti-per-strumento.md) | Per ogni strumento: cosa fa, a che domanda risponde, verdetto e destinazione. |
| 3 | [`03-mappa-livelli-pagine.md`](./03-mappa-livelli-pagine.md) | Mappa livelli × pagine, conseguenze architetturali, scomposizione del monolite. |
| 4 | [`04-decisioni-e-questioni-aperte.md`](./04-decisioni-e-questioni-aperte.md) | Registro delle decisioni prese, dei rinvii, e di ciò che resta aperto. **Documento vivo.** |

---

## Stato dell'avanzamento

| Blocco | Stato |
|---|---|
| Analisi dello stato attuale | ✅ 16 Set 2026 |
| Tesi e quattro domande | ✅ 16 Set 2026 |
| Verdetti per strumento | ✅ 16 Set 2026 |
| Mappa livelli × pagine | ✅ 16 Set 2026 |
| **UI/UX per zona e scelta dei grafici** | ⏳ prossimo blocco |
| Piano esecutivo | ⏳ da scrivere dopo la UI/UX |

---

## Vincoli di scopo già fissati

- **Asset Detail è parcheggiato in beta.** Non rientra in questo giro. La discussione si
  concentra su **Dashboard**, **Broker Detail** e **Asset Global**.
- **I segnali rolling restano dove sono** (Overview di Asset Detail). Non vengono
  spostati né duplicati.
- **Il backend non viene riaperto** su: contratto matematico, QuantLib MC/QMC, obbligo
  di processo `spawn`, serie canoniche, metadata di qualità del dato.
- **La catena G6 non viene ripresa.** 23 item a catena singola con gate umani bloccanti
  si è dimostrato un modello fragile: un solo stop congela tutto il resto.

---

## Riferimenti

- Archivio prima campagna: [`_archive-backendFirst-G0G6/`](./_archive-backendFirst-G0G6/)
- Rinvii registrati: [`../../../../TODO_FUTURI.md`](../../../../TODO_FUTURI.md)
