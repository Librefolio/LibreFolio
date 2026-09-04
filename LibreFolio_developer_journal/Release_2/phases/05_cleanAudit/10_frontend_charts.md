# 10 — Frontend: Grafici & Segnali

> `src/lib/charts/` (28 file, 4 288 righe), incluso `charts/signals/`
> Gravità massima: 🟢

---

## Sintesi

È il sottosistema frontend più pulito, e per una volta il dato è netto:

- **1 export inutilizzato** su 4 288 righe
- **1 tipo inutilizzato**
- **0 statement reattivi legacy `$:`** — migrazione alle Svelte 5 Runes **completa**
- **0 file orfani**

Lo zero sulla migrazione Runes è il risultato più significativo. Il frontend ha 101 `$:`
residui distribuiti su componenti, impostazioni e rotte (vedi report
[11](11_crosscutting.md)), ma **nessuno** nei grafici. Il sottosistema più
matematicamente denso è anche quello con meno debito di migrazione.

Non c'è nulla da rimuovere qui. Questo report documenta *perché* è pulito, perché la
risposta è riutilizzabile altrove.

---

## Metriche

| | Valore |
|---|---:|
| File | 28 |
| Righe | 4 288 |
| Export inutilizzati | **1** |
| Tipi inutilizzati | **1** |
| File orfani | **0** |
| `$:` legacy | **0** |

### Struttura di `charts/signals/`

| Categoria | File |
|---|---|
| Modelli di segnale | `ChartSignal.ts`, `CompoundSignal.ts`, `LinearSignal.ts`, `MeasureSignal.ts`, `SineSignal.ts`, `AssetComparisonSignal.ts`, `FxPairSignal.ts` |
| Ponte con il backend | `backendRenderer.ts`, `backendTypes.ts`, `requestBuilder.ts`, `resultMapper.ts`, `schemaMapper.ts`, `catalogMapper.ts` |
| Politica e registro | `previewPolicy.ts`, `registry.ts`, `signalProblem.ts`, `signalVisualStyle.ts` |
| Test | `__tests__/` |

---

## Reperti

### 🟢 J1 — `signalLabelToText` inutilizzata

**Dove**: `src/lib/charts/signalLabel.ts`

Unico export orfano del sottosistema.

> **Tracciatura**: la resa testuale delle etichette dei segnali avviene altrove — i
> componenti compongono l'etichetta direttamente, o usano la formattazione ECharts. **La
> funzionalità esiste**, questa è una via alternativa non presa.

Stessa forma del *DRY orfano* già osservato nel backend (report
[07](07_schemas_utils.md), G1) e negli store (report [08](08_frontend_state_api.md), H4):
esiste l'helper, i consumatori riscrivono l'espressione.

**Rimedio**: adottarla dove le etichette vengono composte a mano, oppure rimuoverla.
Impatto minimo in entrambi i casi.

Va notato che sull'intero sottosistema questo è **l'unico** reperto — la proporzione
(1 su 4 288 righe) è di un ordine di grandezza migliore rispetto agli store
(26 su 6 665).

---

### 🟢 J2 — Migrazione Runes completa: zero `$:` in 4 288 righe

Nessuno statement reattivo legacy. Per contrasto, il resto del frontend ne ha 101:

| Area | `$:` |
|---|---:|
| `components/ui/` | 26 |
| `components/brokers/` | 26 |
| `components/settings/` | 25 |
| `routes/` | 21 |
| `components/layout/` | 3 |
| **`charts/`** | **0** |

Vale la pena capire perché, perché la ragione è generalizzabile.

I grafici sono l'area con la **catena di derivazione più profonda** del frontend: dati
grezzi → serie normalizzate → serie con indicatori → configurazione ECharts → rendering.
Con `$:` la reattività è implicita e l'ordine di esecuzione è inferito dal compilatore; su
catene lunghe questo produce ricalcoli difficili da prevedere e cicli accidentali.

Con `$derived` la dipendenza è esplicita e il grafo è dichiarato. Su una catena a cinque
livelli, il vantaggio è sostanziale — quindi qui la migrazione ha avuto un ritorno
immediato ed è stata completata.

Nei componenti di impostazioni o nei form dei broker, dove `$:` calcola una singola
espressione da un singolo campo, il ritorno è marginale e la migrazione è slittata. Da qui
i 101 residui, concentrati esattamente nelle aree a derivazione piatta.

> **Conclusione operativa**: i 101 `$:` residui non sono un rischio tecnico immediato, ma
> sono debito di **coerenza**. La regola di progetto dice "Runes nei nuovi componenti", e
> quei file continueranno a essere modificati. La migrazione va fatta file per file quando
> si tocca il file per altri motivi, non come campagna dedicata.

---

### 🟢 J3 — Perché il sottosistema è pulito: separazione modello/rendering

L'organizzazione dei file spiega l'assenza di codice morto meglio di qualunque metrica.

I sette modelli di segnale (`LinearSignal`, `SineSignal`, `CompoundSignal`,
`MeasureSignal`, `AssetComparisonSignal`, `FxPairSignal`, e `ChartSignal` come base)
implementano un'interfaccia comune e sono raggiunti tramite `registry.ts`. Come per i
plugin del backend (report [05](05_signals_risk.md), reperto E4), **un contratto
esplicito impedisce l'accumulo di codice orfano**: se un metodo non serve al contratto,
non viene scritto.

I sei file di ponte con il backend (`backendRenderer`, `backendTypes`, `requestBuilder`,
`resultMapper`, `schemaMapper`, `catalogMapper`) hanno ciascuno una direzione precisa —
richiesta in uscita, risultato in entrata, schema, catalogo. Nessuna sovrapposizione,
quindi nessuna duplicazione parziale del tipo osservato in `fx.py` o nelle property dei
modelli.

Questa è la terza conferma nell'audit — dopo i provider e i signal plugin del backend —
che **il pattern registry + contratto astratto si autopulisce**. Le aree del progetto che
lo adottano non accumulano codice morto; quelle che non lo adottano (store, componenti,
schemi) sì.

---

### 🟢 J4 — `previewPolicy.ts` e `signalProblem.ts`: due file da tenere d'occhio

Non sono reperti — nessuno strumento li ha segnalati. Sono una nota per i prossimi audit.

`previewPolicy.ts` codifica *quando* un segnale può essere mostrato in anteprima e
`signalProblem.ts` *come* si rappresenta un segnale non calcolabile. Sono entrambi
politiche, non calcoli: il tipo di file che tende a crescere per accumulo di casi
particolari, ognuno aggiunto per un motivo valido.

Oggi stanno bene. Valgono un controllo di complessità al prossimo ciclo, insieme ai
validatori di `schemas/signals.py` (report [05](05_signals_risk.md), E1) che risolvono il
problema speculare lato backend — e che sono già arrivati a complessità 32.

---

## Interventi raccomandati

| Priorità | Intervento | Costo | Rischio |
|---|---|---|---|
| 1 | Adottare o rimuovere `signalLabelToText` | basso | nullo |
| 2 | Verificare l'unico tipo esportato inutilizzato | basso | nullo |

Nient'altro. Il sottosistema non richiede interventi.

**Il valore di questo report non è nella lista di cose da fare, è nel riferimento.**
Grafici e segnali dimostrano che su questo codebase è possibile avere 4 288 righe con un
solo simbolo orfano e zero debito di migrazione. Quando si valuta se le 26 rilevazioni
degli store o i 20 file morti dei componenti siano "normali", la risposta è no: questa è
la norma raggiungibile, ed è stata raggiunta qui.

La differenza non è la disciplina di chi ha scritto il codice — è **strutturale**:
contratti espliciti, registry, direzioni di dipendenza chiare. Dove c'è quella struttura,
il codice morto non si accumula.
