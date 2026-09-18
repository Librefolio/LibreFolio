# `contracts/` — i contratti fra mandati, materializzati

> **Questa cartella è del coordinatore.** Nessun mandato scrive qui.

---

## Perché esiste

I mandati girano in **worktree separati**. Un file che il mandato A scrive nel proprio
worktree **non è visibile al mandato E**: non condividono il filesystem, e finché non
c'è un commit integrato non condividono nemmeno la storia.

Quindi un contratto **non può** essere consegnato «mettendolo in un file». Resta un
messaggio fra sessioni — e un messaggio **sparisce al primo azzeramento di contesto**,
esattamente quando serve.

> ## 🔑 Il produttore **comunica**. Il coordinatore **scrive**. Il consumatore **riceve**.
>
> Il file qui dentro è l'unica copia durevole, e vive nel worktree del coordinatore.

## 🔴 E il corollario che ho imparato sbagliando — 18 Set 2026

**Il file da solo non consegna nulla.** L'ho scoperto creando il mandato **E** con un
prompt che diceva *«i contratti sono già su file, leggili»*: E nasce dalla baseline
committata, dove `contracts/` contiene **solo questo README**. I quattro file stavano
**non committati nel worktree del coordinatore**, cioè nell'unico posto che nessun
consumatore può raggiungere.

L'ha visto il mandato **I**, e la sua frase è la diagnosi esatta:

> *«Un contratto che una sola parte può vedere non è ancora un contratto.»*

È l'ironia da tenere scritta: questo README argomenta che i contratti vanno
materializzati **perché i worktree non condividono file**, e poi il coordinatore li ha
lasciati esattamente lì.

### La regola che ne discende

| Momento | Come viaggia un contratto |
|---|---|
| **Prima del commit della baseline** | **relay inline**, dentro il messaggio al consumatore. Il file è il registro del coordinatore, non il canale |
| **Dopo il commit** | il consumatore lo legge dal proprio worktree — ma **solo** se la sua baseline lo contiene |

⚠️ **Verifica prima di dire «leggilo»**:

```bash
git -C <worktree-figlio> ls-tree HEAD <percorso-contratto>
```

Se non torna nulla, **il contratto va relayato nel messaggio**, per intero. Un rimando a
un file che il destinatario non ha è peggio del silenzio: sembra un'istruzione
eseguibile e non lo è.

Ha un secondo effetto, meno ovvio e altrettanto utile: rende visibile un contratto
**cambiato**. La differenza fra la versione scritta e quella nuova diventa un diff
invece che un ricordo contraddittorio — ed è precisamente il tipo di disallineamento
che questa struttura esiste per intercettare.

---

## I contratti

| # | Da | A | Oggetto | Stato |
|---|---|---|---|---|
| **[K1](./K1.md)** | A | E | Serie underwater (**D14**) e bin dell’istogramma (**D21**) | ✅ |
| **[K2](./K2.md)** | B | G | `primaryAssetType` — **contenuto** (D85). Codominio **12** valori enum, **13 chiavi** con `Liquidity`; ⚠️ **uppercasa**, non restituisce verbatim (D123) | ✅ |
| **[K3](./K3.md)** | B | E, F | Selettore benchmark a sezioni: due prop su `AssetSelect` (**D50**) | ✅ |
| **[K4](./K4.md)** | C | E, F, H | Filtro per asset su `PortfolioRiskScope` + pesi rinormalizzati (**D59**) + **quattro** dichiarazioni obbligatorie | ✅ |
| **[K5](./K5.md)** | D | E, F | Primitive promosse **e** divisione dello spec E2E. ⚠️ Garanzia di non-salto **parziale**: `caption`/`sparkline`/`submetrics` sono del chiamante | ✅ **D FROZEN** |
| **[K6](./K6.md)** | H | E | `process` × `regime` e cono. Didascalia shock **«applicato alla tua storia»**; chiavi i18n = **stringhe enum esatte**; ⚠️ `regime != none` **richiede** `block_bootstrap` → altrimenti **422** | ✅ **H FROZEN** |
| **[K7](./K7.md)** | I | E, F, H | I **22** slug (21 metriche + hub), come stringa `path`, **generati a macchina**. ⚠️ Baseline del gate: **12** con il `dev.py` di baseline, **24** con la riparazione di I | ✅ |
| **[K8](./K8.md)** | N | E, **I** | Campi nuovi su `RiskKpiOutput` e `RiskContributionOutput`. 🔴 **`effective_number_of_assets` può superare il numero di titoli** (11,44 su 2): non etichettarlo come conteggio | ✅ **N FROZEN** |
| **[K9](./K9.md)** | E | F | `allowedStressMethods` + replay allargato ad `asset_set` con **audit mostrato**. 🔴 **Esteso**: guardia `scope.kind === 'portfolio'` sui due `formatAmount` — oggi **nulla protegge la regola degli importi** | ✅ **esteso** |

Legenda: ⏳ atteso · 📝 concordato, non ancora implementato · ✅ consegnato e verificato
· ⚠️ cambiato dopo la consegna

> ⚠️ **K9 non era nel piano.** L'ha scoperto **F** misurando invece di assumere: il suo
> cancello viveva dentro un file di **E**, e il suo brief non dichiarava alcun contratto
> con lui. Un contratto mancante non si vede finché qualcuno non prova a lavorare.

> ⚠️ **📝 non significa «fatto».** Significa che produttore e coordinatore si sono
> accordati sulla forma, e che il consumatore può **costruirci contro**. Il passaggio a
> ✅ lo fa il **produttore**, quando il codice esiste e i test lo coprono.

---

## Forma di un file di contratto

`K<n>.md`, e deve rispondere a tutto ciò che serve al consumatore **prima** che il
produttore abbia finito:

```markdown
# K<n> — <da> → <a>

| | |
|---|---|
| Produttore | mandato <X> |
| Consumatori | mandato <Y>, <Z> |
| Stato | ⏳ / 📝 / ✅ / ⚠️ |
| Concordato il | <data> |

## La firma

<nome esatto, tipo esatto, unità esatta>

## Semantica

<cosa significa il valore, e cosa NON significa>

## Cosa il consumatore deve dichiarare a schermo

<se il contratto porta con sé un obbligo di trasparenza>

## Degrado

<cosa fa il consumatore se il campo manca o arriva vuoto>

## Storia

| Data | Cambiamento | Chi è stato avvisato |
|---|---|---|
```

---

## Le tre sezioni che si dimenticano, e perché nessuna è decorativa

**L'unità.** Un numero senza unità è la classe di difetto già trovata due volte in
questa campagna: `Kurtosis` che è `sqrt(m₄)` e non la kurtosi, `MDD_Abs` che è un
drawdown su curva non composta. Entrambi *plausibili*, entrambi sbagliati.

**L'obbligo di dichiarazione.** Alcuni contratti portano con sé una cosa che il
consumatore **deve scrivere a schermo**, non intuire: la rinormalizzazione dei pesi di
K4 (**D59**), l'ipotesi accanto a ogni modalità di K6, il fatto che NEA e
diversification ratio di K8 **si mostrano insieme** perché NEA da solo è cieco alla
correlazione. Se l'obbligo non è nel contratto, il consumatore non ha modo di saperlo.

**Il degrado.** Cosa fa il consumatore se il campo non c'è. È ciò che permette a **E**
di costruire *lasciando il posto* invece di aspettare — che è l'intera ragione per cui
questo piano ha cinque dipendenze invece di ventitré.

---

## ⚠️ La clausola obbligatoria per K1 e K8: il mock stantio

Ogni contratto che **cambia la forma del payload** — oggi K1 e K8 — deve portare una
riga in più, e non è burocrazia.

L'impalcatura degli E2E del rischio (`e2e/portfolio/risk-mocks.ts` dopo la divisione di
**D**, oggi `risk-analysis.spec.ts:210-463`) contiene `resultFor`, che costruisce le
risposte finte del backend. Cioè **congela la forma del payload**.

> ## 🔑 Un mock stantio non fallisce: **rassicura**.
>
> Se K1 aggiunge la serie underwater e nessuno aggiorna `resultFor`, i test continuano
> a passare — servendo una forma che il backend non produce più. Il sistema *sembra*
> coperto, e non lo è.

È la stessa famiglia del CVaR rimasto sbagliato per un anno (**D28**): non un errore
rumoroso, ma una verifica che ha smesso di verificare senza dirlo. Quindi ogni
contratto di questo tipo scrive **chi aggiorna il mock e quando** (**D83**).
