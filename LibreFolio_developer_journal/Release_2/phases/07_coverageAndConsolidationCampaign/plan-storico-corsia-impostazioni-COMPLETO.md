# Piano — copertura: impostazioni, condivisione broker, logica pura

> Lo storico delle corsie precedenti è in `files/plan-storico-corsie-sync-e-logica.md`.

## Il problema

Dopo la corsia precedente il frontend è a **75,77 % di linee / 57,49 % di rami**. Quello
che resta si divide in tre, e solo due terzi valgono la pena:

- i **grafici** (brokers/lots, dashboard) sono ~1 400 rami scoperti ma in gran parte
  configurazione ECharts — esclusi per decisione dell'utente, li troveranno i tester umani;
- le **impostazioni** (14 file, 41,9 % rami, 535 scoperti) e la **condivisione broker**
  (29,7 %, 90) sono comportamento vero;
- una coda di **logica pura** (167 rami) che costa poco e rende subito.

Più un file da decidere: `BulkDeleteLinkedPairModal` — **verificato morto**.

## Il fatto che orienta il piano

`BrokerSharingPanel` **ha già** un E2E (`frontend/e2e/brokers/broker-sharing.spec.ts`) ed è
comunque al 29,7 % di rami. Non manca il percorso felice: mancano gli errori, le liste
vuote, i permessi ai bordi. Quelli un E2E li raggiunge solo facendo fallire il server a
comando; un component test con `$lib/api` simulato li raggiunge tutti.

Stessa logica per le impostazioni: `front-utility settings` esiste già e passa. Quindi
**nessuna nuova spec E2E** in questo piano — solo unit e component test, che è anche ciò
che rende il piano parallelizzabile: vitest non tocca né backend né database, quindi più
agenti possono lavorare insieme senza corrompersi a vicenda.

## Su `BulkDeleteLinkedPairModal`: è morto, dimostrato

- 239 righe, **0 statement eseguiti** su 126, 26 rami mai presi;
- è esportato **solo** da `transactions/modals/index.ts`;
- quel barrel **non è importato da nessuno** (grep su tutto `src/`: zero occorrenze);
- il simbolo non compare in nessun altro file, né in `src/` né in `e2e/`;
- la funzione viva — cancellazione di massa — sta in `TransactionBulkModal`
  (`bulkDeleteSelected`, riga 2414), che è un'implementazione diversa e collegata.

Quindi **rimuovere**, non testare. Con una domanda aperta sul barrel, che a quel punto resta
a esportare otto componenti che nessuno importa da lì.

## Le corsie

Cinque, indipendenti. Le prime quattro sono **solo vitest** e girano insieme; la corsia 0 è
mia e non tocca test.

| # | corsia | file | rami scoperti | tipo |
|---|---|---|---|---|
| 0 | codice morto | `BulkDeleteLinkedPairModal.svelte` | — | rimozione |
| 1 | logica pura, transazioni | `filterState.ts`, `resolveFormItems.ts` | 95 | unit |
| 2 | logica pura, store e file | `fxStoreRegistry.ts`, `imageCrop.ts` | 72 | unit |
| 3 | impostazioni: le schede | `GlobalSettingsTab`, `ProfileTab`, `AboutTab`, `PreferencesTab` | 310 | component |
| 4 | impostazioni: modali e controlli | `SchedulerLogModal`, `SchedulerConfigModal`, `SettingsLayout`, `PasswordChangeModal`, i sei `Setting*` | 222 | component |
| 5 | condivisione broker | `BrokerSharingPanel.svelte` (812 righe) | 90 | component |

### Perché questo taglio

Le corsie 3 e 4 sono entrambe «impostazioni» ma si dividono nettamente: le **schede** sono
form che salvano preferenze (validazione, salvataggio, errore del server), i **modali e i
controlli** sono componenti riusabili con superficie propria. Nessun file compare in due
corsie, quindi nessun conflitto di scrittura.

Le corsie 1 e 2 sono entrambe logica pura ma su domini diversi; si possono fondere in una
sola se si preferisce meno parallelismo.

## Il conflitto da evitare, e come

Tutte le corsie devono registrare i file nuovi in **`scripts/test_runner/_frontend_utility.py`**,
che è una lista scritta a mano. Quattro agenti che la modificano insieme si sovrascrivono.

**Regola del piano: nessun agente tocca il runner.** Ognuno riporta le righe esatte da
aggiungere, e le registro io alla fine in un passaggio solo. `check-orphans` resterà rosso
fino a quel momento, ed è atteso.

Stessa regola per i file di prodotto: se una corsia ha bisogno di un `data-*` che non
esiste, **lo chiede** invece di aggiungerlo — altrimenti due agenti possono toccare lo
stesso `.svelte`.

## Le regole di sempre

`.github/agents/test-author.agent.md` è la fonte. Le tre che in questa campagna hanno morso:

1. **Il test non costruisce l'atteso chiamando la funzione sotto esame.** Ne ho già buttati
   due miei per questo.
2. **Mai asserire su testo tradotto né su classi CSS.** Se lo stato esiste solo come colore,
   il prodotto non lo pubblica: si chiede l'attributo. È successo cinque volte, e una era
   anche una lacuna di accessibilità.
3. **Non inseguire i rami difensivi**, e dichiarare quali si lasciano scoperti.

E quella che vale più delle altre: **se salta fuori un difetto, fermarsi e riportarlo con la
prova**, scrivendo il test che fissa il comportamento *attuale*. In questa sessione ne sono
usciti diciannove per questa via — fra cui un `+-5%` che gli utenti avevano segnalato e un
confronto di stringhe che rendeva irraggiungibili otto traduzioni.

## Validazione finale

Al termine di tutte le corsie, in quest'ordine:

1. registrazione di tutti i file nuovi nel runner, in un passaggio solo;
2. `./dev.py test check-orphans` pulito;
3. `npx prettier --check` e `svelte-check --threshold error` a zero;
4. **`./dev.py test --fresh-run --coverage js --cov-clean-js --workers 8 all`** — la corsa
   completa che valida tutto insieme e dà i numeri confrontabili;
5. misura prima/dopo per file e per gruppo, più il messaggio di commit.

## Cosa non è in questo piano

- **I grafici** (`components/charts/`, `brokers/lots/*Chart`, `dashboard/*Chart`): esclusi
  dall'utente, e concordo — asserire su opzioni ECharts produce test che confermano
  l'implementazione invece del comportamento.
- **Il backend**: 92,4 % di linee, 82,7 % di rami; i BRIM sono al 74,7 % perché mancano casi
  reali, non test.
- **Nuove spec E2E**: le superfici toccate ne hanno già, e il rapporto costo/beneficio è
  peggiore di un component test.

## Numeri di partenza, per il confronto finale

| file | linee | rami |
|---|---|---|
| `settings/tabs/GlobalSettingsTab.svelte` | 61,6 % | 41,6 % |
| `settings/tabs/ProfileTab.svelte` | 55,6 % | 36,0 % |
| `settings/SchedulerLogModal.svelte` | 73,7 % | 52,1 % |
| `settings/tabs/AboutTab.svelte` | 82,6 % | 48,3 % |
| `settings/SchedulerConfigModal.svelte` | 80,0 % | 47,1 % |
| `settings/SettingsLayout.svelte` | 61,6 % | 27,7 % |
| `settings/tabs/PreferencesTab.svelte` | 37,6 % | 24,4 % |
| `settings/PasswordChangeModal.svelte` | 57,1 % | **5,3 %** |
| `brokers/BrokerSharingPanel.svelte` | 57,1 % | 29,7 % |
| `transactions/filterState.ts` | 78,2 % | 67,9 % |
| `stores/fxStoreRegistry.ts` | 66,0 % | 48,8 % |
| `transactions/resolveFormItems.ts` | 48,9 % | 41,1 % |
| `utils/files/imageCrop.ts` | 67,9 % | **20,0 %** |

**Globale frontend: linee 75,77 %, rami 57,49 %** (16 578 / 28 834).
