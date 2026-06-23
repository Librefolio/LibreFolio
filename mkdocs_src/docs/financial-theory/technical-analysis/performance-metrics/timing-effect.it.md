# ⏱️ Effetto Timing

*[⬅️ Torna alla Panoramica delle Metriche di Performance](index.md)*

## 💡 Cos'è?

L'**Effetto Timing** misura quanto il momento e l'importo dei versamenti e dei prelievi hanno inciso sul rendimento personale dell'investitore rispetto al rendimento della strategia sottostante, neutralizzando l’effetto dei flussi di cassa esterni.

Viene calcolato come differenza tra il rendimento cumulativo ponderato per il denaro (MWRR) e il rendimento cumulativo ponderato per il tempo (TWRR):

$$
\text{Effetto Timing} = \text{MWRR}_{\text{cumulativo}} - \text{TWRR}_{\text{cumulativo}}
$$

Si esprime in **punti percentuali (pp)**.

---

## 🧮 Come interpretare l'Effetto Timing

Confrontando il [MWRR Cumulativo](mwrr.md#cumulative-mwrr) (che risente del timing dei flussi) con il [TWRR Cumulativo](twrr.md) (che neutralizza l'impatto dei flussi), l'Effetto Timing evidenzia la differenza tra rendimento personale dell’investitore e rendimento della strategia, attribuibile al timing e alla dimensione dei flussi di cassa:

- **Effetto Timing Positivo ($> 0$ pp):** I flussi di cassa sono avvenuti in momenti favorevoli (ad esempio, acquistando asset a sconto durante un ribasso del mercato). Il tuo rendimento personale (MWRR) è superiore a quello della strategia pura (TWRR).
- **Effetto Timing Negativo ($< 0$ pp):** I flussi di cassa sono avvenuti in momenti sfavorevoli (ad esempio, depositando ingenti somme ai massimi di mercato, subito prima di una correzione). Il tuo rendimento personale (MWRR) è inferiore a quello della strategia pura (TWRR).
- **Effetto Timing vicino allo Zero ($\approx 0$ pp):** I flussi di cassa hanno avuto un impatto minimo sulla performance (ad esempio, in caso di versamenti molto piccoli o se il mercato è rimasto piatto durante le transazioni).

---

## 🔢 Esempi Numerici

### Esempio 1: Effetto Timing Positivo (Flussi Favorevoli)
* **TWRR Cumulativo (Rendimento Strategia):** $+20\%$
* **MWRR Cumulativo (Rendimento Investitore):** $+28\%$

$$
\text{Effetto Timing} = 28\% - 20\% = +8\text{ pp}
$$

* **Interpretazione:** La strategia degli asset sottostanti ha generato un rendimento del $+20\%$. Tuttavia, poiché hai aggiunto una quota significativa di capitale al portafoglio prima che il mercato salisse, il tuo rendimento personale ponderato per il denaro è salito al $+28\%$. Il timing e la dimensione dei tuoi versamenti hanno contribuito positivamente per **$+8$ punti percentuali** di rendimento aggiuntivo.

### Esempio 2: Effetto Timing Negativo (Flussi Sfavorevoli)
* **TWRR Cumulativo (Rendimento Strategia):** $+20\%$
* **MWRR Cumulativo (Rendimento Investitore):** $+12\%$

$$
\text{Effetto Timing} = 12\% - 20\% = -8\text{ pp}
$$

* **Interpretazione:** La strategia ha generato un rendimento del $+20\%$. Tuttavia, hai versato una parte significativa di capitale vicino ai massimi di mercato, poco prima di una discesa. Questo ha fatto sì che una quota maggiore del tuo denaro fosse esposta alla fase di calo, riducendo il tuo rendimento personale al $+12\%$. Il timing dei flussi ha ridotto il tuo rendimento di **$-8$ punti percentuali**.

---

## ⚖️ Cosa Cattura e Cosa Non Cattura

### Cosa Cattura
- **Impatto del timing dei versamenti/prelievi:** Se hai aggiunto liquidità durante i minimi di mercato (acquistando a sconto) o i massimi (acquistando a caro prezzo).
- **Impatto della dimensione dei flussi:** I flussi di cassa più grandi hanno un peso maggiore nel calcolo del MWRR, e l'Effetto Timing riflette questa dinamica.
- **L'"Investor Gap":** la distanza tra il rendimento della strategia e il rendimento effettivamente ottenuto dall’investitore, dovuta al timing e alla dimensione dei flussi.

### Cosa Non Cattura
- **Profitto monetario assoluto:** Un Effetto Timing positivo di $+5$ pp può esistere anche se il portafoglio è in perdita (ad esempio, se il TWRR è al $-20\%$ e il MWRR al $-15\%$). Per valutare il guadagno in valuta, consulta il [P&L del Periodo](period-pnl.md).
- **Rischio e volatilità:** Non fornisce indicazioni sul profilo di rischio o sulla volatilità degli asset.
- **Impatto disaggregato di tasse e costi:** l'Effetto Timing non scompone tasse e costi; eventuali costi e tasse possono essere mostrati separatamente nel P&L del periodo.
- **Qualità intrinseca della strategia:** Un Effetto Timing elevato può verificarsi anche su un asset scadente se lo si acquista subito prima di un rimbalzo temporaneo. Controlla sempre il [TWRR](twrr.md) per giudicare la bontà degli asset.

---

## 🖥️ Uso nella Dashboard
LibreFolio mostra l'Effetto Timing all'interno della card **Rendimenti** della dashboard. Questa scheda riassume i principali indicatori delle performance del tuo portafoglio:

- **Effetto Timing:** Differenza tra MWRR cumulativo e TWRR cumulativo, che mostra l'impatto del timing e della dimensione dei flussi.
- **ROI Semplice:** rendimento percentuale intuitivo del periodo. È utile per leggere rapidamente il risultato, ma non considera il timing dei flussi con la stessa precisione del MWRR.
- **TWRR Cumulativo:** Il rendimento della strategia sottostante, neutralizzando i flussi di cassa.
- **MWRR Cumulativo:** Il rendimento del capitale reale, considerando i flussi di cassa.
- **MWRR Annualizzato:** La velocità annua composta con cui è cresciuto il tuo capitale.

!!! note "Tooltip Sintetico"

    Differenza tra MWRR cumulativo e TWRR cumulativo. Mostra quanto il timing e l'importo dei flussi hanno inciso sul rendimento complessivo.


---

## 🔗 Relazione con le altre Metriche

- **[ROI Semplice](roi.md):** Misura il guadagno o la perdita percentuale in rapporto al capitale investito.
- **[TWRR](twrr.md):** Misura il rendimento della strategia o degli asset neutralizzando il timing dei flussi.
- **[MWRR](mwrr.md):** Misura il rendimento del capitale considerando importi e timing dei flussi.
- **[P&L del Periodo](period-pnl.md):** Misura il profitto o la perdita in termini monetari assoluti generati nel periodo.
