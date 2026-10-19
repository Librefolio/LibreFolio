# Giro 3: le decisioni, in un documento solo (17/10/2026)

> Coordinatore colori, 17/10/2026 sera. Unisce i due messaggi della designer di questa cartella e le scelte che lei e il
> developer hanno fatto alle 22:40–23:10 sul foglio delle opzioni (`materiale-inviato/opzioni-coppie-vicine.html`).
> È la specifica per DV (grafici) e T (token, toast e banner, badge). I valori di questa pagina sono quelli da scrivere
> nel codice; gli originali della designer stanno nelle due risposte.

## 0. Come si è arrivati qui

- **Primo messaggio, grafici:** applicato com'è, salvo le coppie sotto ΔE00 5 nella stessa tavolozza. Per quelle il
  coordinatore ha proposto opzioni e la designer ha scelto.
- **I controlli:** nessuna tinta verde, verde acqua o ciano nelle categorie (OKLCH 115–225). Nessun colore vicino al
  verde di successo. Ogni categoria ha almeno 3:1 sulla card. Dopo le scelte, nessuna coppia della stessa tavolozza
  scende sotto ΔE00 5 (§1.8).
- **Le scelte del developer e della designer:**
  - **Liquidità:** blu ardesia, come scrive il messaggio. In scuro, l'opzione B1-dc.
  - **Testo delle celle della correlazione:** per ogni cella il più leggibile fra nero e bianco puri, cioè C1-b con
    nero e bianco. Con i due testi del messaggio il contrasto scendeva a 3,9:1 verso r = ±0,4.
  - **La barra del valore contabile:** il blu dell'ETF (K1-a).
  - **I badge dei tipi di asset:** i colori dei tipi (A1-a).
- **Secondo messaggio, toast e banner:** applicato com'è.

## 1. Grafici

### 1.1 La regola dei verdi

- Il verde del brand resta alle azioni primarie e agli stati pertinenti, mai come grande superficie.
- Guadagni e perdite restano verde e rosso: KPI, segni ed effetto tempi.
- Nelle categorie, nei settori, nei paesi e nella mappa nessun verde, verde acqua, oliva, lime o ciano verdastro. Vale
  anche per la Liquidità, in blu ardesia.

### 1.2 Tipi di asset (le chiavi di `chartCategories.ts`)

| Chiave | Chiaro | Scuro | Scelta sul foglio |
|---|---|---|---|
| `STOCK` | `#7041C6` | `#B69AF0` |  |
| `ETF` | `#2459B8` | `#82ACF8` |  |
| `BOND` | `#536A9E` | `#9BAED8` |  |
| `CRYPTO` | `#B87916` | `#E8BD69` |  |
| `FUND` | `#5147B8` | `#9280FF` | V1-dc, era `#A7A0F5` |
| `HOLD` | `#5D687B` | `#C6D0E0` | G1-la, era `#657184`; G1-db, era `#A6B0C0` |
| `CROWDFUND` | `#8B547D` | `#D5A0C7` |  |
| `COMMODITY` | `#B85E45` | `#E99A82` |  |
| `REAL_ESTATE` | `#96602C` | `#D6A36C` |  |
| `INDEX` | `#A33D79` | `#E58BB9` |  |
| `OTHER` | `#727B87` | `#A9B0BB` |  |
| `Liquidity` | `#3F628C` | `#639BC0` | B1-dc, era `#83A9D8` |

### 1.3 Settori

| Chiave | Chiaro | Scuro | Scelta sul foglio |
|---|---|---|---|
| `Industrials` | `#586579` | `#ACC6DA` | G3-da, era `#A3B0C2` |
| `Technology` | `#2459B8` | `#82ACF8` |  |
| `Financials` | `#6748A8` | `#B9A0EB` |  |
| `Consumer Discretionary` | `#8B4F9D` | `#D2A0E0` |  |
| `Health Care` | `#2878A8` | `#7CC0E8` |  |
| `Real Estate` | `#A45D2A` | `#DDA16F` |  |
| `Basic Materials` | `#A84C36` | `#E18E7B` |  |
| `Energy` | `#B27A16` | `#E7BD69` |  |
| `Consumer Staples` | `#8B647A` | `#C6A2B6` |  |
| `Telecommunication` | `#5147B8` | `#9280FF` | V1-dc, era `#A7A0F5` |
| `Utilities` | `#526F9A` | `#9CB8E3` |  |
| `Corporate Bonds` | `#993D79` | `#E58BB9` |  |
| `Government Bonds` | `#263F78` | `#7A93CB` | B2-db, era `#8FA9E2` |
| `Other` | `#727B87` | `#A9B0BB` |  |
| `Liquidity` | `#3F628C` | `#639BC0` | B1-dc, era `#83A9D8` |
| `Unknown` | `#718C9F` | `#83939D` | G2-la, era `#737D89`; G2-dc, era `#9CA7B5` |

### 1.4 Sequenza dei paesi (storico geografico)

Quattordici colori, nello stesso ordine nei due temi. Un colore che coincide con un tipo o un settore ne segue la
scelta: così il Paese 10 è il Fondo, l'11 il Bene detenuto e il 13 i Titoli di Stato.

| Pos. | Chiaro | Scuro | Nota |
|---|---|---|---|
| 1 | `#2459B8` | `#82ACF8` |  |
| 2 | `#7041C6` | `#B69AF0` |  |
| 3 | `#A84C36` | `#E18E7B` |  |
| 4 | `#B27A16` | `#E7BD69` |  |
| 5 | `#2878A8` | `#7CC0E8` |  |
| 6 | `#993D79` | `#E58BB9` |  |
| 7 | `#526F9A` | `#9CB8E3` |  |
| 8 | `#8B4F9D` | `#D2A0E0` |  |
| 9 | `#A45D2A` | `#DDA16F` |  |
| 10 | `#5147B8` | `#9280FF` | segue V1-dc |
| 11 | `#5D687B` | `#C6D0E0` | segue G1 |
| 12 | `#8B647A` | `#C6A2B6` |  |
| 13 | `#263F78` | `#7A93CB` | segue B2-db |
| 14 | `#727B87` | `#A9B0BB` |  |

Oltre il 14°: altre tinte desaturate, con etichette o tooltip, mai il colore da solo.

### 1.5 Semi-ciambella delle quote e indicatori

I primi otto tipi: `STOCK`, `ETF`, `BOND`, `CRYPTO`, `FUND`, `HOLD`, `CROWDFUND`, `COMMODITY`. Il colore si sceglie dalla
**chiave** del tipo, cioè dalla tabella 1.2, mai dall'ordine dei dati. Semi-ciambella, indicatori e legenda leggono la
stessa mappatura.

### 1.6 Scale

- **Mappa geografica**, sei passi dal poco al molto. La stessa scala serve Dashboard, scheda dell'asset e PAC.
  - Chiaro: `#E9EFF8`, `#C8D7EF`, `#A1BCE4`, `#7798D0`, `#4E72B3`, `#2B477F`; senza dati `#D5D9E0`.
  - Scuro: `#202A3A`, `#293B57`, `#36527B`, `#456BA2`, `#5D85C2`, `#82A8E2`; senza dati `#343B46`.
- **Correlazione**, divergente, interpolata con gradualità attorno allo zero:
  - chiaro: negativa `#C43D4D`, zero `#8795A8`, positiva `#2459B8`;
  - scuro: negativa `#FF8995`, zero `#526174`, positiva `#82ACF8`;
  - **testo delle celle:** per ogni cella il più leggibile fra `#000000` e `#FFFFFF`, cioè almeno 4,6:1 su tutta la
    scala, nei due temi (C1-b con nero e bianco).

### 1.7 PAC, KPI ed effetto tempi

- **PAC, «Esposizioni ideale vs reale»:**
  - ideale in grigio neutro, chiaro `#8C929E` (P1-a′: 3,0:1 sulla card, era `#9CA3AF` a 2,45:1), scuro `#868594`
    (P2-c, era `#858E9B`, a ΔE00 4,1 dal «Non classificato» scuro: scelto alle 23:30);
  - reale nel colore della categoria della riga, lo stesso della Dashboard.
  - L'ideale dista ΔE00 8,0 dal «Non classificato» e 8,7 da Altro in chiaro, 10,1 e 14,0 in scuro: il test dei 10
    registra le due eccezioni del chiaro.
- **KPI con segno:** verde e rosso semantici (`--lf-gain`/`--lf-loss` e i token di segno).
- **Effetto tempi:** gli stessi token dei KPI, senza una funzione che generi un verde suo.
- **Card del patrimonio della Dashboard:**
  - la barra del valore contabile nel blu dell'ETF, `#2459B8` / `#82ACF8` (K1-a);
  - la barra della liquidità nel colore della Liquidità, `#3F628C` / `#639BC0`.
  - Fra le due, ΔE00 5,9 in chiaro e 10,2 in scuro.

### 1.8 Le coppie vicine rimaste (ΔE00 fra 5 e 8)

Nessuna sotto 5. Fra 5 e 8 restano, distinte da legenda e tooltip:

- **chiaro:** Obbligazione/Liquidità 5,3; Finanziari/Telecomunicazioni 5,2; Servizi pubblici/Liquidità 5,3;
  Tecnologia/Liquidità 5,9; Azione/Fondo 5,9; Crowdfunding/Indice 7,4; Industriali/Liquidità 7,6;
  Industriali/Servizi pubblici 7,9; Paesi 2/10 5,9;
- **scuro:** Tecnologia/Servizi pubblici 5,8; Crowdfunding/Indice 7,0; Finanziari/Beni voluttuari 7,3; ETF/Obbligazione
  7,4; Paesi 1/7 5,8.

Il test di distinguibilità le elenca come eccezioni note.

### 1.9 Badge del tipo di asset (A1-a)

I badge delle liste e delle schede lasciano la loro tavolozza (oggi Azione blu, ETF smeraldo…) e prendono i colori dei
tipi:

- fondo: il colore del tipo al 14 % sulla card;
- testo: il colore del tipo, spostato in luminosità (stessa tinta e croma) solo quanto basta per 4,5:1 sul suo fondo.

| Tipo | Chiaro: fondo / testo | Scuro: fondo / testo |
|---|---|---|
| `STOCK` | `#E7E1F3` / `#7041C6` (5,05:1) | `#2C2D37` / `#B69AF0` (5,77:1) |
| `ETF` | `#DCE4F1` / `#2459B8` (5,13:1) | `#242F38` / `#82ACF8` (5,98:1) |
| `BOND` | `#E3E7ED` / `#50679B` (4,51:1) | `#283034` / `#9BAED8` (6,04:1) |
| `CRYPTO` | `#F1E9DA` / `#925E0C` (4,55:1) | `#333224` / `#E8BD69` (7,34:1) |
| `FUND` | `#E2E2F1` / `#5147B8` (5,57:1) | `#262939` / `#9280FF` (4,63:1) |
| `HOLD` | `#E4E6E8` / `#5C677A` (4,57:1) | `#2E3435` / `#C6D0E0` (8,14:1) |
| `CROWDFUND` | `#EAE4E8` / `#8B547D` (4,58:1) | `#302E31` / `#D5A0C7` (6,2:1) |
| `COMMODITY` | `#F1E5E1` / `#A64E35` (4,53:1) | `#332D28` / `#E99A82` (6,08:1) |
| `REAL_ESTATE` | `#ECE5DD` / `#905A26` (4,57:1) | `#302E25` / `#D6A36C` (6,04:1) |
| `INDEX` | `#EEE0E8` / `#A33D79` (4,7:1) | `#322B2F` / `#E58BB9` (5,73:1) |
| `OTHER` | `#E7E9EA` / `#616A75` (4,51:1) | `#2A3030` / `#A9B0BB` (6,15:1) |
| `Liquidity` | `#E0E6EB` / `#3F628C` (5,0:1) | `#202D30` / `#639BC0` (4,72:1) |

Il fondo è calcolato sulla card `#FAFBFA` / `#151B19`. Nel codice va scritto come `color-mix` sul ruolo della card, non
come esadecimale fisso.

## 2. Toast e banner (il secondo messaggio)

- **Toast tenui nei due temi:**
  - fondo `X-soft`, bordo `X-line`, testo `X-on-soft`, icona `X`;
  - il pulsante di chiusura e il conto alla rovescia nello stesso `X-on-soft`.
  - Oggi sono pieni: `STATUS_TONES.toast`, `bg-lf-X text-lf-on-status`.
- **Chip e pulsanti dentro i banner, proposta a):**
  - fondo della card, bordo `X-line`, testo `X-on-soft`;
  - l'hover resta nella famiglia, per esempio il fondo `X-soft`, senza tinte nuove.
  - Vale per la qualità dei dati, `TxBulkBanners`/`TransactionResultBanner`, le pillole di `RiskPartialNotice` e il
    Retry di `OnboardingBootstrapBanner`.
  - I pulsanti secondari neutri del PAC restano card, `border-raised`, `text-primary`.
  - Oggi i pulsanti della qualità dei dati sono `bg-lf-X-line/50`, cioè la proposta b).
- **Qualità dei dati** (`DataQualityBanner`, `LotDataQualityBanner`):
  - gli errori veri in `danger`, le anomalie non bloccanti in `warning`, le informazioni in `info`, le conferme in
    `success`;
  - oggi errori e avvisi condividono l'ambra (`STATUS_TONES.dataQuality.attention`);
  - la gravità si decide condizione per condizione, non per componente. Il coordinatore porta al developer l'elenco
    delle condizioni oggi «error».
- **Le famiglie:** quasi tutte sono già sui ruoli di stato (W3-c). Restano da verificare e chiudere:
  - le opacità sul testo e sulle icone (la chiusura di `InfoBanner` a `opacity-60`);
  - `OnboardingBootstrapBanner`;
  - `AssetModalImportNotices`, in `danger` solo per gli errori veri;
  - `BrimNoticeList`, il testo colorato misurato sulla card e non sul `X-soft`;
  - la chiusura e i link di `InstanceNotices`;
  - i riquadri in linea, tutti sui quattro stati.
- **Valori di stato confermati**, già in `tokens.css`: `warning` chiaro `#AE4E00`, `danger-soft` chiaro `#FFE5E5`,
  `info-soft` chiaro `#DEEDFF`, `danger` scuro `#FF7A86`, `success` scuro `#5ED69A`. Confermati anche la famiglia AI,
  le superfici, i testi e i link.
- **Verifiche:**
  - testo ≥ 4,5:1, icone ≥ 3:1;
  - bordi dei controlli ≥ 3:1 sulle superfici accanto;
  - hover e focus misurati a parte;
  - nessun testo indebolito da un'opacità.

## 3. Instradamento

| Chi | Cosa |
|---|---|
| **DV** | 1.2–1.8 nei grafici: `chartCategories.ts`, la sequenza dei paesi, la semi-ciambella per chiave, la mappa, la correlazione col testo nero/bianco, il PAC (ideale e reale), l'effetto tempi, le due barre della card del patrimonio. Il test di distinguibilità con le eccezioni di 1.8 |
| **T** | I ruoli categorici in `tokens.css`, se l'analisi con DV li sceglie, perché i badge sono HTML e leggono classi. I badge di 1.9 in `assetTypes.ts`. Toast, chip e qualità dei dati del §2 (`toneClasses.ts`, i componenti di `ui/feedback`). Lo skill `design-system`, cioè la tabella e `palette.md` |
| **G** | La galleria prima/dopo dello stesso giorno, col foglio per la designer |
| **Coordinatore** | I file condivisi con la 1.3, l'elenco delle condizioni «error» della qualità dei dati, l'ingresso dei lotti |
