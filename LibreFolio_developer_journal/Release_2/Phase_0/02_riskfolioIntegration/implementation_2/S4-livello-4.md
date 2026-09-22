# S4 — L4 · «Cosa succede se…?»

> **Fase 2 · superficie.** Vincoli comuni: `implementation_2/_comune.md`
> **Sessione**: H `e-alfy-h-monte-carlo` (riuso)
> **Corsia**: `--test-port 6156` · `--data-dir /tmp/librefolio-r2-s4`
> **Leggi prima di scrivere**: `implementation_2/PRIMITIVE.md` (360 righe, per intero)

---

## 1. Il tuo livello è **il più fedele al design di tutta la consegna**, e va detto

La review lo ha misurato: delle **sette** rappresentazioni prescritte da `05-grammatica-visiva`,
solo **tre** sono rese — e **due delle tre sono tue**: il tornado degli scenari (§7.6) e il cono
della simulazione (§7.7, con `percentile_bands` e `seriesType: 'band'`).

E il selettore delle modalità coincide **parola per parola** col testo del design, con le ipotesi
inline in quattro lingue:

```
Storia rimescolata (consigliata) · Mercato calmo · Crisi prolungata
Shock e recupero · Curva normale (GBM) (avanzata)
```

Anche il divieto è rispettato: *«`sobol_start_index` esce dalla UI in ogni caso»* → in
`L4Simulation` compare **solo** nel costruttore della richiesta, mai come controllo.

> 🔑 **Perché proprio il tuo?** Perché possedevi insieme **il motore, le chiavi i18n e il pannello**.
> È l'unico caso del round 1 in cui una cosa e la sua resa stavano nello stesso albero — ed è la
> ragione per cui il round 2 è organizzato per superficie invece che per componente.

**L4 è anche l'unico livello completo, ed è l'unico che parte chiuso.** I tre che l'utente incontra
aperti sono quelli a cui mancano i grafici. Non è una coincidenza da spiegare: è il tuo vantaggio
da conservare.

---

## 2. Cosa ti manca, e sono due cose diverse

### 2.1 ⚠️ L4 non passa dai componenti del progetto

Il developer, guardandolo: *«una grande lista di componenti standard; in primis il selettore delle
date che non è `SingleDatePicker`, ma in generale anche i colori dei bottoni o la dimensione dei
preset non sono allineati con l'estetica del progetto»*.

Misurato: **`SingleDatePicker` compare 0 volte** in `levels/l4/`. Il progetto ce l'ha —
`ui/date/SingleDatePicker.svelte`, **388 righe**, con la giunzione digitato/calendario già
risolta — e `PRIMITIVE.md` lo elenca fra le cose **da non riscrivere**.

Stesso discorso per bottoni e dimensioni: `PRIMITIVE.md` §1 ha l'inventario completo.

### 2.2 🔴 Il Monte Carlo non dice a che punto è

> *«Non si ha modo di capire da UI a che punto sia la simulazione. Qui avrebbe senso mettere su un
> qualche tipo di stream e comunicare la percentuale di calcoli a cui si è arrivati, con una barra
> che avanza.»*

**È lavoro di piattaforma, non di UI**, e sei l'unico che può farlo: il worker QuantLib gira in un
**processo separato**, quindi l'avanzamento va propagato **dal worker al processo web e da lì al
client**.

⚠️ **Non dare per scontata la forma.** SSE, websocket, polling su un id di lavoro: ciascuna ha un
costo diverso sul confine di processo che hai costruito tu. **L'analisi deve confrontarle**, non
sceglierne una.

📌 E ricorda la regola di progetto: in un `async def` ogni libreria sincrona che fa I/O va avvolta
in `await asyncio.to_thread(...)`. Un canale di avanzamento che blocca l'event loop è peggio di
nessun canale.

---

## 3. La tua superficie

**Possiedi** `components/risk/levels/l4/*` (quattro `.svelte` + gli helper) e, per l'avanzamento,
`services/risk/quant/*` e `risk_plugins/simulation.py`.

**Non toccare**: `L1*` → S1 · `L2*` → S2 · `L3*` → S3 · `AssetSetRiskPanel` → S5 ·
`RiskLevelsPanel.svelte` e `levelHelpers.ts` → **S1** · `i18n/*.json` fuori da `risk.levels.l4.*`.

⚠️ **Una tua chiave è condivisa**: `risk.simulation.mode.gbm` (tua) e
`risk.levels.l4.provenance.values.gbm` (di E) coesistono. Sono **due chiavi diverse** e vanno
lasciate tali — l'integrazione del round 1 l'ha verificato.

---

## 4. Primo deliverable: analisi, non codice

1. Hai letto `PRIMITIVE.md`? Quali componenti di L4 vanno sostituiti con quelli del progetto,
   **elencati uno per uno**?
2. L'avanzamento: **confronta almeno due forme** con il costo sul confine di processo.
3. `SimulationProvenance` è costruita e testata unitariamente, **ma i suoi campi arrivano dal
   contratto K6**: verifica sul filo, non nei test unitari, che `regime`, `seme` e
   `block_length_days` arrivino davvero. *(Nel round 1 non arrivavano: Zod li scartava.)*
4. I passi, con la verifica di ciascuno.

⚠️ **Nessuna riga di codice prima che l'analisi sia rivista.**
