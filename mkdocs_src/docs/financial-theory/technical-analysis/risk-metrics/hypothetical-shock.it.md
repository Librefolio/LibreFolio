# ⚡ Shock Ipotetico

Uno shock ipotetico sostituisce l'episodio storico con uno scelto, il che permette di testare uno scenario che la storia disponibile non ha mai contenuto.

[Replay storico](historical-replay.md) chiede *cosa farebbe quell'episodio a me?* — i movimenti sono reali e tu scegli solo le date. Uno shock ipotetico chiede *cosa succederebbe se decidessi questo?* — tu scegli i movimenti. Nessuno dei due è una previsione, e la differenza tra loro riguarda da dove provengono i numeri.

---

## 🔢 Come viene calcolato lo shock {: #how-the-shock-is-computed }

Scegli una **dimensione** lungo cui applicare lo shock — classe di attività, settore o geografia — e assegni un rendimento ai suoi bucket: *la tecnologia scende del 30%, l'energia sale del 5%*. L'analisi procede poi in due passaggi.

Innanzitutto, lo shock di ciascuna posizione viene composto dalle sue esposizioni a quei bucket:

$$
s_i = \sum_b e_{ib} \cdot \text{shock}_b
$$

dove $e_{ib}$ è l'esposizione della posizione $i$ al bucket $b$. Questo conta più di quanto sembri: una posizione è raramente *in* un singolo bucket. Un fondo diversificato distribuito su più settori riceve una **combinazione ponderata per esposizione** degli shock che hai configurato, non uno solo di essi. Il valore per posizione che leggi è già una miscela.

In secondo luogo, l'impatto sul portafoglio è la somma ponderata di quegli shock per posizione, e il contributo di ciascuna posizione è il suo termine:

$$
r_{shock} = \sum_i w_i \, s_i, \qquad \text{contribution}_i = w_i \, s_i
$$

Non c'è storia di rendimenti in questo calcolo. A differenza di ogni altro strumento analitico della sezione, uno shock ipotetico non legge una singola osservazione passata: richiede i pesi odierni e le classificazioni odierne, e nient'altro. Il risultato riporta zero osservazioni esattamente per questo motivo.

---

## 🧾 Cosa succede a ciò che non hai configurato {: #what-you-did-not-configure }

Uno scenario non è mai completo. Applichi lo shock alla tecnologia, e il portafoglio detiene anche obbligazioni, oro e un fondo a cui non hai mai pensato. Ciò che l'analisi fa con il resto è la cosa più importante in questa pagina — e **non è la stessa cosa per ogni dimensione**.

| Dimensione | Cosa succede a ciò che non hai configurato |
|---|---|
| **Settore**, **geografia** | Non puoi lasciarlo indefinito. Lo scenario viene **rifiutato** a meno che non includa un bucket `Other`, quindi il resto si muove di una quantità **scelta da te** |
| **Classe di attività** | Un bucket non configurato riceve uno shock **zero**, e il risultato etichetta quella riga come *Non configurato → shock zero* |

Il rifiuto nella prima riga avviene alla porta: uno scenario di settore o geografia senza un bucket `Other` viene respinto **prima che venga calcolato alcunché**, quindi non esiste mai un risultato parziale basato su un residuo non dichiarato.

!!! warning "Uno shock zero non è neutralità — è una previsione"

    Lasciare una posizione non sottoposta a shock non la rimuove dallo scenario. Significa che, mentre le azioni scendono del 30%, quella posizione **non si muove**. Questa è un'affermazione sul mondo, e in una svendita generalizzata è di solito generosa.

    Ciò che rende difendibile il design non è che sia cauto — è che l'affermazione è **scritta**. Lo scenario non presume silenziosamente che il resto del portafoglio rimanga fermo; registra, per ogni posizione e ogni bucket, che è stato applicato uno zero perché nulla era stato configurato. L'assunzione rimane comunque un'assunzione. Solo che non è nascosta.

L'asimmetria tra le dimensioni vale la pena di conoscerla piuttosto che giudicarla: su settore e geografia sei **costretto** a dichiarare il residuo, su classe di attività no. In quale stai lavorando decide cosa devi controllare — e se stai applicando lo shock per classe di attività, la cosa da controllare è se qualcosa è tornato come non configurato.

---

## 🖥️ Cosa mostra il risultato {: #what-the-result-shows }

Uno shock ipotetico è offerto nella scheda **Rischio** della dashboard e della pagina di un broker, come secondo strumento di **E se…?**, e nella scheda **Rischio e Scenari** della pagina di dettaglio di un asset. La scheda [Correlazione](../../../user/assets/correlation.md#what-if) della pagina degli asset non lo offre: una selezione non ha pesi da sottoporre a shock.

Nella dashboard e nella pagina di un broker, uno scenario è un clic. Ogni scenario denominato — *Global risk-off*, *Crollo azionario*, *Crisi bancaria*, *Shock Unione Europea* — viene eseguito non appena viene scelto, lungo la dimensione per cui è scritto. **Mostra lo shock per bucket** apre i suoi bucket, ciascuno con il suo shock in percentuale intera; modificarne uno mette da parte lo scenario denominato, poiché ciò che è sullo schermo non è più quello scenario, e **Esegui scenario** esegue quello modificato. Il risultato mostra:

- il totale, $r_{shock}$, come *Questo scenario muoverebbe l'ambito di …*, con l'importo che rappresenta;
- una tabella con **una riga per bucket dello scenario**, non una per posizione, dalla peggiore: lo shock applicato al bucket (**Rendimento**), ciò che le posizioni confluite in esso hanno fatto al totale (**Contributo**: il peso di ciascuna posizione moltiplicato per la parte del suo shock fornita da questo bucket, sommato sulle posizioni, in modo che le righe si sommino al totale), e una barra di quel contributo (**Effetto**), su un'unica scala condivisa da ogni riga;
- quando non tutte le posizioni sono state classificate, una nota che indica la quota che lo è stata — vedi [Quando la classificazione manca](#when-the-classification-is-missing).

La vista posizione per posizione, con la regola dietro ogni shock applicato, è l'audit di seguito. Appare nella scheda **Rischio e Scenari** dell'asset, dove la dimensione e lo shock di ciascun bucket possono anche essere impostati manualmente.

---

## 🔍 Leggere l'audit {: #reading-the-audit }

Nella scheda **Rischio e Scenari** dell'asset, l'impatto è accompagnato da un audit per bucket, che è il punto in cui uno scenario smette di essere qualcosa in cui credi e diventa qualcosa che verifichi. Ogni riga riporta:

| Colonna | Cosa ti dice |
|---|---|
| Bucket di esposizione | A quale bucket della dimensione scelta si riferisce questa riga |
| Esposizione | Quanto della posizione risiede in quel bucket |
| Bucket applicato | Quale shock del bucket è stato effettivamente usato — spesso, ma non sempre, lo stesso |
| Shock | Il rendimento applicato |
| Contributo | Quello shock scalato per l'esposizione |
| Regola | **Come** è stato scelto il bucket applicato |

L'ultima colonna è quella da leggere per prima, perché due posizioni possono mostrare lo stesso shock per ragioni completamente diverse e solo la regola le distingue. Esistono sei regole, e sulla dimensione geografica formano una cascata che viene tentata in ordine:

| Regola | Quando una riga la porta |
|---|---|
| **Diretto** | Il bucket proprio della posizione è uno che hai configurato — il caso ordinario su classe di attività e settore |
| **Paese** | Geografia, primo passo: hai configurato **quel paese** stesso |
| **Gruppo geografico** | Geografia, secondo passo: non il paese, ma un **gruppo che lo contiene**, come un bucket regionale |
| **Other** | Geografia, ultimo passo — e l'equivalente per il settore: nulla di quanto sopra ha corrisposto, quindi si è applicato il residuo obbligatorio |
| **Metadati mancanti → Other** | La classificazione della posizione non era disponibile, quindi è stata trattata come `Other` al 100% |
| **Non configurato → shock zero** | Solo classe di attività: il bucket non è mai stato configurato, ed è stato applicato zero |

Leggendo quella lista dall'alto verso il basso si capisce quanto lontano sia viaggiato uno shock prima di atterrare rispetto alla tua intenzione. Una riga *Paese* è lo scenario che hai scritto; una riga *Other* è il residuo che cattura qualcosa che non hai nominato; una riga *Metadati mancanti* è un problema di classificazione vestito con gli stessi panni.

!!! info "L'ambiguità viene rifiutata, non risolta"

    Un paese può appartenere a più di un gruppo che hai configurato — una posizione in un paese coperto da due bucket regionali sovrapposti non ha un unico shock corretto. Invece di sceglierne uno e riportare un numero, l'analisi **si ferma e segnala il conflitto**, nominando il paese e i gruppi che sono entrati in collisione. È lo stesso principio del bucket residuo, applicato a un caso che la maggior parte degli utenti non anticiperebbe mai: dove lo scenario è genuinamente indeterminato, la risposta non è un valore.

---

## 🏷️ Quando la classificazione manca {: #when-the-classification-is-missing }

Gli shock di settore e geografia dipendono dal sapere a cosa è esposta ciascuna posizione. Quando quei metadati non sono disponibili, la posizione non viene scartata né ipotizzata: viene trattata come **`Other` al 100%**, motivo per cui quelle due dimensioni richiedono il bucket `Other` in primo luogo. La posizione viene segnalata, così il fallback è visibile dove è avvenuto.

!!! info "La cifra di copertura su questo strumento analitico non riguarda la densità dei dati"

    Altrove nella sezione, la copertura descrive quanto densamente è stato campionato un periodo — vedi [Qualità dei dati](data-quality.md). Uno shock ipotetico non legge alcuna storia, quindi su questo strumento analitico la cifra di copertura porta qualcosa di diverso: la quota dell'ambito che è stata classificata da **metadati reali** invece di ricadere su `Other`. Una cifra bassa non significa prezzi radi; significa che gran parte dello scenario è atterrata sul bucket residuo invece che sui bucket che hai configurato.

---

## 💡 Interpretazione {: #interpretation }

Il risultato è un'affermazione lineare a periodo singolo: *se questi movimenti si verificassero, tutti insieme, su un portafoglio composto come oggi, l'impatto sarebbe questo.*

Ogni parola in quella frase è portante.

- **Periodo singolo.** Non c'è un percorso. L'aritmetica fornisce un punto finale, non una sequenza, quindi nulla del cammino verso di esso può essere letto dal risultato — nessun drawdown lungo il tragitto, nessun [tempo di recupero](max-drawdown.md#recovery-time), nessun ordine di eventi.
- **Lineare.** L'impatto è esattamente la somma ponderata di ciò che hai specificato. Non ci sono effetti di secondo ordine, nessun feedback, nessun contagio da un bucket all'altro.
- **Nessuna correlazione.** Questa è la differenza più netta rispetto al resto della sezione. [Correlazione](correlation.md) e [Contributo al rischio](risk-contribution.md) derivano dalla storia come le posizioni si muovono insieme; uno shock ipotetico non lo consulta affatto. Se configuri la tecnologia che scende e le obbligazioni piatte, faranno esattamente questo, qualunque sia stato il loro comportamento congiunto in passato. I co-movimenti nello scenario sono quelli che **tu** hai affermato.

La quota di liquidità non viene sottoposta a shock: non contribuisce nulla all'impatto, quindi un portafoglio che detiene liquidità vede il risultato ridotto dalla sola frazione investita. Per la liquidità questa è un'assunzione molto più piccola che per una posizione non configurata — ma è lo stesso meccanismo.

Usato bene, questo è lo strumento per una domanda che la storia non può rispondere, perché lo scenario che vuoi testare non si è mai verificato. Usato con noncuranza, è un modo per ottenere qualsiasi numero: l'output può essere disciplinato solo quanto gli shock inseriti, e nulla nell'aritmetica ti dirà che uno scenario è implausibile.

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "Non può contraddirti"

    Ogni altra metrica in questa sezione è vincolata dai dati. Questa è vincolata solo dal tuo giudizio: calcolerà fedelmente l'impatto di uno scenario internamente incoerente — uno in cui asset correlati si muovono in direzioni opposte, o in cui uno shock è ben al di fuori di qualsiasi cosa si sia mai verificata — senza alcun segnale che qualcosa non va.

!!! warning "Non dice nulla sulla probabilità"

    L'impatto è condizionato al verificarsi dello scenario esattamente come specificato. L'analisi non assegna alcuna probabilità a ciò, e un impatto maggiore da uno scenario più estremo non è prova che lo scenario sia più probabile. Confrontare due shock confronta due assunzioni, non due rischi.

!!! warning "La composizione è quella odierna"

    Come [Replay storico](historical-replay.md), lo shock viene applicato al portafoglio così come è ora. È un'affermazione sull'esposizione attuale, non su qualcosa che è stato detenuto in precedenza.

---

## 🔗 Correlati {: #related }

- ⏮️ **[Replay storico](historical-replay.md)** — la stessa struttura con un episodio reale invece di uno scelto
- 🧩 **[Contributo al rischio](risk-contribution.md)** — quali posizioni portano il rischio, derivato dalla storia invece che affermato
- 🔗 **[Correlazione](correlation.md)** — i co-movimenti che uno shock ipotetico deliberatamente non usa
- 📉 **[Drawdown massimo](max-drawdown.md)** — la vista consapevole del percorso che uno shock a periodo singolo non può produrre
- 🧪 **[Qualità dei dati](data-quality.md)** — cosa significa copertura sugli strumenti analitici che leggono la storia
