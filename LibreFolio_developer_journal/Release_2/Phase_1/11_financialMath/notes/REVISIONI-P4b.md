# Revisioni del contratto P4b (cura B, serie a gradini) — 25/10/2026

Tre revisori, tutti «ok con modifiche», nessun bloccante. Il coordinatore ha riassunto i loro messaggi; le decisioni
del coordinatore sono in fondo.

## J (lotti, #48) — stima 2,5–3,5 giorni (era 1,5–2,5)

1. Il percorso di #48 è `POST /portfolio/positions-series`, non `/positions/series` (§1.4 e testo del CHANGELOG §9).
2. Contiguità: `market_price_history` non ha riga nei giorni senza cambio, quindi ha buchi in mezzo. Invariante
   proposta: tratti ordinati, senza sovrapposizioni, dentro `range`; nei buchi `valueAt` restituisce `null`.
   L'espansione della regola 1 resta esatta.
3. Tratti massimali nei lotti: i giorni di calcolo sono un sovrainsieme dei cambi di ogni chiave → bisogna unire le
   righe consecutive identiche per chiave, confrontando con `as_tuple` e non con `==` (`Decimal('1.10')` contro `'1.1'`).
   **Chiede a MF** una funzione generica in `series_steps.py` (`steps_from_rows`) che calcola `through`, unisce le
   righe uguali e taglia ai bordi. Il primo tratto parte da `range.start` con i valori del giorno di cambio
   precedente; `range.start = max(display_from, computed_from)`, `range.end = actual_to`.
4. Nei lotti restano cicli per giorno (prezzi `lots_analysis_service.py:368`, `lot_change_days`, lista di date) →
   il secondo stadio diventa obbligatorio: prezzi solo sui giorni candidati. **Chiede a MF** una proprietà pubblica
   `observation_dates` su `AssetPriceSeries` (`price_marks.py`), più i passi di `unit_rate_steps` (da coordinare con
   il cambio `as_of`). Copertura: parità della regola 1 e una prova di mutazione.
5. #48: la novità di una posizione include anche `frame.end + 1`, `date_from` e `date_from + 1`, e il punto «in
   viaggio». L'asset sommato si calcola sull'unione dei giorni di cambio dei broker. J5-4 resta in backlog.
6. Test: la regola 1 copre anche il transito e l'asset sommato; per i lotti, confronto con il giornaliero di HEAD
   (16 coppie); prova di costo sull'anno 1; budget per i lotti < 150 MB.
7. Dal checkpoint piccolo di MF servono: `StepSpan`, `DateSpan`, `value_at`, `steps_from_rows`, `observation_dates`.

## Y (grafici) — stima 6–7 giorni (era 3–4)

1. La linea MWRR non è in `PerformanceChart` (barre dei contributi, invariato): è nella vista % di `GrowthChart`
   (`mwrrCum`, `growthChartData.ts`). Correggere il §7.
2. Manca `pointsBetween(points, from, to)` nel §5 (candele di un bucket: `valueAt` per apertura e chiusura,
   massimo/minimo sui tratti che toccano il bucket). `sumAt` non serve.
3. `expandDays` resta solo per la scala a candele più fine di un tratto, con il tetto.
4.–10. Decisioni di Y (tooltip sul giorno puntato con `valueAt`; MWRR con `nearestPoint` e la data del punto vero;
   risoluzione: tratti veri se ci stanno, altrimenti bucket settimana/mese; aree impilate con tratti allineati;
   serie parziali che finiscono al loro `through`; test «mai un array di tutti i giorni» più un gate; helper di test
   che comprime le fixture giornaliere; #48 a gradini).
- Stima più alta perché tutta la pipeline di `GrowthChart` oggi ragiona per indice di giorno.

## Z (AI Export) — stima 1 giorno

1. Il punto da cambiare è uno solo per due componenti: `build_performance_bucket_rows`
   (`payloads/portfolio_broker.py:322`); il terzo è `broker_cost_efficiency._average_nav` (`:563`). Nessun lettore
   dell'AI Export usa `mwrr_*` → non servono `mwrr_line` né `period_mwrr`.
2. §6: `value_at` restituisce il tratto, e il giorno resta al chiamante (`min_date`/`max_date` =
   `max(date_del_tratto, inizio_bucket)` del primo tratto che raggiunge l'estremo; a parità vince il più vecchio).
   Va scritto nel contratto.
3. `_average_nav` diventa una media pesata per la lunghezza (`through − date + 1`), in giorni e non in tratti.
4. `points_between` taglia ai bordi; i bucket vuoti sono quelli che non toccano `range`. Va nei test di
   `series_steps.py`.
5. **Lettori dimenticati dal contratto (rischio):** `risk/data_quality.py:140-142` legge i quattro
   `incomplete_*_dates` (con gli intervalli il conteggio diventa la somma dei giorni degli intervalli fusi);
   `risk/results.py:80-82` (`portfolio_twrr_returns`) legge `report.history` giorno per giorno → va letto con
   `value_at` sui giorni di osservazione.
6. Probe di diff sulle 6 copie, esito 0 differenze; l'oracolo per giorno resta nel test.

## Decisioni del coordinatore

- MF integra tutte le correzioni nel contratto e aggiunge al checkpoint piccolo: `steps_from_rows`, `points_between`
  con taglio ai bordi, `observation_dates`, `value_at` che restituisce il tratto.
- I due lettori del rischio (`risk/data_quality.py`, `risk/results.py`) passano a **J** (dominio rischio).
- Y: la regola di risoluzione del punto 5 va bene; il badge Weekly/Monthly resta solo dove c'è un bucket. Y può
  partire subito con `stepSeries.ts` e i suoi test (funzioni pure).
- Z: può scrivere subito i test rossi e l'oracolo; il codice parte dopo il checkpoint piccolo di MF.
- Stima totale aggiornata: MF 3–3,5 + J 2,5–3,5 + Y 6–7 + Z 1 ≈ 13–15 giorni-persona (era 8–10). Lo segnalo al
  developer come informazione.
