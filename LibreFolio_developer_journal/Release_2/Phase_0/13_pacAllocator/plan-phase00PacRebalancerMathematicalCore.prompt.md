# PAC & Rebalancer — nucleo matematico target

**Stato:** TARGET CORRENTE — decisioni matematiche consolidate; rilievi della
review indipendente della suite incorporati il 2026-09-16.
**Tipo:** specifica matematica normativa, non codice e non benchmark solver.
**Implementazione:** non autorizzata da questo documento.

**Suite target:** [master](plan-phase00PacRebalancerTargetDesign.prompt.md) ·
[policy, obiettivi e vincoli](plan-phase00PacRebalancerPolicies.prompt.md) ·
[architettura](plan-phase00PacRebalancerArchitecture.prompt.md) ·
[UI completa](plan-phase00PacRebalancerUiTarget.prompt.md) ·
[bundle implementativo](implementation/README.md).

> Questo piano definisce quantità, unità, equazioni, identità contabili,
> obiettivo fixed-L2, confine MIQP/MIQCP e significato della prova.
> Il documento policy stabilisce **quali** variabili sono abilitate e in quale
> ordine lessicografico vengono ottimizzati i tier. Nessuno dei due può essere
> implementato leggendo soltanto l'altro.

---

## 1. Problema matematico

Dato uno snapshot finito contenente:

- Asset canonici e pesi target;
- holding iniziali per Asset×Broker;
- cash selezionato e nuovi contributi per sorgente/valuta;
- Broker operativi e route Asset×Broker;
- prezzi, cambi, fee, buffer e regole fiscali;
- step, minimi, cap e permessi;

costruire un vettore discreto di:

- trasferimenti;
- conversioni FX;
- ordini BUY;
- ordini SELL, soltanto nelle modalità che li autorizzano;

che:

1. rispetti ogni vincolo fisico e di policy;
2. riconcili ogni ledger nativo;
3. produca quantità finali non negative;
4. minimizzi lo scostamento monetario quadratico da target fissi;
5. esponga separatamente fattibilità del candidato e prova di ottimalità.

Il dominio è finito perché ogni azione discreta possiede un bound derivato da
cash, inventario, prezzo, step o cap. Se tale bound non è derivabile senza una
costante arbitraria, lo scenario è fuori dal dominio supportato.

---

## 2. Rappresentazione esatta

### 2.1 Valori autorevoli

Sono autorevoli:

- stringhe Decimal degli input;
- quantità e quantum discreti;
- posting monetari alla minor unit;
- ledger ricostruiti dall'evaluator;
- valori obiettivo esatti razionali/scalati, con proiezione Decimal lossless
  quando terminante;
- prove esatte prodotte da oracle o witness ammessi.

Non sono autorevoli:

- `float` usati dal solver;
- `Number` usati per coordinate grafiche;
- valori formattati a due decimali;
- status `optimal`/`infeasible` del solver senza chiusura esatta;
- un piano continuo successivamente arrotondato.

### 2.2 Dominio aritmetico chiuso

Ogni Decimal finito in ingresso viene convertito senza perdita nella frazione
ridotta:

$$
\operatorname{ExactRatio}(n,d),
\qquad
d>0,
\qquad
\gcd(n,d)=1.
$$

Prodotti, somme, confronti e le divisioni che definiscono prezzo unitario,
prezzi route e quantità economiche restano razionali esatti. Non dipendono dal
context Decimal del processo e non vengono quantizzati a una precisione interna
nascosta. Il nome architetturale **Decimal evaluator** indica il boundary:
parsa Decimal dal wire, usa un kernel integer/rational esatto, applica Decimal
soltanto ai posting con quantum dichiarato e restituisce proiezioni Decimal
lossless quando il denominatore è terminante.

Quando un valore razionale non ha espansione decimale finita:

- ranking, freeze e proof usano numeratore/denominatore ridotti o interi
  ottenuti da uno scaling comune esatto;
- la UI riceve una proiezione formattata non autorevole;
- il futuro contratto product-shaped deve conservare una rappresentazione
  lossless sufficiente al replay; non può troncare il valore per trasformarlo
  in Decimal.

L'unico arrotondamento finanziario v1 è quello esplicitamente dichiarato per un
posting monetario alla minor unit. Ogni posting usa
`ROUND_HALF_UP`; step ordine e quantum restano vincoli discreti, non
arrotondamenti post-solve.

### 2.3 Boundary solver/evaluator

```text
input wire Decimal
  -> normalizer esatto
  -> coefficienti ExactRatio/scalati
  -> solver floating propone quantum interi/binari
  -> evaluator Decimal/ExactRatio ricostruisce ogni posting
  -> solo candidato Decimal-valido può essere pubblicato
```

Il solver non decide la verità finanziaria. L'evaluator non importa il solver e
non “ripara” in silenzio un candidato non fattibile. Una correzione produce un
nuovo vettore, che perde bound e proof del vettore originario.

### 2.4 Sintassi

- un pedice identifica un'entità: $V_a$, $C_{bc}$;
- un apice identifica tempo o lato: $h^0$, $h^{final}$, $I^{BUY}$;
- $\sum_{a\in A}$ somma una volta per Asset canonico;
- $\forall a\in A$ rende il vincolo obbligatorio per ogni Asset;
- $x\ge0$ ammette zero e vieta valori negativi;
- $f(x)^2$ ha l'unità di $f$ elevata al quadrato;
- `→` indica priorità lessicografica, mai somma aritmetica.

La forma generale è:

$$
x^\star=
\operatorname*{argmin}_{\mathrm{lex},\,x\in X}
\left(f_1(x),f_2(x),\ldots,f_k(x)\right),
$$

dove $X$ è il dominio hard-feasible compilato dalla policy.

---

## 3. Insiemi, parametri, variabili e derivati

### 3.1 Insiemi e indici

| Simbolo | Significato |
|---|---|
| $A,a$ | insieme Asset canonici / un Asset |
| $B,b$ | Broker operativi autorizzati / un Broker |
| $C,c,d$ | valute native |
| $S,s$ | fonti di funding selezionate |
| $R,r$ | route ordine; fissa Asset, Broker, lato, valuta e instruction kind |
| $J,j$ | gambe FX dirette dichiarate |
| $K,k$ | categorie Tipo/Settore/Geografia |
| $v$ | valuta tecnica di valorizzazione |

### 3.2 Parametri economici

| Simbolo | Significato | Unità |
|---|---|---|
| $w_a$ | peso target | adimensionale Decimal |
| $h^0_{ab}$ | quantità iniziale | quantità Asset |
| $P^{source}_a$ | prezzo sorgente | valuta quotazione / `quote_base_quantity` |
| $Q_a$ | base positiva cui si riferisce il prezzo | quantità Asset |
| $p^q_a=P^{source}_a/Q_a$ | prezzo unitario normalizzato | valuta $q$/Asset |
| $P^{mid,c}_{r}$ | prezzo economico mid nella valuta route | valuta $c$/Asset |
| $P^{chg,c}_{r}$ | charge BUY dopo spread | valuta $c$/Asset |
| $P^{sell,c}_{r}$ | credit SELL dopo spread | valuta $c$/Asset |
| $g^{BUY}_r$ | maggiorazione esecuzione prudenziale BUY esplicita | adimensionale |
| $g^{SELL}_r$ | riduzione esecuzione prudenziale SELL esplicita | adimensionale |
| $\mu_c$ | minor unit | valuta $c$ |
| $\Delta q_r$ | quantum quantità della route intera | quantità Asset |
| $\Delta m_r$ | quantum monetario della route | valuta route |
| $\rho_{c\to d}$ | cambio snapshot | valuta $d$/valuta $c$ |
| $u_{sc}$ | importo selezionato dalla sorgente | valuta $c$ |
| $K^{cap}_{sbc}$ | cap di funding dichiarato | valuta $c$ |
| $PMC_{ab}$ | costo medio unitario riconciliato | valuta fiscale/Asset |

### 3.3 Variabili decisionali

| Variabile | Significato | Dominio |
|---|---|---|
| $t_{sbc}$ | trasferimento sorgente→Broker | multipli non negativi di $\mu_c$ |
| $f_j$ | debito sorgente FX | multipli non negativi della minor unit sorgente |
| $x_r^{BUY}$ | numero di quantum BUY | intero non negativo |
| $x_r^{SELL}$ | numero di quantum SELL | intero non negativo |
| $y_r^{BUY}$ | attivazione riga BUY | binario |
| $y_r^{SELL}$ | attivazione riga SELL | binario |

Variabili reali ausiliarie del solver possono rappresentare valori, residui e
ledger. Non sono azioni pubblicabili: le azioni finanziarie autorevoli restano
quantum interi/binari.

### 3.4 Valori derivati

| Simbolo | Significato |
|---|---|
| $h^{BUY}_{ab}$, $h^{SELL}_{ab}$ | quantità economica derivata dalle istruzioni |
| $h^{final}_{ab}$ | quantità finale per custodia |
| $V^0_a$, $V^{final}_a$ | valore mid iniziale/finale in $v$ |
| $I^{BUY}_a$, $I^{SELL}_a$ | valore mid acquistato/venduto |
| $F_{ref}$ | riferimento monetario fisso |
| $T_a$ | target monetario fisso |
| $r_a$ | residuo monetario firmato |
| $F_{final}$ | valore Asset finale totale |
| $U$ | shortfall contabile |
| $C^{spendable}_{bc}$ | cash spendibile finale |
| $C^{physical}_{bc}$ | cash fisico finale |
| $A_{round}$ | aggiustamento firmato di posting |

---

## 4. Canonicalizzazione e unità

### 4.1 Identità Asset

Lo stesso Asset su più Broker condivide:

- peso target;
- target monetario;
- residuo;
- valore finale aggregato.

Resta distinto per Broker:

- quantità custodita;
- PMC;
- route BUY/SELL;
- instruction kind;
- fee, valuta e ledger.

Nessuna aggregazione usa il nome visualizzato come identità.

### 4.2 Valute

Tre valute non vanno confuse:

1. **quotazione:** valuta del prezzo sorgente;
2. **addebito/accredito:** valuta del ledger Broker;
3. **valorizzazione $v$:** numeraire per target e score.

Somme cross-Asset avvengono soltanto dopo conversione coerente in $v$. I ledger
restano nativi.

### 4.3 Prezzo unitario

Se una quotazione descrive $Q_a$ unità:

$$
p^q_a=\frac{P^{source}_a}{Q_a}.
$$

$Q_a$ deve essere positivo. Il prezzo è normalizzato una volta; tutti i valori
downstream riusano lo stesso `ExactRatio`. Nessuna divisione usa precisione
implicita del processo.

### 4.4 Prezzi mid, charge e sell

Per Asset quotato in $q$ e ledger in $c$:

$$
P^{mid,c}_{r}=\frac{p^q_a}{\rho_{c\to q}},
$$

$$
P^{chg,c}_{r}
=
\frac{p^q_a(1+g^{BUY}_r)}{\rho^{eff}_{c\to q}},
$$

$$
P^{sell,c}_{r}
=
p^q_a\rho^{eff}_{q\to c}(1-g^{SELL}_r).
$$

Con:

$$
g^{BUY}_r\ge0,
\qquad
0\le g^{SELL}_r<1.
$$

Per $c=q$, tasso spot ed effettivo valgono esattamente uno: le maggiorazioni
route restano applicabili e coprono spread/slippage prudenziale anche senza FX.
Spread FX e margine esecuzione sono input distinti e vengono applicati una sola
volta.

Deve valere:

$$
P^{sell,c}_{r}\le P^{mid,c}_{r}\le P^{chg,c}_{r}.
$$

Il mid misura investimento/turnover/esposizione. Charge e sell governano cassa.
La differenza è perdita economica, non investimento.

---

## 5. Quantizzazione degli ordini

### 5.1 `whole_quantity`

Per una route intera:

$$
q_r=x_r\Delta q_r,
\qquad
x_r\in\mathbb Z_{\ge0}.
$$

Nella v1 visuale $\Delta q_r=1$ per l'istruzione in titoli interi. L'inventario
preesistente $h^0_{ab}$ può essere frazionario e non viene arrotondato.

BUY:

$$
I^{BUY,mid}_r=q_rP^{mid}_r.
$$

SELL:

$$
0\le q_r^{SELL}\le h^0_{ab}+h^{BUY}_{ab}
$$

con il divieto globale BUY+SELL dello stesso Asset applicato dalla policy.

### 5.2 `monetary_amount`

L'istruzione inviata al Broker è:

$$
M_r=x_r\Delta m_r,
\qquad
x_r\in\mathbb Z_{\ge0}.
$$

La quantità economica stimata è derivata esattamente:

$$
h^{BUY}_r=\frac{M_r}{P^{chg}_r}
$$

come `ExactRatio`. Non subisce rounding quantità nascosto e il solver non può
trattarla come quantità libera continua. L'azione operativa autorevole resta
$M_r$. Se un Broker richiede una quantità quantizzata, la route deve essere
modellata come `whole_quantity` con $\Delta q_r$ esplicito, non come eccezione
provider dentro `monetary_amount`.

Per SELL monetario, l'importo è il credito lordo richiesto e la quantità
derivata deve rispettare l'inventario. Nessuna eccezione implicita `sell_all`.

### 5.3 Minimi, obblighi e cap

Sia $\Delta_r$ il minimo quantum positivo nella stessa unità della misura
ordine: $\Delta q_r$ per `whole_quantity`, $\Delta m_r$ per
`monetary_amount`. Con $y_r\in\{0,1\}$:

```text
active_floor_r = max(minimum_if_operated_r, Δ_r)
active_floor_r * y_r <= order_measure_r <= route_cap_r * y_r
y_r = 1 iff order_measure_r >= Δ_r
```

Un `required_minimum` è invece un vincolo obbligatorio e non può essere
disattivato scegliendo $y_r=0$.

Quindi $y_r=1$ con ordine zero è sempre invalido, anche quando
`minimum_if_operated=0`.

Ogni soglia dichiara:

- lato BUY/SELL;
- unità quantità o notional;
- valuta se monetaria;
- applicazione condizionale o obbligatoria.

---

## 6. Funding e ledger

### 6.1 Selezione della liquidità

Per ogni sorgente:

$$
0\le u_{sc}\le balance^{available}_{sc}.
$$

La somma trasferita non supera l'importo selezionato:

$$
\sum_bt_{sbc}\le u_{sc}.
$$

Un Broker che è anche sorgente non auto-trasferisce:

$$
t_{bbc}=0.
$$

Cash non selezionato è invisibile al planner. Cash selezionato esistente e nuovo
contributo restano righe distinte.

### 6.2 Ledger spendibile

Per ogni Broker×valuta:

$$
\begin{aligned}
C^{spendable,final}_{bc}={}&
C^0_{bc}
+\sum_st_{sbc}
-\sum_{b'}t_{bb'c}\\
&+\sum_{j:\cdot\to c}credit_j
-\sum_{j:c\to\cdot}f_j\\
&+\sum_agrossSell_{abc}
-\sum_abuyDebit_{abc}\\
&-\sum_afeeBuy_{abc}
-\sum_afeeSell_{abc}\\
&-\sum_ataxWithheld_{abc}
-\sum_ataxSelfReserved_{abc}\\
&-feeFX_{bc}
-bufferFX_{bc}
\ge0.
\end{aligned}
$$

Il simbolo $C^0_{bc}$ include soltanto cash iniziale selezionato già residente
sul Broker×valuta. Nuovo funding e trasferimenti entrano esclusivamente tramite
$t_{sbc}$; non sono pre-inclusi in $C^0_{bc}$. Il saldo totale non selezionato
resta fuori.

### 6.3 Ledger fisico

$$
C^{physical,final}_{bc}
=
C^{spendable,final}_{bc}
+bufferFX_{bc}
+taxSelfReserved_{bc}.
$$

La tax `broker_withheld` ha lasciato il conto e non viene riaggiunta.

### 6.4 Chiusura del ledger

Ogni termine viene postato una volta. Sono vietati:

- accredito FX senza debito;
- accredito simultaneo di `grossSell` e `cashNetSell`;
- sottrazione doppia di spread o fee;
- buffer contato come fee e come riserva;
- nuovo contributo duplicato nel cash iniziale;
- saldo negativo nascosto da conversione in $v$.

---

## 7. FX

### 7.1 Rate effettivo

Per $j:c\to d$ con spread $s_j$:

$$
\rho^{eff}_{c\to d}=\rho_{c\to d}(1-s_j),
\qquad
0\le s_j<1.
$$

Per ricevere almeno $A_d$:

$$
D_c=\frac{A_d}{\rho^{eff}_{c\to d}}
$$

è soltanto il lower bound continuo. Il debito operativo è:

$$
f_j\in\mu_c\mathbb Z_{\ge0},
\qquad
f_j\ge\left\lceil D_c\right\rceil_{\mu_c}.
$$

Il credito postato:

$$
credit_j=
\operatorname{round}_{\mu_d,\mathrm{HALF\_UP}}
\left(f_j\rho^{eff}_{c\to d}\right).
$$

Un'eccedenza resta cash destinazione.

### 7.2 Buffer e fee

Con tasso buffer $m_j$:

$$
bufferFX_j=
\operatorname{round}_{\mu_c,\mathrm{HALF\_UP}}(m_jf_j).
$$

Il cash sorgente richiesto è:

$$
cashRequired_j=f_j+bufferFX_j+feeFX_j.
$$

Il buffer resta fisicamente nel conto sorgente. Fee e spread sono perdite
economiche distinte.

### 7.3 Grafo ammesso

- solo gambe dichiarate;
- un singolo hop per percorso di funding v1;
- nessun ciclo attivo;
- nessuna incoerenza di tasso capace di creare arbitraggio sintetico;
- ogni credito è funzione del proprio debito;
- tutte le coppie, fonti, date e staleness sono nello snapshot.

---

## 8. Fee

Per lato $h\in\{BUY,SELL\}$, notional $N$, fisso $f_h$, aliquota $r_h$,
minimo $l_h$ e massimo $u_h$:

$$
fee_h(N)=
\begin{cases}
0,&N=0,\\
f_h+\min(\max(r_hN,l_h),u_h),&N>0.
\end{cases}
$$

Regole:

- $0\le l_h\le u_h$;
- massimo assente equivale a nessun cap della componente percentuale;
- minimo/massimo non modificano la componente fissa;
- `rate=0` e minimo positivo applicano comunque il minimo;
- un ordine gratuito richiede fisso, rate e minimo uguali a zero;
- BUY e SELL sono profili indipendenti;
- la fee è per riga ordine attiva;
- profili dinamici per mercato/numero eseguiti sono fuori v1.

La funzione piecewise deve essere modellata con attivazioni e segmenti/bound
derivati, non approssimata con un coefficiente medio.

---

## 9. SELL, PMC e riserva fiscale

### 9.1 Valore rimosso e provento

Per quantità venduta $n_{ab}$:

$$
I^{SELL,v}_{ab}
=
n_{ab}P^{mid,c}_{ab}\rho_{c\to v}.
$$

Il provento lordo nativo è:

$$
grossSell^c_{ab}
=
n_{ab}P^{sell,c}_{ab}.
$$

La perdita economica pre-rounding:

$$
L^{sell}_{ab}
=
I^{SELL,v}_{ab}
-grossSell^c_{ab}\rho_{c\to v}
\ge0.
$$

### 9.2 Base e gain

$$
costBasisSold^c_{ab}=n_{ab}PMC^c_{ab}.
$$

$$
taxableGain^c_{ab}
=
\max\left(
grossSell^c_{ab}
-feeSell^c_{ab}
-costBasisSold^c_{ab},
0
\right).
$$

Con aliquota Asset $\tau_a$:

$$
taxReserve^c_{ab}
=
\operatorname{round}_{\mu_c,\mathrm{HALF\_UP}}
\left(\tau_a taxableGain^c_{ab}\right).
$$

Cash riutilizzabile:

$$
cashNetSell^c_{ab}
=
grossSell^c_{ab}
-feeSell^c_{ab}
-taxReserve^c_{ab}.
$$

Nel ledger entrano provento lordo, fee e riserva come tre termini. Il netto è
soltanto una verifica derivata.

### 9.3 Preconditions

- PMC e provento devono essere nella stessa valuta fiscale oppure avere
  conversione esplicita con fonte/data;
- regime determina `withholding_kind`;
- tax rate è input esplicito, prefill modificabile;
- minus pregresse sono fatto dello snapshot ma non vengono compensate v1;
- un SELL con netto non positivo non può finanziare BUY;
- nessuna vendita oltre quantità custodita.

---

## 10. Riferimento fisso

### 10.1 Cash selezionato

$K_{selected}$ è il valore in $v$ di:

- cash esistente esplicitamente selezionato;
- nuovi contributi esplicitamente selezionati.

Le righe restano native nei ledger anche se il valore viene aggregato per
costruire il riferimento.

### 10.2 Reachable e trapped

$K_{reachable}$ contiene il valore che possiede almeno un percorso strutturale:

```text
sorgente
  -> trasferimento autorizzato
  -> Broker×valuta
  -> eventuale FX autorizzato
  -> BUY di Asset con peso positivo e prezzo utilizzabile
```

Per questa classificazione si ignorano soltanto soglie amount-dependent. Quindi:

- cash sotto minimo/fee è reachable e riappare in $U$;
- cash senza route, permesso, prezzo o direzione FX è trapped;
- $K_{trapped}=K_{selected}-K_{reachable}$;
- fee, spread, tax e buffer non riducono in anticipo $K_{reachable}$.

### 10.3 Formula

$$
F_{ref}=V_0+K_{reachable}.
$$

- PAC: $V_0=0$.
- Rebalancer: $V_0=\sum_aV^0_a$ e deve essere positivo.
- SELL non aumenta $F_{ref}$.

---

## 11. Target e obiettivo fixed-L2

### 11.1 Pesi

$$
w_a\ge0,
\qquad
\sum_aw_a=1.
$$

La somma è Decimal esatta dopo normalizzazione dichiarata; nessuna tolleranza
floating diventa policy.

### 11.2 Target monetario

$$
T_a=w_aF_{ref}.
$$

Il target non dipende dalle decisioni di BUY/SELL né da $F_{final}$.

### 11.3 Valore finale

$$
V^{final}_a
=
V^0_a
+I^{BUY}_a
-I^{SELL}_a
\ge0.
$$

Per ogni custodia:

$$
h^{final}_{ab}
=
h^0_{ab}
+h^{BUY}_{ab}
-h^{SELL}_{ab}
\ge0.
$$

### 11.4 Residuo e score

$$
r_a=V^{final}_a-T_a.
$$

$$
L2_{fixed}
=
\sum_a r_a^2
=
\sum_a\left(V^{final}_a-w_aF_{ref}\right)^2.
$$

Unità:

- $V^{final}_a,T_a,r_a$: valuta $v$;
- $L2_{fixed}$: valuta $v^2$;
- $L2_{fixed}/F_{ref}^2$: diagnostico adimensionale.

Non si confrontano direttamente score di scenari con valuta o $F_{ref}$
diversi.

### 11.5 Perché il quadrato

Il quadrato:

- penalizza uno scostamento grande più di più scostamenti piccoli con uguale
  somma assoluta;
- seleziona piani più bilanciati fra Asset;
- resta convesso perché $F_{ref}$ è fisso;
- evita il prodotto/frazione della precedente percentuale actual-final;
- è direttamente esprimibile come MIQP.

Non è un'identità matematica obbligatoria: è la policy prodotto approvata.
$D_\infty$ e $D_1$ restano diagnostici per rendere leggibile il risultato.

---

## 12. Shortfall, anti-shrink e accounting

### 12.1 Definizione

$$
F_{final}=\sum_aV^{final}_a,
\qquad
U=F_{ref}-F_{final}.
$$

Poiché $\sum_aT_a=F_{ref}$:

$$
\sum_ar_a
=
\sum_aV^{final}_a-\sum_aT_a
=
F_{final}-F_{ref}
=
-U.
$$

Per Cauchy-Schwarz, con $n=|A|$:

$$
\left(\sum_ar_a\right)^2
\le
n\sum_ar_a^2,
$$

quindi:

$$
L2_{fixed}\ge\frac{U^2}{n}.
$$

Vendere e lasciare cash idle non riduce il denominatore target: aumenta
necessariamente il lower bound in funzione di $|U|$.

### 12.2 Decomposizione

$$
U
=
C_{free}
+R_{physical}
+L_{economic}
+A_{round}.
$$

| Termine | Contenuto |
|---|---|
| $C_{free}$ | cash raggiungibile spendibile finale, incluso netto SELL non usato |
| $R_{physical}$ | buffer FX + tax `self_reserved` |
| $L_{economic}$ | fee, spread, differenze charge/sell e tax `broker_withheld`, once-only |
| $A_{round}$ | delta firmato dei posting alla minor unit |

Minimi, cap, quantum e contesa ledger spiegano perché un importo resta in
$C_{free}$; non sono termini monetari aggiuntivi.

### 12.3 Identità di funding

$$
K_{reachable}+I^{SELL}
=
I^{BUY}
+C_{free}
+R_{physical}
+L_{economic}
+A_{round}.
$$

Dato:

$$
F_{final}=V_0+I^{BUY}-I^{SELL},
$$

segue:

$$
\begin{aligned}
F_{ref}-F_{final}
&=(V_0+K_{reachable})-(V_0+I^{BUY}-I^{SELL})\\
&=C_{free}+R_{physical}+L_{economic}+A_{round}.
\end{aligned}
$$

Nessun termine SELL aggiuntivo compare due volte.

### 12.4 Identità estesa

$$
V_0+K_{selected}
=
F_{final}+U+K_{trapped}.
$$

Cash non selezionato resta fuori da entrambi i lati.

---

## 13. Rounding firmato

### 13.1 Famiglie chiuse di posting

1. addebito BUY;
2. accredito lordo SELL;
3. fee BUY/SELL;
4. credito destinazione FX;
5. fee FX;
6. buffer FX;
7. tax reserve.

Funding, trasferimenti e debiti FX sorgente sono già multipli validati della
minor unit e hanno delta zero.

Ogni posting delle sette famiglie viene quantizzato **una sola volta** alla
minor unit della propria valuta con `ROUND_HALF_UP`. La quantità economica di
una route `monetary_amount` resta invece un `ExactRatio`: non è un posting
monetario e non genera un ottavo delta di rounding. Una precisione quantità
Broker trasformerebbe la route in `whole_quantity` con quantum esplicito.

### 13.2 Segno

Con $J_D$ posting debit e $J_C$ posting credit:

$$
A_{round}
=
\sum_{j\in J_D}
\left(x^{posted}_j-x^{exact}_j\right)\rho_{c_j\to v}
+
\sum_{j\in J_C}
\left(x^{exact}_j-x^{posted}_j\right)\rho_{c_j\to v}.
$$

Positivo significa valore consumato; negativo significa posting favorevole.

### 13.3 Bound

Poiché `ROUND_HALF_UP` è rounding al più vicino, per ogni posting $j$:

$$
\left|x^{posted}_j-x^{exact}_j\right|\le\frac{\mu_{c_j}}2.
$$

$$
|A_{round}|
\le
\frac12
\sum_j\mu_{c_j}\rho_{c_j\to v}.
$$

Ne segue:

$$
U\ge-|A_{round}|_{max}.
$$

Un piccolo $U<0$ entro il bound è surplus da rounding, non leva. Un'identità
non chiusa o un delta oltre bound rende il candidato `invalid`.

---

## 14. Diagnostici percentuali ed esposizioni

### 14.1 Percentuali finali

Quando $F_{final}>0$:

$$
p^{final}_a=\frac{V^{final}_a}{F_{final}}.
$$

$$
D_\infty^{pct}
=
\max_a|p^{final}_a-w_a|.
$$

$$
D_1^{pct}
=
\sum_a|p^{final}_a-w_a|.
$$

Sono report facts. Non entrano nella tupla normativa.

### 14.2 Esposizioni

Con $\alpha_{ak}$ esposizione Asset→categoria:

$$
\alpha_{a,Unknown}
=
1-\sum_{k\ne Unknown}\alpha_{ak}
\ge0.
$$

$$
E_k^{current}
=
\frac{\sum_aV^0_a\alpha_{ak}}{\sum_aV^0_a}.
$$

$$
E_k^{target}
=
\sum_aw_a\alpha_{ak}.
$$

$$
E_k^{final}
=
\frac{\sum_aV^{final}_a\alpha_{ak}}{F_{final}}.
$$

Non si rinormalizza il sottoinsieme noto. Cash escluso dalle esposizioni viene
mostrato separatamente.

---

## 15. Rebalancer con SELL

### 15.1 Preconditions

- $V_0>0$;
- $F_{final}>0$ per ogni candidato;
- inventory bound per Asset×Broker;
- PMC/valuta fiscale disponibili per ogni SELL;
- nessun BUY+SELL dello stesso Asset;
- ogni SELL produce cash netto positivo;
- SELL ammessi soltanto dalla policy `invest_and_sell`.

### 15.2 Anti-liquidazione sequenziale

1. risolvere `invest_only`;
2. congelare BUY, funding e FX della baseline;
3. classificare overweight/underweight contro $T_a$:

$$
V^{baseline}_a-T_a>0
\quad\text{o}\quad
V^{baseline}_a-T_a<0;
$$

4. abilitare SELL soltanto da baseline-overweight senza BUY congelato;
5. richiedere almeno un BUY incrementale se esiste una SELL:

$$
\sum_aI^{SELL}_a>0
\Longrightarrow
\sum_aI^{incrementalBUY}_a>0;
$$

6. vietare vendita che termina soltanto in cash idle.

La fase SELL non può scartare la baseline e costruire un piano di liquidazione
globale.

### 15.3 Quantum-minimalità locale

Per vettore SELL $s$ e riga attiva $r$ con quantum $q_r$:

$$
s'=s-q_re_r.
$$

Lo stesso vettore BUY incrementale deve diventare non finanziabile dopo avere:

- ricalcolato fee fisse/variabili;
- ricalcolato tax reserve;
- disattivato la riga se arriva a zero;
- ricostruito ledger e FX;
- permesso tutte le fonti alternative dichiarate;
- rispettato ogni minimo, cap e buffer.

Va anche verificata la necessità dell'intera riga ponendo $s_r=0$. Questa è
irreducibilità locale, non prova di minimalità globale.

Il controllo è un **publication gate** del
`SellIrreducibilityVerifier`, non un predicato locale dell'evaluator. Per ogni
riga SELL attiva costruisce al massimo due sottoproblemi controfattuali:

1. un quantum SELL in meno;
2. riga SELL azzerata.

Il BUY incrementale resta identico; il compiler riapre soltanto funding/FX
dichiarati mutabili e ricostruisce fee, tax, minimi, cap, buffer e ledger. Un
controesempio Decimal-feasible invalida il candidato. L'assenza di
controesempio chiude il gate soltanto con conflict witness Decimal completo o
oracle esaustivo del sottodominio finito; uno status floating `infeasible` non
basta. Se anche un solo sottoproblema resta non chiuso entro budget, il piano
`invest_and_sell` non viene pubblicato e l'esito è
`no_incumbent/not_proven` con reason
`SELL_IRREDUCIBILITY_UNRESOLVED`. Quel candidato SELL non viene pubblicato; il
report conserva l'ultimo candidato già verificato, almeno la baseline
`invest_only`, come `incumbent_found/not_proven`. `no_incumbent/not_proven`
resta possibile soltanto se nessun candidato verificato esiste.

---

## 16. Variante margine

Sia $x^{primary}$ il vettore completo di azioni del primario. La variante impone:

$$
t=t^{primary},
\quad
f=f^{primary},
\quad
x^{SELL}=x^{SELL,primary},
\quad
x^{BUY}\ge x^{BUY,primary}.
$$

L'incremento:

$$
\Delta x^{BUY}=x^{BUY}-x^{BUY,primary}\ge0.
$$

Non sono ammessi nuovi funding, FX o SELL. La variante usa soltanto cash
spendibile già risultante dal primario.

La prima funzione della variante minimizza $U$, equivalendo a massimizzare
l'ulteriore valore mid investito. Sulla faccia di deployment massimo, minimizza
il nuovo $L2_{fixed}$.

È ammesso:

$$
\Delta L2
=
L2_{deployment}-L2_{primary}
>0.
$$

Il delta è obbligatorio nel report. Se $\Delta L2<0$ contro un primario non
provato, la variante domina l'incumbent e deve essere promossa/re-rankata.

---

## 17. Classe del problema

### 17.1 Primo tier

$V^{final}_a$ è affine nelle variabili d'azione scalate. La somma:

$$
\sum_a(V^{final}_a-T_a)^2
$$

è quadratica convessa. Con variabili intere/binarie il primo tier è MIQP.

### 17.2 Tier successivi

Se $L2^\star$ è esattamente provato:

$$
\sum_ar_a^2\le L2^\star
$$

descrive esattamente la faccia ottima, senza uguaglianza non convessa.
Minimizzare il tier successivo produce un MIQCP convesso, anche
MISOCP-rappresentabile.

Se $L2^\star$ è soltanto incumbent:

- il sublevel è un ceiling non-peggiorativo;
- i bound successivi sono condizionati a quel ceiling;
- un candidato con $L2$ inferiore riavvia la cascata;
- nessun risultato viene chiamato globalmente ottimo.

### 17.3 Rilassamento continuo

Rimuovere integrality produce un QP continuo utile per:

- lower bound;
- warm start;
- diagnostica.

Il floor/rounding di quel risultato non è autorevole: può violare ledger,
minimi, fee fisse, route, cap o target policy.

---

## 18. Scaling e coefficient safety

Il normalizer:

1. converte Decimal finiti in razionali;
2. riduce numeratori/denominatori per GCD;
3. deriva bound finiti di ogni quantum;
4. misura coefficiente massimo;
5. misura attività massima di riga;
6. misura dynamic range;
7. include bound dei posting rounded;
8. rifiuta un envelope non sicuro.

Non sono ammessi:

- `NaN` o infinito;
- epsilon nascosti;
- Big-M arbitrari;
- rescaling lossy non dichiarato;
- cap impliciti per fare entrare il problema;
- conversione di Decimal in centesimi se la valuta/step richiede altra
  precisione.

La crescita del quadrato in unità minori va inclusa nel benchmark; non basta che
il modello sia formalmente convesso.

---

## 19. Proof semantics A

Tre piani indipendenti:

1. **incumbent validation:** il candidato passa replay Decimal;
2. **solver evidence:** status, bound, gap, tolleranze, versione e settings
   floating;
3. **proof:** conclusione matematica sul dominio discreto.

### 19.1 Incumbent

Ogni piano pubblicato:

```text
incumbent_validation = decimal_verified
```

Ciò prova:

- ledger;
- vincoli;
- quantità finali;
- tuple obiettivo esatte;

ma non l'ottimalità globale.

### 19.2 Ottimalità

`optimal_proven` richiede chiusura di ogni tier tramite:

- `exhaustive_oracle`; oppure
- `score_lattice_closure` coefficient-safe.

#### 19.2.1 `score_lattice_closure`

La chiusura score-lattice è ammessa per un tier soltanto quando:

1. variabili e bound del dominio congelato sono finiti;
2. ogni coefficiente nasce da Decimal finiti convertiti in `ExactRatio`;
3. un denominatore comune positivo $D$ trasforma tutti i valori raggiungibili
   del tier in interi senza rounding;
4. per $L2_{fixed}$ si scalano prima i residui
   $R_a=Dr_a$, quindi lo score-lattice è
   $S_2=\sum_aR_a^2\in\mathbb Z_{\ge0}$ e
   $L2_{fixed}=S_2/D^2$;
5. il bound solver viene convertito verso l'esterno con un envelope numerico
   dimostrato dai coefficienti e dai bound del modello;
6. fra quel bound sicuro e lo score esatto dell'incumbent non esiste alcun
   valore intero raggiungibile migliore;
7. la stessa chiusura viene ripetuta per ogni tier lessicografico sulla faccia
   esatta congelata dei tier precedenti.

La feasibility tolerance MIQP, il gap stampato dal solver o un Decimal
troncato non costituiscono score lattice. Se $D$, l'envelope, il bound sicuro o
la faccia di un tier non sono derivabili esattamente, la closure fallisce e lo
status resta `gap_bounded` o `not_proven`.

Lo status floating `optimal` è al massimo:

- `gap_bounded`, se bound e unità sono confrontabili;
- `not_proven`, altrimenti.

### 19.3 Infeasibility

`infeasible_proven` richiede:

- conflict witness Decimal completo; oppure
- oracle esaustivo completo.

Lo status floating `infeasible` senza tali prove è:

```text
no_incumbent / not_proven
```

### 19.4 No-op

Un piano vuoto è:

- `no_op/optimal_proven` soltanto se è provato che nessuna azione migliora la
  tupla;
- un normale incumbent se fattibile ma non provato;
- distinto da `infeasible_proven`.

---

## 20. Oracle esaustivo

L'oracle small-domain deve:

- enumerare l'intero dominio dichiarato, non usare la ricerca production;
- includere funding, FX, activation, BUY e SELL;
- usare lo stesso evaluator Decimal indipendente;
- ordinare con la stessa tupla lessicografica;
- riprodurre la sequenza `invest_only` → sell extension;
- verificare variante margine e promozione;
- includere fee fisse, tax, rounding e ledger nativi;
- dichiarare limiti esatti del dominio enumerato.

Casi minimi:

1. un Asset/un Broker/no fee;
2. due Asset e quote intere;
3. route monetaria a step;
4. budget sotto minimo;
5. required minimum incompatibile;
6. due valute con FX;
7. buffer e fee FX;
8. cash trapped;
9. fee fissa e activation;
10. SELL con PMC/gain/tax;
11. SELL non necessario;
12. BUY+SELL vietato;
13. rounding favorevole/sfavorevole;
14. più candidati a stesso $L2$;
15. incumbent limitato senza proof.

---

## 21. Esempi limite da preservare

### 21.1 Target perfetto ma cash enorme

Se una prima combinazione ha proporzioni perfette ma lascia cash:

- $L2_{fixed}$ usa target monetari su tutto $F_{ref}$;
- lasciare un milione idle crea residui monetari grandi;
- il piano non ottiene score zero comprando una sola quota per Asset.

Questo è il motivo per cui il riferimento è fisso e non il capitale investito
effettivo.

### 21.2 Asset irraggiungibile

Un Asset a peso positivo senza route/prezzo:

- se il cash non raggiunge alcun Asset positivo, la parte è trapped;
- se altri Asset sono raggiungibili, il target dell'Asset indisponibile resta
  nel riferimento e produce residuo;
- il Tool non elimina l'Asset e non rinormalizza i pesi.

La classificazione precisa fra `needs_input`, `unsupported` e candidato con
residuo è definita dal constraint/policy plan.

### 21.3 Cash sotto minimo

Cash con route valida ma sotto minimo:

- resta in $K_{reachable}$;
- entra in $F_{ref}$;
- rimane in $C_{free}$;
- aumenta $U$ e lo scostamento;
- può produrre no-op, non cash trapped.

### 21.4 Fee maggiore dell'ordine

Un ordine attivo con fee/minimo che rende il debit non finanziabile è
infeasible. Non si riduce la fee né si tratta il costo come investimento.

### 21.5 Vendita senza acquisto

Una SELL che migliora una percentuale ma lascia soltanto cash è vietata dalla
policy funding-only. Il fixed-L2 anti-shrink non sostituisce questo vincolo:
entrambi sono necessari.

### 21.6 Variante che peggiora target

La variante può investire un quantum addizionale che aumenta $L2_{fixed}$.
È valida perché la sua prima priorità è ridurre $U$ dopo aver congelato il
primario. Il report deve mostrare il peggioramento.

---

## 22. Gate matematici prima del codice

- review indipendente della suite completa;
- schema di input capace di esprimere ogni unità senza ambiguità;
- prova che ogni bound è derivato;
- definizione coefficient envelope;
- benchmark SCIP MIQP e MIQCP;
- confronto oracle su piccoli domini;
- witness multi-valuta/fee/tax/rounding;
- mapping proof/status senza combinazioni impossibili;
- verifica output sotto limite Tool;
- nessun cambio di obiettivo durante il dettaglio contrattuale.

Qualunque modifica a $F_{ref}$, $L2_{fixed}$, ledger, fee, FX, tax, SELL o
rounding richiede una nuova review matematica.
