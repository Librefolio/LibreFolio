# S1 — L1 · «Quanto può fare male?»

> **Fase 2 · superficie.** Cinque mandati in parallelo, file disgiunti.
> **Sessione**: E `e-alfy-vigilant-adventure` (riuso)
> **Corsia**: `--test-port 6153` · `--data-dir /tmp/librefolio-r2-s1`
> **Leggi prima di scrivere**: `implementation_2/PRIMITIVE.md`

---

## 1. Cos'è cambiato sotto di te, e non lo sai ancora

Due mandati hanno lavorato mentre eri fermo. **Entrambi hanno cambiato il terreno su cui costruirai.**

**F1** ha riparato i dati di prova. Prima le analitiche vedevano **15 osservazioni contro le 20
richieste** e metà pannello non poteva mostrare niente. Ora ogni asset posseduto ha **267–373
punti**, e `risk_contribution` calcola invece di dichiararsi indisponibile.

**F2** ha scritto `implementation_2/PRIMITIVE.md` — **360 righe che devi leggere per intero prima
di scrivere una riga**. Contiene cosa esiste, come si monta, e soprattutto **cosa non devi
costruire**. Nel round 1 quel contratto esisteva dentro l'intestazione di `RiskMetricCard`, era
scritto bene, **e nessuno l'ha aperto**: la card è arrivata all'integrazione con **zero consumatori**.

> 🔑 **Tu sei il primo che la monta.** Se devi fare domande a F2 per riuscirci, il documento non
> era abbastanza — e questo è un risultato da riportare, non un fastidio da sopportare.

---

## 2. La tua superficie

**Possiedi** `components/risk/levels/L1HowMuchItHurts.svelte`.

**Sei anche scrittore unico** di due superfici condivise, perché le conosci meglio di chiunque:

```
components/risk/levels/RiskLevelsPanel.svelte      ← contenitore
components/risk/levels/levelHelpers.ts             ← aiutanti
```

**Gli altri quattro mandati ti chiederanno modifiche lì. Sei tu che le applichi.**

**Non toccare**: `L2*` → S2 · `L3*` → S3 · `levels/l4/*` → S4 · `AssetSetRiskPanel` → S5 ·
il catalogo del runner e gli spec E2E → T3 · `i18n/*.json` **fuori** dal tuo namespace
`risk.levels.l1.*`.

---

## 3. Cosa deve esserci alla fine

### 3.1 Le card al posto della lista

Oggi L1 è una `<ul>` con `<li class="flex items-baseline justify-between gap-4 py-2">`: a schermo
largo etichetta e numeri finiscono ai due bordi opposti col vuoto in mezzo. Il developer l'ha
descritto così: *«tre numeri e occupa tutta la pagina, è un casino»*.

`RiskMetricCard` **esiste ed è completa** — l'ha verificato il coordinatore leggendone le props —
e `RiskCardGrid` dispone le card con `auto-fit`, **senza breakpoint enumerati**. Entrambe in
`ui/display/`, entrambe documentate in `PRIMITIVE.md`.

⚠️ **La card ha una doppia etichetta**: `label` è la domanda in lingua piana, `technicalName` è il
nome tecnico accanto. Il developer l'ha chiesta senza sapere che esisteva: *«la label deve essere
più tecnica, mentre il tooltip è giustamente discorsivo»*. **Oggi l'etichetta è già discorsiva,
quindi il tooltip non ha niente da aggiungere e ripete.** La doppia etichetta risolve la causa.

### 3.2 🔴 Le due rappresentazioni mancanti — **i dati ci sono già**

`05-grammatica-visiva` §7.1 e §7.2 le prescrivevano. Non sono mai state rese, **e non perché
mancasse il dato**:

| campo | nel contratto | nel client generato | reso |
|---|---|---|---|
| `underwater_series` | ✅ | ✅ | 🔴 **0 lettori** |
| `return_bins` | ✅ | ✅ | 🔴 **0 lettori** |
| `var_bin_edge` | ✅ | ✅ | 🔴 **0 lettori** |

**7.1 — Underwater chart.** `underwater_series` è una serie **per osservazione**, e la baseline
pre-rendimento **è già tolta** dal produttore (`drawdown_summary` fa `report.drawdowns[1:]` con
`strict=True`). Usa `LineChart`: è fatto per le serie temporali.

**7.2 — Istogramma della distribuzione.** `return_bins` più la barra del taglio a `var_bin_edge`.

> ⚠️ **`var_bin_edge` va letto con `=== null`, mai con `?? 0`.** Uno zero è un taglio legittimo:
> il ripiego lo renderebbe indistinguibile dall'assenza. E la barra va trovata **per
> disuguaglianza** su intervalli semiaperti, non per uguaglianza.
>
> 📌 Questa regola l'avevi scritta tu nella coda del round 1. È qui perché è tua.

### 3.3 Le quattro misure senza casa (W0)

Il developer ha deciso di assegnarle. **Non diventano quattro righe nuove**: ciascuna si aggancia
come **seconda riga** di una che già esiste.

```
Una giornata storta (VaR 95 %)        ← c'è già
  └ e la peggiore vissuta davvero      worst_realization
La peggior discesa (max drawdown)     ← c'è già
  └ che non superi nel 95 % dei casi   drawdown_at_risk
  └ e se la superi, in media           conditional_drawdown_at_risk
Underwater chart                       ← 7.1
  └ Ulcer index                        ulcer_index, come DIDASCALIA del grafico
```

🔑 **L'Ulcer index sotto il grafico, non in una riga sua**: da solo è un numero senza unità che
nessuno sa leggere. Sotto la curva che lo genera **diventa la sua didascalia e si spiega da sé**.

> 🔴 **Correzione (18 Set, trovata da S1).** Avevo scritto: *«Le quattro misure non hanno una
> pagina di documentazione. Chiedile a T2 oppure consegna senza `DocsLink`.»* **Falso: esistono
> tutte e quattro**, 82/90/125/111 righe, sotto
> `mkdocs_src/docs/financial-theory/technical-analysis/risk-metrics/`. ✅ **T2 esce dal percorso
> critico di S1.** Il conteggio «22 pagine» era giusto — **non è mai stato usato per controllare
> l'inventario**, ed è esattamente lì che ho sbagliato (R2-19).
>
> **URL corretto**: `financial-theory/technical-analysis/risk-metrics/<slug>/` — prefisso
> completo, **senza `.md`**, **con lo slash finale**. ⚠️ Il cancello di `dev.py:1238` salta i
> `path={espressione}`: **aprili nel browser**.

---

## 4. Quattro vincoli misurati, non opinioni

**① I link alla documentazione sono sbagliati in due modi.** I sei `DocsLink` dei livelli puntano
a `user/analysis/risk.md#…`: quella cartella **non esiste**, e la forma con `.md#ancora` è
sbagliata comunque perché `use_directory_urls` è `true` per default.

> 🔄 **Decisione cambiata (18 Set).** Avevo scritto *«non ripararli tu — è di T2»*. **Il debito
> dei `DocsLink` è di chi possiede il file**, non di T2: T2 tiene solo quelli che stanno in file
> di nessuno, più il cancello. Motivo, sollevato da S3: **non si possono aggiungere link corretti
> accanto a tre sbagliati senza che la card si contraddica.** Ripara quelli che stanno in casa
> tua, con il percorso verificato per intero.

**② Niente `toFixed` nuovi.** Nel perimetro `components/risk/levels/` ce ne sono **16**; nel
perimetro `components/risk/` sono **26**. *(Due numeri veri di due perimetri diversi: `PRIMITIVE.md`
spiega perché la differenza conta.)* **Ripararli non è tuo, è di T4. Non aggiungerne.**

**③ Gli avvisi in inglese non sono traduzioni mancanti**: sono **17 messaggi in prosa che il
backend produce** (`risk/service.py:608`, `:765`) e che il frontend rende alla lettera. **Non è tuo**
— è di T1 — ma **non incorporarli nel tuo layout come se fossero testo definitivo.**

**④ `api sync` va rieseguito dopo ogni aggiornamento di baseline**, nella forma canonica.
`generated.ts` e `openapi.json` sono **entrambi** nel `.gitignore`: non viaggiano col merge. Nel
round 2 questo ha già prodotto una diagnosi sbagliata e un pomeriggio perso.

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py api sync
```

---

## 5. Definizione di finito — **è cambiata**

```
Round 1:  finito = il mio codice è scritto e i test passano
Round 2:  finito = IL COORDINATORE LO VEDE sull'app in esecuzione, in italiano,
                   con il link che porta a una pagina che esiste
```

**Non chiudi senza che io abbia guardato L1 nel browser.** È la verifica che ha trovato tutti e tre
i delta della review, e nel round 1 l'ho fatta **dopo** l'integrazione invece che **prima di ogni
chiusura**.

---

## 6. Primo deliverable: **analisi, non codice**

1. Hai letto `PRIMITIVE.md`? **Cosa ti manca per montare la card senza chiedere a F2?**
2. `underwater_series`: `LineChart` basta, o serve qualcosa che non c'è?
3. `return_bins`: quale `seriesType`? ⚠️ **`seriesType` non è una prop di `LineChart`** — vive su
   `RenderedSignal`. `PRIMITIVE.md` §3 spiega quale grafico per quale forma di dato.
4. Le quattro misure di W0: gli agganci proposti reggono alla lettura dei campi veri?
5. I passi, con la verifica di ciascuno.

⚠️ **Nessuna riga di codice prima che l'analisi sia rivista.**

---

## 7. Due cose dal round 1 e dalla fase 1

> **Non fidarti di questo documento.** Nel round 1 undici mandati su undici hanno trovato falsa
> almeno un'assunzione del proprio briefing. Nella fase 1, **cinque numeri miei o di F2 sono
> risultati sbagliati, e ciascuno l'ha trovato l'altro**. Se una misura qui sopra diverge dalla
> tua, **dillo subito**.

> **Lo stage è l'ultimo atto, e lo dichiari tu.** Nella fase 1 la finestra fra «il coordinatore
> stagia» e «l'agente finisce di scrivere» si è riaperta **sei volte**. La cura che ha funzionato:
> quando hai finito dici `FROZEN`, **e solo allora** stagio io. E il controllo che non mente è
> quello dimensionale: `git show :file | wc -l` contro `wc -l file` — **non cerca una stringa,
> quindi non può tacere su un'altra.**
