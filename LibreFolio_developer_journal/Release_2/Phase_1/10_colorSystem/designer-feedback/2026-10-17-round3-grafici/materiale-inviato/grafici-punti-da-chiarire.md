# Colori dei grafici: punti da chiarire per una lista definitiva

15 ottobre 2026. Gli stessi dati della pagina `grafici-punti-da-chiarire.html`, in testo, per l'IA.

## In breve

- I tuoi colori dei grafici del giro 2 (GR1–GR5, tabelle 3.2 A e B) sono applicati esattamente come scritti.
- Lo sviluppatore li ha visti dal vivo: il meccanismo va bene, il problema è la lista dei colori.
- In alcuni punti la regola scritta e le tabelle dicono cose diverse: ti chiediamo una lista definitiva (sezione 3).
- Card dei due temi: `#FAFBFA` e `#151B19`. Verde di successo: `#18794E` e `#5ED69A`.
- Misure: «h» è la tinta OKLCH (115–175 verde, 175–200 verde acqua, 200–225 ciano); «card» il contrasto sulla card (almeno 3:1); «ΔE verde» la distanza dal verde di successo (sotto 10 si confondono).

## 1. Cosa abbiamo applicato

### Tipi di asset (3.2 A)

| Chiave | Nome | Chiaro | h | card | ΔE verde | Scuro | h | card | ΔE verde | Tua tinta |
|---|---|---|---|---|---|---|---|---|---|---|
| `STOCK` | Azione | `#6D28D9`  | 293° | 6,8:1 | 48,5 | `#A78BFA`  | 294° | 6,4:1 | 47,5 | Viola Ametista |
| `ETF` | ETF | `#1D5BD8`  | 262° | 5,7:1 | 45,4 | `#60A5FA`  | 255° | 6,9:1 | 43,4 | Blu Cobalto / Oceano |
| `BOND` | Obbligazione | `#0E7490` ciano | 223° | 5,2:1 | 28,6 | `#22D3EE` ciano | 212° | 9,7:1 | 28,1 | Ottanio / Ciano profondo |
| `CRYPTO` | Cripto | `#D97706`  | 58° | 3,1:1 | 48,3 | `#FBBF24`  | 84° | 10,5:1 | 37,7 | Ambra / Oro |
| `FUND` | Fondo | `#4338CA`  | 277° | 7,6:1 | 47,8 | `#818CF8`  | 277° | 5,9:1 | 47,3 | Indaco |
| `HOLD` | Bene detenuto | `#5F6B7A` neutro | 254° | 5,2:1 | 27,3 | `#94A3B8` neutro | 257° | 6,8:1 | 31,8 | Blu-Ardesia calmo |
| `CROWDFUND` | Crowdfunding | `#0D9488` verde acqua | 185° | 3,6:1 | 15,4 | `#2DD4BF` verde acqua | 182° | 9,4:1 | 11,4 | Verde Acqua (Teal) |
| `COMMODITY` | Materia prima | `#C25E00`  | 52° | 4,1:1 | 48,4 | `#FB923C`  | 56° | 7,7:1 | 50,2 | Rame / Terracotta |
| `REAL_ESTATE` | Immobiliare | `#B45309`  | 49° | 4,8:1 | 48,5 | `#F59E0B`  | 70° | 8,1:1 | 44,4 | Ocra / Mattone caldo |
| `INDEX` | Indice | `#A21CAF`  | 324° | 6,1:1 | 47,5 | `#E879F9`  | 322° | 7,1:1 | 50,2 | Prugna / Orchidea |
| `OTHER` | Altro | `#6E7A74` neutro | 164° | 4,3:1 | 19,0 | `#7F8C87` neutro | 171° | 5,0:1 | 26,4 | Grigio Pietra |

### Settori (3.2 B)

| Chiave | Nome | Chiaro | h | card | ΔE verde | Scuro | h | card | ΔE verde | Tua tinta |
|---|---|---|---|---|---|---|---|---|---|---|
| `Industrials` | Industriali | `#475569` neutro | 257° | 7,3:1 | 30,0 | `#94A3B8` neutro | 257° | 6,8:1 | 31,8 | Acciaio / Ardesia |
| `Technology` | Tecnologia | `#1D5BD8`  | 262° | 5,7:1 | 45,4 | `#60A5FA`  | 255° | 6,9:1 | 43,4 | Blu Elettrico / Cobalto |
| `Financials` | Finanziari | `#0F766E` verde acqua | 186° | 5,3:1 | 12,2 | `#2DD4BF` verde acqua | 182° | 9,4:1 | 11,4 | Verde Acqua istituzionale |
| `Consumer Discretionary` | Beni voluttuari | `#7C3AED`  | 293° | 5,5:1 | 48,1 | `#A78BFA`  | 294° | 6,4:1 | 47,5 | Viola |
| `Health Care` | Sanità | `#0284C7`  | 242° | 3,9:1 | 38,9 | `#38BDF8`  | 233° | 8,2:1 | 38,1 | Azzurro Ceruleo |
| `Real Estate` | Immobiliare | `#B45309`  | 49° | 4,8:1 | 48,5 | `#FBBF24`  | 84° | 10,5:1 | 37,7 | Ocra / Ambra |
| `Basic Materials` | Materie prime | `#9A3412`  | 37° | 7,0:1 | 53,1 | `#FB923C`  | 56° | 7,7:1 | 50,2 | Terracotta / Rame |
| `Energy` | Energia | `#D97706`  | 58° | 3,1:1 | 48,3 | `#FACC15`  | 92° | 11,4:1 | 35,2 | Oro / Giallo Solare |
| `Consumer Staples` | Beni di consumo | `#4D7C0F` verde | 132° | 4,8:1 | 14,8 | `#A3E635` verde | 129° | 11,6:1 | 19,4 | Verde Oliva / Lime morbido |
| `Telecommunication` | Telecomunicazioni | `#4338CA`  | 277° | 7,6:1 | 47,8 | `#818CF8`  | 277° | 5,9:1 | 47,3 | Indaco |
| `Utilities` | Servizi pubblici | `#0E7490` ciano | 223° | 5,2:1 | 28,6 | `#22D3EE` ciano | 212° | 9,7:1 | 28,1 | Ciano / Ottanio |
| `Corporate Bonds` | Obbligazioni societarie | `#86198F`  | 325° | 7,9:1 | 47,3 | `#E879F9`  | 322° | 7,1:1 | 50,2 | Prugna |
| `Government Bonds` | Titoli di Stato | `#1E3A8A`  | 266° | 10,0:1 | 44,4 | `#93C5FD`  | 252° | 9,7:1 | 37,8 | Blu Navy / Istituzionale |
| `Other` | Altro | `#6E7A74` neutro | 164° | 4,3:1 | 19,0 | `#7F8C87` neutro | 171° | 5,0:1 | 26,4 | Grigio Pietra |

### Liquidità e Non classificato

| Chiave | Nome | Chiaro | h | card | ΔE verde | Scuro | h | card | ΔE verde | Tua tinta |
|---|---|---|---|---|---|---|---|---|---|---|
| `Liquidity` | Liquidità | `#2D6A54` verde | 167° | 6,1:1 | 7,8 | `#429E79` verde | 164° | 5,3:1 | 15,6 | Verde Salvia Brand (GR3) |
| `Unknown` | Non classificato | `#94A09B` neutro | 169° | 2,6:1 | 26,7 | `#52605B` neutro | 172° | 2,6:1 | 39,8 | Grigio Nebbia neutro |

## 2. Punti da chiarire

### 2.1 Verdi nelle categorie: la regola GR2 e le tabelle non dicono la stessa cosa

- GR2 dice: fuori il rosso d'errore e il verde fluo di guadagno; il verde del brand **solo** per la Liquidità; per i toni caldi ambra, rame e malva.
- Le tabelle però hanno 6 voci che si leggono verdi, verde acqua o ciano: Obbligazione (`BOND`): `#0E7490` / `#22D3EE`, ciano; Crowdfunding (`CROWDFUND`): `#0D9488` / `#2DD4BF`, verde acqua; Finanziari (`Financials`): `#0F766E` / `#2DD4BF`, verde acqua; Beni di consumo (`Consumer Staples`): `#4D7C0F` / `#A3E635`, verde; Servizi pubblici (`Utilities`): `#0E7490` / `#22D3EE`, ciano; Liquidità (`Liquidity`): `#2D6A54` / `#429E79`, verde.
- Lo sviluppatore ha letto GR2 come «nessun verde di nessuna natura» nei grafici di categoria, e si aspettava questo.

**Domanda.** Qual è la regola definitiva? Per esempio: (a) nessun verde, verde acqua o ciano nelle categorie, Liquidità compresa; (b) verde solo per la Liquidità; (c) verdi ammessi, ma lontani dal verde di successo. Poi le tabelle aggiornate.

### 2.2 Liquidità (GR3)

- `#2D6A54` / `#429E79`. In chiaro dista solo ΔE 7,8 dal verde di successo `#18794E`: a colpo d'occhio sono lo stesso verde.
- In scuro è identica a `--lf-focus`, cioè all'anello di focus e ai link.
- Lo sviluppatore non se l'aspettava verde.

**Domanda.** La teniamo verde (e allora più lontana dal verde di successo), o le dai un'altra tinta?

### 2.3 Mappa geografica (GR5.1)

- La scala a 6 verdi salvia e bosco che hai indicato. È la stessa nella dashboard, nella pagina dell'asset e nel PAC.
- Lo sviluppatore: «i paesi sono ancora una sfumatura di verde».
- Scala, chiaro: #E6F2ED, #C2E0D3, #94C7B2, #62AB8E, #378567, #1B4334. Scuro: #182923, #1F3B30, #275241, #316B54, #3D876A, #4FB38B.

**Domanda.** Confermi una scala verde, o ne vuoi una di un'altra tinta? Servono 6 passi per tema, dal poco al molto, più il colore dei paesi senza dati.

### 2.4 Storico geografico

- Per i paesi, che non hanno un colore fisso, hai indicato l'ordine dei 14 colori dei settori.
- Il 3° è il verde acqua dei Finanziari e il 9° il verde oliva dei Beni di consumo: lo sviluppatore vede «il verde in uno dei segnali».
- Ordine, chiaro: #475569, #1D5BD8, #0F766E, #7C3AED, #0284C7, #B45309, #9A3412, #D97706, #4D7C0F, #4338CA, #0E7490, #86198F, #1E3A8A, #6E7A74. Scuro: #94A3B8, #60A5FA, #2DD4BF, #A78BFA, #38BDF8, #FBBF24, #FB923C, #FACC15, #A3E635, #818CF8, #22D3EE, #E879F9, #93C5FD, #7F8C87.

**Domanda.** Vuoi una sequenza dedicata ai paesi, senza verdi? Ne servono almeno 14.

### 2.5 Semi-ciambella delle quote e indicatori (GR5.2)

- «I primi 8 colori della palette categorica» sono gli 8 tipi in quest'ordine. Il 3° (Obbligazione) è ciano e il 7° (Crowdfunding) verde acqua: con tre persone o più compare un verde acqua.
- Lo sviluppatore non l'ha visto, ma può succedere. Lo sfondo della finestra non è ancora migrato, quindi oggi non si giudica bene.
- Ordine, chiaro: #6D28D9, #1D5BD8, #0E7490, #D97706, #4338CA, #5F6B7A, #0D9488, #C25E00. Scuro: #A78BFA, #60A5FA, #22D3EE, #FBBF24, #818CF8, #94A3B8, #2DD4BF, #FB923C.

**Domanda.** La regola di 2.1 vale anche qui? Se serve, dai una sequenza di 8 dedicata.

### 2.6 Matrice di correlazione (GR5.3)

- Centro `--lf-surface-panel` (`#E8ECE9` / `#1B2421`), estremi `--lf-danger` e `--lf-info`. Con la scelta dello sviluppatore, il rosso scuro ora è `#FF7A86`.
- Sulla card il centro ha 1,1:1 in chiaro e 1,1:1 in scuro: le celle vicine allo 0 si confondono con la card, e in scuro quelle appena negative diventano marrone scuro.
- Lo sviluppatore: «i numeri vicino allo 0 in scuro non vanno bene», nella dashboard e nella scheda Correlazione degli asset.
- Chiaro: #C82838, #E8ECE9, #155EEF. Scuro: #FF7A86, #1B2421, #3F86FA.

**Domanda.** Ti serve un centro che resti visibile sulla card nei due temi, e il colore del testo delle celle. Confermi gli estremi?

### 2.7 PAC, «Esposizioni — ideale vs reale» (non era nel giro 2)

- Oggi: ideale in grigio (`#9CA3AF` / `#6B7280`), reale nel verde vecchio `#1A4031` e, in scuro, nel verde fluo `#00D681`, proprio quello che GR2 esclude. Le mappe usano la scala del punto 2.3.
- Nel frattempo, come lavoro tecnico, lo allineiamo: reale nel colore della categoria della riga, uguale alla dashboard, e ideale in un grigio neutro.
- Il grigio neutro di «ideale» è il ruolo `--lf-text-secondary`: `#4A5550` in chiaro, `#9BA8A2` in scuro. Sta a ΔE00 ≥ 10 da ogni categoria, con una sola eccezione: «Altro» (`#7F8C87`, tipo `OTHER` e settore `Other`), in scuro, a 9,0. Un test registra l'eccezione: se la lista nuova avvicina ancora «Altro», o porta un'altra categoria sotto 10, ce ne accorgiamo subito.
- Oggi, chiaro: ideale #9CA3AF, reale #1A4031. Scuro: ideale #6B7280, reale #00D681.

**Domanda.** Ti va bene così, o preferisci una coppia fissa ideale/reale?

### 2.8 Numeri con segno (KPI)

- Guadagni e perdite nei KPI restano verde e rosso, i tuoi `--lf-success` e `--lf-danger`, con il rosso e il verde scuri scelti dallo sviluppatore. Arrivano con l'ondata W3.
- Oggi si vedono ancora i verdi fluo vecchi; l'«effetto tempi» ha un verde diverso perché lo calcola una funzione a parte.

**Domanda.** Confermi che la regola sui verdi riguarda solo le categorie, non guadagni e perdite?

### 2.9 «Non classificato»

- `#94A09B` / `#52605B` ha 2,6:1 e 2,6:1 sulla card: sotto il 3:1 richiesto agli elementi grafici (WCAG 1.4.11).

**Domanda.** Se il grigio tenue è voluto, per dire «assenza», confermalo; altrimenti dai un grigio un poco più marcato.

## 3. Cosa ti chiediamo

Una lista definitiva, nei due temi:

1. la regola sui verdi (2.1, 2.8)
2. gli 11 tipi più la Liquidità
3. i 14 settori più Liquidità e Non classificato
4. la sequenza per le serie senza colore fisso, cioè i paesi nello storico: almeno 14
5. la sequenza della semi-ciambella e degli indicatori: 8
6. la scala della mappa (6 passi) e il colore dei paesi senza dati
7. la correlazione: i due estremi e il centro
8. il PAC: conferma, o la coppia ideale/reale

I controlli li facciamo noi: contrasto, distanza fra categorie vicine, distanza dal verde di successo.

## 4. Schermate (cartella `schermate/`)

- `sviluppatore-1-kpi-scuro.png`: Dashboard, scuro: l'effetto tempi ha un verde diverso dagli altri KPI, che sono ancora quelli vecchi
- `sviluppatore-2-torta-tipo-scuro.png`: Torta per tipo, scuro: Liquidità salvia e Crowdfunding verde acqua
- `sviluppatore-3-correlazione-scuro.png`: Matrice di correlazione, scuro: le celle vicino allo 0
- `sviluppatore-4-pac-esposizioni-scuro.png`: PAC, esposizioni ideale/reale: mappe verdi e barre «reale» nel verde vecchio
- `dv-torta-tipo-chiaro.png`: Torta per tipo, chiaro
- `dv-torta-tipo-scuro.png`: Torta per tipo, scuro
- `dv-torta-settore-scuro.png`: Torta per settore, scuro
- `dv-geografica-scuro.png`: Geografica, scuro
- `dv-storico-geografico-scuro.png`: Storico geografico, scuro
- `dv-correlazione-scuro.png`: Diversificazione e correlazione, scuro
- `dv-semiciambella-scuro.png`: Semi-ciambella delle quote, scuro
- `dv-asset-classificazione-chiaro.png`: Asset, classificazione: mappa e settori, chiaro

## 5. Come rispondere

```text
Regola sui verdi: …
Tipi: (tabella chiave, chiaro, scuro)
Settori: (tabella chiave, chiaro, scuro)
Sequenza paesi: …
Sequenza semi-ciambella e indicatori: …
Scala mappa, chiaro: … / scuro: … / senza dati: …
Correlazione, chiaro: neg … centro … pos … / scuro: …
PAC: …
Altro: …
```
