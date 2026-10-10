---
title: Allocatore PAC
description: Pianifica gli acquisti che avvicinano il più possibile un nuovo investimento alla sua allocazione obiettivo, in unità intere o per importo, senza inviare ordini.
---

# 🧮 Allocatore PAC

L'**allocatore PAC** risponde a una domanda:

> Con il denaro disponibile per questo ciclo di versamenti, quali acquisti
> avvicinano la mia allocazione il più possibile al suo obiettivo?

Apri **Strumenti** dalla barra laterale e fai clic sulla scheda Allocatore PAC:
si apre un pianificatore guidato. Descrivi uno scenario passo per passo, premi
**Calcola piano** e ottieni un piano di acquisto da valutare. È una
simulazione: non si acquista nulla e nessun ordine viene inviato a un broker.

## 🗺️ Usare il pianificatore

Il pianificatore ti guida attraverso questi passi, in ordine. Il passo **FX**
appare solo quando lo scenario necessita di tassi di cambio.

### 🎬 Scenario

Pianifichi un nuovo investimento, un "PAC puro": il calcolo parte da un
portafoglio vuoto, quindi ciò che già possiedi non viene conteggiato, e
ripartisce la liquidità che scegli tra gli asset, il più vicino possibile ai
pesi obiettivo.

Qui imposti la **Valuta di valutazione**, in cui gli importi vengono
confrontati e riepilogati. All'inizio è la **Valuta predefinita** delle tue
preferenze. Il denaro resta nella propria valuta: ogni conversione necessaria
appare nel piano.

La data di riferimento è sempre oggi: il pianificatore la imposta di nuovo
prima di ogni copia da LibreFolio e prima di ogni calcolo.

### 💰 Liquidità

Da dove viene il denaro? Puoi combinare diverse fonti:

- **Dai tuoi Broker**: liquidità già presente sui tuoi broker in LibreFolio.
  Scegli quanto utilizzarne.
- **Nuovo versamento**: denaro nuovo che aggiungi, come la rata PAC.
- **Conto esterno**: un saldo su un conto non registrato in LibreFolio, per
  esempio presso la tua banca. Dichiari quanto c'è e quanto utilizzarne.
  Niente viene acquistato da un conto esterno: il suo denaro viene inviato a un
  broker.

Il broker che riceve un versamento o il denaro di un conto esterno viene scelto
nel passo **Broker**. Ogni importo resta nella propria valuta.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-step-liquidity" alt="Il passo Liquidità, accanto all'elenco dei passi: liquidità da un broker, con l'importo da usare su quanto disponibile; un nuovo versamento, con il suo importo e la sua valuta; e un conto esterno, con la sua liquidità dichiarata e l'importo da usare">
</div>

### 🏦 Broker

Aggiungi i broker dove il piano può acquistare: **Scegli Broker esistente** ne
copia uno dei tuoi, e **Broker manuale** ne aggiunge uno a mano. In entrambi i
casi sono dati di scenario: il broker stesso non viene mai modificato. Le
commissioni e le modalità d'ordine non sono registrate in LibreFolio, per
questo le imposti qui.

Per ogni valuta in cui acquisti, imposta:

- La modalità d'ordine: **Per numero di unità** o **Per importo**.
- L'**Incremento** $\Delta$: ogni ordine proposto è un multiplo intero di
  esso. Con $q$ la dimensione di un ordine, in unità o come importo:

    $$
    q = k\,\Delta, \qquad k = 0, 1, 2, \dots
    $$

    Per numero di unità, $\Delta$ è un numero intero: $\Delta = 1$ significa
    solo unità intere. Per importo, $\Delta$ è il più piccolo importo che puoi
    inserire, come $\Delta = 0.01$, e le unità che ottieni possono essere
    frazioni di unità.

- La **Commissione di acquisto**: una **Parte fissa** $f$ più una
  **Percentuale** $r$ dell'importo dell'ordine $A$, margine sul prezzo
  incluso. Il **Minimo** $f_{\min}$ e il **Massimo** $f_{\max}$ limitano solo
  la parte percentuale, e un **Massimo** vuoto non imposta alcun limite
  superiore:

    $$
    \text{commissione} = f + \min\big(\max(r\,A,\ f_{\min}),\ f_{\max}\big)
    $$

    La commissione viene addebitata su ogni ordine, e nessun ordine significa
    nessuna commissione. Viene pagata dalla tua liquidità e non viene
    investita. Per esempio, con $r = 0.19\%$, $f_{\min} = 1.50$,
    $f_{\max} = 18$ e nessuna parte fissa, un ordine di $500$ paga $1.50$, uno
    di $2{,}000$ paga $3.80$, e uno di $20{,}000$ paga $18$.

Ogni broker ha anche due impostazioni proprie:

- **Liquidità utilizzabile**: il denaro che il piano può usare per acquistare
  lì, cioè la liquidità propria del broker più i versamenti e gli altri conti
  che consenti. Tutti sono consentiti all'inizio: puoi escludere una fonte,
  limitare quanto ne viene usato lì e assegnarle una **Priorità** ($0$ =
  preferita).
- **Conversione di valuta**: **Converti tu prima di acquistare** o
  **Il Broker converte quando acquisti**. Entrambe convertono al tasso del
  passo **FX** meno lo spread, quindi il calcolo è lo stesso in entrambi i
  casi: cambia solo il modo in cui il piano mostra la conversione.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-step-brokers" alt="L'editor del broker, come dati di scenario che lasciano il broker invariato: sotto Come acquisti, valuta per valuta, la Modalità d'ordine Per importo, l'Incremento e la Commissione di acquisto con minimo, percentuale, massimo e parte fissa; Conversione di valuta con Il Broker converte quando acquisti selezionato; e Applica alla bozza">
</div>

Non ancora supportato: un regime fiscale, minusvalenze e commissioni di vendita
per un broker.

### 💼 Asset

Aggiungi gli asset che il piano può acquistare, in qualsiasi combinazione:

- cerca gli asset registrati in LibreFolio;
- aggiungi **I tuoi Asset**: quelli con una posizione aperta oggi nei tuoi
  broker, aggiunti solo come righe, senza quantità;
- aggiungi un **Asset manuale**.

Ogni prezzo è:

- **Auto**: l'ultimo prezzo memorizzato in LibreFolio, letto di nuovo appena
  prima del calcolo. Nessun provider di dati viene chiamato.
- **Manuale**: un tuo prezzo, usato come digitato e mai più letto.

Un prezzo mancante resta nella bozza: il calcolo lo richiede.

La composizione per paese, settore e tipo, copiata dall'asset o digitata,
alimenta solo le mappe e le barre di esposizione del risultato, non il calcolo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-step-assets" alt="Il passo Asset: Cerca Asset, I tuoi Asset e Asset manuale, poi un asset da LibreFolio prezzato Auto, un altro prezzato Manuale, e un asset manuale con il suo badge Manuale, ciascuno con il suo prezzo e la sua composizione">
</div>

### 🔀 Route

Per ogni broker, scegli quali asset può acquistare: **Consenti tutti**,
**Escludi tutti**, o fai clic su ciascuno.

Poi, solo dove ti servono, imposta limiti su ciascuna route. Sono misurati come
gli ordini di quel broker, in unità o come importo. Con $q$ l'acquisto
dell'asset su quel broker:

- **Acquisto minimo** $q_{\min}$: se il piano acquista lì, acquista almeno
  questa quantità, quindi $q = 0$ o $q \ge q_{\min}$.
- **Acquisto obbligatorio** $q_{\text{req}}$: viene acquistato in ogni caso,
  $q \ge q_{\text{req}}$. Se le risorse non bastano, il piano diventa
  impossibile.
- **Acquisto massimo** $q_{\max}$: il massimo che il piano può acquistare lì,
  $q \le q_{\max}$.

Altre due impostazioni determinano come il piano acquista lì:

- **Priorità** ($0$ = preferita): rompe solo le parità tra piani ugualmente
  vicini all'obiettivo.
- **Margine sul prezzo** $m$: ogni acquisto viene conteggiato a $p\,(1 + m)$
  invece del prezzo $p$ di una unità, per coprire un prezzo che sale prima
  dell'ordine. Un margine dello $0.5\%$ su un prezzo di $100$ conta $100.50$.
  La differenza è una riserva, non investita. Per importo, un ordine di $A$
  acquista $A / \big(p\,(1 + m)\big)$ unità.

I campi vuoti non limitano nulla.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-step-routing" alt="Il passo Route: per ogni broker, le sue impostazioni di ordine, Consenti tutti, Escludi tutti e quanti asset può acquistare; sul primo broker, asset esclusi e uno consentito con il suo Acquisto minimo, Acquisto obbligatorio, Acquisto massimo, Margine sul prezzo e Priorità">
</div>

### ⚖️ Obiettivi

Qui ripartisci il denaro che investi ora tra gli asset: un obiettivo $w_i$ per
asset, in percentuale, decimali ammessi. Per calcolare, gli obiettivi devono
sommare esattamente a $100\%$:

$$
\sum_i w_i = 100\%
$$

Due azioni ti aiutano ad arrivarci:

- **Bilancia tutti** ridimensiona ogni obiettivo, mantenendo i loro rapporti:

    $$
    w_i' = \frac{w_i}{\sum_j w_j} \cdot 100\%
    $$

    Se sono tutti $0$, ogni asset riceve una parte uguale. L'arrotondamento
    mantiene il totale esattamente a $100\%$. Per cambiare solo alcune righe,
    **Bilancia a 100%** su una riga dà a quell'asset ciò che manca, o toglie
    l'eccesso, e **Bilancia le righe selezionate a 100%** ridimensiona solo le
    righe che spunti.

- **Copia distribuzione attuale** legge quanto ciascuno di questi asset pesa
  oggi nei broker che spunti, contando solo questi asset e non la liquidità.
  Con $H_i$ il valore di mercato dell'asset $i$ detenuto lì oggi:

    $$
    w_i = \frac{H_i}{\sum_j H_j} \cdot 100\%
    $$

    I pesi sono arrotondati a $0.01$ punti percentuali e sommano comunque
    esattamente a $100\%$, e un asset inserito a mano riceve $0$. Questi sono
    solo pesi, una base da modificare e non un consiglio: li vedi prima di
    usarli, e un obiettivo che hai modificato non viene sovrascritto senza la
    tua conferma.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-step-targets" alt="Il passo Obiettivi dell'allocatore PAC: una percentuale obiettivo per asset, con la sua barra di distribuzione, che somma a 100%; Bilancia tutti, disabilitato perché gli obiettivi sono già bilanciati; e Copia distribuzione attuale">
</div>

### 💱 FX (solo quando serve)

Questo passo appare solo quando lo scenario necessita di tassi di cambio.
Contiene un tasso di cambio $x$ per ogni coppia di valute in gioco, ciascuno
**Auto** o **Manuale**:

- **Auto**: l'ultimo tasso memorizzato in LibreFolio, letto quando il passo si
  apre e di nuovo appena prima del calcolo. Nessun provider di dati viene
  chiamato.
- **Manuale**: un tuo tasso di cambio.

Contiene anche uno **Spread di conversione** $s$: una percentuale di ogni
importo convertito, mantenuta come margine per una variazione del tasso
ufficiale o per le commissioni del broker. Convertire un importo $D$ al tasso
$x$ (unità ricevute per ogni unità convertita) dà

$$
D \cdot x\,(1 - s)
$$

invece di $D \cdot x$. La valutazione, che confronta e somma importi nella
valuta di valutazione, usa il tasso ufficiale $x$ senza spread; le conversioni
usano il tasso con lo spread, $x\,(1 - s)$.

I tassi devono anche essere coerenti tra loro, affinché nessuna conversione
crei valore: con liquidità in CHF, un asset in USD e valutazione in EUR, per
esempio, un CHF convertito in USD dopo lo spread non può valere più in EUR di
un CHF,

$$
x_{\text{CHF} \to \text{USD}}\,(1 - s)\,x_{\text{USD} \to \text{EUR}}
\le x_{\text{CHF} \to \text{EUR}}
$$

e lo stesso vale per ogni conversione che il piano può richiedere tra due
valute diverse dalla valuta di valutazione. Altrimenti il calcolo non parte e
l'esito è **Input non valido** (vedi
[Leggere il risultato](#reading-the-result)): la causa può essere un tasso
**Manuale** o tassi **Auto** da giorni o fonti diversi, quindi allinea i tassi
o imposta uno **Spread di conversione** che copra la differenza. È tollerato
solo uno scarto abbastanza piccolo da derivare dalla memorizzazione dei tassi
con dieci decimali: la conversione usa allora il tasso attraverso la valuta di
valutazione quando questo è inferiore,

$$
\min\left(x_{\text{CHF} \to \text{USD}}\,(1 - s),\;
\frac{x_{\text{CHF} \to \text{EUR}}}{x_{\text{USD} \to \text{EUR}}}\right)
$$

così non crea comunque valore. Quando i tassi concordano, questo tasso è il
solito $x\,(1 - s)$. I tuoi tassi non vengono modificati: ogni conversione del
piano mostra il tasso da cui parte come *spot* e il tasso che usa come
*effettivo*.

Ogni importo che il piano registra viene arrotondato una volta, sul suo valore
finale esatto, all'unità minima della valuta (il centesimo per EUR o USD), e
sempre a sfavore del piano: gli importi che riceve (ciò che una conversione
eroga) sono arrotondati per difetto, gli importi che paga (il costo di un
ordine e la sua commissione) sono arrotondati per eccesso. Così
l'arrotondamento non migliora mai un piano, suddividere una conversione in
conversioni più piccole non guadagna nulla, e la parte di arrotondamento di
**Non investito** non è mai negativa. La colonna **Arrotondamento** di
**Saldi per broker e valuta** mostra quanto di ogni riga deriva
dall'arrotondamento: ≈ contrassegna una cifra mostrata arrotondata, come quando
la differenza esatta non ha una forma decimale finita (per esempio dopo aver
convertito USD → EUR a $1/1.085$), e una differenza inferiore all'unità minima
mantiene le cifre necessarie, come ≈ −0,0022 anziché ≈ −0,00.

Quando LibreFolio non ha un tasso per una coppia, il passo offre **Aggiungi la
coppia** o **Scarica i tassi**: ciascuno apre la finestra corrispondente della
pagina FX, e nulla viene aggiunto o scaricato finché non confermi lì.

Non ancora supportato: un tasso di cambio o uno spread diverso per broker, un
margine di sicurezza sul tasso, una commissione di conversione oltre lo spread,
e conversioni in più di un passo (per esempio EUR → USD → CHF).

### 🧠 Strategia

La strategia è **Proporzionale**: solo acquisti, non vende nulla.

Tra tutti i piani di acquisto che rispettano le tue impostazioni, sceglie il
migliore con una cascata di criteri, ciascuno dei quali decide solo tra i piani
ancora in parità su quelli precedenti:

1. **Vicinanza agli obiettivi (distanza L2)**: la distanza più piccola

    $$
    D = \sum_i \big(V_i - w_i\,R\big)^2
    $$

    dove $V_i$ è il valore dell'asset $i$ dopo il piano, $w_i$ il suo
    obiettivo, e $R$ la **Base degli obiettivi**: la liquidità che hai scelto
    che può raggiungere un broker dove può acquistare (in un PAC nulla è già
    investito). Quindi $w_i\,R$ è il valore ideale dell'asset $i$. I valori
    sono nella valuta di valutazione, al prezzo di quotazione, senza commissioni
    o margine sul prezzo. Elevare al quadrato fa pesare di più gli scarti
    grandi, e $D$ è misurato in unità monetarie al quadrato, per esempio EUR².

2. **Denaro non investito**: il minimo denaro lasciato fuori dagli asset,
    $R - \sum_i V_i$.

3. **Priorità del broker e della fonte**: la somma più piccola dei numeri di
    **Priorità** degli ordini e delle fonti di liquidità che il piano usa.

4. **Costi espliciti (commissioni, spread, margine)**: il totale più basso di
    commissioni, spread di conversione e margine sul prezzo, nella valuta di
    valutazione.

5. **Numero di ordini**: il minor numero di ordini.

Un ordine fisso di asset e broker risolve qualsiasi parità finale, quindi una
ricerca che si completa dà sempre lo stesso piano per gli stessi dati; una
ricerca interrotta da un limite di tempo o di nodi può dare un piano diverso su
una macchina più lenta o più occupata.

### ✅ Riepilogo

Un ultimo controllo prima del calcolo. Elenca la copia completa che verrà
inviata (il backend riceve questa copia, e solo questa), segnala i campi ancora
da completare e offre **Calcola piano**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-step-review" alt="Il passo Riepilogo: il riepilogo di ogni passo, con il passo Obiettivi segnalato; il campo ancora da completare prima di calcolare, con un link al suo passo; Dati di calcolo compressi; e Calcola piano, disabilitato finché quel campo non viene completato">
</div>

### 📋 Valori copiati o digitati

Il pianificatore funziona senza alcun broker o asset registrato: tutto può
essere digitato. Quando preferisci partire dai tuoi dati LibreFolio, li copi con
un'azione esplicita: **Scegli Broker esistente**, **Dai tuoi Broker**, la
ricerca asset o **I tuoi Asset**, e **Copia distribuzione attuale**. Nel passo
**FX**, un tasso **Auto** viene letto da LibreFolio non appena il passo si apre.

Ogni valore mostra da dove proviene (**Copiato**, **Manuale** o **Modificato**),
e una copia mostra anche la sua data. Una copia non segue la sua fonte mentre
modifichi, e una copia che hai modificato può essere ripristinata.

Quando premi **Calcola piano**, il pianificatore legge di nuovo da LibreFolio i
prezzi, i tassi e i saldi che hai copiato e non hai modificato. I valori che hai
digitato o modificato restano come sono. Se quella lettura fallisce, non viene
calcolato nulla: puoi **Riprovare**, o **Calcolare con i dati copiati** per usare
le copie precedenti.

### ⏳ Mentre calcola

Mentre la richiesta è attiva, il pianificatore mostra **Calcolo in corso** e la
configurazione è bloccata. **Interrompi attesa** interrompe solo l'attesa: il
server può comunque finire, e quella risposta viene scartata.

Se modifichi la bozza dopo un risultato, appare un banner **Risultato non
aggiornato**: i valori precedenti possono ancora essere consultati, ma non
descrivono più la bozza corrente. Dal banner, **Torna al Riepilogo** riporta
all'ultimo passo, e **Elimina il risultato precedente** rimuove il vecchio
risultato e ti porta lì.

## 📊 Leggere il risultato {: #reading-the-result }

Un piano calcolato si apre con un'intestazione: la data dello scenario, la
valuta di valutazione e la revisione della bozza, poi una riga di badge. Ogni
badge si spiega quando lo indichi, lo tocchi o lo metti a fuoco. Un piano mostra
anche la sua **distanza L2** dagli obiettivi (la $D$ del passo **Strategia**),
quanto è **Non investito** e quante note ha lasciato il calcolo; le note sono
elencate subito sotto, in **Note sul calcolo**. **Modifica configurazione** ti
riporta al passo **Riepilogo**, e **Calcola nuovo piano** esegue di nuovo il
calcolo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-result" alt="Un piano calcolato: l'intestazione con i suoi badge di esito, la distanza L2, Non investito e le note, Modifica configurazione e Calcola nuovo piano; i Valori principali, ciascuno con le sue parti, accanto al riquadro Calcolo; e la tabella Allocazione per Asset, con la quota obiettivo di ogni asset accanto alla sua quota dopo il piano, il suo valore dopo il piano e il suo valore ideale, e i totali">
</div>

Un calcolo termina con uno di questi esiti:

| Esito | Cosa significa |
|---|---|
| **Piano disponibile** | Un piano che rispetta ogni vincolo. Un secondo badge dice quanto vale. **Ottimale dimostrato**: il solver ha dimostrato, entro il suo piccolo margine di calcolo (che cresce con gli importi), che non esiste un piano migliore, obiettivo per obiettivo nell'ordine del passo **Strategia**, e la verifica esatta del piano corrisponde ai suoi numeri. **Ottimalità non dimostrata**: il solver ha raggiunto il suo limite di tempo o di nodi, oppure i suoi stessi numeri non corrispondono alla verifica esatta del piano; è quindi il miglior piano trovato, ma non è dimostrato che sia il migliore. |
| **Nessuna operazione** | Con la liquidità che hai scelto, nessun acquisto soddisfa i vincoli: il piano è non fare nulla. Nessun ordine, nessun cambio di valuta e nessun finanziamento. |
| **Non ammissibile con questi vincoli** | Contrassegnato **Inammissibilità dimostrata**: nessuna combinazione soddisfa insieme tutti i vincoli rigidi. I vincoli coinvolti sono elencati (ogni **Acquisto obbligatorio**, e la liquidità che può raggiungere i broker), ciascuno con un link al passo dove puoi modificarlo. Il pianificatore non sceglie quale allentare, e nessun piano parziale viene mostrato come valido. |
| **Nessun piano entro i limiti** | Il solver non ha trovato alcun piano prima di raggiungere il suo limite. Questa non è una prova che non ne esista nessuno. Una ricerca più leggera aiuta: meno asset o route, un **Acquisto massimo** più basso, o un **Incremento** maggiore. |
| **Servono più dati** | Manca qualcosa. La tua bozza è intatta, e nessun asset viene rimosso silenziosamente: aggiungi il dato mancante o rimuovi tu l'asset. |
| **Input non valido** | Alcuni dati non sono validi. |
| **Scenario non supportato** | Non è un errore nei tuoi dati: lo strumento non gestisce ancora questo caso. |

Ogni piano mostrato è stato verificato di nuovo in aritmetica decimale esatta,
indipendentemente dal solver: questo è il badge **Verificato in decimale**. Un
ultimo badge dice come è terminata la ricerca: **Completato** (il solver ha
terminato la sua ricerca da solo), **Limite di tempo** o **Limite di nodi**.
Quando è stato trovato un piano ma la ricerca si è fermata a un limite, un
avviso aggiunge che potrebbe esistere un piano migliore; il risultato resta
completo e può essere consultato. Se l'arrotondamento all'unità minima della
valuta lascia un broker leggermente scoperto, un avviso dice quanta liquidità in
più serve a quel broker per eseguire il piano.

Gli ultimi tre esiti significano che il calcolo non è potuto partire sui tuoi
dati: nulla viene calcolato, e i problemi trovati sono elencati, con un link al
passo interessato quando esiste. **Dettagli** aggiunge il codice backend di ogni
problema.

Gli errori di piattaforma, come un timeout, una coda piena o un worker in crash,
non sono conclusioni finanziarie sul tuo scenario: la tua bozza resta intatta,
quindi riprova più tardi. Se lo strumento non è disponibile, vedi
[Impostazioni → Informazioni → Diagnostica plugin](../../settings/about.md).

### 🗂️ Come è disposto un piano

Sotto l'esito, un piano è disposto in questo ordine:

1. **Valori principali**: il piano in pochi numeri, **Base degli obiettivi**,
   **Investito dopo**, **Non investito**, **Liquidità scelta**, **Costi** e
   **Ordini**, ciascuno con un **?** che lo spiega e, sotto il valore, le parti
   che lo compongono. Accanto, il riquadro **Calcolo** mostra per quanto tempo
   ha lavorato l'ottimizzatore, il tempo consentito per ogni obiettivo e quanti
   obiettivi ha chiuso.
2. **Allocazione per Asset**: per ogni asset, la sua quota obiettivo accanto
   alla sua quota dopo il piano, con il suo valore ideale $w_i\,R$, il suo
   valore dopo il piano $V_i$, lo scarto dall'ideale $V_i - w_i\,R$, e il
   valore acquistato.
3. **Piano operativo**: i passi da seguire, in ordine. Prima la liquidità
   (**Liquidità disponibile**, **Giroconto**, **Deposito**), poi i cambi di
   valuta che fai tu stesso, poi una tabella di ordini per broker, con
   l'**Istruzione** da inserire presso il broker, il **Prezzo**, l'**Importo
   ordine** e la **Commissione**. Una conversione che il broker fa da solo
   quando acquisti non ha numero: appare sopra gli ordini di quel broker come
   una **Conversione automatica**. Questa sezione è mostrata solo quando il
   piano ha qualcosa da fare.
4. **Esposizioni – ideale vs effettivo**: mappe e barre per paese, tipo e
   settore, costruite dalle composizioni degli asset. I grafici non cambiano il
   piano.
5. **Saldi per broker e valuta**: come si muove ogni saldo di cassa, e cosa
   resta.
6. **Dimostrazione e solver**: come è stato stabilito l'esito. I badge di esito,
   dimostrazione e arresto, il valore esatto di ogni obiettivo, le fasi del
   solver e le tempistiche backend.

**Allocazione per Asset** e **Piano operativo** sono già aperti; le altre
sezioni si aprono su richiesta, e **Espandi tutto** / **Comprimi tutto** le apre
o le chiude insieme. Senza un piano (**Non ammissibile con questi vincoli** o
**Nessun piano entro i limiti**), **Dimostrazione e solver** è l'unica sezione,
e i valori principali mostrano solo il riquadro **Calcolo**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-result-plan" alt="Il Piano operativo: passi numerati, prima i giroconti e il deposito che portano la liquidità a un broker, poi un cambio valuta con il suo tasso, ciascuno con il suo importo; poi gli ordini di quel broker, con Istruzione, Prezzo, Importo ordine e Commissione; e gli ordini del broker successivo">
</div>

Fai clic su un ordine, o sul suo pulsante **Dettaglio**, per aprire il suo
dettaglio: l'istruzione, la quantità economica, i prezzi usati (prezzo sorgente,
prezzo medio e prezzo applicato con il margine sul prezzo), l'addebito di
liquidità e la commissione, le conversioni che lo pagano, e la priorità, il
limite e i minimi della sua route. **Mostra provenienza** elenca da dove
proviene ogni valore, **Copiato** o **Manuale**, con la data e l'ora della copia
o del tuo inserimento.

**Dimostrazione e tempistiche**, in alto nel risultato, apre **Dimostrazione e
solver** e scorre fino a essa.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-result-proof" alt="La sezione Dimostrazione e solver: i badge Esito, Dimostrazione e Arresto; il valore esatto di ogni obiettivo, in ordine, con lo spareggio finale; la tabella Fasi del solver; le Tempistiche backend; e Dove è andato il tempo, una barra delle fasi del calcolo">
</div>

Ogni cifra proviene dalla contabilità del backend; l'interfaccia non somma
nulla. Con la modalità privacy attiva (vedi
[Preferenze utente](../../settings/preferences.md)), il risultato nasconde ciò
che direbbe quanto possiedi: ogni importo (valori principali, valori, saldi,
importi degli ordini, commissioni e costi, e i valori di obiettivo e solver
misurati in denaro, **distanza L2** inclusa), ogni quantità, e i limiti di
acquisto di una route (**Acquisto minimo**, **Acquisto obbligatorio**, **Acquisto
massimo**). Sono nascosti anche gli importi nei problemi elencati quando un
calcolo non è potuto partire. Prezzi di mercato, tassi di cambio, percentuali
(obiettivi, quote, pesi di esposizione, spread e margini), incrementi,
priorità, conteggi e date restano visibili, perché non dicono nulla su quanto
possiedi.

## 🧮 Cosa fa il motore di calcolo

Il motore dietro questo strumento pianifica **acquisti**. Dato un insieme di
asset con i loro prezzi, i broker e le route d'ordine utilizzabili per
raggiungerli, la liquidità e i versamenti disponibili, e un peso obiettivo per
asset, cerca la combinazione di acquisti la cui allocazione risultante si
colloca il più vicino possibile a quegli obiettivi.

Vale la pena conoscere tre proprietà, perché determinano ciò che il
pianificatore può promettere:

- **Acquista negli incrementi di ciascun broker.** Unità intere o importi,
  sempre in multipli dell'incremento che imposti: incrementi, commissioni e le
  valute coinvolte fanno parte del problema che risolve, non di un passo di
  arrotondamento applicato dopo.
- **I suoi numeri pubblicati provengono da aritmetica esatta.** Ogni piano
  candidato viene riverificato esattamente prima che qualsiasi cosa sia
  mostrata. Un piano che non supera quella verifica non viene mai pubblicato.
- **Non spaccia mai per ottimale un piano non dimostrato.** Un piano interrotto
  da un limite di tempo o di nodi viene mostrato come il migliore trovato e
  contrassegnato **Ottimalità non dimostrata**. Lo stesso vale per un piano la
  cui verifica esatta non corrisponde ai numeri del solver, anche quando la
  ricerca è terminata da sola. Quando non viene trovato alcun piano, lo dice
  invece di indovinare. Con importi pari o superiori a circa dieci miliardi di
  unità di una valuta, i calcoli del solver possono perdere precisione: lo
  strumento può quindi fermarsi con un errore, o contrassegnare il piano come
  **Ottimalità non dimostrata**.

Un calcolo completato riporta quindi uno dei pochi esiti onesti elencati in
[Leggere il risultato](#reading-the-result).

Il motore pianifica solo acquisti. Non pianifica vendite.

## 🎯 Come va letto il suo obiettivo

L'allocatore PAC distribuisce la liquidità disponibile **ora** — liquidità
esistente più nuovi versamenti. I suoi obiettivi descrivono come quel denaro
dovrebbe essere allocato; non descrivono la composizione finale di un
portafoglio che già possiedi.

Il calcolo non prende affatto in input le posizioni che già possiedi, quindi
modificarle non può cambiare ciò che questo strumento pianifica. **Copia
distribuzione attuale** le trasforma solo in pesi obiettivo da modificare, e
quei pesi non seguono cambiamenti successivi.

## 🚫 Cosa questo strumento non fa mai

Il pianificatore e il calcolo dietro di esso restano entro il contratto della
piattaforma Strumenti:

- non piazza ordini, non esegue operazioni e non contatta un broker;
- non scrive nei tuoi asset, broker o transazioni;
- non legge il tuo portafoglio da solo: il calcolo riceve solo lo scenario
  inviato dal **Riepilogo**, e il pianificatore legge i tuoi dati LibreFolio solo
  quando copi qualcosa o apri il passo **FX** (per i suoi tassi **Auto**), poi
  di nuovo appena prima di un calcolo per i valori copiati che non hai
  modificato;
- il suo risultato è un piano da valutare, non un consiglio e non
  un'istruzione.

## 🔒 I tuoi dati finanziari

Il calcolo viene eseguito sullo scenario inviato con la richiesta. Non gli viene
passato un portafoglio live, una connessione al database o la tua sessione
autenticata, e non produce nulla che venga memorizzato.

La tua bozza vive solo nella pagina aperta: non viene salvata né sul server né
nel browser. Lasciare il pianificatore, o ricaricare o chiudere la scheda, con
una bozza in corso ti chiede prima di confermare. Uscendo dall'account o
cambiando account la bozza viene eliminata senza chiedere.

Come sempre, evita di incollare valori reali di portafoglio, esportazioni del
broker o identificatori di conto in esempi o messaggi di supporto.

## 🔗 Correlati

- [Panoramica degli strumenti](../index.md)
- [Preferenze utente](../../settings/preferences.md), incluse la modalità privacy
