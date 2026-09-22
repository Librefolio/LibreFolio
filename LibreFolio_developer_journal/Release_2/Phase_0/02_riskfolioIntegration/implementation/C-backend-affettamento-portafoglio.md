# Mandato C — Affettamento del portafoglio per asset

| | |
|---|---|
| **Flusso** | W3 di [`../07-piano-esecutivo.md`](../07-piano-esecutivo.md) §2 |
| **Dominio** | backend scope + un pezzo di UI di selezione |
| **Taglia** | M |
| **Lane** | porta `6242` · data dir `backend/data/test-risk-c` |
| **Dipende da** | nulla |
| **Consegna** | contratto **K4** a **E** |

> Regole comuni: [`README.md`](./README.md) §5. Finito comune: §6.

---

## 1. Perché questo mandato esiste

Oggi `PortfolioRiskScope` filtra **solo per `broker_ids`** (`schemas/risk.py:549-551`):
sa dire *dove* si tiene una cosa, non *cosa* è.

È il gemello del problema che risolve il mandato **B**. Se confrontare un portafoglio
60/40 con un indice azionario è sbagliato, lo è per **due ragioni simmetriche**: il
riferimento sbagliato **e** la fetta sbagliata. Sceglierne bene uno solo risolve metà
del disallineamento (**D58**).

La domanda dell'utente è *«com'è fatta la mia parte azionaria?»*, e oggi non c'è modo
di porla.

---

## 2. Cosa leggere prima

1. [`../04-…`](../04-decisioni-e-questioni-aperte.md) **D57**, **D58**, e **Q8** chiusa
   da **D59**.
2. [`../03-mappa-livelli-pagine.md`](../03-mappa-livelli-pagine.md) §1 — la regola dei
   pesi, che governa cosa la UI può mostrare.

---

## 3. La scelta di progetto, e perché è quella che costa meno

Ci sono due posti dove un filtro per asset potrebbe andare. Il secondo sembra ovvio ed
è sbagliato.

| Candidato | Esito |
|---|---|
| `AssetSetRiskScope` | ❌ **Non è la risposta.** Significa «questi N asset affiancati», **senza pesi**, ed è accettato da **tre plugin su nove** — `correlation`, `portfolio_optimization`, `stress`. Tutto L1 (VaR, CVaR, drawdown) e L3 (KPI, confronto) accetta solo `asset` o `portfolio`, e `risk_contribution` **solo** `portfolio` |
| **`PortfolioRiskScope`** | ✅ Resta uno scope `portfolio`, quindi **tutti e nove i plugin lo accettano senza modifiche** |

> ## 🔑 La proprietà da conservare
>
> Il plugin riceve la lista di asset **già risolta**, non il filtro. `RiskContributionParams`
> è vuoto — `extra="forbid"`, nessun campo — e legge `context.scope_asset_ids` e
> `context.weights` (**D57**).
>
> È questa indirezione che rende il mandato quasi gratuito: **la fetta si propaga da
> sola**.
>
> ⚠️ Corollario operativo: se durante l'esecuzione senti il bisogno di **toccare un
> plugin**, è il segnale che stai sbagliando strada. Fermati e riporta.

---

## 4. I pesi si rinormalizzano — e va detto a schermo

**D59**: affettando, i pesi si rinormalizzano al 100% della fetta.

Il motivo non è estetico. La fetta esiste per essere confrontata con il riferimento
giusto (**D48**), quindi va guardata **come se fosse tutto il portafoglio**. Coi pesi
reali una fetta al 60% risulterebbe **sempre** meno rischiosa del suo indice, e il
confronto — cioè l'intero motivo per cui questo mandato esiste — si romperebbe in
silenzio.

Conseguenza: i contributi al rischio della fetta sommano al 100% **della fetta**.

| | Rinormalizzati ✅ | Reali ❌ |
|---|---|---|
| Domanda | «Com'è fatta la mia parte azionaria, guardata da sola?» | «Quanto pesa sul rischio di tutto?» |
| Confronto con benchmark | sensato | la fetta sembra sempre meno rischiosa |
| Rischio d'equivoco | far credere di essere tutto investito in azioni | leggere un CVaR basso e credere la fetta tranquilla |

La colonna di destra resta comunque servita, ma da un altro strumento: **il contributo
al rischio sull'intero portafoglio**, che la dà già senza affettare nulla.

> ⚠️ **Obbligo di dichiarazione nella UI.** La stessa percentuale significa due cose
> diverse a seconda di cosa la genera. Va scritto, non lasciato intuire. Questa parte
> entra nel contratto **K4** verso E.

---

## 5. Confini

**Di questo mandato**:

- `backend/app/schemas/risk.py` → **solo** le classi di **scope** (`:537-585`)
- `backend/app/services/risk/service.py` → risoluzione dello scope
- la UI di selezione della fetta — concordare con **E** dove vive, perché il pannello è
  suo

**Condiviso**: `schemas/risk.py` con i mandati **A** e **N** — **tre scrittori**. A
scrive `RiskVarCvarOutput` (`:820-835`) e `RiskDrawdownOutput` (`:945-1018`); N scrive
`RiskKpiOutput` (`:640-647`) e `RiskContributionOutput` (`:676-680`). Le tre regioni
sono lontane e Git fonde senza attrito.

⚠️ **Il conflitto vero è `__all__` (`:1067-1126`)**: il file finisce con una lista di
sessanta nomi **ordinata alfabeticamente**, e chi aggiunge una classe deve inserire un
nome in mezzo. È **l'unica regione dell'intera campagna** dove è autorizzata una
risoluzione meccanica — **unione + riordino alfabetico**. Ovunque altro vale
[`README.md`](./README.md) §2.2: **non riformattare, non riordinare gli import, non
toccare una classe non propria**.

**Fuori**, tassativamente:

- i **nove plugin** di `risk_plugins/` — nessuno va toccato, è il collaudo della scelta
  di progetto;
- `metrics.py` e tutto ciò che è del mandato A;
- il catalogo benchmark, che è del mandato B.

> ### ⚠️ Una cosa da sapere per non spaventarsi a un aggiornamento di baseline
>
> Il mandato **N** aggiunge campi additivi a `historical_kpi.py` e
> `risk_contribution.py`. Quindi **dopo l'integrazione** `risk_plugins/` *avrà* delle
> modifiche — ma **non le tue**.
>
> La tua verifica resta valida ed è quella giusta: `git diff` su `risk_plugins/` **nel
> tuo worktree** deve essere vuoto. Se dopo un aggiornamento di baseline vedi arrivare
> le modifiche di N, **non è una violazione del tuo confine**: è lavoro previsto.

---

## 6. Ordine dei passi

1. Campo di filtro per asset su `PortfolioRiskScope`.
2. Risoluzione nel servizio: dal filtro alla lista di `scope_asset_ids`.
3. Rinormalizzazione dei pesi (**D59**).
4. `./dev.py api sync`.
5. **Verifica che i nove plugin siano invariati** — `git diff` su `risk_plugins/` deve
   essere vuoto.
6. UI di selezione, concordata con E.
7. **Comunicare K4**: nome del campo, forma della richiesta, regola dei pesi.

---

## 7. Test

| Cosa | Comando |
|---|---|
| Schemi di scope | `schemas risk` |
| Servizio | `services risk-all -k service` |
| API | `api risk` |
| Integrazione | `services risk-all` |

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test --test-port 6242 --data-dir backend/data/test-risk-c \
  services risk-all
```

Il test che conta più di tutti: **la fetta produce, per ciascuno dei nove analytic, un
risultato coerente con il portafoglio intero quando la fetta *è* il portafoglio
intero**. Se un plugin si comporta diversamente, la propagazione non è trasparente come
si assume.

---

## 8. Definizione di finito

- [ ] Filtro per asset su `PortfolioRiskScope`, scope ancora `portfolio`;
- [ ] **`git diff` su `risk_plugins/` vuoto** — nessun plugin toccato;
- [ ] pesi rinormalizzati, con test che lo prova;
- [ ] la rinormalizzazione è **dichiarata nella UI**, non implicita;
- [ ] `api sync` eseguito;
- [ ] `services risk-all` e `api risk` verdi;
- [ ] **K4 consegnato e comunicato a E**;
- [ ] nessun processo in ascolto su `6242`.
