# 🇮🇹 Borsa Italiana

**Borsa Italiana** è la borsa valori italiana, gestita da Euronext. LibreFolio include un **provider di dati asset** dedicato che recupera prezzi, serie storiche e metadati degli strumenti direttamente dal sito web di Borsa Italiana.

---

## 🔍 Cosa Fornisce

| Dati | Descrizione |
|------|-------------|
| **Prezzo corrente** | Ultimo prezzo ufficiale di mercato per strumenti quotati; NAV dei fondi solo se datato oggi |
| **Prezzi storici** | OHLCV giornaliero per strumenti quotati; un punto NAV alla data reale del NAV per i fondi |
| **Metadati dello strumento** | ISIN, segmento di mercato, valuta e identificatori alternativi quando disponibili |

Gli asset negoziati su Borsa Italiana includono azioni italiane (segmento MTA/MIL), ETF (ETFplus), obbligazioni (MOT) e fondi comuni/SICAV.

---

## ⚙️ Configurazione

Non è richiesta alcuna chiave API o registrazione: il provider effettua lo scraping dei dati pubblici dal sito web di Borsa Italiana. La configurazione è disponibile per singolo asset nel pannello **Provider Config** nella pagina di dettaglio dell'asset.

1. Naviga verso l'asset che desideri monitorare.
2. Apri il pannello **⚙️ Provider Config**.
3. Seleziona **Borsa Italiana** dall'elenco dei provider.
4. Inserisci l'**ISIN** per gli strumenti quotati. Per i fondi, usa la Ricerca Intelligente per acquisire automaticamente il codice interno Borsa.
5. Salva — LibreFolio recupererà la prima serie storica al prossimo sync.

!!! tip "Trovare l'ISIN"

    Puoi cercare l'ISIN su [borsaitaliana.it](https://www.borsaitaliana.it) cercando il nome dello strumento. L'ISIN è indicato in ogni pagina di dettaglio dello strumento.

!!! tip "La Ricerca Intelligente può usare i link di Borsa"

    Se la ricerca normale non trova un fondo, incolla o cerca con l'URL della pagina del fondo/dettaglio di Borsa Italiana. La ricerca intelligente di LibreFolio può risolvere le pagine Borsa supportate, collegare i `provider_params` corretti e rendere il fondo quotabile tramite il suo codice interno.

---

## 🔄 Sincronizzazione

Il provider Borsa Italiana partecipa al ciclo standard di **asset sync**. Avvialo manualmente dalla pagina di dettaglio dell'asset con il pulsante **🔄 Sync**, oppure lascia che il job di background pianificato venga eseguito durante la notte.

!!! note "Rate limiting"

    Il provider applica un throttling automatico per evitare di essere bloccato da Borsa Italiana. Se possiedi molti asset di questo exchange, il sync completo potrebbe richiedere alcuni minuti.

!!! note "Fondi comuni (NAV)"

    I fondi comuni e le SICAV sono valorizzati tramite il loro **NAV** giornaliero, pubblicato una volta al giorno con un ritardo. LibreFolio identifica ogni fondo tramite il suo codice fondo di Borsa, non per ISIN. Lo storico prezzi mostra un punto NAV alla sua data reale e il valore corrente viene aggiornato solo quando il NAV pubblicato è datato oggi (altrimenti viene usato l'ultimo prezzo di acquisto come stima).

!!! note "Identificatori alternativi"

    Alcuni identificatori importati o scoperti dal provider vengono salvati come elenco modificabile di identificatori alternativi. Per i fondi di Borsa Italiana, questo elenco può includere il codice interno del fondo mentre l'ISIN reale rimane l'identificatore principale quando disponibile.

---

## 🔗 Documentazione per Sviluppatori

Per i dettagli di implementazione (formato delle richieste, strategia di parsing HTML, mappatura dei campi), consulta:

→ [Manuale per sviluppatori — Provider Borsa Italiana](../../../developer/backend/assets/provider_borsa_italiana.md)

---

## 🔗 Correlati

- 📋 **[Panoramica Asset](../index.md)** — Gestisci la tua libreria di asset
- 🏦 **[Provider di Asset](./index.md)** — Altre fonti di dati
- 📡 **[justETF](./justetf.md)** — Fonte alternativa per i dati sugli ETF
