# 03 — Mappa livelli × pagine

**Data**: 16 Settembre 2026
**Scopo**: stabilire chi mostra cosa, prima di toccare qualunque componente.
**Fuori scopo in questo giro**: Asset Detail, parcheggiato in beta.

---

## 1. Le tre pagine

| Pagina | Natura | Pesi | Linguaggio |
|---|---|:---:|---|
| **Dashboard** | tutto il patrimonio | ✅ | euro — «io» |
| **Broker Detail** | stesso patrimonio, scope ridotto | ✅ | euro — «io» |
| **Asset Global** | laboratorio: 3 popolazioni di asset | ❌ | percentuali — «questi» |

Asset Global ha, dalla consegna F15 round-2, tre pannelli discriminati da `txScope`:

- `own` — asset posseduti;
- `others` — asset di altri utenti di cui si ha visibilità;
- `analysis` — **asset osservati e non posseduti** ← il laboratorio vero e proprio.

---

## 2. La mappa

| | **Dashboard** | **Broker Detail** | **Asset Global** |
|---|---|---|---|
| **L1** Quanto può fare male? | ✅ pieno, in € — scala giorno → mese → drawdown | ✅ identico | ⚠️ per-asset, in % — come confronto |
| **L2** Sono diversificato? | ✅ correlazione + contributo al rischio | ✅ identico | ✅ **casa primaria della correlazione**<br/>❌ contributo (mancano i pesi) |
| **L3** Sono pagato per il rischio? | ✅ pieno + beta vs benchmark persistente | ✅ identico | ⚠️ confronto **fra** asset, mai un giudizio |
| **L4** Cosa succede se…? | ✅ replay + shock + simulazione, in € | ✅ identico | ⚠️ **solo replay storico, in %**<br/>❌ shock ipotetico |

---

## 3. Le tre conseguenze

### 3.1 Dashboard e Broker Detail sono **lo stesso componente**

Non «simili»: identici, con scope diverso. Lo conferma già il codice — entrambe le
route montano `RiskAnalysisPanel`, cambiando solo lo scope
(`portfolio` vs `portfolio + broker_ids`).

> **Non progettiamo due pagine, ne progettiamo una.**

Corollario importante per L3: il benchmark deve essere **lo stesso** nelle due pagine.
Se Dashboard dicesse «vs MSCI World» e Broker Detail «vs S&P 500», le due pagine non
sarebbero più confrontabili e si perderebbe esattamente la proprietà che stiamo
costruendo.

### 3.2 Il monolite si scompone da sé — e non arbitrariamente

Non si tratta di «dividere 1.271 righe in pezzi più piccoli», che è un refactor senza
tesi. Si tratta di **un pannello per livello**, composto diversamente da ogni pagina:

```text
Dashboard      = L1 + L2 + L3 + L4          (€)
Broker Detail  = L1 + L2 + L3 + L4          (€)   ← stesso codice, scope diverso
Asset Global   = L2* + L1° + L3° + L4°      (%)   *primario  °ridotto
```

La scomposizione diventa così una conseguenza della tesi, non una scelta di stile — ed
è verificabile: se un pannello non appartiene a un livello, non deve esistere.

### 3.3 Asset Global non ha bisogno dello shock ipotetico

Il replay storico in percentuale (*«come si sono comportati davvero questi tre ETF nel
2008»*) è un confronto genuino. Lo shock ipotetico senza pesi è invece quasi
tautologico: riscrive l'input in forma diversa.

---

## 4. Correzioni necessarie su Asset Global

Dallo stato verificato in [`00-analisi-stato-attuale.md`](./00-analisi-stato-attuale.md),
lacune 3-5.

| # | Problema | Direzione |
|---|---|---|
| 1 | 🔴 Il filtro broker costruisce **solo il set**, senza pesi, con la stessa etichetta di Broker Detail dove i pesi ci sono | Rinominare in senso esplicito (*«precarica gli asset di…»*) e non mostrare **mai** euro in questa pagina |
| 2 | 🔴 Il default preseleziona **fino a 100 asset** → matrice 100×100 = 10.000 celle illeggibili | Default **vuoto o 2-3 asset**; il 100 resta un limite, non un punto di partenza |
| 3 | 🟡 Intitolata «Correlation» ma renderizza anche lo stress | Il titolo deve corrispondere al contenuto, o il contenuto al titolo |
| 4 | 🟡 Percentuali senza valuta, subito dopo aver visto euro in Dashboard | La regola dei pesi rende la differenza strutturale e visibile, non un disclaimer |

### Ipotesi ad alto rapporto valore/costo

Le tre tabelle hanno già la sincronizzazione delle colonne fra pannelli
(`mirrorColumnResize`, `additionalTableRefs`). Aggiungere **colonne di rischio** — 
volatilità annua, max drawdown, correlazione media col resto del set — trasformerebbe la
tabella in uno strumento di confronto **senza introdurre un solo grafico nuovo** e senza
uscire dal linguaggio percentuale.

Da valutare nel blocco UI/UX, non decisa qui.

---

## 5. Cosa resta fuori da questo giro

| Elemento | Motivo |
|---|---|
| **Asset Detail** | Parcheggiato in beta per decisione del developer. La sua lacuna principale è però già registrata: `risk_contribution` è `PORTFOLIO`-only, quindi la pagina non può oggi dire *«questo asset è il 6% del tuo capitale ma il 19% del tuo rischio»* — il dato più prezioso che potrebbe mostrare. |
| **Home risk card** | Dipendeva dalla catena G6, ora abbandonata. Da riconsiderare solo a valle. |
| **Segnali rolling** | Restano nella Overview di Asset Detail, invariati. |

---

## 6. Prossimo blocco

**UI/UX per zona e scelta delle rappresentazioni grafiche.** La mappa stabilisce *cosa*
va dove; il blocco successivo stabilisce *come* viene mostrato — quali grafici, quali
primitive riusate, quale gerarchia visiva, quale progressive disclosure.

Solo dopo si scrive il piano esecutivo.
