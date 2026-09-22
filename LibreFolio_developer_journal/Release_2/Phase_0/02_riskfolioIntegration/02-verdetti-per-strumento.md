# 02 — Verdetti per strumento

**Data**: 16 Settembre 2026
**Criterio**: *ogni strumento che non risponde a una delle quattro domande viene tagliato.*
**Fonte del criterio**: [`01-tesi-e-quattro-domande.md`](./01-tesi-e-quattro-domande.md)

Ogni scheda riporta: cosa fa lo strumento, a quale domanda risponde, il verdetto e la
destinazione.

---

## Quadro d'insieme

| Strumento | Verdetto | Livello |
|---|---|---|
| Volatilità annualizzata | 🟢 core | L3 (unità di misura) |
| Max drawdown + durata | 🟢 core — **il più importante** | L1 |
| Drawdown corrente / underwater | 🟢 core | L1 |
| CVaR (+ VaR secondario) | 🟢 core, **riformulato in scala temporale** | L1 |
| Correlazione | 🟢 core — **valore #1 del sottosistema** | L2 |
| Contributo al rischio (PCTR) | 🟢 core, sottovalutato | L2 |
| Sortino / Sharpe | 🟡 tieni, gerarchia da correggere | L3 |
| Beta / active return | 🟢 core con benchmark persistente | L3 |
| Segnali rolling | 🟡 restano dove sono | Overview Asset Detail |
| Shock ipotetico | 🟢 core, **interazione da invertire** | L4 |
| Replay storico | 🟢 core, ottimo rapporto valore/costo | L4 |
| Monte Carlo | 🟡 **da rifondare** fino al livello 3 | L4 |
| Qualità del dato | 🟢 **non negoziabile** | trasversale |
| Tracking error / Information ratio | 🔴 **tagliato** | → TODO |
| Portfolio optimization | 🔴 **rinviato** | → TODO |

---

# 🟢 Core

## Volatilità annualizzata

**Cosa fa.** Deviazione standard dei rendimenti giornalieri moltiplicata per √A, dove
`A = osservazioni incluse × 365 / giorni di calendario`. Misura *quanto oscilla*, non
*quanto perdi*. È **simmetrica**: tratta un +8% esattamente come un −8%.

**Perché serve.** È l'unico numero che rende confrontabili due portafogli diversi.
*«Questo si muove come un 12% l'anno»* è un'unità di misura, non un giudizio.

**Verdetto.** Core, ma come **unità di misura di L3**, non come metrica di L1: da sola
non dice quanto puoi perdere.

**Nota.** L'annualizzazione osservata è una scelta sopra la media del settore: per
l'equity tende naturalmente a ~252, per le crypto 24/7 a ~365, senza costanti
hardcoded. Va conservata e va spiegata all'utente.

---

## Max drawdown + durata

**Cosa fa.** La massima caduta dal picco al minimo successivo, e per quanti giorni si è
rimasti sotto il picco precedente.

**Perché serve.** È l'unica metrica che l'essere umano **sente davvero**. Nessuno
abbandona un piano di investimento a causa della varianza; lo abbandona perché ha visto
−38% e sono passati 19 mesi. La **durata** vale quanto la profondità: risponde a
*«per quanto tempo avrei dovuto resistere?»*, che è la vera domanda.

**Verdetto.** Core, e il più importante dell'intero pacchetto. Va con il **recupero
richiesto** accanto (−38% richiede +62% per tornare in pari): è il modo più efficace di
far capire l'asimmetria delle perdite.

---

## Drawdown corrente e underwater

**Cosa fa.** Quanto si è sotto il picco **adesso**, da quando, e la serie storica della
distanza dal picco nel tempo (*underwater chart*).

**Perché serve.** È il grafico di rischio più leggibile che esista: una sola linea,
sempre ≤ 0, dove ogni avvallamento è un periodo di sofferenza e la sua larghezza è la
durata. Non richiede alcuna alfabetizzazione statistica.

**Verdetto.** Core.

---

## CVaR e VaR storici

**Cosa fanno.** Il **VaR** al 95% su orizzonte *h* è la perdita che viene superata nel
5% dei periodi peggiori. Il **CVaR** (o Expected Shortfall) è la *media* delle perdite
in quel 5%.

**Il difetto del VaR.** Dichiara una soglia e **tace su cosa c'è oltre**. Non è
subadditivo: in casi patologici può segnalare che diversificare aumenta il rischio. Il
CVaR risolve entrambi i problemi e costa esattamente lo stesso.

**Limite della versione storica.** Non assume alcuna distribuzione, ma di conseguenza
**non vede mai un crash che non sia nel campione**.

**Verdetto.** Core, ma **riformulati**: il problema non era la metrica, era accostare
una perdita a 1 giorno a un drawdown pluriennale senza dichiarare la scala. Vanno
presentati come **gradini bassi della scala temporale di L1**, con il CVaR come numero
principale, gli euro accanto alla percentuale, e un link alla documentazione per riga.

---

## Correlazione

**Cosa fa.** Misura quanto due asset si muovono insieme, da −1 a +1.

**Perché serve.** È **la** metrica di diversificazione. Spiega perché *«ho 12 ETF»* non
significa *«sono diversificato»*: se sono correlati 0,92 si è comprata dodici volte la
stessa cosa. Ed è qualcosa che l'utente **non può calcolare a mano** e che **nessun
broker gli mostra**.

**Verdetto.** Core. Probabilmente il valore singolo più alto dell'intero sottosistema, e
oggi quello con meno cura dedicata. **Casa primaria: Asset Global.**

---

## Contributo al rischio (MCTR / CCTR / PCTR)

**Cosa fa.** Scompone la volatilità *totale* del portafoglio nel contributo di ciascun
asset.

**Perché serve.** Il contributo **non è il peso**. Un asset al 5% del capitale, se
volatile e correlato col resto, può portare il 20% del rischio. E può essere
**negativo**: un asset che *riduce* il rischio complessivo — motivo per cui la
rappresentazione corretta è a barre divergenti e non un treemap.

**Verdetto.** Core, e sottovalutato dalla prima campagna. È la risposta diretta a
*«dove sta davvero il mio rischio?»* e produce un'azione concreta. Richiede pesi →
solo Dashboard e Broker Detail.

---

## Shock ipotetico

**Cosa fa.** Si applica un −30% all'equity, −10% ai bond, e si legge l'impatto **in
euro**.

**Perché serve.** È deterministico e onesto: non stima niente, dice *«se succede questo,
perdi tanto»*. È il miglior strumento **educativo** del pacchetto, perché converte le
percentuali in euro — che è dove nasce la reazione emotiva.

**Verdetto.** Core, ma **l'interazione va invertita**: oggi si chiede all'utente di
riempire i bucket uno per uno, e nessuno lo farà mai. Servono **preset a un clic**, con
il dettaglio per bucket disponibile solo su richiesta.

**Esclusione.** Senza pesi lo shock è quasi tautologico (riscrive l'input) → **fuori da
Asset Global**.

---

## Replay storico

**Cosa fa.** Riapplica i rendimenti **reali** di un periodo passato (Covid 2020, crisi
2008, inflazione 2022) alla composizione di oggi.

**Perché serve.** È più credibile del Monte Carlo per l'utente medio, perché *è successo
davvero*. Costo basso, valore alto.

**Avvertenza da rendere visibile.** Se un asset di oggi non esisteva nel 2008 serve un
*proxy*, e il proxy è **una scelta, non un fatto**. Il backend ha già l'audit necessario
(`bucket_audit`, `metadata_fallback`): va mostrato, non nascosto.

**Verdetto.** Core. Funziona anche **senza pesi**, in percentuale, come confronto fra
asset → è l'unico strumento di L4 ammesso in Asset Global.

---

## Qualità del dato

**Cosa fa.** `data_quality_status` (`ok` / `carried_forward` / `partial`), asset con
prezzi mancanti, punti riportati in avanti, coppie FX mancanti. Non è una metrica: è
infrastruttura di onestà.

**Verdetto.** **Non negoziabile.** È ciò che separa LibreFolio da un giocattolo. Un
numero di rischio senza la sua qualità del dato è *peggio* di nessun numero.

---

# 🟡 Tieni, con correzioni

## Sortino e Sharpe

**Cosa fanno.** **Sharpe** = (rendimento − tasso privo di rischio) / volatilità:
rendimento per unità di rischio. **Sortino** usa al denominatore solo la *downside
deviation*, cioè gli scarti sotto una soglia.

**Il difetto dello Sharpe.** Usa la volatilità *totale*, quindi **penalizza anche le
salite violente**. E dipende criticamente da un tasso privo di rischio che oggi l'utente
deve digitare a mano.

**Verdetto.** Utili, mai da soli, mai come «voto». Se se ne mostra **uno**, si mostra
**Sortino**, più onesto su rendimenti asimmetrici. Oggi sono due card di pari dignità
accanto al drawdown: gerarchia sbagliata. Casa corretta: **L3**.

---

## Beta e active return

**Cosa fanno.** **Beta** = sensibilità ai movimenti di un benchmark (β = 1,2 → ci si
muove il 20% più del benchmark). **Active return** = differenza di rendimento rispetto
al benchmark.

**Verdetto.** Core **a condizione** che il benchmark sia persistente e scelto
consapevolmente — decisione presa, vedi
[`04-decisioni-e-questioni-aperte.md`](./04-decisioni-e-questioni-aperte.md).
Con un benchmark scelto al volo a ogni esecuzione, il beta è un numero senza contesto.

**Vincolo matematico.** Il beta ammette solo benchmark **variabili**: una baseline
sintetica a varianza nulla darebbe `var = 0` e beta indefinito. Un tasso privo di
rischio non è un benchmark.

---

## Segnali rolling di rischio

**Cosa fanno.** Invece di un numero unico sul periodo, una serie temporale: *«la
volatilità a 90 giorni come è cambiata in cinque anni»*.

**Verdetto.** Architettura corretta e già realizzata (riuso di `SignalPlugin`).
**Restano dove sono**, nella Overview di Asset Detail: non vengono spostati né
duplicati nelle viste Risk. Una card che mostra *un solo valore puntuale* di una rolling
è il peggio dei due mondi — occupa spazio e perde proprio la forma nel tempo, che è
l'unica cosa che una rolling ha da dire.

---

## Monte Carlo

**Cosa fa.** Genera migliaia di traiettorie future sotto moto browniano geometrico, con
drift e covarianza stimati dallo storico, e restituisce percentili, probabilità di
perdita e un cono.

**Il problema epistemico.** Il risultato è determinato **quasi interamente dalle
assunzioni, non dai dati**. Il GBM assume rendimenti log-normali, volatilità costante,
correlazione costante, nessuna coda grassa e nessun cambio di regime — cioè
precisamente tutto ciò che rende i mercati pericolosi. Conseguenza pratica: il cono
**sottostima sistematicamente le code**. E visivamente è l'oggetto più convincente
della pagina, quindi il danno cognitivo è massimo.

**Verdetto.** **Da rifondare**, non da buttare. Il ventaglio insegna una cosa vera —
*«non esiste un numero, esiste una distribuzione»* — ma non può stare accanto a metriche
osservate come se fosse della stessa natura.

**Scaletta approvata** (livelli 1-3 in scope, 4-5 rinviati al TODO):

| # | Approccio | Cattura | Calibrabile? | Spiegabile |
|---|---|---|---|---|
| 1 | **Block bootstrap** | code grasse, asimmetria, cluster di volatilità, sequenze di crisi — *sono dati veri* | non serve | ⭐⭐⭐ *«rimescolo a blocchi la storia vera»* |
| 2 | **GJR-GARCH** (nativo QuantLib) | cluster di volatilità + effetto leva | ✅ dalla sola serie prezzi | ⭐⭐ |
| 3 | **Preset di regime prescritti** | fasi di mercato con vol, correlazioni e drift propri | ❌ dichiarati, non stimati | ⭐⭐⭐ se l'ipotesi è a schermo |
| 4 | Markov-switching calibrato | idem, stimato | ⚠️ overfitta su 3-5 anni | ⭐ → TODO |
| 5 | Heston / Bates / Merton | vol stocastica, salti | ❌ richiede opzioni | ⭐ → TODO |

Il **block bootstrap** diventa il default: batte il GBM su ogni asse — più onesto, più
realistico, più facile da spiegare e più economico da implementare.

Il selettore presenta **modalità, non parametri**, con l'ipotesi scritta *inline*:

```text
Come simulo?
 ● Storia rimescolata   — uso i tuoi rendimenti reali, riordinati a blocchi  [consigliato]
 ○ Mercato calmo        — ipotesi: volatilità ridotta del 30%
 ○ Crisi prolungata     — ipotesi: vol ×2,5 · correlazioni → 0,9 · drift −20%/anno · 14 mesi
 ○ Shock e recupero     — ipotesi: −35% in 2 mesi, poi ritorno al regime normale
 ○ Curva normale (GBM)  — modello classico: sottostima le code  [avanzato]
```

`sobol_start_index` esce dalla UI in ogni caso: è un controllo da quant, non da utente.

---

# 🔴 Tagliati e rinviati

## Tracking error e Information ratio → tagliati

**Cosa fanno.** **TE** = deviazione standard della differenza di rendimento rispetto al
benchmark. **IR** = extra-rendimento diviso TE.

**Perché si tagliano.** Nascono per valutare **un gestore attivo contro un mandato
dichiarato**. Un investitore privato non ha né mandato né benchmark ufficiale: misurano
quanto *aderisci* a un indice, mentre la domanda vera è se lo *batti* — a cui rispondono
già active return, beta e correlazione.

> ⚠️ **Attenzione a un errore facile.** La decisione di introdurre un benchmark
> persistente (vedi documento 04) **non riapre** TE/IR. La precondizione tecnica sarà
> soddisfatta, ma la ragione del taglio è semantica, non tecnica: anche con un benchmark
> persistente, misurare l'aderenza a un mandato inesistente resta privo di senso.

**Backend intatto**: `ComparisonAnalytic` continua a calcolarli, restano disponibili via
API. È una rimozione dalla UI, non dal dominio.

**Registrato in**: `TODO_FUTURI.md` → *«Risk Analysis — Tracking Error / Information
Ratio con benchmark selezionabile»*, priorità bassa.

---

## Portfolio optimization / frontiera efficiente → rinviato

**Cosa fa.** Dato un campione di rendimenti, trova i **pesi** che minimizzano la
varianza, massimizzano lo Sharpe o pareggiano i contributi al rischio (ERC / risk
parity). È Markowitz 1952.

**Tre precisazioni.**

1. **Non sceglie un asset, sceglie i pesi.** Non dice *«compra X»*, dice *«metti 23% su
   A, 41% su B»* fra gli asset che gli si danno. Non fa selezione, fa combinazione.
2. **«Serve un paniere ampio» — intuizione giusta, motivo rovesciato.** Con pochi asset
   risponde comunque, dando una soluzione d'angolo concentrata su due o tre nomi. Ma
   **più asset significa più errore, non meno**: con 50 asset si devono stimare 50 medie
   e 1.275 covarianze da poche centinaia di osservazioni. È per questo che esistono gli
   shrinkage estimator (Ledoit-Wolf, OAS), peraltro già implementati.
3. **La potenza di calcolo non è il vincolo**: misurato, **0,0159 s warm**.

**Il difetto è strutturale, non implementativo.** L'ottimizzatore media-varianza è un
*error maximizer*: predilige esattamente gli asset il cui rendimento atteso è stato
**sovrastimato** dal campione. I pesi sono instabili — si sposta la finestra di stima e
l'allocazione si ribalta. Per questo nella pratica sopravvivono min-variance e risk
parity, che **non usano i rendimenti attesi**, mentre il max-Sharpe in-sample è
considerato poco affidabile.

**Il motivo vero del rinvio.** Produce un output **prescrittivo** («i pesi giusti sono
questi») che lo strumento non può giustificare onestamente. LibreFolio è un tracker,
non un consulente: è un confine di prodotto, non tecnico.

**Nota costruttiva.** La variante onesta e a costo quasi nullo è **ERC come
diagnostica**, non come consiglio: *«se ogni asset contribuisse allo stesso rischio i
pesi sarebbero questi — i tuoi sono questi»*. È il complemento naturale del contributo
al rischio, vive in **L2**, e **non richiede Riskfolio**: si risolve in poche decine di
righe di NumPy.

**Registrato in**: `TODO_FUTURI.md` → *«Risk Analysis — Portfolio optimization /
frontiera efficiente (Riskfolio)»*, priorità molto bassa, con la decisione pendente
sulla rimozione delle dipendenze.
