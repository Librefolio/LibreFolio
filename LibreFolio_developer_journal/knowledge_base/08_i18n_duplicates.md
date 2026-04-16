# i18n Duplicate Management

> **Scopo**: documentare la strategia di de-duplicazione chiavi i18n e tracciare
> i gruppi duplicati che accettiamo come intenzionali.

---

## 🎯 Principio

Consolidare sotto `common.*` solo quando **significato, contesto E valore coincidono
in tutte e 4 le lingue**. Se il valore è uguale ma il significato è diverso, le chiavi
restano separate.

---

## 📊 Stato Attuale (Aprile 2026)

| Metrica | Valore |
|---------|--------|
| Chiavi totali | 825 |
| Unused | 0 |
| Gruppi duplicati totali | 42 |
| Gruppi consolidati | 18 (eliminati dal cleanup) |
| Gruppi accettati | ~30 (documentati sotto) |

Piano di consolidamento: [`plan-phase06Step6-i18n-dedup.prompt.md`](../RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step6/plan-phase06Step6-i18n-dedup.prompt.md)

---

## ✅ Duplicati Accettati — Significato Diverso

Queste coppie hanno **valore uguale** (case-insensitive) in una o più lingue, ma
significato o contesto diverso. **Non** devono essere consolidate.

### Semantica diversa

| Chiave A | Chiave B | Valore EN | Perché separate |
|----------|----------|-----------|-----------------|
| `common.close` | `dataEditor.col.close` | "Close" | **Bottone** (Chiudi) vs **prezzo OHLC** (Chiusura). In IT/FR/ES le traduzioni divergono: "Chiudi" vs "Chiusura", "Fermer" vs "Clôture", "Cerrar" vs "Cierre". |
| `common.reset` | `common.undo` | — | EN diverso ("Reset to Default" vs "Undo"), stessa traduzione IT "Ripristina". Significato opposto: reset = valori iniziali, undo = annulla ultima azione. |
| `common.retry` | `error.tryAgain` | "Retry" / "Try Again" | Contesto diverso: `retry` per operazioni idempotenti, `tryAgain` per errori generici. IT/FR convergono, EN/ES divergono. |
| `chartSettings.discardTitle` | `common.discardChanges` | "Discard changes?" | Formulazione diversa in IT ("Scartare le modifiche?" vs "Annullare le Modifiche?") e FR ("Rejeter" vs "Annuler"). Il chart settings usa un tono più informale. |
| `assets.confirm.confirmChange` | `assets.confirm.identifierChanged` | "Confirm Change" / "Confirm Asset Change" | EN diverso. Il primo è generico, il secondo specifico per cambio identificatore asset. ES ha "Confirmar Cambio" vs "Confirmar Cambio de Activo". |
| `assets.modal.saveChanges` | `common.save` | "Save Changes" / "Save" | "Salva Modifiche" vs "Salva". Il modale usa la versione esplicita per chiarire che ci sono modifiche pendenti. |
| `assetDetail.syncPrices` | `assets.sync.modalTitle` | "Sync Prices" / "Sync Asset Prices" | EN diverso. Il primo è il bottone nella detail page, il secondo è il titolo del modal di sync bulk. |

### Dynamic prefix / Singolare-Plurale

| Chiave A | Chiave B | Perché separate |
|----------|----------|-----------------|
| `assets.types.OTHER` | `common.other` | `assets.types` è un **dynamic prefix** (`$t(\`assets.types.${var}\`)`). Tutte le chiavi sotto quel prefisso devono restare per il lookup dinamico. |
| `uploads.file` | `uploads.files` / `uploads.title` | Singolare ("file"), plurale ("files"), titolo pagina ("Files"). Servono tutte e tre. |
| `brokers.title` | `uploads.broker` | Titolo pagina "Brokers" vs label campo "Broker" nel form upload. |
| `brokers.sharing.editors` | `brokers.sharing.roleEditorShort` | Plurale "Editors" vs singolare "Editor" — usati in contesti diversi (lista utenti vs badge ruolo). |

### Contesto UI diverso

| Chiave A | Chiave B | Perché separate |
|----------|----------|-----------------|
| `assets.sync.assetsCount` / `assets.title` / `dashboard.assetCount` | — | Count label nella sync / titolo pagina / statistica dashboard. 3 contesti diversi, potrebbero divergere (es. "2 assets synced" vs "Assets" vs "Assets: 42"). |
| `assets.type` | `common.type` | `assets.type` è usato come label specifico nel contesto asset. Potrebbe servire una formulazione diversa (es. "Asset Type" vs "Type"). |
| `assets.schedule.currency` / `settings.categoryCurrency` | `common.currency` | ES diverge: "Moneda" (schedule/settings) vs "Divisa" (common). Contesti: interessi schedulati, categoria settings, header generico. |
| `assets.schedule.period` | `chartSettings.params.period` | "Period" in contesti diversi: periodi interessi vs periodo chart signals. Potrebbero servire label diversi in futuro. |
| `assets.provider.selectProvider` | `assets.table.provider` | Label dropdown "Provider" vs column header "Provider". Il primo potrebbe diventare "Select Provider". |
| `assets.search.providers` | `fx.providers` | Label nel contesto search assets vs label nella sezione FX. |
| `nav.settings` | `sharedResource.settings` | ES diverge: "Configuración" (nav) vs "Ajustes" (shared resource). Contesti UI diversi. |
| `settings.resetAllToDefault` / `uploads.resetAll` | `common.resetAll` | EN diverso: "Reset All" vs "Reset All to Defaults". Tre contesti diversi. |
| `fileStatus.uploaded` | `uploads.uploadDate` | Status ("Uploaded" = stato file) vs data ("Uploaded" = data di upload). FR diverge: "Téléchargé" vs "Téléversé". |
| `chartSettings.discard` | `common.discard` | FR diverso: "Rejeter" (chart) vs "Abandonner" (common). Contesti diversi. |
| `dataEditor.clearSelection` | `table.clearSelection` | IT diverso: "Deseleziona" vs "Deseleziona tutto". |

### Abbreviazioni Signal (intenzionali)

| Nome | Abbreviazione | Perché separate |
|------|---------------|-----------------|
| `chartSettings.signals.ema` | `chartSettings.signals.emaAbbr` | Entrambi "EMA" oggi, ma il nome potrebbe diventare "Exponential Moving Average" mentre l'abbreviazione resta "EMA". Pattern coerente per tutti i segnali. |
| `chartSettings.signals.macd` | `chartSettings.signals.macdAbbr` | Idem — "MACD" / "MACD". |
| `chartSettings.signals.rsi` | `chartSettings.signals.rsiAbbr` | Idem — "RSI" / "RSI". |
| `chartSettings.signals.fxPair` | `chartSettings.signals.fxPairAbbr` | "FX Pair" vs "FX" — già diversi in EN. IT converge a "Coppia FX" per entrambi. |

### Unità Settings (dynamic prefix)

| Gruppo | Perché separato |
|--------|-----------------|
| `settings.globalSettingUnits.price_sync_interval_hours` / `settings.globalSettingUnits.session_ttl_hours` | Sotto dynamic prefix `settings.globalSettingUnits`. Entrambi "hours" ma per settings diversi. Il lookup è dinamico `$t(\`settings.globalSettingUnits.${key}\`)`. |

---

## 🔧 Comandi Utili

```bash
# Audit completo con duplicati
./dev.py i18n audit --duplicates

# Report in formato markdown
./dev.py i18n audit --duplicates --format md -o audit_duplicate.md

# Cercare un valore specifico
./dev.py i18n search "Close" --values

# Albero per namespace
./dev.py i18n tree common --counts
```

---

## ⚠️ Regole per Nuove Chiavi

1. **Prima di creare una chiave**, cercare se esiste già sotto `common.*`
2. Se il valore è generico (Cancel, Save, Delete, etc.), usare `common.*`
3. Se il valore è specifico di un feature, usare il namespace della feature
4. **Mai** creare una chiave con lo stesso valore di un `common.*` esistente, a meno
   che il significato sia genuinamente diverso (documentare qui sopra il motivo)

