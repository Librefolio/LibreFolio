# 📈 Metriche di Performance

Quando si valuta il successo di un portafoglio d'investimento, guardare solo al saldo totale o al profitto assoluto non è sufficiente. Per comprendere appieno le performance, sono necessarie metriche standardizzate che rispondano a domande diverse: "Come hanno performato i miei asset?", "Quanto è stato buono il mio tempismo (timing)?" e "Qual è il rendimento di questa specifica operazione?".

---

## 🎭 I Due Attori nel Tuo Portafoglio

Per capire perché esistono più metriche, immagina che ci siano due diversi "attori" che gestiscono il tuo patrimonio:

1. **Il Mercato (Gli Asset):** Fa salire o scendere i prezzi degli strumenti che possiedi.
2. **Tu (L'Investitore):** Decidi *quando* depositare o prelevare liquidità dal portafoglio.

Questi due attori possono avere performance molto diverse. Potresti scegliere un ottimo titolo (il Mercato performa bene), ma potresti acquistarlo proprio sui massimi prima di un crollo (tu performi male). LibreFolio utilizza metriche diverse per isolare questi due comportamenti.

---

## 📚 Argomenti in Questo Capitolo

| Metrica / Concetto | Descrizione |
|--------------------|-------------|
| **[ROI Semplice](roi.md)** | Rendimento percentuale assoluto generato da un investimento rispetto al suo costo. Ideale per valutare singole posizioni. |
| **[TWRR](twrr.md)** | Rendimento Ponderato nel Tempo (Time-Weighted Rate of Return). Misura la performance pura degli asset sottostanti, ignorando il timing dei flussi di cassa. |
| **[MWRR (XIRR)](mwrr.md)** | Rendimento Ponderato per il Capitale (Money-Weighted Rate of Return). Misura la tua performance personale come investitore, tenendo conto del timing dei flussi di cassa. Copre sia la forma **Annualizzata** sia quella **Cumulativa**. |
| **[Costo Medio Ponderato](weighted-average-cost.md)** | Il costo unitario medio di un asset in portafoglio, ponderato per le quantità acquistate. |

---

## ⚖️ Guida Comparativa delle Metriche

Per aiutarti a scegliere la metrica corretta per la tua analisi, consulta questa guida comparativa:

### 1. [ROI Semplice](roi.md)
* **Domanda Chiave:** "Quanto ho guadagnato rispetto al capitale netto che ho investito?"
* **Denominatore della Formula:** Prezzo di Carico Medio (PCM).
* **Limiti:** Non tiene conto di *quando* si sono verificati i flussi di cassa, il che può portare alla diluizione del ROI in caso di acquisti successivi di uno stesso asset.

### 2. [TWRR (Rendimento Ponderato nel Tempo)](twrr.md)
* **Domanda Chiave:** "Come ha performato la mia strategia o allocazione di asset, ignorando il timing dei miei versamenti?"
* **Concetto della Formula:** Spezza la linea temporale ad ogni flusso di cassa, calcola i rendimenti dei sotto-periodi e li moltiplica.
* **Miglior Caso d'Uso:** Confrontare le tue performance con benchmark esterni (come l'S&P 500) o valutare la bontà degli asset selezionati in sé.

### 3. [MWRR Annualizzato (Rendimento Ponderato per il Capitale)](mwrr.md#annualized-mwrr)
* **Domanda Chiave:** "A quale tasso annuo composto è cresciuto il mio capitale reale, considerando i miei depositi e prelievi?"
* **Concetto della Formula:** Calcola il tasso interno di rendimento ($r$) che azzera il valore attuale netto di tutti i flussi di cassa.
* **Miglior Caso d'Uso:** Confrontare la tua performance personale con i tassi di interesse a lungo termine o valutare la crescita composta su orizzonti temporali lunghi. Può essere molto volatile su periodi brevi.

### 4. [MWRR Cumulativo](mwrr.md#cumulative-mwrr)
* **Domanda Chiave:** "Qual è il rendimento cumulativo equivalente ponderato per il capitale per la finestra temporale selezionata?"
* **Concetto della Formula:** Capitalizza il MWRR annualizzato per il numero effettivo di giorni trascorsi.
* **Miglior Caso d'Uso:** Grafici storici seriali e widget della dashboard per confrontare visivamente l'andamento della performance affiancandolo a TWRR e ROI.

---

## 💡 L'Esempio Pratico (TWRR vs MWRR vs ROI)

Vediamo un esempio estremo per capire come TWRR, MWRR e ROI Semplice raccontino storie diverse, ma matematicamente corrette.

* **Mese 1:** Acquisti **1.000 €** di un'azione. Il mese successivo, l'azione raddoppia (+100%). Ora hai **2.000 €**.
* **Mese 2:** Depositi altri **100.000 €** nella stessa identica azione. Ora hai 102.000 € investiti.
* **Mese 3:** L'azione scende del **-10%**. Il tuo capitale totale scende a **91.800 €**.

Ecco cosa calcolerà LibreFolio per questo scenario:

### TWRR Cumulativo: +80,00%
Gli asset che hai scelto sono saliti del +100% e poi scesi del -10%. Matematicamente:

$$
(1 + 1,00) \times (1 - 0,10) - 1 = +80,00\%
$$

Questo isola la performance pura dell'azione. La tua selezione degli asset (*asset picking*) è stata eccellente. Se avessi investito tutto il capitale il primo giorno, avresti ottenuto un rendimento dell'80%.

### ROI Semplice: -9,11%
Hai versato un totale di 101.000 € di tasca tua (1.000 € + 100.000 €), ma attualmente il portafoglio vale 91.800 €:

$$
ROI = \frac{91.800 - 101.000}{101.000} = -9,11\%
$$

Questo rappresenta il guadagno o la perdita reale del tuo portafoglio rispetto al capitale netto investito.

### MWRR Cumulativo: -16,99%
Poiché hai depositato 100.000 € proprio sui massimi prima del calo, il tempismo dei tuoi flussi ha penalizzato pesantemente il rendimento:

$$
\text{MWRR}_{\text{cumulativo}} \approx -16,99\%
$$

Questo rendimento cumulativo ponderato per il capitale rappresenta la performance di un "euro teorico" soggetto alla tempistica dei tuoi flussi di cassa reali.

### MWRR Annualizzato: -67,19%
Poiché il forte calo si è verificato in una finestra temporale molto breve (31 giorni) su una base di capitale enorme (100.000 €), il tasso composto annuo di perdita è estremamente elevato:

$$
\text{MWRR}_{\text{annualizzato}} \approx -67,19\%
$$

Questo rappresenta la velocità annualizzata di perdita del capitale in questa specifica finestra temporale.

---

## ⚖️ Perché LibreFolio mostra entrambi affiancati

Posizionando TWRR e MWRR uno accanto all'altro nella dashboard, LibreFolio ti fornisce un'immediata diagnosi comportamentale:

* **TWRR > MWRR:** *"Scegli buoni investimenti, ma il tuo timing è sbagliato. Probabilmente stai acquistando ai massimi (FOMO) e stai penalizzando i tuoi rendimenti personali."*
* **MWRR > TWRR:** *"Hai un timing eccellente! Stai acquistando asset a prezzi scontati quando il mercato scende, portando i tuoi rendimenti personali al di sopra della media di mercato."*

---

## 🔗 Integrazione UI e Link di Aiuto nella Dashboard

Per facilitare la navigazione, la dashboard di LibreFolio presenta icone e link di aiuto accanto a ciascuna metrica. Cliccando su questi link verrai reindirizzato direttamente al relativo capitolo della teoria finanziaria:

* I widget del **ROI** collegano direttamente alla [Pagina del ROI Semplice](roi.md).
* I widget del **TWRR** collegano direttamente alla [Pagina del TWRR](twrr.md).
* I widget del **MWRR** collegano direttamente alla [Pagina del MWRR](mwrr.md).
