# Attività per l'inizio della 1.4

Qui stanno i lavori che **faremo di certo** quando parte la 1.4 (developer, 22/10/2026). Le idee da ponderare restano
in [`TODO_FUTURI.md`](../../../TODO_FUTURI.md); il lavoro della 1.3 sta in
[`../Phase_1/PROSSIMI_LAVORI.md`](../Phase_1/PROSSIMI_LAVORI.md) (ondate 4 e 5).

I link sono relativi a questa cartella; il testo del link riporta il titolo della sezione da cercare nel file.

---

## 🧹 Il riordino del codice: il resto del piano 43

**Origine**: filtro di `PROSSIMI_LAVORI.md` del 22/10. Il riordino del piano 43 (T, 11/10) è fatto per circa due
terzi: registri per famiglia di plugin (T-PL2), `services/fx/` (T-PL4), `services/signals/` (T-PL1), asset (T-PL6), i
tagli di PAC, transazioni, `broker_service`, `price_store`, asset, cambi, rischio e segnali (T-P2.2), il frontend di
dashboard e transazioni in `lib/features/`.

**Perché tutto insieme e dopo la 1.3**: nessun effetto per l'utente, molti file toccati. Fatto a codice fermo, all'inizio
della 1.4, non litiga con i lavori in corso. Ogni lotto è un riordino puro: stessi URL, `operationId` e comportamento.

| Lotto | Cosa | Chi | Dove è descritto |
|---|---|---|---|
| W3 | `api/v1/brokers.py` (1 265 righe, due router) diventa il pacchetto `api/v1/brokers/`, un modulo per risorsa | W | [piano 04, «7. Lotti e checkpoint» (riga W3)](../Phase_1/04_importTransactions/plan-phase01ImportTransactions.prompt.md); backlog «T-P2.2» |
| W4/CP7 | il taglio di `services/brim/brim_provider.py` (2 349 righe) per tema; il contratto resta dov'è | W | [piano 04, «W4 — CP6–CP7, PL5», nota «Disegno di CP7 (taglio)»](../Phase_1/04_importTransactions/plan-phase01ImportTransactions.prompt.md); backlog «T-PL5» |
| W5–W6 (U-B3, U-B4) | l'icona di Scalable (l'unica fatta da noi; gli altri plugin usano il favicon via URL, e restano così) in `broker_scalable/static/`; i 62 report d'esempio di `brim_providers/sample_reports/` nella cartella del loro plugin | W (la rotta delle icone con H) | [piano 04, «2. Voci assegnate» (U-B3, U-B4)](../Phase_1/04_importTransactions/plan-phase01ImportTransactions.prompt.md); [piano 45, «9»](../Phase_0/45_pluginModules/plan-phase00PluginModules.prompt.md) |
| CP5 (T-PL7) | un router proprio per i segnali, con gli URL invariati | X | [piano 03, «Stato vero di CP5…»](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md); backlog «T-PL7» |
| CP7/FE4 | il frontend dei cambi in `lib/features/fx/` (con X-R9, X-R10, X-R14) | X | [piano 03, «4.2 Riordino frontend»](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md) |
| FE5a | il frontend degli asset in `lib/features/assets/` (il resto di CP8) | X | [piano 03, «4.2 Riordino frontend»](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md) |
| CP-8 | il taglio di `services/portfolio_service.py` (2 238 righe) e dei suoi schemi | J | [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md); backlog «T-P2.2» |
| CP-9b/9c | `schemas/risk.py` e `schemas/signals.py` in pacchetti (~45 importatori) | J | [piano 05, «CP-9b», «CP-9c»](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md) |
| T-SG | i moduli sciolti in cima a `backend/app/services/` raggruppati per dominio (`accounts/`, `platform/`, `files/`) | T | backlog [«T-SG»](../Phase_0/BACKLOG_POST_1.2.md) |

**Vincoli noti**:
- FE4 e FE5a aspettavano il lotto A dei colori. Al 22/10 la baseline del ratchet (`frontend/src/themeRoles.baseline.tsv`)
  ha ancora 2 righe dei cambi e 7 di `components/assets/`: si ricontrolla alla partenza.
- Y4a (i segnali di Y) aspetta FE4 e FE5a.
- CP5 tocca i router che l'isolamento dei segnali di X-R16 ha cambiato.
- CP-9b/9c toccano 45 file: serve una finestra quieta.
- Prima la rinomina, poi il taglio (§4.2 del piano 43).
