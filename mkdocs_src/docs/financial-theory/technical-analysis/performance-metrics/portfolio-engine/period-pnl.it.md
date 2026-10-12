# 📊 P&L periodo (Profitto e perdita)

## 💡 Che cos'è il P&L periodo?

Il guadagno o la perdita monetaria assoluta generata dal tuo portafoglio nell'intervallo $[t_0, t_1]$, rettificata per i flussi di cassa esterni.

---

## 🧮 Formula

$$
\boxed{\mathrm{PnL}_{\text{period}} = \mathrm{NAV}(t_1)-\mathrm{NAV}(t_0)-\Delta \mathrm{CapitalBaseline}_{[t_0,t_1]}}
$$

Il delta della baseline di capitale deriva da `cumulative_external_cash_flow`, quindi include flussi di cassa e capitale ADJUSTMENT/TRANSFER in natura valorizzato.

---

## 🧮 Scomposizione

$$
\mathrm{PnL}_{\text{period}} = \Delta\mathrm{UGL} + \mathrm{Realized} + \mathrm{Income} - \mathrm{FeesTaxes} + \mathrm{Other}
$$

| Componente | Definizione |
|-----------|-----------|
| $\Delta\mathrm{UGL}$ | Variazione del P&L latente nel periodo — per gli asset prezzati in un'altra valuta, incluso l'effetto del tasso di cambio sul loro costo storico |
| Realized | Somma di (ricavato di vendita − costo storico delle unità vendute) per le operazioni SELL nel periodo; il ricavato è convertito alla data di vendita |
| Income | DIVIDEND + INTEREST nel periodo |
| FeesTaxes | FEE + TAX nel periodo |
| Other | Ciò che chiude l'identità: il risultato di cambio sulla liquidità detenuta in un'altra valuta (Effetto cambio sulla liquidità) più un residuo |

Other è calcolato come:

$$
\mathrm{Other} = \mathrm{PnL}_{\text{period}} - \Delta\mathrm{UGL} - \mathrm{Realized} - \mathrm{Income} + \mathrm{FeesTaxes}
$$

Poiché il costo di carico mantiene i suoi tassi di cambio storici (vedi [Valore contabile](book-value.md)), l'effetto dei tassi di cambio sugli asset esteri fa parte di $\Delta\mathrm{UGL}$, non di Other. La liquidità detenuta in un'altra valuta è diversa: il NAV e il valore contabile la valutano entrambi al tasso di ogni giorno, quindi il suo effetto di cambio si annulla nel P&L latente e non è in $\Delta\mathrm{UGL}$. È la prima parte di Other, l'[Effetto cambio sulla liquidità](#fx-on-cash) di ciascun broker $b$, che la vista Performance mostra per broker:

$$
\mathrm{Other} = \sum_{b \in S} \mathrm{FXonCash}_b + \mathrm{Residual}
$$

Il residuo contiene ciò che né i quattro componenti né il risultato di cambio sulla liquidità riescono a vedere:

- il movimento del tasso di cambio sulla liquidità mentre viaggia tra due broker: in transito, non appartiene al saldo di alcun broker;
- il costo di un cambio di valuta, presso un broker o tra due: −1.000 USD che valgono €920 al tasso del giorno, cambiati in +€900, danno −€20, che non è né una commissione né una vendita;
- il valore di asset che passano tra due broker in un giorno di confine;
- una vendita esclusa da Realized perché il suo ricavato non ha potuto essere convertito o il costo della sua posizione è incompleto.

### 💵 Effetto cambio sulla liquidità {: #fx-on-cash }

Per ciascun broker $b$ che detiene liquidità in una valuta diversa da $C^*$, sul periodo $(t_0, t_1]$, dove $t_0$ è lo stato di apertura:

$$
\mathrm{FXonCash}_b = \sum_{c \neq C^*} \Bigl[N_{b,c}(t_1)\,\mathrm{fx}(c, C^*, t_1) - N_{b,c}(t_0)\,\mathrm{fx}(c, C^*, t_0)\Bigr] - \sum_{\substack{m \in (t_0, t_1] \\ \mathrm{ccy}(m) \neq C^*}} s_m \cdot \mathrm{amount}_m \cdot \mathrm{fx}(\mathrm{ccy}(m), C^*, d_m)
$$

$N_{b,c}(t)$ è il saldo che $b$ detiene nella valuta $c$ alla data $t$, in proporzione alla quota del broker, e $\mathrm{fx}$ l'ultimo tasso disponibile in quel giorno o prima. La seconda somma scorre i movimenti di $b$ in una valuta estera datati nel periodo: ogni importo, in proporzione alla quota $s_m$, al tasso della propria data $d_m$. Il primo termine è la variazione di valore della liquidità in valuta estera, il secondo ciò che i movimenti hanno portato dentro o fuori: la differenza è l'effetto dei tassi di cambio sulla liquidità che il broker deteneva. È pari ai risultati di cambio che il motore registra nei giorni del periodo in cui il tasso cambia ([Portfolio Engine — §6](index.md#exchange-result-on-foreign-cash)). La liquidità in $C^*$ non ne ha.

??? example "Esempio: dollari presso un broker su una dashboard in euro"

    Un broker detiene 1.000 USD per tutto il periodo mentre il tasso passa da 0,90 a 0,92 EUR per USD:

    $$
    \mathrm{FXonCash} = 1\,000 \times 0.92 - 1\,000 \times 0.90 = +20 \text{ EUR}
    $$

    Con un deposito di 500 USD a metà periodo a 0,91, e 0,92 alla fine:

    $$
    \mathrm{FXonCash} = 1\,500 \times 0.92 - 1\,000 \times 0.90 - 500 \times 0.91 = 1\,380 - 900 - 455 = +25 \text{ EUR}
    $$

    Il deposito è entrato nel capitale per €455; i +€25 sono quanto i dollari hanno guadagnato sull'euro mentre il broker li deteneva.

---

## 💱 Variazione del P&L latente per valuta {: #unrealized-change-by-currency }

$\Delta\mathrm{UGL}$ è suddiviso per la valuta $A$ in cui gli asset sono prezzati. Per le posizioni nella valuta $A$ al giorno $t$, sia

| Simbolo | Significato |
|--------|---------|
| $\mathrm{MV}_A(t)$ | Il loro valore di mercato in $C^*$, al prezzo e al tasso del giorno |
| $\mathrm{Cost}^{A}_A(t)$ | Il loro costo storico in $A$ |
| $\mathrm{Cost}^{*}_A(t)$ | Il loro costo storico in $C^*$ |
| $r_A(t) = \mathrm{fx}(A, C^*, t)$ | Il tasso di cambio del giorno |

Il costo di ciascun acquisto in $A$ deriva dal suo costo in $C^*$ alla data di acquisizione, $c^{A} = c^{*} \cdot \mathrm{fx}(C^*, A, d)$ (o dall'importo pagato, quando pagato in $A$). Il P&L latente si suddivide quindi esattamente in un **effetto asset** e in un **effetto tasso di cambio**:

$$
E^{\text{asset}}_A(t) = \mathrm{MV}_A(t) - \mathrm{Cost}^{A}_A(t)\, r_A(t)
$$

$$
E^{\text{fx}}_A(t) = \mathrm{Cost}^{A}_A(t)\, r_A(t) - \mathrm{Cost}^{*}_A(t)
$$

$$
E^{\text{asset}}_A(t) + E^{\text{fx}}_A(t) = \mathrm{MV}_A(t) - \mathrm{Cost}^{*}_A(t) = \mathrm{UGL}_A(t)
$$

Per un mark quotato in $A$, $\mathrm{MV}_A(t) = \frac{q}{qbq} \cdot \mathrm{mark}_A(t) \cdot r_A(t)$, quindi l'effetto asset è la variazione propria degli asset nella loro valuta, tradotta al tasso del giorno: $E^{\text{asset}}_A(t) = \bigl(\frac{q}{qbq} \cdot \mathrm{mark}_A(t) - \mathrm{Cost}^{A}_A(t)\bigr)\, r_A(t)$. L'effetto tasso di cambio è nullo il giorno di ogni acquisto. Per $A = C^*$, $r = 1$ e $\mathrm{Cost}^{A} = \mathrm{Cost}^{*}$: l'effetto tasso di cambio svanisce, e gli asset già nella valuta di riferimento hanno solo un effetto asset.

Una posizione in una valuta $A \neq C^*$ che non può essere suddivisa al giorno $t$ — nessun valore di mercato, nessun tasso $r_A(t)$, o un costo incompleto in una delle due valute — aggiunge invece il suo intero $\mathrm{MV} - \mathrm{Cost}^{*}$ (con $\mathrm{MV} = 0$ quando non ha valore di mercato) a una parte separata, **unsplit**, $E^{\text{unsplit}}_A(t)$. Le posizioni in $C^*$ contano sempre nell'effetto asset.

Le righe del periodo sono le variazioni tra i due stati limite del periodo — l'ultimo stato al giorno $t_0$ o prima (zero se non esiste) e lo stato a $t_1$ —, gli stessi due stati di $\Delta\mathrm{UGL}$:

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
    | $t_0$ | 520 USD | 0,78 | 405,60 | $(520-500) \times 0.78 = 15.60$ | $500 \times 0.78 - 400 = -10.00$ | 5,60 |
    | $t_1$ | 550 USD | 0,75 | 412,50 | $(550-500) \times 0.75 = 37.50$ | $500 \times 0.75 - 400 = -25.00$ | 12,50 |

    $$
    \Delta E^{\text{asset}} = +21.90, \qquad \Delta E^{\text{fx}} = -15.00, \qquad \Delta\mathrm{UGL} = +6.90 \text{ EUR}
    $$

    L'ETF ha guadagnato in dollari (+€21,90), il dollaro ha perso terreno rispetto all'euro (−€15,00): insieme, i +€6,90 della variazione del P&L latente del periodo.

---

## 🎯 Contributo per asset

Per ogni posizione $(a,b)$:

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{FeesTaxes}(a,b)
$$

L'insieme delle posizioni include **tutta l'attività** nel periodo:

$$
\mathcal{P} = \text{posizioni con attività BUY/SELL/ADJUSTMENT/TRANSFER o quantità limite}
$$

Il rendimento annualizzato del periodo limita l'inizio della propria finestra alla data più recente tra l'inizio richiesto e la data del lotto aperto più vecchio. Usa $|\mathrm{StartValue}|$ come base di annualizzazione, ricadendo sul costo di carico finale per le posizioni aperte a metà periodo. Vedi [Rendimento annualizzato netto](net-annualized-return.md).

🔗 Vedi **[Motore di portafoglio — §7 Contributo del periodo](index.md#7-period-contribution)** per i dettagli.

---

## 📝 Esempio

- NAV a $t_0$: €27.000
- Incremento della baseline di capitale nel periodo: €1.000
- NAV a $t_1$: €33.000

$$
\mathrm{PnL} = 33\,000 - 27\,000 - 1\,000 = +5\,000 \text{ EUR}
$$

---

## 🔗 Correlati

- 💼 [NAV](nav.md) — punto finale di ogni formula P&L
- 📖 [Valore contabile](book-value.md) — costo di carico storico alla base del P&L latente
- 💸 [Capitale versato](deposited-capital.md) — P&L totale dall'inizio a oggi
- ⚙️ [Motore di portafoglio](index.md) — modello matematico completo
- 📈 [Panoramica delle metriche di performance](../index.md) — tutte le metriche di performance a colpo d'occhio
