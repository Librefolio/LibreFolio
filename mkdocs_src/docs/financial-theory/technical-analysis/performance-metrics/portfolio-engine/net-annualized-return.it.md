# 📈 Rendimento annualizzato netto

## 💡 Scopo

LibreFolio riporta il rendimento annualizzato solo quando la finestra osservata è abbastanza lunga da rendere significativo l'interesse composto. La conversione condivisa è:

$$
\boxed{r_{\mathrm{ann}} = (1+r_{\mathrm{cum}})^{365/d}-1}
$$

dove $d$ è il numero di giorni di calendario. È l'inverso di:

$$
r_{\mathrm{cum}}=(1+r_{\mathrm{ann}})^{d/365}-1
$$

L'implementazione restituisce `None` quando:

- $r_{\mathrm{cum}} \leq -1$
- $d < 30$
- il calcolo va in overflow

!!! warning "Salvaguardia dei trenta giorni"

    Un rendimento di una settimana annualizzato a 365 giorni può esplodere in percentuali prive di significato. LibreFolio sopprime quindi l'annualizzazione sotto i 30 giorni e mostra un valore vuoto invece di un CAGR matematicamente corretto ma fuorviante.

## 🧾 Vista delle posizioni

Per una posizione aperta in “Le tue posizioni” / riepilogo del portafoglio:

$$
r_{\mathrm{net}} =
\frac{
\mathrm{MarketComponent}
+ \mathrm{Income}
- \mathrm{FeesTaxes}
}{
\mathrm{CostBasis}
}
$$

dove:

$$
\mathrm{MarketComponent} =
\begin{cases}
\mathrm{CurrentValue}-\mathrm{CostBasis}, & \text{esiste il valore di mercato}\\
0, & \text{senza prezzo / valutato al costo}
\end{cases}
$$

Finestra di annualizzazione:

$$
d = t_{\mathrm{report}} - t_{\mathrm{first\ lot\ affecting}}
$$

I tipi di transazione che influiscono sui lotti sono:

$$
\{\text{BUY},\ \text{SELL},\ \text{ADJUSTMENT},\ \text{TRANSFER}\}
$$

Ciò include successioni in natura, trasferimenti tra broker e posizioni create da rettifiche. Una vecchia individuazione basata solo su BUY/SELL perderebbe quelle posizioni.

## 🪟 Vista del periodo

Per il contributo di periodo per singolo asset:

$$
\mathrm{PnL}_{period} =
\Delta \mathrm{UGL}
+ \mathrm{Realized}
+ \mathrm{Income}
- \mathrm{FeesTaxes}
$$

La percentuale di periodo visualizzata rimane:

$$
r_{\mathrm{period}} = \frac{\mathrm{PnL}_{period}}{|\mathrm{StartValue}|}
$$

quando `StartValue` è diverso da zero. L'annualizzazione può ricadere sul costo di carico finale per gli asset aperti a metà periodo:

$$
\mathrm{ann\_base}=
\begin{cases}
|\mathrm{StartValue}|, & |\mathrm{StartValue}|>0\\
\mathrm{CostBasis}_{end} + \sum_a \left(V_a - C_a\right), & \text{altrimenti}
\end{cases}
$$

La somma riguarda i trasferimenti che la posizione ha ricevuto nel periodo da un altro broker del perimetro, ciascuno conteggiato come in
[Posizioni chiuse nel periodo](#closed-in-period): ciò che le loro unità hanno guadagnato prima di arrivare, valore all'arrivo meno
il costo storico trasferito (MF-A9). Il risultato della posizione conta quelle unità dal loro valore all'arrivo e il suo costo di carico finale corrisponde al
loro costo storico, quindi la base aggiunge lo stesso importo. Si applica solo finché nessuna unità ha lasciato la posizione nel
periodo, prima dell'arrivo o dopo di esso: una volta che delle unità l'hanno lasciata, un trasferimento non reca alcuna quantità che indichi quale parte della somma se n'è andata con
loro, e la somma viene scartata — il solo costo di carico finale è la base, come per qualsiasi posizione aperta a metà periodo che abbia venduto parte di
ciò che aveva acquistato.

L'inizio della finestra è limitato al lotto FIFO più vecchio ancora aperto alla fine del periodo:

$$
t_{\mathrm{start}}=\max(t_{\mathrm{from}},\ t_{\mathrm{oldest\ open\ lot}})
$$

I lotti sono conteggiati presso ciascun broker: un trasferimento apre un lotto datato al suo arrivo presso il broker ricevente. Uno split azionario ridimensiona i lotti aperti e ne conserva le date, quindi non accorcia mai la finestra. I lotti più vecchi che insieme detengono $10^{-5}$ unità o meno — il residuo che una vendita lascia — vengono messi da parte, poiché una posizione chiusa considera chiuso un simile residuo: un residuo lasciato anni prima non riporta indietro l'inizio della finestra alla sua data, e una posizione che non detiene nulla più di quel residuo non ha alcun lotto aperto (MF-A7). Le quantità sono quelle del motore, alla quota del proprietario sul broker: su un broker detenuto al 50 %, un residuo di $0.000012$ unità è $0.000006$ per il proprietario, trascurabile per la finestra come per la riga (MF-A10).

Poi:

$$
r_{\mathrm{ann}} =
\operatorname{annualize}\left(\frac{\mathrm{PnL}_{period}}{\mathrm{ann\_base}},\ t_{\mathrm{end}}-t_{\mathrm{start}}\right)
$$

### 🔚 Posizioni chiuse nel periodo {: #closed-in-period }

Una posizione è chiusa quando la sua quantità a $t_{\mathrm{end}}$, alla quota del proprietario sul broker, è pari o inferiore alla soglia di trascurabilità di $10^{-5}$ unità, così un residuo lasciato da rimborsi a tranche conta come chiuso. Non ha costo di carico finale, e un valore iniziale non dice nulla su una posizione venduta dopo poche settimane dall'inizio del periodo. Il suo rendimento annualizzato usa il capitale impiegato e il tempo in cui è stata detenuta all'interno del periodo:

$$
\mathrm{CostOut} = \sum_{s\,\in\,(t_{\mathrm{from}},\ t_{\mathrm{end}}]} C_s \;+\; \sum_{m\,\in\,(t_{\mathrm{from}},\ t_{\mathrm{end}}]} C_m \;+\; \sum_{a\,\in\,(t_{\mathrm{from}},\ t_{\mathrm{end}}]} \left(V_a - C_a\right)
$$

$$
t_{\mathrm{start}} = \max(t_{\mathrm{from}},\ t_{\mathrm{first\ opening}}), \qquad t_{\mathrm{close}} = \text{ultimo giorno in cui la sua quantità è scesa alla soglia di trascurabilità o al di sotto}
$$

$$
r_{\mathrm{ann}} =
\operatorname{annualize}\left(\frac{\mathrm{PnL}_{period}}{\mathrm{CostOut}},\ t_{\mathrm{close}}-t_{\mathrm{start}}\right)
$$

- $C_s$ è il costo storico, in $C^*$, di ogni dismissione conteggiata dal P&L realizzato del periodo — una SELL, o un ADJUSTMENT in uscita non collegato a uno split ([Motore del portafoglio — §8](index.md#8-realized-gain-loss)). Una dismissione esclusa dal P&L realizzato non aggiunge alcun costo.
- $C_m$ è il costo storico che ciascun trasferimento verso un altro broker del perimetro ha portato fuori, quando la riga conteggia il tratto di quel trasferimento: è partito dopo $t_{\mathrm{from}}$, è arrivato entro $t_{\mathrm{end}}$, e sono noti sia il suo valore all'arrivo sia il costo trasferito ([P&L periodo](period-pnl.md), decisione dello sviluppatore P22). Il risultato della riga porta con sé ciò che quelle unità hanno fatto fino al loro arrivo (la rettifica del tratto), quindi il loro costo appartiene alla base.
- $V_a - C_a$ è, per ciascun trasferimento di questo tipo che la posizione ha **ricevuto**, ciò che le sue unità hanno guadagnato prima di arrivare: il loro valore all'arrivo meno il costo storico trasferito con esse. Il risultato della riga fa partire quelle unità da $V_a$ (la rettifica del tratto sottrae $V_a - C_a$), mentre $C_s$ e $C_m$ portano il loro costo storico, quindi la base aggiunge lo stesso importo e le conta anch'essa al loro valore all'arrivo (MF-A8). Dunque $\mathrm{CostOut}$ non è soltanto costo storico: per le unità ricevute dalla posizione, la base contiene il loro valore all'arrivo.
- $t_{\mathrm{first\ opening}}$ è la prima acquisizione della posizione presso quel broker: un trasferimento la apre al suo arrivo lì, uno split non lo fa mai. È la prima in assoluto, non quella dell'ultimo lotto, quindi i giorni a zero tra due chiusure all'interno del periodo restano nella finestra.
- Il numeratore è l'intero $\mathrm{PnL}_{period}$ della riga: per una posizione detenuta a $t_{\mathrm{from}}$, il suo $\Delta\mathrm{UGL}$ restituisce il P&L latente con cui era iniziata.
- La percentuale di periodo visualizzata mantiene $|\mathrm{StartValue}|$ come base: solo il valore annualizzato cambia base e finestra.

Quando questo non dà alcun valore, seguono due casi:

- **Meno di 30 giorni di detenzione** nel periodo, $t_{\mathrm{close}} - t_{\mathrm{start}} < 30$: la riga non ha rendimento annualizzato (`—`), qualunque altra cosa abbia reso la base inutilizzabile. La regola sopra annualizzerebbe su $t_{\mathrm{from}} \to t_{\mathrm{end}}$, come se dieci giorni di detenzione fossero durati l'intero periodo (MF-A3).
- **Altrimenti** la riga mantiene la regola sopra. Ciò accade quando delle unità hanno lasciato la posizione in qualsiasi altro modo — un trasferimento fuori dal perimetro, o ancora in transito a $t_{\mathrm{end}}$, un trasferimento o una dismissione il cui valore o costo è sconosciuto — poiché il risultato della riga conterrebbe allora più di quanto copra la sua base; e con un rendimento di $-100\%$ o peggiore. La regola sopra è: $|\mathrm{StartValue}|$ su $t_{\mathrm{from}} \to t_{\mathrm{end}}$, e nessun valore per una posizione aperta nel periodo.

??? example "Esempio: una posizione venduta 90 giorni dopo l'inizio di un periodo di un anno"

    A $t_{\mathrm{from}}$ la posizione vale 1.100 per un costo di 1.000. Tutto viene venduto 90 giorni dopo per 1.250:

    $$
    \mathrm{PnL}_{period} = (0 - 100) + (1{,}250 - 1{,}000) = +150
    $$

    $$
    r_{\mathrm{ann}} = \operatorname{annualize}\left(\frac{150}{1{,}000},\ 90\right) = 1.15^{365/90} - 1 \approx +76.3\%
    $$

    Il P&L latente di +100 con cui era iniziata viene stornato dal $\Delta\mathrm{UGL}$, il P&L realizzato aggiunge +250. La percentuale di periodo resta $150 / 1{,}100 = 13.64\%$; annualizzato sull'intero anno sul valore iniziale, come farebbe una posizione aperta, lo stesso +150 darebbe comunque 13,64%.

??? example "Esempio: metà venduta, metà trasferita a un altro broker"

    A $t_{\mathrm{from}}$ la posizione detiene 10 unità, del valore di 1.100 per un costo di 1.000. Cinque vengono vendute per 625; cinque passano a un altro broker del perimetro e valgono 600 quando arrivano:

    $$
    \mathrm{PnL}_{period} = \underbrace{(0 - 100)}_{\Delta\mathrm{UGL}} + \underbrace{(625 - 500)}_{\text{Realized}} + \underbrace{(600 - 500)}_{\text{tratto}} = +125
    $$

    $$
    \mathrm{CostOut} = 500 + 500 = 1{,}000, \qquad \frac{125}{1{,}000} = 12.5\%
    $$

    Considerando come base il solo costo delle unità vendute, si otterrebbe $125 / 500 = 25\%$: il risultato delle unità trasferite sarebbe nel numeratore, senza il loro costo nella base (MF-A5).

    Il broker che ha ricevuto le cinque unità e in seguito le ha vendute per 660 mostra l'immagine speculare: il suo risultato è $(660 - 500) - (600 - 500) = +60$, e la sua base $500 + (600 - 500) = 600$, quindi $60 / 600 = 10\%$ — le unità contano dal loro valore all'arrivo, sia nel risultato sia nella base (MF-A8).

## 🧬 Lotti FIFO

Il rendimento annualizzato del lotto FIFO è calcolato al netto delle commissioni e delle imposte allocate e include i proventi allocati:

$$
\mathrm{NetTotalPnL}_i =
\mathrm{MarketPnL}_i
+ \mathrm{RealizedPnL}_i
+ \mathrm{Income}_i
- \mathrm{Fees}_i
- \mathrm{Taxes}_i
$$

$$
\mathrm{NetTotalReturn}_i =
\frac{\mathrm{NetTotalPnL}_i}{\mathrm{OpeningValue}_i}
$$

Il valore annualizzato usa `net_total_return`, non il `total_return` lordo:

$$
r_{\mathrm{ann},i} =
\operatorname{annualize}
\left(
\mathrm{NetTotalReturn}_i,\ 
t_{\mathrm{lot\ end}}-t_{\mathrm{opening}}
\right)
$$

dove $t_{\mathrm{lot\ end}}$ è la data di chiusura per i lotti completamente chiusi, altrimenti la data finale dell'analisi.

## 🔗 Correlati

- 🧭 [Risoluzione dei prezzi](price-resolution.md) — fonte delle valutazioni di mercato e di quelle all'origine delle operazioni
- 📉 [ROI semplice](roi.md) — contesto del rendimento di sintesi e a livello di posizione
- 📊 [P&L periodo](period-pnl.md) — scomposizione del periodo
- 🔬 [Analisi dei lotti FIFO](../fifo-engine/fifo-lot-analysis.md) — metriche nette per lotto
- ⚙️ [Motore del portafoglio](index.md) — modello matematico completo
