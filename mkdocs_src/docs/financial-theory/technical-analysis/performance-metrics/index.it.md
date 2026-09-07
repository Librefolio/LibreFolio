# 📈 Metriche di Performance

Quando si valuta il successo di un portafoglio di investimenti, osservare solo il saldo totale o il profitto assoluto non è sufficiente. Per comprendere davvero la performance, servono metriche standardizzate che rispondano a domande diverse: "Come si sono comportati i miei asset?", "Quanto è stato buono il mio tempismo?" e "Qual è il rendimento di questa specifica operazione?".

---

## 🎭 I Due Attori nel Tuo Portafoglio

Per capire perché esistono più metriche, immagina che ci siano due diversi "attori" che gestiscono la tua ricchezza:

1. **Il Mercato (Gli Asset):** Fa salire o scendere i prezzi delle cose che possiedi.
2. **Tu (L'Investitore):** Decidi *quando* depositare o prelevare contante dal portafoglio.

Questi due attori possono avere performance molto diverse. Potresti scegliere un'azione eccellente (il Mercato si comporta bene), ma potresti acquistarla proprio al massimo, poco prima di un crollo (tu invece hai avuto una performance negativa). LibreFolio utilizza metriche diverse per isolare questi due comportamenti.

---

## 📚 Argomenti in Questo Capitolo

Le metriche di performance di LibreFolio sono organizzate attorno a tre motori di calcolo. Ciascuno ha la propria pagina di panoramica con il modello matematico completo.

### ⚙️ Motore di Portafoglio

Contabilità aggregata basata su PMC per l'intero portafoglio (o qualsiasi ambito broker/asset).

| Metrica / Concetto | Descrizione |
|------------------|-------------|
| **[Panoramica del Motore di Portafoglio](portfolio-engine/index.md)** | Modello matematico completo: resolver unificato dei prezzi, PMC, aggregazione, modello a 3 pool, contribuzione, architettura pre-frame/frame. |
| **[Risoluzione dei Prezzi](portfolio-engine/price-resolution.md)** | Livelli del resolver unificato: MARKET → TRADE_AVG → CARRIED → MISSING, con mark nativi e FX per data. |
| **[Valore Patrimoniale Netto (NAV)](portfolio-engine/nav.md)** | Valutazione di mercato totale del portafoglio (asset + contante + in transito), utilizzando il resolver unificato. |
| **[Valore Contabile](portfolio-engine/book-value.md)** | Costo contabile storico delle posizioni aperte (PMC × quantità) più contante. Differenza dal NAV = P&L non realizzato. |
| **[P&L di Periodo](portfolio-engine/period-pnl.md)** | Profitto/perdita monetario rettificato per i flussi di cassa in un intervallo. Si scompone in: delta non realizzato + realizzato + reddito − commissioni. Include l'attribuzione del contributo per singolo asset. |
| **[Capitale Depositato e P&L Totale](portfolio-engine/deposited-capital.md)** | Capitale esterno netto dall'avvio. Documenta il modello di scomposizione della cassa **a 3 pool guidato dagli eventi** (K, R, W) con regole formali di aggiornamento a livello di transazione. |
| **[Effetto di Tempismo](portfolio-engine/timing-effect.md)** | Differenza tra MWRR Cumulativo e TWRR Cumulativo — quantifica l'impatto del tempismo dei flussi di cassa sui rendimenti. |
| **[ROI Semplice](portfolio-engine/roi.md)** | Rendimento percentuale rispetto al capitale investito netto. Semplice ma soggetto alla diluizione dei flussi di cassa. |
| **[Rendimento Annualizzato Netto](portfolio-engine/net-annualized-return.md)** | Definizioni del CAGR netto per posizioni, contributo di periodo e lotti FIFO, con finestra minima di 30 giorni. |
| **[TWRR](portfolio-engine/twrr.md)** | Tasso di Rendimento Ponderato nel Tempo. Performance pura di asset/strategia, che neutralizza il tempismo di depositi/prelievi. |
| **[MWRR (XIRR)](portfolio-engine/mwrr.md)** | Tasso di Rendimento Ponderato per il Capitale. Performance personale dell'investitore che tiene conto del tempismo dei flussi di cassa. Forme annualizzate e cumulative. |

### 🔬 Motore FIFO

Contabilità per lotto: tiene traccia di ogni lotto di acquisizione attraverso il proprio ciclo di vita invece di fonderlo in un'unica media.

| Metrica / Concetto | Descrizione |
|------------------|-------------|
| **[Panoramica del Motore FIFO](fifo-engine/index.md)** | Stati del ciclo di vita del lotto, elaborazione cronologica degli eventi, abbinamento FIFO, frazionamenti e trasferimenti tra broker. |
| **[Analisi dei Lotti FIFO](fifo-engine/fifo-lot-analysis.md)** | Complemento per lotto del PMC: tiene traccia di ogni lotto di acquisizione attraverso il proprio ciclo di vita, abbina le vendite in ordine FIFO e calcola il rendimento aperto/totale per lotto. |

### 📊 Prezzo Medio di Carico (PMC)

| Metrica / Concetto | Descrizione |
|------------------|-------------|
| **[Prezzo Medio di Carico (PMC)](weighted-average-cost.md)** | PMC iterativo sensibile all'inventario per posizione (broker, asset). Calcolato inline durante il ciclo giornaliero del motore. |

---

## ⚖️ Guida al Confronto delle Metriche

Per aiutarti a scegliere la metrica giusta per la tua analisi, utilizza questa guida al confronto:

### 💼 1. [Valore Patrimoniale Netto (NAV) / Patrimonio Netto](portfolio-engine/nav.md)
* **Domanda Chiave:** "Quanto vale in questo momento il portafoglio nell'ambito selezionato?"
* **Concetto della Formula:** $\text{Valore di Mercato} + \text{Contante} + \text{Asset in Transito}$ alla fine del periodo.
* **Caso d'Uso Ideale:** Istantanea della ricchezza assoluta alla data finale selezionata (`date_to`).

### 📖 2. [Valore Contabile](portfolio-engine/book-value.md)
* **Domanda Chiave:** "Quanto è costato costruire il mio portafoglio attuale?"
* **Concetto della Formula:** $\text{Costo di Carico Aperto} + \text{Contante} + \text{Valore Contabile in Transito}$ utilizzando il prezzo medio di carico (PMC).
* **Caso d'Uso Ideale:** Valutare i costi di acquisizione e confrontarli con il valore di mercato attuale (NAV) per individuare plusvalenze latenti.

### 📊 3. [P&L di Periodo](portfolio-engine/period-pnl.md)
* **Domanda Chiave:** "Quanti soldi ho effettivamente guadagnato o perso in questo periodo?"
* **Concetto della Formula:** $\text{NAV}_{\text{fine}} - \text{NAV}_{\text{inizio}} - \Delta\text{BaselineCapitale}$.
* **Caso d'Uso Ideale:** Misurare i guadagni di periodo in valuta assoluta, indipendentemente da iniezioni/prelievi di cassa dell'investitore.

### ⏱️ 4. [Effetto di Tempismo](portfolio-engine/timing-effect.md)
* **Domanda Chiave:** "In che modo il tempismo e l'entità dei miei flussi di cassa hanno influenzato il mio rendimento complessivo rispetto a una strategia buy-and-hold?"
* **Concetto della Formula:** $\text{MWRR}_{\text{cumulativo}} - \text{TWRR}_{\text{cumulativo}}$.
* **Caso d'Uso Ideale:** Diagnosticare se depositi e prelievi hanno aggiunto valore ($>0$ pp) o hanno trascinato al ribasso la performance ($<0$ pp).

### 📉 5. [ROI Semplice](portfolio-engine/roi.md)
* **Domanda Chiave:** "Quanto ho guadagnato rispetto al capitale netto che ho investito?"
* **Denominatore della Formula:** Baseline di capitale, incluso il capitale in natura valorizzato.
* **Limitazioni:** Non tiene conto di *quando* si sono verificati i flussi di cassa, portando a una diluizione dei flussi di cassa quando successivamente si acquistano ulteriori quantità dello stesso asset.

### ⏱️ 6. [TWRR (Tasso di Rendimento Ponderato nel Tempo)](portfolio-engine/twrr.md)
* **Domanda Chiave:** "Come si è comportata la mia asset allocation/strategia scelta, ignorando il mio tempismo di cassa?"
* **Concetto della Formula:** Spezza la linea temporale in corrispondenza di ogni flusso di cassa, calcola i rendimenti dei sottoperiodi e li moltiplica.
* **Caso d'Uso Ideale:** Confrontare la tua performance con benchmark esterni (come lo S&P 500) o valutare la performance pura degli asset.

### 📈 7. [MWRR Annualizzato (Tasso di Rendimento Ponderato per il Capitale)](portfolio-engine/mwrr.md#annualized-mwrr)
* **Domanda Chiave:** "A quale tasso annuo composto è cresciuto il mio capitale effettivo, considerando i miei depositi e prelievi?"
* **Concetto della Formula:** Risolve il tasso interno di rendimento ($r$) che porta il valore attuale netto di tutti i flussi di cassa a zero.
* **Caso d'Uso Ideale:** Confrontare la tua performance personale con i tassi di interesse a lungo termine o valutare la crescita composta su orizzonti lunghi. Può essere altamente volatile su finestre brevi.

### 📊 8. [MWRR Cumulativo](portfolio-engine/mwrr.md#cumulative-mwrr)
* **Domanda Chiave:** "Qual è il rendimento cumulativo equivalente ponderato per il capitale su questa finestra temporale selezionata?"
* **Concetto della Formula:** Compone il MWRR annualizzato per il numero effettivo di giorni trascorsi.
* **Caso d'Uso Ideale:** Grafici seriali e widget della dashboard per confrontare visivamente i trend di performance fianco a fianco con TWRR e ROI.

---

## 💡 L'Esempio Pratico (TWRR vs MWRR vs ROI)

Osserviamo un esempio estremo per vedere come TWRR, MWRR e ROI Semplice raccontino storie diverse, ma matematicamente corrette.

* **Mese 1:** Acquisti **€1.000** di un'azione. Il mese successivo, l'azione raddoppia (+100%). Ora hai **€2.000**.
* **Mese 2:** Depositi altri **€100.000** nella stessa identica azione. Ora hai investito €102.000.
* **Mese 3:** L'azione scende del **-10%**. Il tuo capitale totale scende a **€91.800**.

Ecco cosa calcolerà LibreFolio per questo scenario:

### 📊 TWRR Cumulativo: +80,00%

Gli asset che hai scelto sono saliti del +100% e poi sono scesi del -10%. Matematicamente:

$$
(1 + 1.00) \times (1 - 0.10) - 1 = +80.00\%
$$

Questo isola la performance pura dell'azione. La tua *selezione degli asset* è stata eccellente. Se avessi investito tutti i tuoi soldi il primo giorno, avresti ottenuto un rendimento dell'80%.

### 📉 ROI Semplice: -9,11%

Hai depositato un totale di €101.000 di tasca tua (€1.000 + €100.000), ma attualmente detieni €91.800:

$$
ROI = \frac{91,800 - 101,000}{101,000} = -9.11\%
$$

Questo rappresenta il tuo guadagno/perdita effettivo e non rettificato rispetto al capitale investito netto.

### 💵 MWRR Cumulativo: -16,99%

Poiché hai depositato €100.000 proprio al picco, poco prima di un calo, il tuo tempismo ha trascinato significativamente al ribasso il tuo rendimento:

$$
\text{MWRR}_{\text{cumulative}} \approx -16.99\%
$$

Questo rendimento cumulativo ponderato per il capitale rappresenta la performance di un "euro teorico" sottoposto al tuo effettivo tempismo dei flussi di cassa.

### 📈 MWRR Annualizzato: -67,19%

Poiché il calo sostanziale si è verificato in una finestra temporale molto breve (31 giorni) su una base di capitale molto ampia (€100.000), il tasso di perdita composto annualizzato è molto elevato:

$$
\text{MWRR}_{\text{annualized}} \approx -67.19\%
$$

Questo rappresenta la velocità annualizzata della perdita di capitale su questa specifica finestra.

---

## ⚖️ Perché LibreFolio mostra entrambi fianco a fianco

Collocando TWRR e MWRR fianco a fianco nella tua Dashboard, LibreFolio ti fornisce una diagnosi comportamentale immediata:

* **TWRR > MWRR:** *"Stai scegliendo buoni investimenti, ma il tuo tempismo è scarso. Probabilmente stai acquistando ai massimi (FOMO) e trascinando al ribasso i tuoi rendimenti personali."*
* **MWRR > TWRR:** *"Hai un tempismo eccellente! Stai acquistando asset a sconto quando il mercato scende, portando i tuoi rendimenti personali al di sopra della media di mercato."*

---

## 🔗 Integrazione UI e Collegamenti di Aiuto nella Dashboard

Per facilitare la navigazione, le tre card KPI nella dashboard di LibreFolio — **P&L di Periodo**, **Rendimenti** e **Patrimonio Netto** — hanno ciascuna un'icona di aiuto. Il percorso verso questi capitoli teorici è composto da due passaggi:

1. L'icona di aiuto apre la sezione corrispondente della pagina [KPI Cards](../../../user/dashboard/kpi-cards.md) della guida utente ([Card 1](../../../user/dashboard/kpi-cards.md#card-1-period-pl), [Card 2](../../../user/dashboard/kpi-cards.md#card-2-returns), [Card 3](../../../user/dashboard/kpi-cards.md#card-3-net-worth)).
2. Da lì, ogni metrica collega al proprio capitolo di teoria finanziaria: [P&L di Periodo](portfolio-engine/period-pnl.md), [Valore Contabile](portfolio-engine/book-value.md), [ROI](portfolio-engine/roi.md), [TWRR](portfolio-engine/twrr.md), [MWRR](portfolio-engine/mwrr.md), [Effetto di Tempismo](portfolio-engine/timing-effect.md), [NAV / Patrimonio Netto](portfolio-engine/nav.md), [Capitale Depositato e P&L Totale](portfolio-engine/deposited-capital.md).

Altrove nell'app, l'anteprima PMC nel modulo di transazione collega direttamente al capitolo [Prezzo Medio di Carico (PMC)](weighted-average-cost.md), e ogni segnale/indicatore dei grafici collega alla propria pagina di teoria.
