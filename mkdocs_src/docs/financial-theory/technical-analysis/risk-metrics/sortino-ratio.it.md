# 📊 Indice di Sortino

L'indice di Sortino è una modifica dell'indice di Sharpe che penalizza solo la **volatilità al ribasso**. Riconosce che gli investitori sono principalmente interessati alle perdite, non alle sorprese al rialzo.

---

## 🔢 Formula {: #formula }

$$
So = \frac{R_p - R_f}{\sigma_d}
$$

dove:

- $R_p$ = rendimento del portafoglio (annualizzato)
- $R_f$ = tasso privo di rischio (o rendimento minimo accettabile)
- $\sigma_d$ = **deviazione al ribasso** (annualizzata)

!!! info "Come la soglia entra nel calcolo"

    La soglia — il rendimento minimo accettabile — è fornita come tasso **effettivo annuo** e convertita in tasso **effettivo per periodo** attraverso la stessa conversione usata dall'indice di Sharpe:

    $$
    r_{period} = (1 + r_{annual})^{1/f} - 1
    $$

    dove $f$ è lo stesso fattore di annualizzazione che scala la deviazione al ribasso, misurato dai dati osservati — vedi [Annualizzazione osservata](observed-annualization.md). Quella soglia per periodo viene poi sottratta da ogni rendimento del periodo, sia nei rendimenti in eccesso sia all'interno della deviazione al ribasso di seguito indicata, così un'unica definizione di "accettabile" governa sia il numeratore sia il denominatore.

### 📐 Deviazione al ribasso {: #downside-deviation }

$$
\sigma_d = \sqrt{\frac{1}{N} \sum_{i=1}^{N} \min(R_i - R_f, 0)^2}
$$

Solo i rendimenti **sotto** la soglia contribuiscono alla deviazione al ribasso. I rendimenti sopra la soglia danno un contributo nullo.

---

## ⚖️ Due convenzioni sulla deviazione al ribasso {: #two-downside-conventions }

Due diverse grandezze sono comunemente chiamate "deviazione al ribasso", e differiscono in due modi — uno trascurabile, uno decisivo.

| | Punto di riferimento | Divisore |
|---|---|---|
| **Convenzione della soglia** (usata qui) | Una soglia **scelta** — il rendimento minimo accettabile | $N$, ogni osservazione |
| **Convenzione della media** | La **media campionaria della serie stessa** | $N - 1$, le osservazioni meno una |

**Il divisore è la differenza trascurabile.** Quando la soglia coincide con la media campionaria, i due risultati differiscono solo per il fattore $\sqrt{N/(N-1)}$ — su un anno di osservazioni giornaliere, circa due parti su mille. È una scelta contabile, non un cambiamento di significato.

**Il punto di riferimento è quello decisivo**, e il divario che apre non ha limite superiore. I valori seguenti derivano direttamente dalle due definizioni applicate a serie costruite — sono aritmetica che un lettore può riprodurre, non risultato di un'esecuzione di LibreFolio:

| Serie su 250 osservazioni | Convenzione della media | Convenzione della soglia (soglia $= 0$) |
|---|---|---|
| **Perde esattamente lo 0,5% ogni giorno** | **0,000000** | **0,005000** |
| Alterna $+1\%$ e $-1\%$ intorno a zero | 0,007085 | 0,007071 |
| Guadagna esattamente lo 0,5% ogni giorno | 0,000000 | 0,000000 |

L'intero argomento è racchiuso nella prima riga. Un portafoglio che perde mezzo punto percentuale **ogni singolo giorno per un anno** non devia mai dalla propria media, perché la sua media *è* quella perdita giornaliera — quindi la convenzione della media misura il suo rischio di ribasso come esattamente zero. La convenzione della soglia, alla domanda di quanto la serie sia scesa sotto zero, risponde che è scesa sotto zero in ognuno dei 250 giorni.

!!! warning "Non sono due stime della stessa grandezza"

    Le due convenzioni rispondono a domande diverse. Misurare rispetto alla media della serie stessa chiede *quanto sono incoerente rispetto a me stesso*; misurare rispetto a una soglia scelta chiede *quanto scendo sotto ciò che avevo chiesto*. Solo la seconda può segnalare che perdere costantemente è un rischio — la prima, per costruzione, non può vedere una perdita che non varia mai.

    Nessuna delle due è sbagliata in generale. La convenzione della media appartiene naturalmente all'ottimizzazione di portafoglio, dove la grandezza da minimizzare è la dispersione attorno alla media che l'allocazione raggiunge. La domanda di questa pagina è l'altra: la soglia è qualcosa che l'investitore dichiara in anticipo, e l'indice riporta il risultato rispetto a essa.

LibreFolio usa la **convenzione della soglia con divisore $N$** — la formula data sopra. La soglia è un parametro esplicito dell'analisi ed è zero a meno che non venga impostata a qualcos'altro, quindi per impostazione predefinita la domanda posta è *quanto è sceso il portafoglio sotto il punto di pareggio, e il suo risultato è stato al di sopra di esso*.

---

## 💡 Interpretazione {: #interpretation }

| Indice di Sortino | Cosa significa il valore |
|---|---|
| $< 0$ | Il rendimento è stato inferiore alla soglia: il numeratore è negativo qualunque sia stata la deviazione al ribasso |
| $0 - 1.0$ | Meno di un'unità di rendimento in eccesso per unità di deviazione al ribasso |
| $1.0 - 2.0$ | Da una a due unità di rendimento in eccesso per unità di deviazione al ribasso |
| $> 2.0$ | Più di due unità di rendimento in eccesso per unità di deviazione al ribasso — non comune su periodi lunghi, molto meno su periodi brevi e favorevoli |

!!! warning "Leggere la scala prima di leggere il numero"

    Questi intervalli sono espressi in unità di deviazione **al ribasso**, quindi un Sortino e uno Sharpe con lo stesso valore numerico non sono la stessa affermazione su un portafoglio. E come per qualsiasi indice di questa famiglia, il valore dipende dalla finestra e dalla classe di asset su cui è stato misurato: un breve periodo favorevole e un ciclo di mercato completo non producono cifre comparabili, anche per lo stesso portafoglio. La tabella dice cosa *è* il numero, non se è buono.

!!! example "Esempio numerico"

    Rendimento del portafoglio: 12%, Tasso privo di rischio: 3%, Deviazione al ribasso: 10%

    $$So = \frac{0.12 - 0.03}{0.10} = 0.90$$

    Confrontare con Sharpe (se σ totale = 15%): $S = 0.60$. L'indice di Sortino è più alto perché la volatilità al rialzo è esclusa.

---

## 📊 Sharpe vs Sortino {: #sharpe-vs-sortino }

| Aspetto | Sharpe | Sortino |
|--------|--------|---------|
| **Misura del rischio** | Deviazione standard totale | Solo deviazione al ribasso |
| **Penalizza il rialzo?** | Sì ❌ | No ✅ |
| **Ideale per** | Distribuzioni dei rendimenti simmetriche | Rendimenti asimmetrici / con asimmetria |
| **Esempio** | Indice di mercato ampio | Strategie su opzioni, portafogli concentrati |

### 🔑 Quando preferire Sortino {: #when-to-prefer-sortino }

- **Distribuzioni asimmetriche**: Strategie che hanno occasionali grandi guadagni ma perdite controllate
- **Portafogli basati su opzioni**: payoff intrinsecamente asimmetrici
- **Titoli growth**: tendono ad avere distribuzioni dei rendimenti con asimmetria positiva
- **Qualsiasi investitore** che tiene al rischio di ribasso più che al rischio totale

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "Distorsione da campione ridotto"

    La deviazione al ribasso richiede un numero sufficiente di punti dati sotto la soglia. Con pochi rendimenti negativi (ad es., brevi periodi di mercato rialzista), la stima diventa inaffidabile e l'indice di Sortino può risultare ingannevolmente alto.

---

## 🔗 Correlati {: #related }

- 📐 **[Indice di Sharpe](sharpe-ratio.md)** — Variante con volatilità totale
- 📊 **[Volatilità](volatility.md)** — Comprendere la deviazione standard
- 📈 **[Drawdown massimo](max-drawdown.md)** — Un'altra metrica incentrata sul ribasso
