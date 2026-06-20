# 📈 Metriche di Performance

Quando si valuta il successo di un portafoglio di investimenti, guardare solo il saldo totale o il profitto assoluto non è sufficiente. Per comprendere davvero le performance, sono necessarie metriche standardizzate che rispondano a domande diverse: "Come hanno performato i miei asset?", "Quanto è stato buono il mio timing?" e "Qual è il rendimento di questo specifico trade?".

---

## 🎭 I Due Attori nel Tuo Portafoglio

Per capire perché esistono più metriche, immagina che ci siano due "attori" diversi che gestiscono la tua ricchezza:

1. **Il Mercato (Gli Asset):** Causa l'aumento o la diminuzione dei prezzi dei tuoi asset.
2. **Tu (L'Investitore):** Decidi *quando* depositare o prelevare liquidità dal portafoglio.

Questi due attori possono avere performance molto diverse. Potresti scegliere un titolo eccellente (Il Mercato performa bene), ma potresti acquistarlo proprio al massimo subito prima di un crollo (le tue performance sono scarse). LibreFolio utilizza metriche diverse per isolare questi due comportamenti.

---

## 📚 Argomenti in questo Capitolo

| Metrica / Concetto | Descrizione |
|------------------|-------------|
| **[ROI Semplice](roi.md)** | Rendimento percentuale assoluto generato da un investimento rispetto al suo costo. Ideale per valutare singole posizioni. |
| **[TWRR](twrr.md)** | Time-Weighted Rate of Return (Rendimento Ponderato nel Tempo). Misura la performance pura degli asset sottostanti, ignorando il timing dei flussi di cassa. |
| **[MWRR (XIRR)](mwrr.md)** | Money-Weighted Rate of Return (Rendimento Ponderato per il Capitale). Misura la tua performance personale come investitore, tenendo conto del timing dei flussi di cassa. |
| **[Costo Medio Ponderato](weighted-average-cost.md)** | Il costo unitario medio di un asset in un portafoglio, ponderato per le quantità acquisite. |

---

## 💡 L'Esempio Pratico (TWRR vs MWRR)

Vediamo un esempio estremo per capire come [TWRR](twrr.md) e [MWRR](mwrr.md) raccontino due storie completamente diverse, ma matematicamente corrette.

* **Mese 1:** Hai un ottimo intuito. Acquisti per **€1.000** di un titolo. Il mese successivo, il titolo raddoppia (+100%). Ora hai **€2.000**.
* **Mese 2:** Trascinato dall'entusiasmo, svuoti il tuo conto risparmio e depositi altri **€100.000** nello stesso identico titolo. Ora hai €102.000 investiti.
* **Mese 3:** Sfortunatamente, il titolo scende del **-10%**. Il tuo capitale totale scende da €102.000 a **€91.800**.

Se guardassi LibreFolio ora, cosa vedresti?

### 📈 Il tuo TWRR sarà: +80%
*Perché?* Gli asset che hai scelto sono saliti del +100% e poi sono scesi del -10%. Matematicamente: 

$$
(2.0 \times 0.9) - 1 = +0.8
$$

Gli asset scelti hanno performato incredibilmente bene. Se avessi investito tutti i tuoi soldi il primo giorno, saresti ricco. La tua *scelta degli asset* è stata eccellente.

### 📉 Il tuo MWRR sarà: FORTEMENTE NEGATIVO (circa -9%)
*Perché?* Hai depositato un totale di €101.000 di tasca tua, ma attualmente possiedi €91.800. Hai subito una perdita reale e assoluta di €9.200! 
Il tuo pessimo timing — depositare €100.000 proprio al picco prima di un calo — ha distrutto i tuoi rendimenti. Il tuo *timing* è stato terribile.

---

## ⚖️ Perché LibreFolio mostra entrambi affiancati

Posizionando TWRR e MWRR uno accanto all'altro nella dashboard, LibreFolio ti fornisce un'immediata diagnosi comportamentale:

- **TWRR > MWRR:** *"Scegli buoni investimenti, ma il tuo timing è sbagliato. Probabilmente stai comprando ai massimi (FOMO) e stai penalizzando i tuoi rendimenti personali."*
- **MWRR > TWRR:** *"Hai un timing eccellente! Stai acquistando asset a prezzi scontati quando il mercato scende, portando i tuoi rendimenti personali al di sopra della media di mercato."*
