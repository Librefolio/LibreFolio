# Solver operativo PAC + Ribilanciamento

> **ARCHIVIO:** piano solver superato, non specifica corrente. L'entrypoint
> della suite target è
> [`../plan-phase00PacRebalancerTargetDesign.prompt.md`](../plan-phase00PacRebalancerTargetDesign.prompt.md).

**Stato:** SUPERATO / RE-SCOPED PRIMA DELL'IMPLEMENTAZIONE — Round 5 e Round 7
sono tappe storiche; la suite target è l'unica autorità corrente.

← Previous: [Round 4 — PAC + Ribilanciamento P1 multi-servizio](plan-phase00Step2Round4-PacAndRebalancerUiAcceptance.prompt.md)

→ Replacement:
[Round 5 — PAC/Rebalancer operational planner](plan-phase00Step2Round5-PacRebalancerOperationalPlanner.prompt.md)

→ Piano implementativo successivo nel percorso storico:
[Round 7 — PAC/Rebalancer operational migration](plan-phase00Step2Round7-PacRebalancerOperationalMigration.prompt.md)

> Questo file conserva il primo abbozzo solver. `quantity_step`, assenza di
> routing Broker, vecchi status e obiettivi non sono più contratto attivo.
> Round 7 sostituisce integralmente lo scope eseguibile; nessuna implementazione
> di questo piano storico è richiesta.
>
> **Correzione 2026-09-16:** tutte le formulazioni nel corpo sono storiche.
> L'autorità corrente usa, per PAC e Rebalancer, il primario fixed-L2 globale:
> primo tier MIQP, poi convex-MIQCP sul sublevel `L2_fixed` incumbent per
> ottimizzare `U`; il sublevel è la faccia ottima solo dopo prova esatta.
> La variante BUY-only usa `U → L2_fixed` su azioni congelate.
> `F_ref` fissa target/accounting; percentuali/D∞/D1 sono diagnostici e SELL
> resta funding-only quantum-minimal. PySCIPOpt/SCIP è candidato additivo
> approvato, ma dependency/probe/capacità e payload restano gate Round 7.

## 1. Obiettivo

Estendere i due servizi già separati:

- PAC: distribuire liquidità disponibile in acquisti;
- Ribilanciamento: avvicinare il portafoglio al target con buy-only o
  buy+sell opzionale.

Nessun ordine viene eseguito. Il piano congelerà contratto numerico, dominio
solver e criteri prima di scegliere/installare/eseguire un solver.

## 2. Contratto da congelare

- Target per identità canonica; contesti Broker solo fatti di custodia.
- Nessun routing Broker implicito.
- Nessun buy+sell dello stesso strumento per gonfiare l'obiettivo.
- Nessuna vendita oltre inventario.
- Nessuno short o leva.
- Cash separato per valuta.
- FX opzionale esplicito con flussi, costi e margini; nessun ciclo/arbitraggio.
- Fee, buffer, riserve, cap min/max buy/sell e minimi operativi espliciti.
- `quantity_step` per ordini; `monetary_step` per contributi.
- Inventario esistente mai arrotondato al quantum ordini.
- Costi non sono investimento; cash/contributi non sono duplicati.
- PAC buy-only non diventa “massimizza acquisti” quando vendite abilitate.

Obiettivi lessicografici proposti:

1. minimizzare massimo scostamento;
2. minimizzare errore quadratico;
3. preservato lo score, minimizzare turnover/numero ordini o massimizzare
   capitale investito secondo preset esplicito.

Stati distinti:

- `no_op`;
- `infeasible_proven`;
- `feasible_unproven`;
- `limit_without_incumbent`;
- `timeout`;
- `optimal` solo con prova.

## 3. Output

PAC:

- quantità proposte/quantizzate;
- consumo per cassa/valuta;
- residui, fee e buffer;
- scostamento prima/dopo;
- spiegazioni backend.

Ribilanciamento:

- buy/sell opzionali;
- valore finale;
- modalità buy-only;
- liquidità mancante senza vendite;
- turnover/numero ordini;
- vincoli attivi e motivi infeasibilità.

## 4. Prove obbligatorie

- evaluator Decimal indipendente dal solver;
- oracle esaustivo completo per casi piccoli, non add-only;
- equivalenza preset su input normalizzati uguali;
- multi-currency/FX/limiti/no-op/contributi/quantum/rounding/nonfinite;
- budget basso, permessi e privacy;
- benchmark e dominio supportato dichiarati;
- esempi 3484.14/3493.24 solo aritmetica delle assunzioni originali, non golden
  optimal del nuovo criterio.

## 5. UI

- Route PAC/Rebalancer restano separate.
- Componenti P1 accettati riusati.
- Grafici prima/target/dopo.
- Tabelle buy/sell/cash/FX complete.
- Spiegazioni backend.
- Nessun calcolo economico frontend.

→ Follow-up:
[Round 5 — PAC/Rebalancer operational planner](plan-phase00Step2Round5-PacRebalancerOperationalPlanner.prompt.md)

→ Current implementation plan:
[Round 7 — PAC/Rebalancer operational migration](plan-phase00Step2Round7-PacRebalancerOperationalMigration.prompt.md)
