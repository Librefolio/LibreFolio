# Toast e banner di LibreFolio, con i tuoi colori (giro 2)

15 ottobre 2026. Questo file ha **gli stessi dati** della pagina `toast-e-banner.html`, ma in testo, per darlo all'IA.
Per vederli, apri la pagina con un doppio clic.

## Da dove vengono i colori

- Sono **i tuoi colori del giro 2**, come sono già nel codice di sviluppo. Cinque valori sono diversi dai tuoi: sono
  nella tabella qui sotto; tutto il resto è esattamente il tuo valore.
- **Non sono i colori che l'app mostra oggi.** Toast e banner usano ancora le tinte di Tailwind: ambra, rosso, smeraldo
  e verde, blu e azzurro. Passeranno ai tuoi con le prossime ondate; i due azzurri diventano un solo «info», i due verdi
  un solo «success». Per ogni componente, «Classi di oggi» dice che cosa usa adesso.
- I nomi dei colori sono i ruoli del tema: `X-soft` è il fondo tenue dello stato X, `X-line` il suo bordo, `X-on-soft` il
  testo sul fondo tenue, `X` il colore pieno.

### Dove i valori non sono i tuoi

| Ruolo | Tema | Il tuo | Nella pagina | Perché |
|---|---|---|---|---|
| `warning` | chiaro | `#B45309` | `#AE4E00` | il tuo dava 4,21:1 sulla superficie secondaria: corretto per il contrasto, da confermare nel giro 3 |
| `danger-soft` | chiaro | `#FEE2E2` | `#FFE5E5` | il testo attenuato sopra dava 4,42:1: corretto per il contrasto, da confermare nel giro 3 |
| `info-soft` | chiaro | `#DBEAFE` | `#DEEDFF` | l'info e il testo attenuato sopra davano 4,44 e 4,42:1: corretto per il contrasto, da confermare nel giro 3 |
| `danger` | scuro | `#F84361` | `#FF7A86` | scelto dallo sviluppatore il 15/10: un rosso più morbido, 7,0:1 sulla card |
| `success` | scuro | `#36D399` | `#5ED69A` | scelto dallo sviluppatore il 15/10: un verde più morbido, 9,6:1 sulla card |

## Regole usate nella pagina

X è uno degli stati: `success`, `warning`, `danger`, `info`.

| Elemento | Fondo | Bordo | Testo | Icona |
|---|---|---|---|---|
| Banner o avviso | `X-soft` | `X-line` | `X-on-soft` | `X` |
| Toast «pieno» | `X` | come il fondo | `on-status`, il colore della card | come il testo |
| Toast «tenue» | `X-soft` | `X-line` | `X-on-soft` | `X` |
| Chip e pulsanti dentro un banner, proposta a) | card | `X-line` | `X-on-soft` | `X-on-soft` |
| Pulsante secondario (PAC) | card | `border-raised` | `text-primary` | — |
| Link dentro un banner | — | — | `link` | — |

L'AI ha i suoi: `ai-soft`, `ai-line`, `ai`.

Le soglie di contrasto sono quelle WCAG AA: **testo almeno 4,5:1, icona almeno 3:1**. Nessun valore qui sotto è sotto soglia.

## Domande aperte

1. **Toast: pieno o tenue?**
   - Oggi sono pieni, con il testo bianco in tutti e due i temi.
   - Con i tuoi colori, il pieno nel tema scuro diventa una tinta accesa con il testo scuro.
   - L'alternativa è il tenue, come i banner.
   - Nella pagina sono a confronto nella sezione 1.
2. **Chip e pulsanti dentro i banner.**
   - Oggi hanno un fondo un gradino più scuro del banner (per esempio `amber-100` su `amber-50`).
   - Con la regola presa alla lettera, il fondo `100` diventerebbe `-soft`, uguale al banner, e il pulsante sparirebbe.
   - Nella pagina ho usato la proposta a): fondo della card, bordo `X-line`, testo `X-on-soft`. La regola alla lettera è la b).
   - Il confronto è nel riquadro «Da decidere».
3. **Errori nella qualità dei dati.**
   - Oggi `DataQualityBanner` e `LotDataQualityBanner` disegnano gli errori in ambra come gli avvisi: cambia solo l'icona.
   - Con i tuoi colori restano avviso, o diventano rosso?

## Valori

### Tinte degli stati

| Stato | Tema | Fondo | Bordo | Testo | Contrasto testo | Icona | Contrasto icona |
|---|---|---|---|---|---|---|---|
| success | chiaro | `#E6F4ED` | `#B8DFCA` | `#145937` | 7,4:1 | `#18794E` | 4,8:1 |
| success | scuro | `#13261E` | `#1F4435` | `#86EFAC` | 11,3:1 | `#5ED69A` | 8,7:1 |
| warning | chiaro | `#FEF3C7` | `#FDE68A` | `#92400E` | 6,4:1 | `#AE4E00` | 4,8:1 |
| warning | scuro | `#291E0C` | `#54380E` | `#FCD34D` | 11,3:1 | `#F59E0B` | 7,6:1 |
| danger | chiaro | `#FFE5E5` | `#FECACA` | `#991B1B` | 7,0:1 | `#C82838` | 4,6:1 |
| danger | scuro | `#2A1417` | `#581C24` | `#FCA5A5` | 9,1:1 | `#FF7A86` | 6,9:1 |
| info | chiaro | `#DEEDFF` | `#BFDBFE` | `#1E40AF` | 7,3:1 | `#155EEF` | 4,6:1 |
| info | scuro | `#131F33` | `#1E3A5F` | `#93C5FD` | 9,2:1 | `#3F86FA` | 4,7:1 |
| ai | chiaro | `#F3E8FF` | `#DDD6FE` | `#6D28D9` | 6,0:1 | `#6D28D9` | 6,0:1 |
| ai | scuro | `#1E1B2E` | `#3B3054` | `#A78BFA` | 6,2:1 | `#A78BFA` | 6,2:1 |

### Superfici e testi intorno

| Ruolo | Chiaro | Scuro | Dove |
|---|---|---|---|
| `surface-page` | `#F3F5F3` | `#0D1110` | fondo della pagina |
| `surface-card` | `#FAFBFA` | `#151B19` | card; fondo di chip e pulsanti nella proposta a) |
| `surface-panel` | `#E8ECE9` | `#1B2421` | pannelli |
| `surface-neutral` | `#D8E0DC` | `#222C28` | cerchio dietro le icone di RefreshNotice e CopyNotice |
| `text-primary` | `#1C2420` | `#EDF2F0` | testo del pulsante secondario |
| `text-secondary` | `#4A5550` | `#9BA8A2` | icone nel cerchio neutro, righe del file BRIM |
| `border-subtle` | `#D8E0DC` | `#222C28` | bordo della card |
| `border-raised` | `#D8E0DC` | `#2E3B36` | bordo del pulsante secondario |
| `link` | `#236B4D` | `#429E79` | link «Chiudi» di CopyNotice |
| `on-status` | `#FAFBFA` | `#151B19` | testo dei toast pieni |

### Chip e pulsanti dentro i banner

Contrasto del testo del chip: a) sulla card, la proposta; b) sul fondo del banner, la regola alla lettera.

| Stato | Tema | Testo | Bordo | a) su card | b) su `X-soft` |
|---|---|---|---|---|---|
| success | chiaro | `#145937` | `#B8DFCA` | 8,1:1 | 7,4:1 |
| success | scuro | `#86EFAC` | `#1F4435` | 12,4:1 | 11,3:1 |
| warning | chiaro | `#92400E` | `#FDE68A` | 6,8:1 | 6,4:1 |
| warning | scuro | `#FCD34D` | `#54380E` | 12,1:1 | 11,3:1 |
| danger | chiaro | `#991B1B` | `#FECACA` | 8,0:1 | 7,0:1 |
| danger | scuro | `#FCA5A5` | `#581C24` | 9,2:1 | 9,1:1 |
| info | chiaro | `#1E40AF` | `#BFDBFE` | 8,4:1 | 7,3:1 |
| info | scuro | `#93C5FD` | `#1E3A5F` | 9,7:1 | 9,2:1 |

### Link dentro i banner

| Stato | Tema | Link | Contrasto su `X-soft` |
|---|---|---|---|
| success | chiaro | `#236B4D` | 5,6:1 |
| success | scuro | `#429E79` | 4,8:1 |
| warning | chiaro | `#236B4D` | 5,7:1 |
| warning | scuro | `#429E79` | 5,0:1 |
| danger | chiaro | `#236B4D` | 5,4:1 |
| danger | scuro | `#429E79` | 5,3:1 |
| info | chiaro | `#236B4D` | 5,4:1 |
| info | scuro | `#429E79` | 5,0:1 |

## 1. Toast

- **Dove:** in alto al centro, sopra la pagina. Si chiudono con la ✕ o trascinandoli; la barretta in basso è il conto alla rovescia.
- **File:** `frontend/src/lib/components/ui/feedback/ToastContainer.svelte`; colori di oggi in `toneClasses.ts`, `STATUS_TONES.toast`.
- **Chiamate nel codice:** success 35 · error 63 · warning 4 · info 10.
- **Classi di oggi:** success `bg-emerald-600 text-white`, error `bg-red-600 text-white`, warning `bg-amber-500 text-white`, info `bg-blue-500 text-white`, uguali nei due temi.
- **Messaggi d'esempio:** success: «"VWCE" aggiornato con successo» · error: «Impossibile raggiungere il server. Controlla la connessione e riprova.» · warning: «3 transazioni escluse: accesso Editor richiesto» · info: «Sincronizzazione tassi FX…».

| Tipo | Stile | Tema | Fondo | Bordo | Testo | Contrasto testo | Icona | Contrasto icona |
|---|---|---|---|---|---|---|---|---|
| success | pieno | chiaro | `#18794E` | `#18794E` | `#FAFBFA` | 5,2:1 | `#FAFBFA` | 5,2:1 |
| success | pieno | scuro | `#5ED69A` | `#5ED69A` | `#151B19` | 9,6:1 | `#151B19` | 9,6:1 |
| success | tenue | chiaro | `#E6F4ED` | `#B8DFCA` | `#145937` | 7,4:1 | `#18794E` | 4,8:1 |
| success | tenue | scuro | `#13261E` | `#1F4435` | `#86EFAC` | 11,3:1 | `#5ED69A` | 8,7:1 |
| error | pieno | chiaro | `#C82838` | `#C82838` | `#FAFBFA` | 5,3:1 | `#FAFBFA` | 5,3:1 |
| error | pieno | scuro | `#FF7A86` | `#FF7A86` | `#151B19` | 7,0:1 | `#151B19` | 7,0:1 |
| error | tenue | chiaro | `#FFE5E5` | `#FECACA` | `#991B1B` | 7,0:1 | `#C82838` | 4,6:1 |
| error | tenue | scuro | `#2A1417` | `#581C24` | `#FCA5A5` | 9,1:1 | `#FF7A86` | 6,9:1 |
| warning | pieno | chiaro | `#AE4E00` | `#AE4E00` | `#FAFBFA` | 5,2:1 | `#FAFBFA` | 5,2:1 |
| warning | pieno | scuro | `#F59E0B` | `#F59E0B` | `#151B19` | 8,1:1 | `#151B19` | 8,1:1 |
| warning | tenue | chiaro | `#FEF3C7` | `#FDE68A` | `#92400E` | 6,4:1 | `#AE4E00` | 4,8:1 |
| warning | tenue | scuro | `#291E0C` | `#54380E` | `#FCD34D` | 11,3:1 | `#F59E0B` | 7,6:1 |
| info | pieno | chiaro | `#155EEF` | `#155EEF` | `#FAFBFA` | 5,2:1 | `#FAFBFA` | 5,2:1 |
| info | pieno | scuro | `#3F86FA` | `#3F86FA` | `#151B19` | 5,0:1 | `#151B19` | 5,0:1 |
| info | tenue | chiaro | `#DEEDFF` | `#BFDBFE` | `#1E40AF` | 7,3:1 | `#155EEF` | 4,6:1 |
| info | tenue | scuro | `#131F33` | `#1E3A5F` | `#93C5FD` | 9,2:1 | `#3F86FA` | 4,7:1 |

## 2. Banner e avvisi (11 famiglie, 33 varianti)

Ogni famiglia è un componente, o un gruppo di componenti fratelli. Le varianti sono quelle disegnate nella pagina; i loro colori sono nella tabella «Tinte degli stati», secondo la regola del banner.

### 2.1 Avvisi dell'istanza — `InstanceNotices`

- **Dove:** In cima a ogni pagina dell'app. È l'unico avviso **già con i tuoi colori**; oggi nessuna funzione lo usa, quindi i testi sono d'esempio.
- **File:** `lib/features/instance/components/InstanceNotices.svelte`
- **Superficie:** la pagina
- **Struttura:** testo, azione, chiusura ✕ (azioni: link)
- **Varianti nella pagina:** info → `info`; warning, con link e ✕ → `warning`; danger → `danger`
- **Classi di oggi:**
  - `instance-notice-info|warning|danger`: bg `bg-lf-info-soft | bg-lf-warning-soft | bg-lf-danger-soft`; border `border-lf-info-line | border-lf-warning-line | border-lf-danger-line`; body `text-lf-{info,warning,danger}-on-soft text-sm`; icon `text-lf-info | text-lf-warning | text-lf-danger`; action `link ml-1 font-medium underline; X button hover:opacity-70`

### 2.2 Stato delle guide non aggiornato — `OnboardingBootstrapBanner`

- **Dove:** In cima all'app, quando lo stato delle guide non si carica.
- **File:** `lib/features/onboarding/components/OnboardingBootstrapBanner.svelte`
- **Superficie:** la pagina
- **Struttura:** testo, azione (azioni: Retry)
- **Varianti nella pagina:** warning, con pulsante → `warning`
- **Classi di oggi:**
  - `onboarding-bootstrap-banner`: bg `bg-amber-50 dark:bg-amber-950/30`; border `border-amber-300 dark:border-amber-800`; body `text-amber-900 dark:text-amber-100`; action `button border-amber-400 hover:bg-amber-100 dark:border-amber-700 dark:hover:bg-amber-900/40`

### 2.3 Banner generico — `InfoBanner · RiskBetaBanner`

- **Dove:** 54 usi: schede delle impostazioni, form e Bulk delle transazioni, analisi del rischio (il banner «beta» è un InfoBanner con titolo).
- **File:** `lib/components/ui/feedback/InfoBanner.svelte · lib/components/risk/RiskBetaBanner.svelte`
- **Superficie:** dentro una card
- **Struttura:** titolo, testo, elenco, azione, chiusura ✕ (azioni: inline Sync FX button)
- **Varianti nella pagina:** info → `info`; info con titolo · RiskBetaBanner → `info`; info senza ✕ · suggerimento del Bulk → `info`; warning, con elenco e pulsante → `warning`; error → `danger`; success → `success`
- **Classi di oggi:**
  - `info-banner-info`: bg `bg-blue-50 dark:bg-blue-900/10`; border `border-blue-200 dark:border-blue-800/40`; title `(inherits) text-blue-700 dark:text-blue-200/60`; body `text-blue-700 dark:text-blue-200/60`; icon `text-blue-500 dark:text-blue-400/50`; action `dismiss ✕: opacity-60 hover:opacity-100`
  - `info-banner-warning`: bg `bg-amber-50 dark:bg-amber-900/10`; border `border-amber-200 dark:border-amber-800/40`; title `text-amber-700 dark:text-amber-200/60`; body `text-amber-700 dark:text-amber-200/60`; icon `text-amber-500 dark:text-amber-500/50`; action `dismiss ✕ opacity-60`
  - `info-banner-error`: bg `bg-red-50 dark:bg-red-900/10`; border `border-red-200 dark:border-red-800/40`; title `text-red-700 dark:text-red-200/60`; body `text-red-700 dark:text-red-200/60`; icon `text-red-500 dark:text-red-400/50`; action `dismiss ✕`
  - `info-banner-success`: bg `bg-emerald-50 dark:bg-emerald-900/10`; border `border-emerald-200 dark:border-emerald-800/40`; title `text-emerald-700 dark:text-emerald-200/60`; body `same`; icon `text-emerald-500 dark:text-emerald-400/50`; action `dismiss ✕`
  - `risk-beta-banner`: bg `= info-banner-info`; border `=`; title `font-semibold, same color`; body `=`; icon `=`
  - `tx-bulk-hint-info`: bg `= info-banner-info`; border `=`; body `=`; icon `=`

### 2.4 Esito del salvataggio delle transazioni — `TransactionResultBanner · TxBulkBanners`

- **Dove:** In cima all'editor Bulk e all'importazione: senza icona, l'emoji è nel titolo; le righe sono link che portano alla riga.
- **File:** `lib/components/transactions/shared/TransactionResultBanner.svelte · lib/components/transactions/bulk/TxBulkBanners.svelte`
- **Superficie:** dentro una card
- **Struttura:** titolo, testo, elenco, azione, chiusura ✕ (azioni: titleAction snippet; Sync FX button + per-row jump links; Sync FX + jump links)
- **Varianti nella pagina:** success → `success`; warning, con righe e pulsante → `warning`; error → `danger`
- **Classi di oggi:**
  - `tx-result-banner-success`: bg `bg-emerald-50 dark:bg-emerald-900/20`; border `border-emerald-200 dark:border-emerald-800/40`; title `text-emerald-700 dark:text-emerald-300 font-semibold`; body `same; subtitle opacity-80`; action `dismiss ✕ opacity-60`
  - `tx-result-banner-warning`: bg `bg-amber-50 dark:bg-amber-900/20`; border `border-amber-200 dark:border-amber-800/40`; title `text-amber-700 dark:text-amber-300`; body `same`; action `button bg-amber-100 dark:bg-amber-800/40 hover:bg-amber-200 dark:hover:bg-amber-700/50; row links underline`
  - `tx-result-banner-error`: bg `bg-red-50 dark:bg-red-900/20`; border `border-red-200 dark:border-red-800/40`; title `text-red-700 dark:text-red-300`; body `same`; action `button bg-red-100 dark:bg-red-800/40 hover:bg-red-200 dark:hover:bg-red-700/50`

### 2.5 Qualità dei dati — `DataQualityBanner`

- **Dove:** Pannelli del rischio e dell'insieme di asset: apribile, una riga per problema, chip per andare all'asset.
- **File:** `lib/components/ui/feedback/DataQualityBanner.svelte · toneClasses.ts STATUS_TONES.dataQuality`
- **Superficie:** dentro una card
- **Struttura:** titolo, testo, elenco, azione, apribile (azioni: per-issue CTA chip + asset nav chips; CTA chips; CTA chip)
- **Varianti nella pagina:** attention (oggi anche gli errori sono in ambra) → `warning`; info → `info`; riga compatta, una per problema → `warning`
- **Classi di oggi:**
  - `data-quality-banner-attention`: bg `bg-amber-50 dark:bg-amber-900/20`; border `border-amber-200 dark:border-amber-800`; title `text-amber-700 dark:text-amber-400 font-medium`; body `same, text-xs`; icon `currentColor`; action `chips bg-amber-100 dark:bg-amber-800/40 hover:bg-amber-200 dark:hover:bg-amber-700/40`
  - `data-quality-banner-info`: bg `bg-sky-50 dark:bg-sky-900/20`; border `border-sky-200 dark:border-sky-800`; title `text-sky-700 dark:text-sky-400`; body `same`; icon `currentColor`; action `bg-sky-100 dark:bg-sky-800/40 hover:bg-sky-200 dark:hover:bg-sky-700/40`
  - `data-quality-inline-row`: bg `as above per tone`; border `as above`; body `text-xs`; icon `currentColor`; action `chip as above`

### 2.6 Qualità dei dati dei lotti — `LotDataQualityBanner`

- **Dove:** Broker → analisi dei lotti: chip per saltare al lotto.
- **File:** `lib/components/brokers/lots/LotDataQualityBanner.svelte`
- **Superficie:** dentro una card
- **Struttura:** titolo, testo, elenco, azione, apribile (azioni: lot chips (jump to lot))
- **Varianti nella pagina:** warning (oggi anche gli errori sono in ambra) → `warning`; info → `info`
- **Classi di oggi:**
  - `lot-data-quality-banner`: bg `bg-amber-50 dark:bg-amber-900/20 | bg-sky-50 dark:bg-sky-900/20`; border `border-amber-200 dark:border-amber-800 | border-sky-200 dark:border-sky-800`; title `text-amber-700 dark:text-amber-400 | text-sky-700 dark:text-sky-400`; body `same`; icon `currentColor`; action `lot chips {styles.chip} (amber-100/sky-100)`

### 2.7 Risultati parziali del rischio — `RiskPartialNotice`

- **Dove:** Pannello dei livelli di rischio: le misure coinvolte in pillole.
- **File:** `lib/components/risk/levels/RiskPartialNotice.svelte`
- **Superficie:** dentro una card
- **Struttura:** titolo, elenco
- **Varianti nella pagina:** info → `info`; warning → `warning`
- **Classi di oggi:**
  - `risk-partial-notice-info`: bg `bg-blue-50 dark:bg-blue-950/30`; border `border-blue-200 dark:border-blue-900/50`; title `text-blue-800 dark:text-blue-300 font-medium`; body `same`; icon `currentColor`; action `chips border-blue-200 bg-white/70 dark:border-blue-900/60 dark:bg-slate-900/40 rounded-full`
  - `risk-partial-notice-warning`: bg `bg-amber-50 dark:bg-amber-950/30`; border `border-amber-200 dark:border-amber-900/50`; title `text-amber-800 dark:text-amber-300`; body `same`; icon `currentColor`; action `chips border-amber-200 bg-white/70 dark:border-amber-900/60 dark:bg-slate-900/40`

### 2.8 Avvisi dell'importazione nella finestra dell'asset — `AssetModalImportNotices`

- **Dove:** Finestra dell'asset aperta dall'importazione, un avviso per tipo.
- **File:** `lib/components/assets/AssetModalImportNotices.svelte`
- **Superficie:** dentro una card
- **Struttura:** titolo, testo, elenco
- **Varianti nella pagina:** warning, nella finestra dell'asset → `warning`
- **Classi di oggi:**
  - `asset-import-notice`: bg `bg-amber-50 dark:bg-amber-900/20`; border `border-amber-300 dark:border-amber-700/60`; title `text-amber-800 dark:text-amber-300 text-xs font-semibold`; body `list text-amber-700 dark:text-amber-200/90; footer text-amber-600 dark:text-amber-300/70`; icon `amber (title row)`

### 2.9 Note del plugin d'importazione — `BrimNoticeList`

- **Dove:** Wizard d'importazione e dettaglio dell'analisi: **senza riquadro**, testo colorato direttamente sulla card.
- **File:** `lib/components/transactions/import/BrimNoticeList.svelte`
- **Superficie:** dentro una card
- **Struttura:** testo, elenco, apribile
- **Varianti nella pagina:** info, senza riquadro → `info`; warning, senza riquadro, con le righe del file → `warning`
- **Classi di oggi:**
  - `brim-notice-list`: bg `none`; border `none`; body `text-sky-800 dark:text-sky-300 | text-amber-700 dark:text-amber-400`; icon `text-sky-600 dark:text-sky-400 | text-amber-600 dark:text-amber-400`; action `collapsible evidence table`

### 2.10 Pianificatore PAC — `StateNotice · StaleBanner · RefreshNotice · CopyNotice`

- **Dove:** Strumento PAC: esiti del calcolo, risultato vecchio, dati riletti, copia eseguita. Pulsanti secondari neutri e link.
- **File:** `lib/features/tools/pac-allocator/planner/result/*.svelte · toneClasses.ts STATUS_TONES.pacNotice`
- **Superficie:** dentro una card
- **Struttura:** titolo, testo, elenco, azione, chiusura ✕, badge (azioni: secondary buttons/links; Edit configuration; Back to Review / Discard the previous result; Close link)
- **Varianti nella pagina:** StateNotice · info → `info`; StateNotice · warning → `warning`; StateNotice · danger → `danger`; StaleBanner · warning → `warning`; RefreshNotice · info → `info`; CopyNotice · success → `success`
- **Classi di oggi:**
  - `pac-notice-info|warning|danger|success`: bg `bg-{sky,amber,red,emerald}-50 dark:bg-{…}-950/30`; border `border-{…}-200 dark:border-{…}-900`; title `text-{…}-900 dark:text-{…}-100 font-semibold`; body `same`; action `BUTTON_SECONDARY; BUTTON_LINK text-libre-green hover:underline; HINT text-gray-500 dark:text-gray-400`
  - `pac-state-notice`: bg `pacNotice.*`; border `=`; title `=`; body `=`; action `BUTTON_SECONDARY 'Edit configuration'; BUTTON_LINK go-to`
  - `pac-stale-banner`: bg `pacNotice.warning`; border `=`; title `=`; body `=`; action `2× BUTTON_SECONDARY`
  - `pac-refresh-notice`: bg `pacNotice.info|warning`; border `=`; body `=`; icon `RefreshCw in neutral badge`
  - `pac-copy-notice`: bg `pacNotice.success|warning`; border `=`; title `= font-medium`; body `=`; icon `Clock in neutral badge`; action `BUTTON_LINK Close`

### 2.11 Riquadri in linea — `classi Tailwind scritte nei componenti`

- **Dove:** 61 riquadri sparsi (editor dei cambi, coppie di transazioni, strumenti, PAC, lotti, finestre): solo testo, a volte con icona.
- **File:** `FxDataEditorSection · TxFormPairSection · ToolHost · ToolDiagnosticsPanel · RoutingStep · BrokerSharingPanel · WelcomePage · UnifiedLotsTable …`
- **Superficie:** dentro una card
- **Struttura:** testo
- **Varianti nella pagina:** rosso · 25 riquadri → `danger`; ambra · 16 riquadri → `warning`; smeraldo e verde · 8 riquadri → `success`; blu e azzurro · 12 riquadri → `info`
- **Classi di oggi:**
  - `inline-red-900-20-box`: bg `bg-red-50 dark:bg-red-900/20`; border `border-red-200 dark:border-red-800`; body `text-red-600 dark:text-red-400`
  - `inline-red-950-30-box`: bg `bg-red-50 dark:bg-red-950/30`; border `border-red-200|300 dark:border-red-900`; body `text-red-700|800 dark:text-red-200`
  - `inline-amber-950-box`: bg `bg-amber-50 dark:bg-amber-950/30|40`; border `border-amber-200 dark:border-amber-900`; body `text-amber-900 dark:text-amber-100|200`
  - `inline-amber-900-20-box`: bg `bg-amber-50 dark:bg-amber-900/20`; border `border-amber-200 dark:border-amber-800`; body `text-amber-700 dark:text-amber-400`; icon `AlertTriangle (flex items-center)`
  - `inline-emerald-box`: bg `bg-emerald-50 dark:bg-emerald-950/30 | dark:bg-emerald-900/20`; border `border-emerald-200 dark:border-emerald-900`; body `text-emerald-800 dark:text-emerald-200`
  - `inline-green-success`: bg `bg-green-50 dark:bg-green-900/20`; border `green-200/800`; body `green-700/300`
  - `inline-blue-info-box`: bg `bg-blue-50 dark:bg-blue-900/20`; border `border-blue-200 dark:border-blue-800`; body `text-blue-700 / text-gray-600 dark:text-gray-300`
  - `inline-sky-info-box`: bg `bg-sky-50 dark:bg-sky-900/20`; border `sky-200/800`; body `sky-700/400`

## Come rispondere

Basta un messaggio con queste parti; quello che va bene si può saltare.

```text
Toast: pieno / tenue / altro: …
Chip e pulsanti nei banner: a) / b) / altro: …
Errori della qualità dei dati: restano avviso (ambra) / diventano rosso
Famiglia 2.x: va bene / da cambiare: … (ruolo, tema, nuovo valore)
Altro: …
```

Per un colore nuovo, scrivi il ruolo (per esempio `warning-soft`, scuro) e l'esadecimale: il contrasto lo controlliamo noi.

## Per lavorare con l'IA

Puoi allegare questo file e scrivere, per esempio:

> Ti allego i dati dei toast e dei banner di un'app, con i miei colori nei due temi. Aiutami a rispondere alle tre domande
> aperte e a controllare, famiglia per famiglia, se i colori sono coerenti tra tema chiaro e scuro. Per ogni valore che
> proponi di cambiare, dammi il ruolo, il nuovo esadecimale e il contrasto WCAG con il suo fondo (testo ≥ 4,5:1, icona ≥ 3:1).
