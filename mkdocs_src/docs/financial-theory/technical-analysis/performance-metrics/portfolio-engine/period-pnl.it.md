# 📊 P&L periodo (Profitto e perdita)

## 💡 Che cos'è il P&L periodo?

Il guadagno o la perdita monetaria assoluta generata dal tuo portafoglio nell'intervallo $[t_0, t_1]$, rettificata per i flussi di cassa esterni.

---

## 🧮 Formula

$$
\boxed{\mathrm{PnL}_{\text{period}} = \mathrm{NAV}(t_1)-\mathrm{NAV}(t_0)-\Delta \mathrm{CapitalBaseline}_{[t_0,t_1]}}
$$

Il delta della baseline del capitale proviene da `cumulative_external_cash_flow`, quindi include flussi di cassa e capitale in natura valorizzato derivante da rettifiche/trasferimenti. Una rettifica in uscita non ha valore e non preleva nulla ([Capitale versato — Rettifiche in uscita](deposited-capital.md#outgoing-adjustments)).

---

## 🧮 Scomposizione

$$
\mathrm{PnL}_{\text{period}} = \Delta\mathrm{UGL} + \mathrm{Realized} + \mathrm{Income} - \mathrm{FeesTaxes} + \mathrm{Other}
$$

| Componente | Definizione |
|-----------|-----------|
| $\Delta\mathrm{UGL}$ | Variazione del P&L latente nel periodo: valore di mercato − costo di carico aperto delle posizioni detenute a ciascun confine, titoli in transito esclusi ([la variazione non realizzata del periodo](index.md#two-unrealized-figures)) — per gli asset valorizzati in un'altra valuta, incluso l'effetto del tasso di cambio sul loro costo storico |
| P&L realizzato | Somma di (ricavato − costo storico delle unità cedute) per le vendite nel periodo e per le rettifiche in uscita non collegate a uno split, i cui ricavati sono zero; i ricavati sono convertiti alla data della transazione ([Portfolio Engine — §8](index.md#8-realized-gain-loss)) |
| Reddito | DIVIDENDO + INTERESSE nel periodo |
| Commissioni e imposte | COMMISSIONE + IMPOSTA nel periodo |
| Altro | Ciò che chiude l'identità: il risultato di cambio sulla liquidità detenuta in un'altra valuta (effetto cambio sulla liquidità), il P&L maturato dai titoli fuori dalla vista prima di attraversarne il confine (trasferimenti a valore di mercato), più un residuo |

Altro è calcolato come:

$$
\mathrm{Other} = \mathrm{PnL}_{\text{period}} - \Delta\mathrm{UGL} - \mathrm{Realized} - \mathrm{Income} + \mathrm{FeesTaxes}
$$

Poiché il costo di carico mantiene i propri tassi di cambio storici (vedi [Valore contabile](book-value.md)), l'effetto dei tassi di cambio sugli asset esteri fa parte di $\Delta\mathrm{UGL}$, non di Altro. La liquidità detenuta in un'altra valuta è diversa: NAV e valore contabile la valorizzano entrambi al tasso di ogni giorno, quindi l'effetto del tasso di cambio su di essa si annulla nel P&L latente e non è in $\Delta\mathrm{UGL}$. È la prima parte di Altro, l’[effetto cambio sulla liquidità](#fx-on-cash) di ciascun broker $b$, che la vista Periodo mostra per broker. La seconda parte, i [trasferimenti a valore di mercato](#transfers-at-market-value), è anch'essa mostrata per broker:

$$
\mathrm{Other} = \sum_{b \in S} \mathrm{FXonCash}_b + \sum_{b \in S} \mathrm{TMV}_b + \mathrm{Residual}
$$

Il residuo contiene ciò che né le quattro componenti, né il risultato di cambio sulla liquidità, né i trasferimenti a valore di mercato riescono a vedere:

- la variazione del tasso di cambio sulla liquidità mentre si sposta tra due broker: in transito, non appartiene al saldo di alcun broker;
- il costo di un cambio valuta, presso un broker o tra due: −1.000 USD che valgono €920 al tasso del giorno, convertiti in +€900, danno −€20, che non è né una commissione né una vendita;
- il valore degli asset che viaggiano tra due broker in un giorno di confine;
- una vendita esclusa dal P&L realizzato perché non è stato possibile convertire il suo ricavato, oppure una vendita o una rettifica in uscita escluse perché il costo della loro posizione è incompleto.
- il costo del dust: una vendita che lascia $10^{-5}$ unità o meno in una posizione rimuove ciò che resta dal costo di carico aperto senza venderlo, quindi il suo costo non è né in $\Delta\mathrm{UGL}$ né nel P&L realizzato — 0,00001 unità acquistate a 100.000 lasciano −1,00 qui ([§7](index.md#7-period-contribution)).

### 💵 Effetto cambio sulla liquidità {: #fx-on-cash }

Per ciascun broker $b$ che detiene liquidità in una valuta diversa da $C^*$, nel periodo $(t_0, t_1]$, con $t_0$ come stato di apertura:

$$
\mathrm{FXonCash}_b = \sum_{c \neq C^*} \Bigl[N_{b,c}(t_1)\,\mathrm{fx}(c, C^*, t_1) - N_{b,c}(t_0)\,\mathrm{fx}(c, C^*, t_0)\Bigr] - \sum_{\substack{m \in (t_0, t_1] \\ \mathrm{ccy}(m) \neq C^*}} s_m \cdot \mathrm{amount}_m \cdot \mathrm{fx}(\mathrm{ccy}(m), C^*, d_m)
$$

$N_{b,c}(t)$ è il saldo che $b$ detiene nella valuta $c$ alla data $t$, ponderato per la quota del broker, e $\mathrm{fx}$ è il tasso più recente alla data o precedente. La seconda somma si riferisce ai movimenti di $b$ in una valuta estera datati nel periodo: ciascun importo, ponderato per la quota $s_m$, al tasso della propria data $d_m$. Il primo termine è la variazione di valore della liquidità estera, il secondo ciò che i movimenti hanno apportato o prelevato: la differenza è ciò che i tassi di cambio hanno fatto alla liquidità detenuta dal broker. È uguale ai risultati di cambio che il motore registra nei giorni di variazione del tasso del periodo ([Portfolio Engine — §6](index.md#exchange-result-on-foreign-cash)). La liquidità in $C^*$ non ne ha.

??? example "Esempio: dollari presso un broker su una dashboard in euro"

    Un broker detiene 1.000 USD per l'intero periodo mentre il tasso di cambio passa da 0,90 a 0,92 EUR per USD:

    $$
    \mathrm{FXonCash} = 1{,}000 \times 0.92 - 1{,}000 \times 0.90 = +20 \text{ EUR}
    $$

    Con un deposito di 500 USD a metà del periodo a 0,91, e 0,92 alla fine:

    $$
    \mathrm{FXonCash} = 1{,}500 \times 0.92 - 1{,}000 \times 0.90 - 500 \times 0.91 = 1{,}380 - 900 - 455 = +25 \text{ EUR}
    $$

    Il deposito è entrato nel capitale a €455; i +€25 sono ciò che i dollari hanno guadagnato rispetto all'euro mentre il broker li deteneva.

### 🔀 Trasferimenti a valore di mercato {: #transfers-at-market-value }

In una vista che seleziona solo alcuni broker, una gamba di trasferimento il cui altro lato è fuori dalla vista — titoli inviati a un broker non selezionato, ricevuti da uno, o un trasferimento senza controparte — è capitale in natura al suo valore di mercato alla sua data, mentre il costo della posizione si sposta con essa ([Capitale versato](deposited-capital.md)). L'utile maturato dalle unità presso l'altro broker non è quindi né in $\Delta\mathrm{UGL}$ né nel P&L realizzato, e finiva nel residuo. È la seconda parte di Altro. Per ciascun broker $b$ della vista, sulle gambe $\ell$ datate in $(t_0, t_1]$:

$$
\mathrm{TMV}_b = \sum_{\ell \in (t_0, t_1]} \bigl(\mathrm{Cost}_\ell - \mathrm{Capital}_\ell\bigr)
$$

$\mathrm{Capital}_\ell$ è il valore di mercato che la gamba aggiunge al capitale (positivo quando ricevuto, negativo quando inviato) e $\mathrm{Cost}_\ell$ il costo che sposta nella posizione (stesso segno), entrambi in $C^*$ alla quota del broker. Per unità con valore di mercato $\mathrm{MV}$ e costo $C$:

| Gamba | $\mathrm{Capital}$ | $\mathrm{Cost}$ | Contributo |
|-----|---------|------|--------------|
| Inviata fuori dalla vista | $-\mathrm{MV}$ | $-C$ | $+(\mathrm{MV} - C)$ |
| Ricevuta dall'esterno della vista | $+\mathrm{MV}$ | $+C$ | $-(\mathrm{MV} - C)$ |

La vista del mittente considera come proprio risultato l'utile che le unità hanno prodotto mentre le deteneva; la vista del destinatario parte dal valore con cui arrivano, quindi ciò che hanno guadagnato prima non è un suo risultato e viene tolto. Una cifra sotto la soglia di arrotondamento non viene mostrata, e il residuo diminuisce dell'importo mostrato. Con entrambi i broker selezionati non cambia nulla: la coppia è interna, e le unità si limitano a dividere il risultato tra le due righe (vedi il trasferimento interno nella sezione Contributo per asset più avanti).

??? example "Esempio: unità acquistate presso un broker e inviate a un altro"

    10 unità acquistate a 50 ciascuna (costo €500) presso il broker A vengono inviate al broker B quando valgono €800.

    - **Vista solo su A:** le unità escono a €800 di capitale e portano con sé €500 di costo: $\mathrm{TMV}_A = -500 + 800 = +300$ EUR.
    - **Vista solo su B:** le unità arrivano a €800 di capitale con €500 di costo: $\mathrm{TMV}_B = 500 - 800 = -300$ EUR.
    - **Vista su A e B:** nessuna riga di questo tipo.

---

## 💱 Variazione non realizzata per valuta {: #unrealized-change-by-currency }

$\Delta\mathrm{UGL}$ è suddiviso per la valuta $A$ in cui gli asset sono valorizzati. Per le posizioni nella valuta $A$ al giorno $t$, sia

| Simbolo | Significato |
|--------|---------|
| $\mathrm{MV}_A(t)$ | Il loro valore di mercato in $C^*$, al prezzo e al tasso del giorno |
| $\mathrm{Cost}^{A}_A(t)$ | Il loro costo storico in $A$ |
| $\mathrm{Cost}^{*}_A(t)$ | Il loro costo storico in $C^*$ |
| $r_A(t) = \mathrm{fx}(A, C^*, t)$ | Il tasso di cambio del giorno |

Il costo di ciascun acquisto in $A$ deriva dal suo costo in $C^*$ alla data di acquisto, $c^{A} = c^{*} \cdot \mathrm{fx}(C^*, A, d)$ (o dall'importo pagato, quando pagato in $A$). Il P&L latente si suddivide quindi esattamente in un **effetto asset** e in un **effetto del tasso di cambio**:

$$
E^{\text{asset}}_A(t) = \mathrm{MV}_A(t) - \mathrm{Cost}^{A}_A(t)\, r_A(t)
$$

$$
E^{\text{fx}}_A(t) = \mathrm{Cost}^{A}_A(t)\, r_A(t) - \mathrm{Cost}^{*}_A(t)
$$

$$
E^{\text{asset}}_A(t) + E^{\text{fx}}_A(t) = \mathrm{MV}_A(t) - \mathrm{Cost}^{*}_A(t) = \mathrm{UGL}_A(t)
$$

Per un mark quotato in $A$, $\mathrm{MV}_A(t) = \frac{q}{qbq} \cdot \mathrm{mark}_A(t) \cdot r_A(t)$, quindi l'effetto asset è la variazione degli asset stessi nella loro valuta, tradotta al tasso del giorno: $E^{\text{asset}}_A(t) = \bigl(\frac{q}{qbq} \cdot \mathrm{mark}_A(t) - \mathrm{Cost}^{A}_A(t)\bigr)\, r_A(t)$. L'effetto del tasso di cambio è zero il giorno di ciascun acquisto. Per $A = C^*$, $r = 1$ e $\mathrm{Cost}^{A} = \mathrm{Cost}^{*}$: l'effetto del tasso di cambio svanisce, e gli asset già nella valuta di report hanno solo un effetto asset.

Una posizione in una valuta $A \neq C^*$ che non può essere suddivisa al giorno $t$ — nessun valore di mercato, nessun tasso $r_A(t)$, o un costo incompleto in una delle due valute — aggiunge invece l'intero $\mathrm{MV} - \mathrm{Cost}^{*}$ (con $\mathrm{MV} = 0$ quando non ha valore di mercato) a una parte **non suddivisa** $E^{\text{unsplit}}_A(t)$. Le posizioni in $C^*$ contano sempre nell'effetto asset. Una posizione valorizzata al suo costo perché il suo asset non ha alcun mark ([Portfolio Engine — §3](index.md#3-position-state)) ha $\mathrm{MV} = \mathrm{Cost}^{*}$ e non si aggiunge a nessuna parte: suddividerla inventerebbe un effetto asset e un effetto del tasso di cambio di segno opposto.

Le righe del periodo sono le variazioni tra i due stati di confine del periodo — l'ultimo stato alla data $t_0$ o precedente (zero se non esiste) e lo stato a $t_1$ —, gli stessi due stati di $\Delta\mathrm{UGL}$:

$$
\Delta E^{k}_A = E^{k}_A(t_1) - E^{k}_A(t_0), \qquad k \in \{\text{asset}, \text{fx}, \text{unsplit}\}
$$

$$
\sum_{A}\ \sum_{k} \Delta E^{k}_A = \Delta\mathrm{UGL} \quad \text{esattamente}
$$

??? example "Esempio: un ETF statunitense su una dashboard in euro"

    10 unità acquistate per €400 quando valevano 500 USD, quindi $\mathrm{Cost}^{*} = 400$ EUR e $\mathrm{Cost}^{A} = 500$ USD.

    | Giorno | Valore in USD | $r_{USD}$ | MV in EUR | $E^{\text{asset}}$ | $E^{\text{fx}}$ | $\mathrm{UGL}$ |
    |-----|-------|-----------|---------------|--------------------|-----------------|----------------|
    | $t_0$ | 520 USD | 0.78 | 405.60 | $(520-500) \times 0.78 = 15.60$ | $500 \times 0.78 - 400 = -10.00$ | 5.60 |
    | $t_1$ | 550 USD | 0.75 | 412.50 | $(550-500) \times 0.75 = 37.50$ | $500 \times 0.75 - 400 = -25.00$ | 12.50 |

    $$
    \Delta E^{\text{asset}} = +21.90, \qquad \Delta E^{\text{fx}} = -15.00, \qquad \Delta\mathrm{UGL} = +6.90 \text{ EUR}
    $$

    L'ETF ha guadagnato in dollari (+€21,90), il dollaro ha perso terreno rispetto all'euro (−€15,00): insieme, i +€6,90 della variazione non realizzata del periodo.

---

## 🎯 Contributo per asset

Per ciascuna posizione $(a,b)$:

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{FeesTaxes}(a,b)
$$

L'insieme delle posizioni include **tutta l'attività** del periodo:

$$
\mathcal{P} = \text{posizioni con attività di acquisto/vendita/rettifica/trasferimento o quantità di confine}
$$

I valori iniziali e finali di una posizione sono la valorizzazione che il portafoglio stesso ne dà alla fine di $t_0$ e di $t_1$, i due stati di $\Delta\mathrm{UGL}$ ([Portfolio Engine — §3](index.md#3-position-state)):

- il suo mark ([§2](index.md#2-valuation-price)): una quotazione di mercato, oppure un prezzo di acquisto/vendita — o, per un asset che non ha ancora nient'altro, il costo di un trasferimento in entrata come stima —, con il prezzo di una negoziazione rideterminato attraverso qualsiasi split successivo;
- il suo costo di carico, per una posizione il cui asset non ha alcun mark (`ESTIMATED_AT_COST`);
- convertito al tasso di cambio del giorno di confine stesso.

Le righe quindi sommano al portafoglio: quando ogni riga è nota, $\sum_{(a,b)} \Delta\mathrm{UGL}(a,b) = \Delta\mathrm{UGL}$, e le righe più gli altri effetti del periodo — proventi e costi non allocati, effetto cambio sulla liquidità, trasferimenti a valore di mercato, il residuo — chiudono $\mathrm{PnL}_{\text{period}}$. Altro non contiene alcuna differenza di valorizzazione. Una posizione rimasta con $10^{-5}$ unità o meno — dust — non è rappresentata né da una riga né dal portafoglio, quindi non cambia nulla nell'identità ([§3](index.md#3-position-state)); il suo costo è nel residuo (sopra).

- **Trasferimento interno.** Un titolo spostato tra due dei tuoi broker all'interno del periodo divide il suo risultato: la riga del broker mittente risponde per le unità fino al loro arrivo, quella del broker destinatario dal loro arrivo, e il totale resta invariato. Un trasferimento già in transito a $t_0$, o ancora in transito a $t_1$, mantiene i semplici valori di confine ([§7](index.md#7-period-contribution)).
- **Valori sconosciuti.** Una posizione detenuta a un confine il cui P&L latente è sconosciuto in quel punto — un tasso di cambio mancante, un costo incompleto — ha un $\Delta\mathrm{UGL}(a,b)$ sconosciuto, mai il lato noto meno zero.

Il rendimento annualizzato del periodo limita l'inizio della sua finestra alla più recente tra la data di inizio richiesta e la data del lotto aperto più vecchio. Usa $|\mathrm{StartValue}|$ come base di annualizzazione, ricorrendo al costo di carico finale per le posizioni aperte a metà periodo. Vedi [Rendimento annualizzato netto](net-annualized-return.md).

Una posizione chiusa nel periodo — nulla rimasto a $t_1$ — si annualizza diversamente: sul costo storico delle unità che l'hanno lasciata nel periodo — vendute, o spostate a un altro broker dell'ambito — rispetto al tempo in cui è stata detenuta al suo interno, dal giorno più recente tra $t_0$ e la sua prima apertura fino al giorno in cui sono uscite le sue ultime unità. La sua percentuale di periodo mantiene $|\mathrm{StartValue}|$ come base. Vedi [Rendimento annualizzato netto — Posizioni chiuse nel periodo](net-annualized-return.md#closed-in-period).

🔗 Vedi **[Portfolio Engine — §7 Contributo del periodo](index.md#7-period-contribution)** per i dettagli.

---

## 📝 Esempio

- NAV a $t_0$: €27.000
- Aumento della baseline del capitale nel periodo: €1.000
- NAV a $t_1$: €33.000

$$
\mathrm{PnL} = 33\,000 - 27\,000 - 1\,000 = +5\,000 \text{ EUR}
$$

---

## 🔗 Correlati

- 💼 [NAV](nav.md) — punto di arrivo di ogni formula del P&L
- 📖 [Valore contabile](book-value.md) — costo di carico storico sottostante il P&L latente
- 💸 [Capitale versato](deposited-capital.md) — P&L totale dall'inizio a oggi
- ⚙️ [Portfolio Engine](index.md) — modello matematico completo
- 📈 [Panoramica delle metriche di performance](../index.md) — tutte le metriche di performance a colpo d'occhio
