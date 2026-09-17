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

Ha un secondo effetto, meno ovvio e altrettanto utile: rende visibile un contratto
**cambiato**. La differenza fra la versione scritta e quella nuova diventa un diff
invece che un ricordo contraddittorio — ed è precisamente il tipo di disallineamento
che questa struttura esiste per intercettare.

---

## I contratti

| # | Da | A | Oggetto | Stato |
|---|---|---|---|---|
| **K1** | A | E | Serie underwater (**D14**) e bin dell'istogramma (**D21**) | ⏳ || **K2** | B | G | `primaryAssetType(type)` — **mappa esplicita**, mai `split('_')` | ⏳ |
| **K3** | B | E, F | Selettore benchmark ordinato a sezioni (**D50**) | ⏳ |
| **K4** | C | E | Filtro per asset su `PortfolioRiskScope` + pesi rinormalizzati (**D59**) | ⏳ |
| **K5** | D | E, F | Primitive promosse in `components/ui/`: nomi, percorsi, props | ⏳ |
| **K6** | H | E | Modalità di simulazione e payload del cono | ⏳ |
| **K7** | I | E, F, H | Slug delle pagine di documentazione | ⏳ |
| **K8** | N | E | Campi nuovi su `RiskKpiOutput` e `RiskContributionOutput` | ⏳ |

Legenda: ⏳ atteso · 📝 concordato, non ancora implementato · ✅ consegnato e verificato
· ⚠️ cambiato dopo la consegna

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
