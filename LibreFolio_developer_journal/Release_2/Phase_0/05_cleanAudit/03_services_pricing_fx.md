# 03 — Pricing & FX

> `asset_source.py` (4 800), `fx.py` (1 643), price resolver
> Gravità massima: 🟡

---

## Sintesi

Nessun bug conclamato qui, ma è il sottosistema con la maggiore **concentrazione di
debito**: `asset_source.py` da solo pesa 4 800 righe — il file più grande del progetto —
e raccoglie il 9 % dei rilievi ruff e il **68 % dei candidati N+1** di tutto il backend.

Il codice mostra però consapevolezza architetturale: la pipeline a 3 fasi di
`bulk_refresh_prices` cita esplicitamente il pattern di `sync_pairs_bulk` come modello, e
la nota sui provider multi-base in `fx.py` elenca in anticipo i quattro punti da
rielaborare. Non è codice scritto alla cieca.

Il tema dominante è la **dimensione**: file troppo grandi, funzioni troppo lunghe, e
alcune loop che interrogano il DB una riga alla volta.

---

## Metriche

| | `asset_source.py` | `fx.py` |
|---|---:|---:|
| Righe | 4 800 | 1 643 |
| Rilievi ruff | 62 | 28 |
| Candidati N+1 | **26** | 3 |
| Funzioni sopra soglia | 8 | 5 |

### Funzioni più complesse

| Complessità | Funzione | File |
|---:|---|---|
| 59 | `bulk_refresh_prices` | `asset_source.py` |
| 54 | `sync_pairs_bulk` | `fx.py` |
| 46 | `get_prices_bulk` | `asset_source.py` |
| 30 | `ensure_rates_multi_source` | `fx.py` |
| 23 | `convert_bulk` | `fx.py` |

`asset_source.py` è anche il file con più rilievi ruff dell'intero backend (62), seguito
da `api/v1/assets.py` (29) e `fx.py` (28).

---

## Reperti

### 🟡 C1 — 26 candidati N+1 concentrati in `asset_source.py`

Il rilevatore ha individuato 38 punti in cui una query DB viene eseguita dentro un
ciclo; **26 sono in questo file**. Vanno verificati uno per uno — alcuni cicli iterano
su provider (N piccolo e limitato), altri su asset o transazioni (N illimitato).

I blocchi più densi:

| Loop da riga | Query nel corpo | Righe |
|---:|---:|---|
| 4034 | **7** | 4038, 4095, 4098, 4108, 4119, 4126, 4127 |
| 1354 | 3 | 1363, 1407, 1473 |
| 3635 | 3 | 3636, 3643, 3656 |
| 918 | 3 | 982, 1018, 1020 |

Il caso di riga 4034 è il più chiaro ed è un endpoint **bulk**:

```python
# bulk patch degli asset
for patch in patches:
    stmt = select(Asset).where(Asset.id == patch.asset_id)
    result = await session.execute(stmt)
    asset: Asset = result.scalar_one_or_none()
    ...
```

Sette query per elemento, moltiplicate per la dimensione del batch. Un batch da 50 asset
genera fino a 350 round-trip.

Rimedio standard: precaricare in una sola query con `WHERE id IN (...)`, costruire un
dizionario, e usarlo dentro il ciclo. Il resto della logica non cambia.

Da fare in ordine di N atteso: prima i loop su liste fornite dall'utente (i bulk), poi
quelli su collezioni interne.

---

### 🟡 C2 — `ensure_rates_multi_source`: impalcatura per il futuro, non codice morto

**Dove**: `backend/app/services/fx.py:399` (complessità 30)

Nessun chiamante in produzione; solo i test la usano. Ma **non va rimossa senza
discuterne**, e il motivo è scritto nel codice stesso:

```text
# ARCHITECTURAL NOTE: multi-base
# As of March 2026, ALL implemented providers have exactly 1 base currency.
# The pipeline (sync_pairs_bulk, ensure_rates_multi_source, frontend currency
# graph) implicitly assumes single-base per provider. When adding a multi-base
# provider (e.g., Open Exchange Rates, Fixer.io), the following must be reworked:
#   1. Pipeline Phase 1 grouping key: (provider, base_currency) instead of just provider
#   2. ensure_rates_multi_source(): explicit base_currency routing
#   ...
```

> **Tracciatura della logica**: la sincronizzazione FX in produzione passa da
> `sync_pairs_bulk` (`api/v1/fx.py:203`, `scheduler/jobs.py:143`). Ma
> `ensure_rates_multi_source` implementa il **routing esplicito per valuta base**, che
> `sync_pairs_bulk` non fa. La logica **non è riassorbita**: è il pezzo previsto per
> quando arriverà il primo provider multi-base.

Tre opzioni, in ordine di preferenza:

1. **Tenerla e documentarla** come punto di estensione — aggiungere un commento
   `# Intentionally unwired: see ARCHITECTURAL NOTE multi-base` così il prossimo audit
   non la ripesca.
2. Cablarla ora, se è già prevista l'aggiunta di un provider multi-base.
3. Rimuoverla, accettando di riscriverla da zero al momento del bisogno.

L'opzione 1 costa una riga di commento ed evita di perdere 30 punti di logica già
scritta e testata.

---

### 🟡 C3 — `AssetMetadataService` usata solo dai test

**Dove**: `backend/app/services/asset_source.py:4230`

Classe statica con tre metodi, tutti privi di chiamanti in produzione:

| Metodo | Riga | Scopo |
|---|---:|---|
| `compute_metadata_diff` | 4237 | diff campo per campo fra vecchia e nuova metadata, per audit/visualizzazione |
| `apply_partial_update` | 4283 | applica un aggiornamento parziale |
| `merge_provider_metadata` | 4336 | fonde la metadata proveniente dal provider |

> **Tracciatura**: il percorso di produzione (`api/v1/assets.py`, righe 851-852) legge e
> scrive `asset.classification_params` **direttamente**, senza passare da questi
> helper. La logica di *diff* per audit non esiste altrove: se un utente modifica la
> classificazione di un asset, non viene tracciato cosa è cambiato.

Non è riassorbita. Le opzioni:

- **Cablare** `compute_metadata_diff` nel percorso di aggiornamento, ottenendo il
  tracciamento delle modifiche che il docstring promette ("for audit/display purposes");
- **Rimuovere** la classe e i suoi test, accettando che la metadata si aggiorni senza
  storico.

Va deciso con chi conosce il requisito. Il tipo di ritorno
(`list[FAMetadataChangeDetail]`) suggerisce che era destinata a comparire nell'interfaccia.

---

### 🟢 C4 — `get_asset_provider` usata solo dai test

**Dove**: `backend/app/services/asset_source.py:1295`

```python
@staticmethod
async def get_asset_provider(asset_id: int, session: AsyncSession) -> Optional[AssetProviderAssignment]:
    """Fetch provider assignment for asset."""
```

> **Tracciatura**: il recupero dell'assegnazione provider in produzione avviene inline
> nei metodi che ne hanno bisogno. La logica è **duplicata**, non persa.

Delle due l'una: o i chiamanti inline usano questo helper (riducendo duplicazione), o
l'helper va rimosso. La prima è preferibile — è già testato.

---

### 🟢 C5 — Complessità di `bulk_refresh_prices` (59) e `get_prices_bulk` (46)

Entrambe sono pipeline multifase legittime — il docstring di `bulk_refresh_prices` a
riga 2609 dichiara *"Uses a 3-phase pipeline (pattern from FX `sync_pairs_bulk`)"*, il
che è un buon segno: c'è un modello condiviso.

Il problema è che le fasi sono **inline** invece che estratte. Una funzione che dichiara
di avere 3 fasi dovrebbe avere 3 metodi privati. L'estrazione è meccanica, non cambia il
comportamento, e riporta ciascun pezzo sotto la soglia.

Non urgente, ma è il candidato più semplice fra i refactoring di complessità: la
struttura a fasi è già definita, va solo resa esplicita.

---

### 🟢 C6 — 4 `try/except/pass` silenziosi

`asset_source.py:2697`, `asset_source.py:3076`, più `yahoo_finance.py:357` e `:630`
(vedi report [04](04_providers.md)).

Un `except: pass` in un provider di prezzi nasconde i fallimenti di rete e di parsing.
Il sistema continua a funzionare, ma nessuno sa perché un prezzo non è stato aggiornato.
Minimo indispensabile: un `logger.debug` con la ragione.

---

## Interventi raccomandati

| Priorità | Intervento | Costo | Rischio |
|---|---|---|---|
| 1 | Eliminare l'N+1 nel bulk patch (`asset_source.py:4034`, 7 query per elemento) | basso | basso |
| 2 | Verificare e correggere gli altri 25 candidati N+1, in ordine di N atteso | medio | basso |
| 3 | Decidere su `AssetMetadataService`: cablare il diff o rimuovere | basso | — |
| 4 | Documentare `ensure_rates_multi_source` come punto di estensione intenzionale | nullo | nullo |
| 5 | Far usare `get_asset_provider` ai chiamanti inline | basso | basso |
| 6 | Estrarre le 3 fasi di `bulk_refresh_prices` in metodi privati | medio | basso |
| 7 | Aggiungere log ai `try/except/pass` | basso | nullo |

L'intervento 1 è quello con il miglior rapporto valore/costo dell'intero audit: poche
righe, effetto misurabile sulla latenza degli endpoint bulk.

**Nota sulla dimensione**: `asset_source.py` a 4 800 righe è oltre ogni soglia
ragionevole. Una scissione (gestione provider / recupero prezzi / metadata / bulk
operations) renderebbe il file navigabile, ma è un intervento invasivo da pianificare a
parte, non da infilare in un ciclo di pulizia.
