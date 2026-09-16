# Step 4 — copie read-only dai domini Asset/Portfolio/Broker/FX

**Stato:** PENDING TOOL HANDSHAKE.
**Dipende da:** autorizzazione prodotto e audit API corrente.
**Può procedere in parallelo con:** core esatto, input condiviso e shell fixture-driven.

← Master: [piano implementativo](plan-phase00PacRebalancerImplementation.prompt.md)
← Precedente: [solver e policy](plan-phase00Step3PacRebalancerSolverPolicies.prompt.md)

## 1. Scopo

Fornire al planner copie esplicite, modificabili e autorizzate dei fatti già
posseduti dai domini LibreFolio. Il planner deve funzionare anche senza tali
copie e senza Asset persistiti nel DB.

Le API di dominio raccolgono fatti; il Tool compute riceve uno snapshot
autosufficiente e non accede a DB/provider.

## 2. Ownership

Percorso primario:

```text
backend/app/services/portfolio_allocation_source.py
```

Percorsi eventuali, assegnati soltanto dopo audit:

```text
backend/app/api/v1/assets.py
backend/app/api/v1/portfolio_api.py
backend/app/api/v1/brokers.py
backend/app/api/v1/fx.py
backend/app/schemas/assets.py
backend/app/schemas/portfolio.py
```

Frontend source client:

```text
frontend/src/lib/features/tools/pac-allocator/planner/source-copy.ts
frontend/src/lib/features/tools/pac-allocator/planner/source-types.ts
```

API schema/client generati restano al writer integrazione. Nessun secondo
writer modifica questi file.

## 3. Audit iniziale obbligatorio

Per ogni fatto richiesto indicare:

| Fatto | API/service esistente | Completo | Auth | Azione |
|---|---|---:|---:|---|
| Asset canonical ID | da verificare | sì/no | principal | riuso/estensione |
| holding per Broker | da verificare | sì/no | principal | riuso/estensione |
| quantità custodita | da verificare | sì/no | principal | riuso/estensione |
| quota economica | da verificare | sì/no | principal | riuso/estensione |
| cash Broker×valuta | da verificare | sì/no | principal | riuso/estensione |
| prezzo mid/valuta | da verificare | sì/no | principal | riuso/estensione |
| `quote_base_quantity` | da verificare | sì/no | principal | riuso/estensione |
| PMC | da verificare | sì/no | principal | riuso/estensione |
| type/sector/geography | da verificare | sì/no | principal | riuso/estensione |
| Broker capability/fee/tax | da verificare | sì/no | principal | riuso/estensione |
| FX rate/source/date | da verificare | sì/no | principal | riuso/estensione |

Prima di creare un endpoint, dimostrare che nessuna API/service esistente
fornisce già il fatto con semantica corretta.

## 4. Azioni di copia

La UI espone pulsanti indipendenti:

1. copia scenario/holding iniziali;
2. copia cash esistente;
3. copia prezzi;
4. usa distribuzione corrente come base modificabile del target;
5. copia Broker/capability;
6. copia FX salvati.

Una response unica può trasportare più sezioni, ma:

- nessuna sezione viene applicata implicitamente;
- nessun refresh live;
- la distribuzione corrente è base, non consiglio;
- l'utente vede preview e staleness;
- il manuale resta sempre possibile.

## 5. Asset e holding

Regole:

- aggregazione economica per identità Asset canonica, non nome/simbolo;
- custodia per Broker preservata;
- quantità e valore con unità;
- inventario frazionario non arrotondato;
- OWNER `0%`: quantità custodita intera, quota economica separata;
- PMC Asset×Broker/lote secondo dominio esistente, senza cambiare FIFO/WAC;
- prezzo con currency, source, as-of e `quote_base_quantity`;
- type/sector/geography espliciti o missing issue;
- Asset senza prezzo non viene eliminato.

Il planner non assume che due record con label uguale siano lo stesso Asset.

## 6. Cash, contributi e Broker

- cash esistente copiato per Broker×valuta;
- contributi nuovi non vengono inventati dalla copy e restano input separato;
- nessuna cassa unica convertita;
- Broker ID/currency/capability autorizzati;
- fee BUY/SELL e tax mode separati;
- un Broker non autorizzato causa failure atomica;
- non restringere silenziosamente la response ai Broker visibili;
- scenario manuale può usare Broker locali alla request, senza DB ID.

## 7. Prezzi e FX

Le copy leggono soltanto dati salvati.

Vietato usare automaticamente:

```text
/assets/prices/current
```

perché può attivare fetch e scrivere OHLC.

Ogni prezzo/FX riporta:

- valore;
- coppia/currency;
- source/provider;
- timestamp/as-of;
- staleness;
- base quantity;
- eventuale missing/unsupported.

FX manca/incoerente:

- non omettere Asset o cash;
- restituire issue strutturata;
- lasciare al draft la decisione manuale;
- nessun provider call durante Tool compute.

## 8. Autorizzazione e privacy

Ogni endpoint/service:

- riceve il principal standard;
- verifica Portfolio/Broker/Asset;
- non restituisce subset “best effort” se una selezione contiene entità
  non autorizzate;
- non logga quantità, valori o payload;
- non inserisce valori personali in diagnostics;
- non restituisce route/order consigliati;
- non modifica record.

Test obbligatori:

- utente proprietario;
- admin secondo policy esistente;
- altro utente;
- Broker misto autorizzato/non autorizzato;
- Asset mancante/stale;
- account switch durante request;
- nessun side effect DB.

## 9. Lifecycle frontend della copy

Ogni request cattura:

```text
account_generation
component_instance_id
request_sequence
draft_revision
target_section
```

La response è applicabile soltanto se tutti coincidono. Inoltre:

- `AbortController` per nuova request/unmount/account switch;
- risposte vecchie ignorate;
- nessuna sovrascrittura silenziosa di campi modificati;
- preview diff e conferma quando la sezione non è pristine;
- applicazione atomica della sezione scelta;
- source metadata resta visibile nel draft.

Il backend fornisce fatti; questa logica non calcola valori finanziari.

## 10. Sequenza

- [ ] 1. Verificare baseline e file ownership.
- [ ] 2. Compilare matrice fatto→API/service.
- [ ] 3. Identificare gap reali e ottenere approvazione dei file.
- [ ] 4. Implementare estensioni domain-level minime.
- [ ] 5. Implementare schema response read-only.
- [ ] 6. Scrivere test auth/missing/provenance/no-side-effect.
- [ ] 7. Rigenerare client tramite writer integrazione.
- [ ] 8. Implementare source-copy client e lifecycle.
- [ ] 9. Collegare pulsanti indipendenti nella shell.
- [ ] 10. Review auth/privacy e checkpoint.

Selector:

```text
services portfolio-allocation-source
front-utility component-unit
```

I selector Playwright `front-utility pac-tool` e
`front-utility rebalancer-tool` restano vietati fino al doppio `APPROVED`
della review umana in Step 5.

## 11. Stop conditions

- serve modificare FIFO/WAC o schema DB;
- manca un principal check standard;
- un endpoint di prezzo ha side effect;
- il dato richiede provider I/O durante compute;
- non è possibile distinguere custodia/quota economica;
- una response parziale nasconderebbe entità non autorizzate;
- la UI dovrebbe ricostruire PMC, FX o valore.

Ogni caso torna al coordinator; nessuna scorciatoia.

## 12. Definition of Done

- audit fatto→source completo;
- sole estensioni necessarie;
- manual scenario ancora indipendente;
- sei copy action indipendenti;
- canonical identity e multi-custody corretti;
- cash nativo e contributi separati;
- prezzi/FX con provenance/staleness;
- auth fail-closed;
- zero side effect;
- stale-response protection verificata;
- CP3 domain-copy pronto e porta libera.

→ Step 5: [Frontend e review umana](plan-phase00Step5PacRebalancerFrontendReview.prompt.md)
