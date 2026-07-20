# 📈 Metriche di Performance

Quando si valuta il successo di un portafoglio di investimenti, osservare solo il saldo totale o il profitto assoluto non è sufficiente. Per comprendere veramente la performance, sono necessarie metriche standardizzate che rispondano a domande diverse: "Come si sono comportati i miei asset?", "Quanto è stato buono il mio tempismo?" e "Qual è il rendimento su questa specifica operazione?".

---

## 🎭 I Due Attori nel Tuo Portafoglio

Per capire perché esistono molteplici metriche, immagina che ci siano due diversi "attori" che gestiscono la tua ricchezza:

1. **Il Mercato (Gli Asset):** Causa l'aumento o la diminuzione dei prezzi delle cose che possiedi.
2. **Tu (L'Investitore):** Decidi *quando* depositare o prelevare denaro dal portafoglio.

Questi due attori possono avere performance molto diverse. Potresti selezionare un'azione eccellente (Il Mercato si comporta bene), ma potresti acquistarla al massimo storico appena prima di un crollo (Tu ti comporti male). LibreFolio utilizza metriche diverse per isolare questi due comportamenti.

---

## 📚 Argomenti in Questo Capitolo

Le metriche di performance di LibreFolio sono organizzate attorno a tre motori di calcolo. Ciascuno ha la propria pagina di panoramica con il modello matematico completo.

### ⚙️ Motore del Portafoglio (Portfolio Engine)

Contabilità aggregata basata sul Prezzo Medio di Carico (PMC) per l'intero portafoglio (o per qualsiasi ambito broker/asset).

| Metrica / Concetto | Descrizione |
|-------------------|-------------|
| **[Panoramica del Motore del Portafoglio](portfolio-engine/index.md)** | Modello matematico completo: catena di valutazione, PMC, aggregazione, modello a 3 pool, contribuzione, architettura pre-frame/frame. |
| **[Valore Patrimoniale Netto (NAV)](portfolio-engine/nav.md)** | Valutazione di mercato totale del portafoglio (asset + liquidità + in-transito). Utilizza la catena di valutazione: Prezzo di Mercato → Ultimo Prezzo di Acquisto → Mancante. |
| **[Costo Contabile (Book Value)](portfolio-engine/book-value.md)** | Costo storico contabile delle posizioni aperte (PMC × quantità) più liquidità. La differenza dal NAV = P&L non realizzato. |
| **[P&L di Periodo](portfolio-engine/period-pnl.md)** | Profitto/perdita monetario in un intervallo, aggiustato per i flussi di cassa. Si decompone in: delta non realizzato + realizzato + reddito − commissioni. Include l'attribuzione del contributo per singolo asset. |
| **[Capitale Depositato e P&L Totale](portfolio-engine/deposited-capital.md)** | Capitale esterno netto dall'inizio. Documenta il modello di scomposizione della cassa **basato su eventi a 3 pool** (K, R, W) con regole formali di aggiornamento a livello di transazione. |
| **[Effetto di Tempismo](portfolio-engine/timing-effect.md)** | Differenza tra MWRR Cumulativo e TWRR Cumulativo — quantifica l'impatto della tempistica dei flussi di cassa sui rendimenti. |
| **[ROI Semplice](portfolio-engine/roi.md)** | Rendimento percentuale rispetto al capitale netto investito. Semplice ma soggetto a diluizione da flussi di cassa. |
| **[TWRR](portfolio-engine/twrr.md)** | Tasso di Rendimento Ponderato nel Tempo. Performance pura dell'asset/della strategia, neutralizzando la tempistica di depositi/prelievi. |
| **[MWRR (XIRR)](portfolio-engine/mwrr.md)** | Tasso di Rendimento Ponderato dal Capitale. Performance personale dell'investitore che considera la tempistica dei flussi di cassa. Forme Annualizzata e Cumulativa. |

### 🔬 Motore FIFO

Contabilità per lotto: tiene traccia di ogni lotto di acquisizione attraverso il proprio ciclo di vita invece di fonderlo in un'unica media.

| Metrica / Concetto | Descrizione |
|-------------------|-------------|
| **[Panoramica del Motore FIFO](fifo-engine/index.md)** | Stati del ciclo di vita del lotto, elaborazione cronologica degli eventi, abbinamento FIFO, frazionamenti e trasferimenti tra broker. |
| **[Analisi dei Lotti FIFO](fifo-engine/fifo-lot-analysis.md)** | Complemento per lotto al PMC: tiene traccia di ogni lotto di acquisizione attraverso il proprio ciclo di vita, abbina le vendite in ordine FIFO e calcola il rendimento aperto/totale per lotto. |

### Prezzo Medio di Carico (Weighted Average Cost)

| Metrica / Concetto | Descrizione |
|-------------------|-------------|
| **[Prezzo Medio di Carico](weighted-average-cost.md)** | PMC iterativo con consapevolezza dell'inventario per posizione (broker, asset). Calcolato in linea durante il ciclo giornaliero del motore. |

---

## ⚖️ Guida al Confronto delle Metriche

Per aiutarti a scegliere la metrica giusta per la tua analisi, utilizza questa guida comparativa:

### 1. [Valore Patrimoniale Netto (NAV) / Patrimonio Netto](portfolio-engine/nav.md)
* **Domanda Principale:** "Quanto vale in questo momento il portafoglio nell'ambito selezionato?"
* **Concetto della Formula:** $\text{Valore di Mercato} + \text{Liquidità} + \text{Asset In Transito}$ alla fine del periodo.
* **Miglior Caso d'Uso:** Istantanea della ricchezza assoluta alla data di fine selezionata (`date_to`).

### 2. [Costo Contabile (Book Value)](portfolio-engine/book-value.md)
* **Domanda Principale:** "Quanto è costato costruire il mio attuale portafoglio?"
* **Concetto della Formula:** $\text{Base di Costo Aperta} + \text{Liquidità} + \text{Valore Contabile In Transito}$ utilizzando il Prezzo Medio di Carico (PMC).
* **Miglior Caso d'Uso:** Valutare i costi di acquisizione e confrontarli con il valore di mercato corrente (NAV) per trovare plusvalenze latenti.

### 3. [P&L di Periodo](portfolio-engine/period-pnl.md)
* **Domanda Principale:** "Quanti soldi ho effettivamente guadagnato o perso durante questo periodo?"
* **Concetto della Formula:** $\text{NAV}_{\text{fine}} - \text{NAV}_{\text{inizio}} - \text{Flussi Esterni Netti}$.
* **Miglior Caso d'Uso:** Misurare i guadagni di periodo in valuta assoluta, indipendentemente da iniezioni/prelievi di cassa dell'investitore.

### 4. [Effetto di Tempismo](portfolio-engine/timing-effect.md)
* **Domanda Principale:** "In che modo la tempistica e l'entità dei miei flussi di cassa hanno influenzato il mio rendimento complessivo rispetto a una strategia di acquisto e mantenimento (buy-and-hold)?"
* **Concetto della Formula:** $\text{MWRR}_{\text{cumulativo}} - \text{TWRR}_{\text{cumulativo}}$.
* **Miglior Caso d'Uso:** Diagnosticare se depositi e prelievi hanno aggiunto valore ($>0$ pp) o hanno penalizzato la performance ($<0$ pp).

### 5. [ROI Semplice](portfolio-engine/roi.md)
* **Domanda Principale:** "Quanto ho guadagnato rispetto al capitale netto che ho investito?"
* **Denominatore della Formula:** Prezzo Medio di Carico (PMC).
* **Limitazioni:** Non considera *quando* si sono verificati i flussi di cassa, portando a diluizione da flussi di cassa quando si acquistano successivamente più quote di un asset.

### 6. [TWRR (Tasso di Rendimento Ponderato nel Tempo)](portfolio-engine/twrr.md)
* **Domanda Principale:** "Come si è comportata la mia allocazione/strategia di asset scelta, ignorando la mia tempistica di cassa?"
* **Concetto della Formula:** Suddivide la linea temporale in corrispondenza di ogni flusso di cassa, calcola i rendimenti dei sotto-periodi e li moltiplica.
* **Miglior Caso d'Uso:** Confrontare la tua performance con benchmark esterni (come l'S&P 500) o valutare la performance pura degli asset.

### 7. [MWRR Annualizzato (Tasso di Rendimento Ponderato dal Capitale)](portfolio-engine/mwrr.md#annualized-mwrr)
* **Domanda Principale:** "A quale tasso annuale composto è cresciuto il mio capitale effettivo, considerando i miei depositi e prelievi?"
* **Concetto della Formula:** Risolve il tasso di rendimento interno ($r$) che azzera il valore attuale netto di tutti i flussi di cassa.
* **Miglior Caso d'Uso:** Confrontare la tua performance personale con i tassi di interesse a lungo termine o valutare la crescita composta su lunghi orizzonti temporali. Può essere altamente volatile su finestre brevi.

### 8. [MWRR Cumulativo](portfolio-engine/mwrr.md#cumulative-mwrr)
* **Domanda Principale:** "Qual è il rendimento cumulativo equivalente ponderato dal capitale su questa finestra temporale selezionata?"
* **Concetto della Formula:** Compone il MWRR annualizzato per il numero effettivo di giorni trascorsi.
* **Miglior Caso d'Uso:** Grafici seriali e widget della dashboard per confrontare visivamente l'andamento delle performance affiancate con TWRR e ROI.

---

## 💡 L'Esempio Pratico (TWRR vs MWRR vs ROI)

Analizziamo un esempio estremo per vedere come TWRR, MWRR e ROI Semplice raccontano storie diverse, ma matematicamente corrette.

* **Mese 1:** Acquisti **€1.000** di un'azione. Il mese successivo, l'azione raddoppia (+100%). Ora hai **€2.000**.
* **Mese 2:** Depositi altri **€100.000** nella stessa identica azione. Ora hai €102.000 investiti.
* **Mese 3:** L'azione scende del **-10%**. Il tuo capitale totale scende a **€91.800**.

Ecco cosa calcolerà LibreFolio per questo scenario:

### TWRR Cumulativo: +80,00%
Gli asset che hai scelto sono aumentati del +100%, poi sono scesi del -10%. Matematicamente:

$$
(1 + 1,00) \times (1 - 0,10) - 1 = +80,00\%
$$

Questo isola la performance pura dell'azione. La tua *selezione di asset* è stata eccellente. Se avessi investito tutti i tuoi soldi il giorno 1, avresti ottenuto un rendimento dell'80%.

### ROI Semplice: -9,11%
Hai depositato un totale di €101.000 di tasca tua (€1.000 + €100.000), ma attualmente possiedi €91.800:

$$
ROI = \frac{91.800 - 101.000}{101.000} = -9,11\%
$$

Questo rappresenta il tuo guadagno/perdita reale e grezzo rispetto al tuo capitale netto investito.

### MWRR Cumulativo: -16,99%
Poiché hai depositato €100.000 proprio al picco prima di un calo, il tuo tempismo ha penalizzato significativamente il tuo rendimento:

$$
\text{MWRR}_{\text{cumulativo}} \approx -16,99\%
$$

Questo rendimento cumulativo ponderato dal capitale rappresenta la performance di un "euro teorico" soggetto alla tua effettiva tempistica dei flussi di cassa.

### MWRR Annualizzato: -67,19%
Poiché il calo sostanziale si è verificato in un arco di tempo molto breve (31 giorni) su una base di capitale massiccia (€100.000), il tasso di perdita composto annualizzato è molto alto:

$$
\text{MWRR}_{\text{annualizzato}} \approx -67,19\%
$$

Questo rappresenta la velocità annualizzata della perdita di capitale in questa specifica finestra temporale.

---

## ⚖️ Perché LibreFolio li mostra entrambi affiancati

Posizionando TWRR e MWRR uno accanto all'altro sulla tua Dashboard, LibreFolio ti fornisce una diagnosi comportamentale immediata:

* **TWRR > MWRR:** *"Stai selezionando buoni investimenti, ma il tuo tempismo è cattivo. È probabile che tu stia acquistando ai massimi (FOMO) e questo sta penalizzando i tuoi rendimenti personali."*
* **MWRR > TWRR:** *"Hai un tempismo eccellente! Stai acquistando asset a sconto quando il mercato scende, aumentando i tuoi rendimenti personali al di sopra della media del mercato."*

---

## 🔗 Integrazione UI e Collegamenti di Aiuto della Dashboard

Per facilitare la navigazione, la dashboard di LibreFolio presenta icone di aiuto e collegamenti adiacenti a ciascuna metrica. Cliccando su questi collegamenti si viene reindirizzati direttamente al capitolo teorico finanziario pertinente:

* I widget **Patrimonio Netto (NAV)** collegano direttamente alla pagina [NAV / Patrimonio Netto](portfolio-engine/nav.md).
* I campi **Costo Contabile (Book Value)** collegano direttamente alla pagina [Costo Contabile](portfolio-engine/book-value.md).
* I widget **P&L di Periodo** collegano direttamente alla pagina [P&L di Periodo](portfolio-engine/period-pnl.md).
* I widget **Effetto di Tempismo** collegano direttamente alla pagina [Effetto di Tempismo](portfolio-engine/timing-effect.md).
* I widget **ROI** collegano direttamente alla pagina [ROI Semplice](portfolio-engine/roi.md).
* I widget **TWRR** collegano direttamente alla pagina [TWRR](portfolio-engine/twrr.md).
* I widget **MWRR** collegano direttamente alla pagina [MWRR](portfolio-engine/mwrr.md).
* **Capitale Depositato / P&L Totale** (suggerimento del Grafico di Crescita) collega alla pagina [Capitale Depositato e P&L Totale](portfolio-engine/deposited-capital.md).
