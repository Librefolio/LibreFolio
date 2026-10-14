# Feedback dell'utente C — mappatura sul repository

> **Fonte**: la chat su Telegram fra il developer e l'utente C (04–08/09/2026) e i due riepiloghi di Gemini, letti
> per intero. **Verifica** in sola lettura il 14/10/2026: `dev_release2` a `f21b41f7c`, con lo stesso codice di
> `v1.2.0` (`cf00fac7d`: dopo il tag cambia solo `BACKLOG_POST_1.2.md`); `v1.1.0` è `837a8f2c7` (07/09).
>
> **Abbreviazioni**: «r. N» è la riga della fonte, numerata come `grep -n`. «CL 1.1.0 r. N» e «CL 1.2.0 r. N» sono righe
> di `CHANGELOG.md`. «07:N» è la riga N di
> `LibreFolio_developer_journal/Release_2/Phase_0/09_feedbackJobs/07_feedback_import_critici.md`, dove stanno i
> difetti E1–E9 nati da questa chat. «TODO_FUTURI» è `TODO_FUTURI.md` alla radice.

## 1. Sintesi

**34 voci**, dopo aver unito i doppioni. In fondo alla tabella ci sono anche 3 domande di chiarimento, non contate.

| Stato | Voci | Quali |
| --- | --- | --- |
| FATTO in 1.1.0 | 6 | 1, 2, 16; e 7, 12, 34, che c'erano già prima della chat |
| FATTO in 1.2.0 | 10 | 8, 17, 19, 22, 23, 24, 25, 26, 27, 28 (la 8 e la 17 non sono citate nel CHANGELOG) |
| PARZIALE | 2 | 3, 11 |
| IN BACKLOG | 7 | 6, 15, 18, 21, 29, 30, 33 |
| MANCANTE | 5 | 4, 5, 14, 31, 32 |
| NON PIÙ VALIDO | 4 | 9, 10, 13, 20 |

**Le voci sfuggite sono 6**: le 5 MANCANTI e la parte nell'app della voce 11. Stavano nella chat o nei riepiloghi di
Gemini, ma non nel prompt finale (r. 1977–2048), che ha fissato solo i 4 difetti, i 2 ritocchi e i 3 temi sulle valute.

## 2. La tabella

| n | Voce | Stato | Prova | Riga della fonte |
| --- | --- | --- | --- | --- |
| 1 | Un titolo di Stato USA quotato su EuroTLX: la ricerca lo trovava su Borsa Italiana, ma poi mancavano prezzo e storico; funzionava solo scrivendo a mano il mercato (MIC). Neanche Yahoo Finance dava quei dati. | FATTO in 1.1.0 | CL 1.1.0 r. 453; commit `4eea87544`, `2110c7382`, `029b8a5e8`, antenati di `v1.1.0`; oggi `borsa_italiana/plugin.py:400,445` (`mic`). L'utente lo conferma su 1.1.0 il 07/09 (r. 1008–1012). Yahoo: limite della fonte (r. 91). | 51–81, 147, 527–583; Gemini 971 |
| 2 | Borsa Italiana non compilava la distribuzione geografica di quel titolo. | FATTO in 1.1.0 | CL 1.1.0 r. 454: per i titoli di Stato, il paese dell'emittente diventa la distribuzione geografica. In `v1.1.0`, `backend/app/services/asset_source_providers/borsa_italiana.py:203` («united states of america» → USA) e `:1035-1040`. | 63–69 |
| 3 | Poter collegare la propria fonte di dati, anche a pagamento, con un plugin. | PARZIALE | Fatto: la guida e la skill per scrivere un plugin di prezzi (`mkdocs_src/docs/developer/architecture/patterns/asset_plugin_guide.md`, già in `v1.1.0`); in 1.2.0 ogni plugin è una cartella e si può montare con un volume Docker (`registry_pattern.md:132-134`). Manca, ma è tracciato: dove inserire la chiave d'accesso (TODO_FUTURI r. 1924, «⚙️ Impostazioni per plugin», r. 1929) e le traduzioni dei plugin montati (`BACKLOG_POST_1.2.md:1673`, U-B1). | 107–111; developer 153 |
| 4 | Un provider di prezzi che usi le API di Interactive Brokers, con prezzo corrente e storico («un quarto provider»). | MANCANTE | Nessuna voce in TODO_FUTURI, `BACKLOG_POST_1.2.md`, `09_feedbackJobs/` e backlog 38. È tracciato solo il prerequisito delle chiavi (TODO_FUTURI r. 1929). | 141, 873–897; developer 431; Gemini 995 |
| 5 | I dati delle obbligazioni: rendimento a scadenza (YTM) e duration. | MANCANTE | Nessuna voce. Lo YTM c'è solo nella teoria (`mkdocs_src/docs/financial-theory/instruments/asset-types/bonds.en.md:34`). | 903–909; developer 941; Gemini 995 |
| 6 | OpenFIGI come fonte dei dati descrittivi degli asset. | IN BACKLOG | TODO_FUTURI r. 8, «🔌 Arricchimento asset da fonti esterne — ESMA FIRDS, OpenFIGI, JustETF (F16)». Il suggerimento è precedente alla chat (r. 129). | 123–135 |
| 7 | Altri identificativi oltre all'ISIN, per esempio il ticker. | FATTO in 1.1.0 (c'era già) | Un asset ha già più identificativi; in 1.1.0 la lista «altri identificativi» si accumula fra gli import (CL 1.1.0 r. 401). Nel CSV generico la colonna `asset` accetta ticker, ISIN o nome (`mkdocs_src/docs/user/transactions/import/generic-csv.en.md:61`, uguale in `v1.1.0`). | 257–263; developer 275–287 |
| 8 | Settori per le obbligazioni: «Corporate» e «Governativo». | FATTO in 1.2.0 | `backend/app/utils/asset/sector.py:32-33` (in `v1.1.0` `sector_fin_utils.py` non li ha); `frontend/src/lib/i18n/base/it.json:300-301`, «Obbligazioni societarie» e «Titoli di Stato»; Borsa Italiana li assegna da sola (`borsa_italiana/plugin.py:228-239`). Commit `e50d66408` (10/09), voce A1 ✅ in `09_feedbackJobs/03_asset_dati_classificazione.md:77`. **Non è citato nel CHANGELOG 1.2.0.** | 293, 589; developer 311, 691; Gemini 977 |
| 9 | Settori personalizzati, scritti liberamente dall'utente. | NON PIÙ VALIDO | Scelta del developer: la lista resta fissa, così plugin diversi danno gli stessi nomi; si allarga su richiesta (r. 689–695). | 293, 589 |
| 10 | Lo storico dei prezzi dei bond di Borsa Italiana sembrava corto (5–6 giorni). | NON PIÙ VALIDO | Era l'anteprima di «Testa configurazione», che legge solo gli ultimi 7 giorni (`backend/app/services/asset_sources/provider_management.py:379`). Quando si crea l'asset si scarica tutto lo storico: `AssetModal.svelte:1456-1462` chiede `start: 'resume'`, che senza prezzi diventa `min` (`asset_sources/refresh.py:159-161`). | 301–305, 589, 1016, 1068–1078; developer 1166–1174; Gemini 987 |
| 11 | Dire nell'app che «Testa configurazione» mostra solo una prova, non tutto lo storico. | PARZIALE | Fatto: la guida 1.2.0 dice che il test legge «a few days of History» (`mkdocs_src/docs/user/assets/create-edit.en.md:67`, commit `eee56b42a`). Manca: nell'app il risultato mostra solo «N punti — date» (`ProviderAssignmentSection.svelte:372`), senza nota. Non tracciato: voce proposta al §5. | 1068–1078; Gemini 1911 |
| 12 | Caricare lo storico dei prezzi da un file CSV, anche settimanale. | FATTO in 1.1.0 (c'era già) | L'import CSV dell'editor dati di asset e FX c'era già (`importCsv` è in `v1.0.1`); il developer lo mostra il 06/09 (r. 445–467). | 305, 417, 439, 589 |
| 13 | Import dello storico in JSON. | NON PIÙ VALIDO | L'utente stesso: «il JSON penso sia un extra inutile adesso». | 305; developer 457; 473 |
| 14 | Un pacchetto di dati di qualità in abbonamento, anche come forma di monetizzazione. | MANCANTE | Nessuna voce: «monetizz», «abbonamento» e «pacchetto dati» non compaiono nei backlog. | 381, 407–417; developer 423 |
| 15 | justETF mostra lo stesso fondo più volte, una per valuta: filtrare per valuta e lingua preferite. | IN BACKLOG | TODO_FUTURI r. 1924, «⚙️ Impostazioni per plugin», primo esempio a r. 1937 (filtro per paese e valuta predefiniti, tutto solo se non trova niente). Il 👑 che segna la valuta del fondo non è spiegato nell'app (`justetf/plugin.py:464-470`). | 613, 771, 805; developer 749–757, 785; Gemini 981 |
| 16 | Le distribuzioni di settore e di paese di un ETF da justETF fallivano del tutto. | FATTO in 1.1.0 | Libreria justETF aggiornata in `Pipfile.lock` (ref `af6aa25` → `f24a5c4`) nel commit `029b8a5e8` (05/09), antenato di `v1.1.0`. L'utente, il 07/09 su 1.1.0: «Funziona tutto bene» (r. 1012). Certezza media: vedi §6. | 627–629; developer 861; Gemini 985 |
| 17 | Look-through dettagliato: caricare la propria composizione dei fondi, aggiornata ogni trimestre. | FATTO in 1.2.0 | Import CSV delle distribuzioni: `frontend/src/lib/components/ui/input/DistributionEditor.svelte:460` e `assets/DistributionDataImportModal.svelte` (assente in `v1.1.0`); guida `mkdocs_src/docs/user/assets/create-edit.en.md:173`. Commit `e50d66408` e `cc57b6a38`, voce A2 ✅ in `09_feedbackJobs/03:78`. Una sola composizione per asset, senza storico (scelta del developer, r. 317). **Non è citato nel CHANGELOG 1.2.0.** | 629, 879; developer 915; Gemini 991 |
| 18 | Qualche distribuzione geografica manca alla fonte: prenderla da un'altra fonte. | IN BACKLOG (voce generica) | TODO_FUTURI r. 1353 (extraetf.com, anche con la distribuzione per valuta) e r. 8 (F16). Nel frattempo c'è l'import CSV della voce 17. | 1012; developer 853; 867 |
| 19 | Spiegare cosa sono la «Valuta» dell'asset e la «Currency» del provider. | FATTO in 1.2.0 | Suggerimento accanto alla valuta: `AssetModal.svelte:1887`, testo `frontend/src/lib/i18n/assets/it.json:213`, «Valuta in cui vengono salvati i prezzi dell'asset.» CL 1.2.0 r. 285, commit `ef722b552`. In più gli ETF ed ETC di Borsa Italiana prendono la valuta di quotazione, non quella del fondo (CL 1.2.0 r. 156). Resta: la «Currency» di justETF è spiegata solo in inglese (backlog 38, O-9, `38_postReleaseBacklog/README.md:117`). | 619–621, 833, 1120–1160, 1412, 1442; developer 819; Gemini 979, 1915 |
| 20 | Aggiungere lo yen (JPY) alla lista delle valute. | NON PIÙ VALIDO | La lista è quella di justETF: EUR, USD, CHF, GBP (`justetf/plugin.py:215`). Il bisogno vero è la voce 21, come precisa il developer (r. 1949). | 1114, 1208; Gemini 1905 |
| 21 | La valuta d'origine di ogni titolo e un grafico dell'esposizione per valuta («un must have»). | IN BACKLOG | TODO_FUTURI r. 1317, F-MC-3 (sezione «💱 Settlement multicurrency ed esposizione», r. 1265); collegata la r. 1353. Oggi la Dashboard divide solo per tipo, settore e paese (`AllocationPanel.svelte:152-160`). | 1252–1306, 1404; developer 1272–1276; Gemini 1907, 2043 |
| 22 | Transazioni in una valuta diversa da quella del titolo, per esempio un fondo in dollari comprato in euro: i conti devono tornare. | FATTO in 1.2.0 | CL 1.2.0 r. 188 (#32: un asset in dollari comprato in euro aveva costo d'acquisto zero), r. 296 (ogni acquisto al cambio del suo giorno), r. 189 (un cambio mancante è segnalato, mai uno zero). | 1336–1338, 1370, 1386, 1424, 1474 |
| 23 | L'import del CSV generico non riconosceva gli asset dal codice ISIN. | FATTO in 1.2.0 (con riserva) | CL 1.2.0 r. 115 (asset e suggerimenti aggiornati insieme, anche per gli asset creati dopo l'analisi) e r. 285 (nota «Asset da creare a mano», `frontend/src/lib/i18n/importWizard/it.json:318-320`). Commit `ef722b552` (`utils/transactions/importMerge.ts`, E2E `tx-import-matching.spec.ts`); E4 a 07:25. Riserva: vedi §6. | 595, 735–739, 1020–1024, 1486; Gemini 973, 1897, 2011 |
| 24 | Le distribuzioni sparivano riaprendo «Ispeziona/modifica» nel wizard di import, anche quelle inserite a mano. | FATTO in 1.2.0 | CL 1.2.0 r. 112; `frontend/src/lib/components/assets/assetEditData.ts:10` (assente in `v1.1.0`), usato da `ImportWizardModal.svelte:2947`; commit `ef722b552`; E2 a 07:23. La causa: salvando dal wizard le distribuzioni venivano cancellate (07, §4). | 1090–1102, 1132–1136; Gemini 1893, 1933 |
| 25 | Dopo aver cambiato la valuta, «Ispeziona/modifica» sembrava bloccata e «Salva modifiche» non faceva nulla. | FATTO in 1.2.0 | CL 1.2.0 r. 113. La conferma del cambio di valuta restava sotto il wizard; ora `zIndex={zIndex + 20}` (`AssetModal.svelte:2480`, assente in `v1.1.0`). Commit `ef722b552`; E1 a 07:22. | 1108, 1132, 1482; Gemini 1891, 1931 |
| 26 | «Applica» restava grigio inserendo a mano un cambio valuta nel wizard. | FATTO in 1.2.0 | CL 1.2.0 r. 114; `TransactionFormModal.svelte:733` (`effectiveDualTo`, da `ef722b552`); E3 a 07:24. In più: i suggerimenti 💡 di unione funzionano anche a 0 giorni (CL 1.2.0 r. 145), e unire due righe in un cambio valuta non sbaglia più il segno (r. 143). | 1547–1551; developer 1645, 1855; Gemini 1895, 1937 |
| 27 | Un solo CSV con le transazioni di più broker crea problemi: va detto chiaramente. | FATTO in 1.2.0 | Avviso «One file per broker» in `mkdocs_src/docs/developer/backend/brim/generic_csv.md:5-7` e in `mkdocs_src/docs/user/transactions/import/generic-csv.it.md:22`; devWiki `LibreFolio_devWiki/wiki/decisions/brim-broker-scoped.md:75-91`; CL 1.2.0 r. 274; commit `ef722b552`; E6 a 07:30. | 1569, 1593; developer 1663, 1961; Gemini 2025–2028 |
| 28 | Il broker creato dal pannello della transazione «non compariva»: il nome era già usato, ma l'errore non diceva come uscirne. | FATTO in 1.2.0 | `frontend/src/lib/i18n/brokers/it.json:294`, «Per risolvere rinomina il broker esistente o cambia il nome di quello che stai provando ad aggiungere»; `backend/app/services/broker_service.py:62` (assente in `v1.1.0`); `BrokerModal.svelte:84`, usato anche dal modulo della transazione. CL 1.2.0 r. 152 e r. 216; E5 a 07:29. L'errore resta nel riquadro in alto (`BrokerModal.svelte:254`), non sotto il campo. | 1575–1587; developer 1669–1679, 1953; Gemini 1913, 2020 |
| 29 | Acquisti in un'altra valuta bloccati dal controllo della liquidità, quando il broker cambia «al volo» senza una riga di cambio nel file. | IN BACKLOG | TODO_FUTURI r. 1272, F-MC-1. Collegato, in 1.2.0: un saldo negativo evidenzia tutte le righe che lo causano (CL 1.2.0 r. 119, E7). | 1521, 1597–1631, 1749–1771; Gemini 1901, 2033 |
| 30 | Proporre in automatico i cambi valuta mancanti al tasso BCE, accettando un piccolo scarto. | IN BACKLOG | TODO_FUTURI r. 1295, F-MC-2: facoltativo, con anteprima da confermare. | 1607, 1763, 1817–1825; developer 1831; Gemini 1903, 2039 |
| 31 | Le due date («Da» e «A») del cambio valuta non si capiscono. | MANCANTE | Il modulo mostra due date senza spiegazione (`TransactionFormModal.svelte:1645` e `:1693`); la guida dice solo «Each side has its own date» (`mkdocs_src/docs/user/transactions/form.en.md:63`). Nessuna voce. | 1867–1875; developer 1885 |
| 32 | Provare i plugin d'importazione di Interactive Brokers e di Fineco su report veri. | MANCANTE | Sono ancora Beta (`mkdocs_src/docs/user/transactions/import/ibkr.en.md:3-5`, `fineco.en.md:3-5`); nessuna voce di collaudo. | 1799; developer 919, 1837; Gemini 993 |
| 33 | Recuperare la password dall'app, via email, senza terminale. | IN BACKLOG | TODO_FUTURI r. 56, «📧 Server email — verifica account, inviti, recupero password». In 1.2.0 il reset da terminale funziona di nuovo: in 1.1.0 i comandi dentro il container si fermavano (CL 1.2.0 r. 260–261). | 791–793; developer 825; Gemini 997 |
| 34 | Non perdere asset e transazioni con gli aggiornamenti, e poter fare il backup. | FATTO in 1.1.0 (c'era già) | Il database si aggiorna da solo (r. 399); guida al backup in `mkdocs_src/docs/user/installation.en.md:212` (in `v1.1.0` r. 201) e `mkdocs_src/docs/admin/filesystem.en.md:95`. In 1.2.0, prima di convertire il database si fa una copia di sicurezza (CL 1.2.0 r. 281). | 387, 487, 1026, 1486 |

**Domande di chiarimento, non contate:**

| Domanda | Risposta | Riga della fonte |
| --- | --- | --- |
| Le obbligazioni gestiscono il valore nominale? | Sì, c'era già: il campo «Unità per singolo prezzo» e il suggerimento «100» per i bond (`frontend/src/lib/i18n/assets/it.json:205-207`). | 27; developer 33–35 |
| Le distribuzioni si possono cambiare dopo la creazione? | Sì, dalla modifica dell'asset. | 295; developer 313 |
| I dati restano solo sul computer dell'utente? | Sì: nessun collegamento a un server esterno. | 577; developer 675 |

## 3. Le voci per il messaggio all'utente

**(a) Le tue idee fatte nella 1.2.0**

1. Fra i settori ci sono ora «Obbligazioni societarie» e «Titoli di Stato», e Borsa Italiana li assegna da sola ai bond.
2. Puoi importare da un file CSV la composizione di un fondo per settore e per paese: così usi i tuoi dati di
   look-through.
3. Le distribuzioni non spariscono più quando riapri un asset con «Ispeziona/modifica» durante l'import, e salvare non
   le cancella più.
4. Cambiare la valuta di un asset durante l'import non blocca più la finestra: la richiesta di conferma ora si vede.
5. Il cambio valuta inserito a mano si salva: «Applica» non resta più grigio.
6. L'import riconosce meglio gli asset dal codice ISIN, anche quelli che crei durante l'import; ti dice quali vanno
   creati a mano, e dagli import successivi li riconosce da solo.
7. Se crei un broker con un nome già usato, il messaggio ti dice come risolvere: rinomina quello che c'è o scegli un
   altro nome.
8. La guida del CSV generico dice chiaramente di usare un file per broker; valute diverse nello stesso file vanno bene.
9. Accanto alla «Valuta» di un asset c'è una spiegazione: è la valuta in cui vengono salvati i suoi prezzi.
10. Un titolo quotato in una valuta e comprato in un'altra, per esempio in dollari e pagato in euro, ora ha il costo
    d'acquisto giusto: ogni acquisto è convertito al cambio del suo giorno.

**(b) Le tue idee fatte già nella 1.1.0**

1. Il titolo di Stato USA quotato su EuroTLX funziona: la ricerca imposta da sola il mercato, e arrivano prezzo e
   storico.
2. Per i titoli di Stato, la distribuzione geografica è il paese dell'emittente.
3. Le distribuzioni di settore e di paese degli ETF da justETF vengono di nuovo scaricate.

C'erano già prima della chat:

4. Un asset può avere più codici (ISIN, ticker e altri), e nel CSV generico la colonna «asset» accetta anche il ticker.
5. Lo storico dei prezzi si importa da un file CSV, anche con dati settimanali.
6. Gli aggiornamenti non cancellano i dati: il database si aggiorna da solo, e la guida spiega come fare il backup.

**Tre avvisi utili da aggiungere al messaggio**

- Con la 1.1.0, salvare un asset da «Ispeziona/modifica» durante l'import poteva cancellarne settori e paesi: conviene
  ricontrollare gli asset modificati così.
- Vale la pena rifare l'import del CSV con la 1.2.0 e dire se gli asset vengono riconosciuti.
- Se dimentichi la password, il comando da terminale nel container, che nella 1.1.0 si fermava, ora funziona.

## 4. Ancora da fare

**In programma**

- La valuta d'origine di ogni titolo e un grafico dell'esposizione per valuta.
- Gli acquisti in un'altra valuta quando il broker cambia «al volo», senza una riga di cambio nel file.
- Per il CSV generico, una proposta automatica dei cambi mancanti al tasso BCE, da confermare prima di salvare.
- Su justETF, mostrare solo i risultati nella valuta e nel paese preferiti, e tutti solo se non ce ne sono.
- Il recupero della password via email.
- Altre fonti per i dati descrittivi e per le composizioni che mancano (OpenFIGI, extraETF).
- Un posto nelle impostazioni per la chiave d'accesso dei plugin, per collegare una propria fonte di dati.

**Non ancora in programma: da aggiungere (§5)**

- Un provider di prezzi con le API di Interactive Brokers.
- Rendimento a scadenza e duration delle obbligazioni.
- Un pacchetto di dati di qualità in abbonamento.
- Una spiegazione delle due date del cambio valuta.
- Una nota accanto a «Testa configurazione»: è solo una prova, lo storico completo arriva quando crei l'asset.
- Il collaudo dei plugin d'importazione di Interactive Brokers e Fineco con un report vero, con i numeri cambiati.

**Decise in un altro modo**

- Settori scritti liberamente: la lista resta fissa, ma si allarga su richiesta.
- Lo yen nella lista di justETF: justETF offre solo euro, dollari, franchi e sterline; il bisogno vero è la valuta
  d'origine, in programma.
- L'import in JSON: non serve.
- Lo storico corto: era solo l'anteprima della prova; quando crei l'asset arriva tutto lo storico.

## 5. Le voci di backlog proposte

Per le 5 MANCANTI e per la parte non tracciata della voce 11 (PARZIALE). Gli id li assegna il coordinatore; la voce 14
è futuro deliberato, quindi va in `TODO_FUTURI.md` più che in `BACKLOG_POST_1.2.md`.

- **Provider di prezzi Interactive Brokers (API)** — basso; utente C, chat del 04/09. Un provider che legga prezzo
  corrente e storico dalle API di Interactive Brokers con la chiave dell'utente; dipende dal posto per le chiavi dei
  plugin (TODO_FUTURI, «⚙️ Impostazioni per plugin») e da un account per le prove. Dettagli: fonte, r. 141, 431, 873–897.
- **Rendimento a scadenza (YTM) e duration delle obbligazioni** — basso; utente C, chat del 04/09. Salvare per ogni
  obbligazione YTM e duration con la loro data, perché cambiano nel tempo, e mostrarli nella pagina dell'asset; da
  decidere se leggerli da un provider o calcolarli in `backend/app/services/financial_math/`. Dettagli: fonte, r.
  903–909, 941.
- **Pacchetto di dati di qualità in abbonamento** — minimo, idea per `TODO_FUTURI.md`; utente C, chat del 04/09.
  Offrire a chi lo vuole una fonte a pagamento di prezzi storici e composizioni dei fondi, anche come sostegno al
  progetto; da valutare licenze dei dati, costi e convivenza con l'installazione self-hosted. Dettagli: fonte, r. 381,
  417, 423.
- **Spiegare le due date del cambio valuta** — minimo; utente C, chat del 04/09. Nel modulo, un suggerimento accanto
  alle date «Da» e «A»: di solito coincidono, si separano quando il broker accredita la nuova valuta in un altro giorno;
  la stessa frase nella guida (`user/transactions/form.*.md`, «Paired transactions»). Dettagli: fonte, r. 1867–1885.
- **«Testa configurazione» dice che è solo una prova** — minimo; utente C, chat del 04/09. Accanto al risultato dello
  storico, una riga: «Prova sugli ultimi 7 giorni: quando crei l'asset, LibreFolio scarica tutto lo storico
  disponibile»; oggi lo dice in parte solo la guida (`user/assets/create-edit.en.md:67`). Dettagli: fonte, r.
  1068–1078, 1166–1172.
- **Collaudo dei plugin d'importazione IBKR e Fineco su report veri** — minimo; utente C, chat del 04/09. Sono Beta,
  scritti su esempi trovati online: chiedere all'utente un report vero con i numeri cambiati, ricavarne fixture
  sintetiche e, se regge, togliere il Beta. Dettagli: fonte, r. 919, 1799, 1837.

## 6. Incertezze e note per il coordinatore

- **Voce 16**: la chat non nomina l'ETF. La prova è l'aggiornamento della libreria justETF in `v1.1.0` più la conferma
  dell'utente; non l'ho riprovato.
- **Voce 18**: le voci di TODO_FUTURI sono generiche (extraetf, F16); nessuna dice «riempire le distribuzioni che
  justETF non ha».
- **Voce 23**: il piano 14
  (`LibreFolio_developer_journal/Release_2/phases/14_feedbackImportUrgent/plan-phase00FeedbackImportUrgent.prompt.md:160-185`)
  non ha riprodotto un difetto del backend: la lettura del developer è che l'utente si aspettasse la creazione
  automatica degli asset al primo import, che non è prevista. Le correzioni della 1.2.0 riguardano l'aggiornamento dei
  suggerimenti e i casi ambigui. Va confermato con l'utente, rifacendo l'import.
- **Voce 24**: in 1.1.0 salvare dal wizard poteva cancellare settori e paesi (07, §4). La base di quella prova è 3
  commit dopo `v1.1.0`, e fra le due il codice cambia solo in `TransactionFormModal.svelte` e nella pagina delle
  transazioni: nessun file dell'asset o del wizard. Per questo l'avviso del §3.
- **Voci 8 e 17**: sono nel codice della 1.2.0 ma non nel CHANGELOG 1.2.0.
- **Voce 19**: il developer aveva tolto il suggerimento «Valuta/Currency» dal prompt (r. 1957); la 1.2.0 lo ha
  comunque, sulla Valuta.
- **Voce 28**: l'errore resta in alto nella finestra; l'errore sotto il campo era solo un'idea di Gemini (r. 1913), il
  developer ha chiesto solo la frase.
- **Voce 15**: il 👑 non è spiegato nell'app; una legenda costerebbe poco, ma nessuno l'ha chiesta in modo esplicito.
- **Voce 3**: il montaggio di un plugin con un volume Docker compare solo come limite nella guida per sviluppatori; non
  ho trovato una guida passo passo.
- **Voce 10**: non ho misurato quanto storico dia davvero Borsa Italiana per i singoli bond.
- **Collegati, ma non dell'utente**: E7 (il saldo negativo evidenzia tutte le righe) ed E8 (il cambio valuta
  retrodatato va al suo posto), CL 1.2.0 r. 119, vengono da osservazioni del developer mentre riproduceva il caso.
- **Privacy**: nel file non ci sono codici dei titoli, nomi di broker dell'utente, quantità o percorsi della chat.
