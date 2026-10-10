# 📉 Drawdown a rischio

Il drawdown a rischio applica l'idea del quantile ai drawdown anziché ai rendimenti: è la profondità di drawdown che non dovrebbe essere superata a un livello di confidenza scelto.

Tutto ciò che è il [Value at Risk](value-at-risk.md), lo è anche questo — con una sola sostituzione. Dove quella misura ordina le **perdite** subite dal portafoglio, questa ordina le **distanze al di sotto di un picco** che esso ha attraversato. La ristrettezza è identica, e lo è anche la trappola: segna dove inizia la coda dei drawdown, e tace su tutto ciò che sta oltre.

---

## 🔢 Formula {: #formula }

Il drawdown all'osservazione $t$ è la distanza dal valore più alto raggiunto fino a quel momento:

$$
DD_t = \frac{V_t - \max_{\tau \leq t} V_\tau}{\max_{\tau \leq t} V_\tau} \leq 0
$$

Al livello di confidenza $c$, scrivendo $\alpha = 1 - c$ per la frazione di coda, il drawdown a rischio è il quantile $\alpha$ di quella serie:

$$
DaR_c = \inf\left\{\, d : P(DD_t \leq d) \geq \alpha \,\right\}
$$

In pratica si tratta di un esercizio di ordinamento, esattamente come per il Value at Risk: i drawdown osservati nella finestra analizzata vengono ordinati dal più profondo al meno profondo, e la cifra viene letta nella posizione indicata da $\alpha T$.

!!! info "Segno e lettura"

    Il drawdown a rischio è **non positivo** — zero o negativo. Un drawdown è una caduta da un picco, quindi non può risultare superiore a zero, e una cifra *più profonda* è *più negativa*. Al 95% di confidenza l'affermazione è: in 19 osservazioni su 20 il portafoglio non è sceso sotto il proprio picco più di questo valore, e nella restante osservazione è sceso ancora più in basso — di un ammontare che questa misura non dichiara.

    La $T$ qui conta solo i punti osservati. La linea di base da cui parte un indice di ricchezza porta con sé un drawdown esattamente pari a zero per costruzione, e la famiglia dei quantili la scarta prima dell'ordinamento, quindi non entra nella graduatoria né gonfia il denominatore. L'[indice di Ulcer](ulcer-index.md) la mantiene, senza danno, per una ragione esposta [nella sua pagina](ulcer-index.md#the-divisor).

---

## 🎯 È una statistica d'ordine {: #it-is-an-order-statistic }

La cifra viene letta da una lista ordinata, il che fissa in anticipo due delle sue proprietà.

- **Può riportare solo una profondità che il portafoglio ha effettivamente visitato.** Non c'è interpolazione né distribuzione ipotizzata; il numero è una delle osservazioni, selezionata per posizione. Non può descrivere un drawdown che la storia non ha mai contenuto.
- **È una funzione a gradini di un indice.** Tra una posizione e la successiva non si muove affatto, e quando la posizione cambia salta di un'intera osservazione. È lo stesso meccanismo che fa cambiare il Value at Risk in modo tutto-o-niente, descritto in [ciò che la correzione cambia](value-at-risk.md#what-the-correction-changes).

---

## 🔁 Lo stesso passo che il VaR compie verso il CVaR {: #the-same-step-that-var-takes-to-cvar }

Un quantile si ferma al confine. Due portafogli possono riportare lo stesso drawdown a rischio mentre uno lo supera di un soffio e l'altro crolla ben oltre, e nulla in questa cifra li distingue. Quel silenzio è esattamente ciò che il [drawdown a rischio condizionale](conditional-drawdown-at-risk.md) colma.

| Legge la serie delle **perdite** | Legge la serie dei **drawdown** | A cosa risponde |
|---|---|---|
| [Value at Risk](value-at-risk.md) | **Drawdown a rischio** | Dove inizia la coda? |
| [VaR condizionale](conditional-value-at-risk.md) | [drawdown a rischio condizionale](conditional-drawdown-at-risk.md) | Quanto è profonda una volta che inizia? |

Leggendo le colonne verso il basso si ottengono le due coppie soglia-severità; leggendo le righe in orizzontale si ottiene la stessa domanda posta a una distribuzione e a un percorso. Un quadro completo richiede tutte e quattro, e la coppia a destra è quella che sa che il portafoglio aveva un picco da cui cadere.

---

## 💡 Interpretazione {: #interpretation }

Leggila come quanto in basso rispetto al picco ti trovi tipicamente in una brutta giornata, mai come un pavimento.

- **È una soglia, non un limite.** I drawdown più profondi non sono esclusi — per costruzione, sono attesi alla frequenza dichiarata.
- **Il livello di confidenza cambia la domanda, non la precisione.** Passare dal 95% al 99% riguarda un intervallo più raro, stimato da meno osservazioni, non lo stesso intervallo misurato meglio.
- **Non è il drawdown massimo.** Il [drawdown massimo](max-drawdown.md) è il singolo punto più profondo nella finestra; questo è il livello che una frazione scelta della finestra ha oltrepassato. I due coincidono solo nel limite in cui la coda contiene una sola osservazione.

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "Silenziosa oltre la soglia"

    La misura si ferma al confine della coda dei drawdown. Se le cadute oltre tale confine siano leggermente più profonde o catastroficamente più profonde è un'informazione che essa non porta, e nessun livello di confidenza la recupera. Usa il [drawdown a rischio condizionale](conditional-drawdown-at-risk.md) per la profondità.

!!! warning "Le osservazioni di drawdown non sono indipendenti tra loro"

    Osservazioni consecutive all'interno dello stesso episodio sono quasi lo stesso numero: un portafoglio sotto il picco martedì è quasi certamente sotto il picco mercoledì. La coda di una serie di drawdown è quindi raramente $\alpha T$ eventi separati — è più spesso una manciata di episodi, o uno lungo, contato giorno per giorno.

    Questo rende la cifra meno stabile di quanto suggerisca il suo conteggio di osservazioni, e significa che un singolo declino prolungato può fornire da solo l'intera coda.

!!! warning "Eredita la sua finestra"

    Un quantile empirico è limitato dalla storia da cui è tratto. Una finestra senza episodi severi produce un drawdown a rischio poco profondo — non perché il portafoglio sia sicuro, ma perché nulla di peggio è stato ancora osservato. Un [replay storico](historical-replay.md) o uno [shock ipotetico](hypothetical-shock.md) è il modo in cui uno scenario esterno alla finestra entra nell'analisi.

---

## 🔗 Correlati {: #related }

- 🌊 **[drawdown a rischio condizionale](conditional-drawdown-at-risk.md)** — quanto è profonda la coda dei drawdown oltre questa soglia
- 📉 **[Value at Risk](value-at-risk.md)** — la stessa costruzione del quantile, applicata alle perdite invece che ai drawdown
- 🌊 **[VaR condizionale](conditional-value-at-risk.md)** — la controparte di gravità sulla serie delle perdite
- 📉 **[drawdown massimo](max-drawdown.md)** — la singola caduta più profonda, anziché un tasso
- 🩹 **[indice di Ulcer](ulcer-index.md)** — l'intera serie di drawdown in un solo numero, senza un livello di confidenza
- 🧪 **[qualità dei dati](data-quality.md)** — la finestra e il conteggio di osservazioni da cui è stato letto il quantile
