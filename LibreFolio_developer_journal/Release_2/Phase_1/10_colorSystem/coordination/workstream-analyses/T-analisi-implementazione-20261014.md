# T — Token e tema · analisi d'implementazione (14/10/2026, sera)

> Stato: **FROZEN**, solo analisi. Nessun file del repo modificato; nessun build, test, server o `npm ci` (finestra di
> quiete di G fino alle 22:45 rispettata). Il codice parte solo con l'autorizzazione del developer, inoltrata alla
> lettera dal coordinatore (`aec04834-1532-4d86-9e3f-f942e82aca89`).
> Piano nel repo, da creare dopo l'autorizzazione:
> `LibreFolio_developer_journal/Release_2/Phase_1/10_colorSystem/T-tokensTheme/plan-phase01TokensTheme.prompt.md`.

## 0. In breve

- **Base verificata:** HEAD = `d9aec01936fe7207f1fa118558ce36dcafc90748` = baseline del kickoff, worktree pulito.
  R (lotti A e B) e L **non** sono nella baseline (`merge-base --is-ancestor`): niente `lib/theme/`, niente gate della
  meta, niente Designer Lab. Ne tengo conto nell'ordine dei passi.
- **Architettura:** ruoli `--lf-<gruppo>-<nome>` in `lib/theme/tokens.css` (chiaro su `:root, html.light`, scuro su
  `html.dark, .dark`), esposti come utility da `@theme inline { --color-lf-<nome>: var(--lf-…) }`: `bg-lf-card`,
  `text-lf-muted`, `border-lf-input`, `bg-lf-action`… Il tema scuro passa dalle variabili: **mai `dark:` sui ruoli**.
  Nessuna ritintura delle scale Tailwind né del bianco (D-T3).
- **P1 sui componenti migrati:** le regole per classe (`.bg-white`, `.text-gray-*`…) non li toccano; le quattro regole
  **strutturali** sì (`input/select/textarea`, `::placeholder`, `.rounded-xl/2xl`, `option`): batterebbero bordo, focus,
  placeholder e bordo delle card. Soluzione: un'eccezione `:where(:not([class*='-lf-']))`, che **non cambia la
  specificità**, quindi i componenti non migrati restano identici al pixel. Un layer, invece, cambierebbe l'aspetto di
  centinaia di elementi legacy (§2.2).
- **B1 (fondamenta) non cambia nessun pixel:** nessun elemento porta oggi classi `-lf-` (verificato), e le utility dei
  ruoli entrano nel CSS solo quando qualcuno le usa. Si prova sul CSS compilato.
- **Rimasti indietro visibili:** nel build, un gate a cricchetto (classi di palette e colori letterali per file, solo in
  discesa, più una grammatica dei ruoli); nel rendering, la gallery: le parti migrate sono calde, le altre conservano
  l'aspetto di oggi.
- **Piloti:** accesso (icone, via il sottotitolo, box dei requisiti, card, chiave i18n) e shell (barra laterale verde
  della testata nei due temi, sfondo app `#F1EDE3`/`#131A17`, header), solo classi nei file condivisi. Meta della PWA,
  manifest e splash dopo l'ingresso del lotto A di R, che porta il gate della meta.
- **Contrasti:** oltre ai 5 punti di `analisi.md` §3, la decisione D-T2 (sfondo app) e la superficie secondaria ne
  aggiungono 3. Correzioni minime proposte (solo luminosità OKLCH), **non applicate** senza OK (§3.5).
- **Decisioni richieste:** §13. Bloccanti per partire: nomi (D-T4), spazio colore (D-T5), correzioni di contrasto
  (D-T6), regole del gate (D-T8), file extra dei piloti (D-T9).

## 1. Base, corsia, ambiente

| Voce | Valore |
|---|---|
| Worktree | `/Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-expert-barnacle` |
| Branch | `e-alfy-t-tokens-theme` (rinominato dall'app su richiesta di avvio; era `e-alfy-expert-barnacle`) |
| HEAD | `d9aec01936fe7207f1fa118558ce36dcafc90748` = baseline ✅ (worktree pulito) |
| Destinazione | `dev_release2` (locale ora a `410e68ee2`: un commit di documenti del coordinatore dopo la baseline) |
| Corsia | porta **6155**, dati **`/tmp/librefolio-r2-t`**; non usata (finestra di quiete) |
| Ambiente | `node_modules` assente (atteso); graphify assente (atteso): lette direttamente le pagine wiki F-007, F-098, `domains/layout-settings` |
| Fuori baseline | R lotto A `d80b9e0cd`, lotto B `75c45d923` (branch `e-alfy-r-fattorizzazione-colori`), L `6e967202e` (branch `e-alfy-designer-lab`): letti solo come oggetti git, in sola lettura |

Wiki: F-007 dice ancora che i grafici seguono il tema con «store reattivi» (sono `MutationObserver`, drift già noto);
F-098 lega la meta `theme-color` alla barra laterale. Nient'altro di rilevante sui colori.

## 2. Verifica sul codice

### 2.1 Dove vive oggi ogni ruolo: conferme e correzioni ad `analisi.md` §1

La tabella di `analisi.md` §1 regge. Correzioni e dati nuovi:

1. **`.animated-bg-gradient` in `app.css` è codice morto**: nessun file lo usa. Lo sfondo del login vive tutto in
   `ui/AnimatedBackground.svelte` (di G): `.animated-bg` `#f5f4ef`/`#11151c`, colline `#9caf9c`/`#00ff9a` (opacità .25,
   .18, .12), linee `#1a4031`/`#4ade80` (opacità animata fino a .15). Si toglie in B1, senza effetti.
2. **`hover:bg-opacity-90` dei pulsanti di login e registrazione non esiste in Tailwind v4** (utility rimossa): oggi
   il pulsante non ha hover. Il pilota lo sostituisce con il ruolo `action-hover`.
3. **Le card di accesso sono «solo chiaro»** (nessun `dark:`): in scuro il loro aspetto viene tutto da P1. Card
   `bg-libre-beige` → `#0f172a`; campi `#546175`; testi `text-libre-dark` → `#f8fafc`. Nel box dei requisiti
   `text-green-700`/`text-green-600` non sono rimappati: è il testo poco leggibile che la designer ha visto.
4. **`bg-libre-beige` ha tre significati:**
   - sfondo app o pagina: 6 rami del layout `(app)`, Header, benvenuto, `ServerUnreachable`, blocchi d'onboarding;
   - card: Login, Register, Forgot, `+error`;
   - corpo di modale: AskAdmin, UpdateAvailable, DonationPopup, SocialShare.

   Nella conversione serve il contesto (§4.2).
5. **Meta `theme-color`:** tre scrittori (`app.html` anti-FOUC, `themeStore.applyTheme`, `static/offline.html`) più
   `manifest.json`. Il lotto A di R (fuori baseline) corregge `#156534`→`#166534` in quei tre file e aggiunge
   `src/themeColorMeta.gate.test.ts`. La sua regola (b) fissa la coppia `#1a4031`/`#166534`; la (d) legge
   `--color-libre-green` di `@theme` e `html.dark .bg-libre-green` di `app.css`. Quando la barra passa al ruolo
   `brand`, T riscrive (b) e (d) (§5.3).
6. **Splash (`app.html`):** `#f5f4ef`/`#0f172a`, riquadro del logo `#fff`, spinner `#1a4031`/`#86efac`.
   **`offline.html`:** una palette propria di 16 variabili, con lo sfondo scuro `#11151c`.
7. **`PasswordInput` e `PasswordStrength` si usano anche in `settings/PasswordChangeModal.svelte`:** il pilota li
   cambia anche lì (campi coi ruoli in una modale legacy).
8. **`RegisterCard` usa `ui/feedback/InfoBanner`** (lotto A di R): nel pilota resta legacy.
9. **Controlli dell'header** (classi colore per file): `ThemeToggle` 1 riga, `PrivacyToggle` 1, `LanguageSelector` 4,
   `HelpMenu` 17 (A ci aggiungerà una condizione), `ConnectionSecurityIndicator` 5 (sta nella barra laterale).
10. **Test che fissano classi di colore:**
    - Vitest, 5 file: `TransactionFormModal`, `AssetTable`, `RiskMetricCard`, `KpiDivergingFlowBar`, `KpiMetricBar`;
    - E2E, 5 punti: `asset-data-editor`, `asset-list` (`bg-white` e `dark:bg-slate-800`), `fx-list`, `tx-wac-mode`
      (`bg-libre-green`).

    Nessuno riguarda accesso o layout. Si aggiornano nelle rispettive ondate, meglio passando a `data-*`/`aria-*`.
11. **Nessuna classe in `src` contiene oggi `-lf-`** (grep): l'eccezione del §2.2 non colpisce niente per caso.
12. **Numeri sull'albero attuale** (file di produzione):
    - ~9.965 classi di palette con gradino, più 643 `white`/24 `black` e ~800 `libre-*`, in **276 file**;
    - 4.843 varianti `dark:`.

    Per area:

    | Area | Classi | Area | Classi |
    |---|---:|---|---:|
    | `components/transactions` | 2.165 | `components/dashboard` | 350 |
    | `components/ui` | 1.116 | `routes/(app)/fx` | 227 |
    | `components/brokers` | 889 | `features/onboarding` | 182 |
    | `components/assets` | 862 | `components/layout` | 161 |
    | `features/tools` | 845 | `components/fx` | 159 |
    | `components/settings` | 786 | `routes/(app)/brokers` | 139 |
    | `components/risk` | 732 | `lib/utils` | 120 |
    | `routes/(app)/assets` | 464 | `components/auth` | 82 |
    | `components/charts` | 369 | `features/ai-export` | 78 |

    Le altre aree hanno meno di 70 classi ciascuna (support, table, files, routes minori).

### 2.2 Cosa fa P1 ai componenti migrati

Le regole scure di `app.css` stanno fuori dai layer; le utility di Tailwind stanno in `@layer utilities`. Una regola
fuori dai layer vince su qualunque utility, a prescindere dalla specificità.

| Regola P1 | Tipo | Effetto su un componente migrato |
|---|---|---|
| `html.dark .bg-white`, `.bg-gray-50/100`, `.text-gray-400…900`, `.border-gray-100/200`, `.hover:bg-gray-50/100`, `.bg-libre-beige`, `.bg-surface-100`, `.text-libre-dark`, `.text-libre-green`, `.bg-white/90,95`, `.focus:ring-libre-green`, `.bg-libre-green` | per classe | **nessuno**: il componente migrato non porta più quelle classi |
| `html.dark input, select, textarea { border-color:#546175; color }` | strutturale | **sì**: `border-lf-input`, `focus:border-lf-focus` e il colore del testo perdono. Il campo resta `#546175` e il focus non si vede |
| `html.dark input::placeholder, textarea::placeholder` | strutturale | **sì**: `placeholder:text-lf-placeholder` perde |
| `html.dark .rounded-xl, .rounded-2xl { border-color }` | strutturale | **sì**: la card di login (`rounded-2xl border-lf-subtle`) e ogni avviso con `border-lf-danger-line` prenderebbero `#334155` |
| `html.dark option` | strutturale | **sì**: opzioni ardesia nei select migrati |
| `html.dark .shadow*` (`--tw-shadow`) | geometria | ombre più scure in scuro, uguali per tutti: si tiene |
| `html.dark body { background; color }` | eredità | il testo che eredita resta `#f8fafc` fino a B6: un componente migrato imposta il proprio ruolo di testo alla radice |

**Soluzione: eccezione, non layer né rimozione.**

- Le quattro regole strutturali ricevono `:where(:not([class*='-lf-']))`. Per esempio
  `html.dark input:where(:not([class*='-lf-']))` e `html.dark option:where(:not(select[class*='-lf-'] option))`.
  - `:where()` vale zero, quindi la specificità resta (0,1,2) e (0,2,1).
  - Con un `:not()` nudo sarebbe salita a (0,2,2), sopra il CSS con scope dei componenti Svelte (0,2,0). I campi
    legacy stilizzati nei `<style>` (filtri di `DataTable`, modali dei file) avrebbero cambiato bordo in scuro.
  - Gli elementi legacy restano identici; un elemento migrato porta almeno una classe `-lf-` e ne esce.
- **Perché non un layer.** Spostate in un layer sotto le utility, le regole strutturali farebbero vincere le classi
  scritte: i campi legacy con il solo `border-gray-300` diventerebbero chiari in scuro, e ~100 contenitori arrotondati
  cambierebbero bordo. È contro D-T3.
- **Rimozione:** ogni regola per classe si toglie quando la sua classe arriva a zero (il gate segnala le regole morte,
  §4.6). Le regole strutturali, le `--theme-*` e `body` si tolgono in B6.
- **Conseguenza per i migratori: un elemento si migra tutto o niente.** Una classe di ruolo accanto a una classe
  legacy farebbe uscire l'elemento da P1 con metà dei colori vecchi. Il gate lo vieta (G3, §4.6).

## 3. Architettura

### 3.1 Tre livelli

1. **Ruoli** (`frontend/src/lib/theme/tokens.css`, nuovo, unico scrittore T). I valori della designer stanno sui
   selettori che usano già le `--theme-*`, così lo scanner di L li legge come oggi:
   - `:root, html.light { … }` per il chiaro;
   - `html.dark, .dark { … }` per lo scuro (`.dark` serve per un sotto-albero forzato, come il campionario);
   - i ruoli derivati (`color-mix`) in un blocco `:root, .light, .dark { … }`, così ogni sotto-albero li ricalcola
     con i propri valori di base.
2. **Utility**: `@theme inline { --color-lf-<nome>: var(--lf-<gruppo>-<nome>); }`, nello stesso file. `tokens.css`
   è importato da `app.css` subito dopo `@import 'tailwindcss'`.
   - **`inline`**: l'utility scrive direttamente `var(--lf-…)`. Così un override su un sotto-albero o del Lab vale
     anche dentro. È la forma che la documentazione di Tailwind raccomanda quando una variabile del tema ne richiama
     un'altra.
   - **Namespace `--color-*`**, documentato: ogni ruolo vale per `bg`, `text`, `border`, `ring`, `ring-offset`,
     `outline`, `divide`, `fill`, `stroke`, `placeholder`, `from/via/to`, `accent`, `caret`, `decoration`.
   - Tailwind 4.1.18 ha anche namespace per utility (`--background-color-*`, `--text-color-*`, verificati nel
     sorgente), ma non sono documentati: non li uso. I nomi delle utility sono quindi **unici su tutti i gruppi**
     (§3.2).
   - Trasparenze: `bg-lf-card/90` diventa `color-mix(in oklab, var(--lf-surface-card) 90%, transparent)`.
3. **Componenti**: solo utility `*-lf-*`; mai `dark:` sui ruoli; un `border` dichiara sempre il colore del suo ruolo
   (in v4 il bordo di default è `currentColor`).

Restano intatti, finché ci sono classi che li usano: le scale di Tailwind, il bianco, le `--theme-*`, i
`--color-libre-*` con i valori scuri di `html.dark`, `primary-*`, `surface-*`.

### 3.2 Tabella ruolo → utility (per la 1.3 e per i migratori)

Fonte: **D** = designer, giro 1; **D-T2** = decisione del developer; **der.** = derivato solo da valori della
designer, in attesa del giro 2; **→** = correzione di contrasto proposta, §3.5, non applicata.

**Superfici**

| Ruolo | Variabile | Utility | Chiaro | Scuro | Fonte |
|---|---|---|---|---|---|
| Sfondo dell'app (shell, header) | `--lf-surface-app` | `bg-lf-app` | `#F1EDE3` | `#131A17` | D-T2 |
| Sfondo di pagina autonoma (login, errore, offline) | `--lf-surface-page` | `bg-lf-page` | `#F7F4ED` | `#0F1412` | D |
| Card, modale, superficie 1 | `--lf-surface-card` | `bg-lf-card` | `#FBF8F1` | `#171F1C` | D |
| Superficie secondaria (pannelli, intestazioni di tabella, box interni) | `--lf-surface-panel` | `bg-lf-panel` | `#EEE9DE` | `#1E2824` | D |
| Fondo dei campi | `--lf-surface-field` | `bg-lf-field` | `#FBF8F1` | `#121815` | D |
| Hover di righe e voci | `--lf-surface-hover` | `hover:bg-lf-hover` | = panel | = panel | der. |
| Neutro pieno (tracce, scheletri, chip neutri) | `--lf-surface-neutral` | `bg-lf-neutral` | = bordo `#DDD5C7` | = bordo `#26312C` | der. |
| Inverso (tooltip) | `--lf-surface-inverse` | `bg-lf-inverse` | = testo primario | = testo primario | der. |
| Fondale delle modali | `--lf-surface-overlay` | `bg-lf-overlay` | `#0F1412` al 60% | `#0F1412` al 60% | der. (oggi `slate-900/70` e `black/50`) |
| Riquadro del logo | `--lf-surface-logo` | `bg-lf-logo` | `#FFFFFF` | `#FFFFFF` | oggi, e nei render |

**Testi**

| Ruolo | Variabile | Utility | Chiaro | Scuro | Fonte |
|---|---|---|---|---|---|
| Primario | `--lf-text-primary` | `text-lf-primary` | `#292D27` | `#EAE6DF` | D |
| Secondario | `--lf-text-secondary` | `text-lf-secondary` | `#555C53` | `#A8B0A8` | D |
| Attenuato (anche disabilitato) | `--lf-text-muted` | `text-lf-muted` | `#687066` → `#636B61` | `#758078` → `#848F87` | D |
| Placeholder | `--lf-text-placeholder` | `placeholder:text-lf-placeholder` | = attenuato | = attenuato | D (nota della designer: l'attenuato vale «per placeholder e testi disabilitati») |
| Su inverso | `--lf-text-on-inverse` | `text-lf-on-inverse` | = card | = card | der. |

**Bordi**

| Ruolo | Variabile | Utility | Chiaro | Scuro | Fonte |
|---|---|---|---|---|---|
| Bordo, divisori | `--lf-border-subtle` | `border-lf-subtle`, `divide-lf-subtle` | `#DDD5C7` | `#26312C` | D |
| Bordo dei campi | `--lf-border-input` | `border-lf-input` | `#B9AE9B` → `#978C7A` | `#38463F` → `#5D6C64` | D |

**Marchio e interazione**

| Ruolo | Variabile | Utility | Chiaro | Scuro | Fonte |
|---|---|---|---|---|---|
| Verde marchio: testate, barra laterale, barra della PWA | `--lf-brand` | `bg-lf-brand` | `#1B4334` | `#1B4334` | D, D-T2 |
| Testo e icone sul marchio | `--lf-on-brand` | `text-lf-on-brand`, `border-lf-on-brand/20`, `bg-lf-on-brand/10` | = card `#FBF8F1` | = primario `#EAE6DF` | der. («avorio»), 10,4:1 e 8,9:1 |
| Azione (pulsante primario) | `--lf-action` | `bg-lf-action` | `#1B4334` | `#245A46` | D |
| Azione, hover | `--lf-action-hover` | `hover:bg-lf-action-hover` | `#245A46` | `#2D6E56` | D (scuro); der. (chiaro: un mezzo tono più luminoso, come il 90% di oggi) |
| Testo sull'azione | `--lf-on-action` | `text-lf-on-action` | = card | = primario | der., ≥ 4,9:1 |
| Focus | `--lf-focus` | `ring-lf-focus`, `border-lf-focus`, `outline-lf-focus` | `#236B4D` | `#469E76` | D |
| Link attivi | `--lf-link` | `text-lf-link` | = focus | = focus | D («Focus, link attivi») |
| Fondo selezionato | `--lf-selected` | `bg-lf-selected` | focus al 12% | focus al 12% | der. (oggi `bg-libre-green/10`, `dark:bg-libre-green/20`) |

**Stati**: X = `success`, `warning`, `danger`, `info`.

| Ruolo | Variabile | Utility | Chiaro | Scuro | Fonte |
|---|---|---|---|---|---|
| Stato: testo, icona, pieno | `--lf-X` | `text-lf-X`, `bg-lf-X` | `#18794E` `#895000` `#B42332` `#155EEF` | `#3DD68C` `#F5A623` `#F25F5C` `#5899FA` | D |
| Fondo tenue | `--lf-X-soft` | `bg-lf-X-soft` | `color-mix(in oklab, X 8%, card)` | `color-mix(in oklab, X 6%, card)`; per il successo, `#1A2822` | der. (6% riproduce `#1A2822`: ottiene `#1B2822`) |
| Bordo tenue | `--lf-X-line` | `border-lf-X-line` | X 25% sulla card | X 22% sulla card; per il successo, `#284237` | der. |
| Testo sul fondo tenue | `--lf-X-on-soft` | `text-lf-X-on-soft` | X 60% sul primario («verde scuro») | X 37% sul primario; per il successo, `#B8D8C8` | der. |
| Testo su stato pieno | `--lf-on-status` | `text-lf-on-status` | = card (≥ 5,1:1) | = card `#171F1C` (≥ 5,3:1) | der. |

**Semantica di dominio**

| Ruolo | Variabile | Utility | Chiaro | Scuro | Fonte |
|---|---|---|---|---|---|
| Guadagno, perdita | `--lf-gain`, `--lf-loss` | `text-lf-gain`, `text-lf-loss` | = successo, = errore | idem | D, salvo decisione diversa (B2) |
| Donazione («Offrimi un caffè») | `--lf-donate` | `text-lf-donate` | = avviso | = avviso | D («perfetta anche per il link») |

**Illustrazione del login** (dopo G, solo variabili, nessuna utility)

| Ruolo | Variabile | Chiaro | Scuro | Fonte |
|---|---|---|---|---|
| Tre colline | `--lf-art-hill-1/2/3` | salvia di oggi (`#9CAF9C` a 25/18/12%) | `#14241E`, `#192E26`, `#1F382F` | D |
| Linee | `--lf-art-line` | marchio al 15% | `#284238` | D |

Grafici (`--lf-chart-*`) e categoriali (`--lf-cat-*`) arrivano con B4, sul giro della designer.

### 3.3 Ruoli mancanti, in attesa della designer

- **Regola:** un ruolo derivato si calcola solo da valori della designer, con un riferimento (`var()`) o un
  `color-mix(in oklab, …)`. Nessun hex nuovo. Il Lab li modifica come gli altri, e cambiare un ruolo di base aggiorna
  i suoi derivati.
- **Dove la designer ha dato valori espliciti, vincono sulla formula:** box dei requisiti in scuro (`#1A2822`,
  `#284237`, `#B8D8C8`); placeholder e disabilitato = attenuato.
- **Ancora aperti per il giro 2:**
  - hover e premuto in chiaro;
  - fondale delle modali;
  - inverso;
  - tinte di avviso, errore e informazione;
  - guadagno e perdita distinti;
  - la barra a 5 livelli della robustezza della password (D-T13).

### 3.4 Spazio colore (P11)

**Raccomandazione (D-T5): hex sRGB** per i valori della designer, **`color-mix(in oklab, …)`** per i derivati.

- I suoi valori sono hex e stanno in sRGB: conservarli tali evita gli arrotondamenti di un'andata e ritorno in OKLCH.
- OKLCH servirebbe solo per colori fuori sRGB, che oggi nessuno chiede.
- I token accettano qualunque colore CSS: se il Lab esporta OKLCH, `tokens.css` lo accetta.
- **Grafici (B4):** `getComputedStyle` restituisce la stringa del token (`color-mix(…)` o `oklch(…)`), che ECharts non
  sa calcolare. Il ponte di `chartTheme` converte ogni ruolo in sRGB con un canvas 2D (`fillStyle`), in cache per
  revisione del tema.
- Le classi legacy restano in OKLCH fino alla loro migrazione: la divergenza P11 sparisce con le ondate.

### 3.5 Contrasti: correzioni minime proposte, non applicate

WCAG 2.2: testo 4,5:1, componenti 3:1. Stesso tono e croma OKLCH, cambia solo la luminosità.

| Coppia | Valore della designer | Contrasto oggi | Proposta | Dopo |
|---|---|---|---|---|
| Chiaro · attenuato su **app** e su pannello (nuovo: D-T2) | `#687066` | 4,38 / 4,23 | `#636B61` | 4,72 / 4,56 |
| Scuro · attenuato su pannello, card e box dei requisiti `#1A2822` | `#758078` | 3,70 / 4,09 / 3,73 | `#848F87` | 4,52 / 5,01 / 4,57 |
| Chiaro · bordo dei campi su card e campo | `#B9AE9B` | 2,06 | `#978C7A` | 3,12 |
| Scuro · bordo dei campi su card e campo | `#38463F` | 1,69 / 1,81 | `#5D6C64` | 3,04 / 3,25 |
| Chiaro · successo e info su pannello | `#18794E`, `#155EEF` | 4,47 | `#17784D`, `#145DEE` (invisibili), oppure si evita il testo piccolo sul pannello | ≥ 4,5 |
| (nuovo) campi posati direttamente su app o pannello | `#978C7A` / `#5D6C64` | 2,83 / 2,73 (chiaro), 2,74 (scuro) | `#8F8573` / `#64736B`, se servono | 3,0 |
| (nuovo) barra laterale: email e versione, oggi `white/50` e `white/40` | — | 3,9 / 3,0 | `on-brand/70` | 6,0 |

Passano con margine: primario 12–15:1; secondario ≥ 5,7:1; focus e link ≥ 4,6:1 su ogni superficie; avviso ed errore
≥ 5,4:1 in chiaro e ≥ 4,7:1 in scuro; testo sul marchio e sull'azione ≥ 4,9:1.

Da sapere, non da correggere per forza: `#245A46` sulla card scura ha 2,1:1 (il pulsante si riconosce dal testo, 7,5:1).

**Proposta D-T6:** applicare subito le correzioni minime in `tokens.css`, commentate con il valore originale, e farle
confermare alla designer nel giro 2. In alternativa, i suoi valori così come sono, con un elenco di eccezioni nel test
dei contrasti (§7).

### 3.6 Cosa contiene B1, e perché non cambia un pixel

- `lib/theme/tokens.css` (nuovo): ruoli chiari, scuri e derivati; `@theme inline` con la tabella del §3.2; in testa,
  il contratto (regole d'uso, nessun `dark:`, rimandi).
- `app.css`:
  - `@import './lib/theme/tokens.css'`;
  - eccezioni `:where(:not([class*='-lf-']))` sulle quattro regole strutturali;
  - via `.animated-bg-gradient`, morto;
  - una sezione «P1 legacy» con la regola di ritiro.
- Gate e test (§4.6, §7); istruzioni per gli agenti (§13, D-T12).
- **Prova:**
  - nessun elemento porta classi `-lf-`, quindi le eccezioni non escludono nulla;
  - le utility dei ruoli non entrano nel CSS finché non si usano;
  - il CSS compilato prima e dopo differisce solo per le variabili `--lf-*` e per il testo dei quattro selettori.

  Diff del CSS compilato come evidenza; la gallery di controllo si fa insieme a quella dei piloti.

## 4. Strategia di migrazione di tutto il frontend

### 4.1 Unità di lavoro

- **L'unità è il file:** tutte le classi colore di un componente in un colpo solo, tutto o niente per elemento.
- **Un lotto per sotto-agente:** ≤ 15 file e ≤ ~400 classi, presi da una sola cartella.
- **Il sotto-agente** (`general-purpose`, con la skill di migrazione, D-T12) modifica solo i file del suo lotto. Non
  esegue test, build né server: la corsia è una sola e i comandi non vanno in parallelo.
- **T** riesamina il diff, esegue in serie gate, `svelte-check`, Prettier e i test dei componenti toccati, poi chiede
  al coordinatore la gallery dell'ondata.
- Nei file condivisi con la 1.3 (shell, Header, HelpMenu): **solo classi**, nessun riordino del markup.

### 4.2 Tabella di conversione (classe → ruolo)

Si converte per **significato e gradino**, non per famiglia: `gray` e `slate` vanno agli stessi ruoli.

| Oggi (chiaro + scuro) | Ruolo | Note |
|---|---|---|
| `bg-white` + `dark:bg-slate-800/900`, `gray-800` (card, modali, menu, dropdown) | `bg-lf-card` | 318 `bg-white` |
| `bg-white` su campi | `bg-lf-field` | |
| `bg-white/90`, `/95` (sticky, header di modale) | `bg-lf-card/90` | |
| `bg-gray-50`, `bg-gray-100`, `bg-slate-50` + `dark:bg-slate-700/800/900` | `bg-lf-panel` | i due gradini si fondono: se servono due livelli, `panel` + `hover` |
| `bg-gray-200` (tracce, scheletri, chip neutri) | `bg-lf-neutral` | |
| `hover:bg-gray-50/100` + `dark:hover:bg-slate-700/600` | `hover:bg-lf-hover` | 291 + 303 |
| `bg-libre-beige` | per contesto: `bg-lf-app` (shell), `bg-lf-page` (pagina autonoma), `bg-lf-card` (card, corpo di modale) | §2.1, punto 4 |
| `bg-black/45–50`, `bg-slate-900/30–70`, `bg-gray-900/40–50` (fondali) | `bg-lf-overlay` | |
| `bg-gray-900 text-white` (tooltip) | `bg-lf-inverse text-lf-on-inverse` | |
| `text-gray-900/800`, `text-libre-dark` + `dark:text-gray-100/200`, `white`, `slate-100` | `text-lf-primary` | |
| `text-gray-700/600` + `dark:text-gray-300/200` | `text-lf-secondary` | |
| `text-gray-500/400` + `dark:text-gray-400/500` | `text-lf-muted` | `gray-400` è a 2,5:1 oggi: diventa AA |
| `text-gray-300` (icone decorative) | `text-lf-muted` | |
| `placeholder-gray-*`, `placeholder:text-gray-*` | `placeholder:text-lf-placeholder` | |
| `border-gray-100/200` + `dark:border-slate-700/600`, `gray-700` | `border-lf-subtle` | `divide-*` uguale |
| `border-gray-300/400` sui campi + `dark:border-slate-600` | `border-lf-input` | sui separatori: `border-lf-subtle` |
| `bg-libre-green text-white hover:bg-libre-green/90` (pulsante primario) | `bg-lf-action text-lf-on-action hover:bg-lf-action-hover` | |
| `bg-libre-green` su testate, banner, barra laterale | `bg-lf-brand text-lf-on-brand` | |
| `text-libre-green` (link, accenti) + `dark:text-green-400` | `text-lf-link` | |
| `bg-libre-green/10` + `dark:bg-libre-green/20` (selezione) | `bg-lf-selected` | |
| `focus:ring-libre-green`, `focus:border-libre-green`, `focus-visible:outline-libre-green` | `…-lf-focus` | |
| `text-white`, `border-white/N`, `bg-white/N` su superfici verdi | `text-lf-on-brand`, `border-lf-on-brand/N`, `bg-lf-on-brand/N` | |
| Stato `red`/`rose`, `amber`/`yellow`/`orange`, `emerald`/`green`, `blue`/`sky`: testo 500–700 + `dark:` 300–400 | `text-lf-<stato>` | |
| Stato: fondo 50–100 + `dark:` 900/20–40 | `bg-lf-<stato>-soft` | |
| Stato: bordo 200–400 + `dark:` 700–800 | `border-lf-<stato>-line` | |
| Stato: testo 800–900 sul fondo tenue + `dark:` 100–200 | `text-lf-<stato>-on-soft` | |
| Stato pieno `bg-<stato>-500/600 text-white` | `bg-lf-<stato> text-lf-on-status` | |
| Segni di guadagno e perdita (`SIGN_TEXT`, `SIGN_BAR` di R) | `text-lf-gain`, `text-lf-loss`… | in B2, con R |
| `violet`, `purple`, `indigo`, `pink`, `teal`, `cyan`, `fuchsia`, `lime` (categoriali: tipi di asset, ruoli dei broker, badge) | **restano** | fino ai categoriali di B4: contati dal cricchetto |
| Colori di terzi (Reddit, Facebook, Instagram, TikTok nei pulsanti di condivisione) | **restano** | eccezione motivata, nell'elenco del gate |

### 4.3 I `dark:` esistenti

- Una coppia chiaro/scuro che diventa un solo ruolo perde il `dark:`.
- Il `dark:` resta solo per ciò che non è colore (`dark:hidden`, `dark:invert`) e per i categoriali in attesa di B4.
- Sui ruoli il gate lo vieta (G1).

### 4.4 P1 durante la transizione

| Momento | Cosa succede |
|---|---|
| B1 | Eccezione `:where(:not([class*='-lf-']))` sulle quattro regole strutturali. Valori e regole per classe intatti |
| Durante le ondate | Una regola per classe si toglie nello stesso cambio in cui la sua classe arriva a zero: il gate segnala le regole morte. Le `--theme-*` restano finché qualche regola le usa |
| B6 | Via le regole strutturali, `html.dark body`, le `--theme-*` e i valori scuri di `--color-libre-*`. `body` passa ai ruoli in `@layer base`. Si tolgono anche i token inutilizzati (`primary-*`, `surface-*`, `libre-sage`, `libre-banner`). Gallery prima e dopo |

### 4.5 Ordine per aree e ripartizione

La regola: si migra un'area dopo che il lotto di R che la elenca è entrato in `dev_release2`, e dopo lo spostamento o
il taglio della 1.3 su quell'area. Un `git mv` puro si fonde bene con le modifiche di T (rinomina riconosciuta); un
taglio di file (FE5, FE6, FE8) no.

| Ondata | Aree | Classi | Prerequisiti | Lotti di sotto-agenti |
|---|---|---:|---|---:|
| T-2, T-3 piloti | accesso, shell | ~150 | — (accesso prima di F13 di A) | io |
| W1 primitivi liberi | `ui/modals` (`ModalBase`, `PageSyncModal`, `SyncModalBase`), `ui/select`, `ui/input`, `ui/date`, `ui/tabs`, `ui/toolbar`, `ui/data-editor`, toggle | ~700 | nessuno (non sono file di R) | 3–4 |
| W2 aree libere | `settings`, `support`, `onboarding`, `ai-export`, resto di `layout`, rotte minori | ~1.300 | spostamenti `features/settings`, `features/support` della 1.3 («subito»): prima o dopo, d'accordo | 5–6 |
| W3 stati e mappe | `ui/feedback`, `ui/display`, `toneClasses` (B2), `features/tools` (PAC `ui.ts`), `lib/utils` (mappe di classi) | ~1.100 | lotto A di R | 4–5 |
| W4 dati di mercato e transazioni | `fx`, `assets`, `transactions` (componenti e rotte) | ~3.900 | lotto A; FE4, FE5 (taglio di `AssetModal` e della pagina dell'asset), FE8 (wizard diviso per passo) | 10–12 |
| W5 portafoglio e grafici | `charts`, `dashboard`, `risk`, `brokers` e lotti; B4 (neutri dei grafici con R) | ~2.500 | lotto B (e D per gli osservatori); FE2, FE6, FE7 | 6–8 |
| W6 stili propri | `table`, `files`, `ui/media`, dialoghi; B5 (`--lf-cmp-*` sui ruoli, poi via le gemelle `-dark`) | ~600 + i `<style>` | lotti C e D; FE3 | 3–4 |
| B6 pulizia | P1, `--theme-*`, token morti, `body` | — | tutte le ondate | io |

- **Ripartizione:** T orchestra sotto-agenti nel proprio worktree, ondata per ondata.
- **Per andare più veloci**, il coordinatore può aprire altri workstream con corsie proprie sulle ondate indipendenti
  (W1, W2): D-T10.

### 4.6 Il gate a cricchetto

`frontend/src/themeRoles.gate.test.ts`, con la baseline `frontend/src/themeRoles.baseline.json` e uno script di
aggiornamento `frontend/scripts/theme/legacy-colors.mjs --update`. Registrazione nel catalogo del runner
(`front_utility_unit`, `core-unit`) a cura di `test-author`.

**Metriche**, per file di produzione `*.svelte|ts|js` sotto `src` (esclusi test, API generata, `lib/dev/designer-lab/**`):

- **(M1) classi legacy:** palette con gradino, `white`/`black`, `libre-*`, `primary-*`, `surface-*`. La regex è la
  stessa di `TW_RE` dello scanner di L, copiata finché L non entra; poi un modulo solo.
- **(M2) colori letterali:** hex, `rgb()`, `hsl()`, `oklch()` fuori da `lib/theme/**`, `app.css`, `app.html` e
  `static/`. **Proposta:** lo fa T subito, al posto del cricchetto previsto in W10 di R (D7 di R), con il suo
  consenso.

**Regole del cricchetto (D-T8)**

- **R1:** il totale di ogni metrica non sale mai.
- **R2:** per file, il conteggio non sale. Fanno eccezione le tabelle centrali di R in `lib/theme/**`, che assorbono
  le classi spostate purché R1 regga.
- **R3:** un file nuovo nasce a zero.
- **R4:** una rinomina (stesso nome di file, conteggio non superiore) vale come lo stesso file. I `git mv` della 1.3
  e i merge dei lotti di R non toccano la baseline.
- **R5:** se un conteggio scende, il gate passa e lo segnala; T stringe la baseline a ogni checkpoint.

**Grammatica dei ruoli**

- **G1:** nessun `dark:` su una classe `-lf-`.
- **G2:** ogni classe `-lf-` usata esiste nella tabella di `@theme inline`. Tailwind ignora in silenzio una classe
  sconosciuta: è l'errore più probabile dei migratori.
- **G3:** nessun elemento misto, cioè nessuna stringa di classi o tag Svelte (`class=`, `class={…}`, `class:`) con
  ruoli e classi legacy insieme.
- **G4:** nessun valore arbitrario di colore (`-[#…]`, `-[rgb…]`), salvo `var(--lf-…)` e l'elenco motivato dei colori
  di terzi.

**Contratto dei token** (`src/themeTokens.gate.test.ts`)

- **C1:** ogni ruolo di base ha un valore chiaro e uno scuro.
- **C2:** ogni voce di `@theme inline` punta a un ruolo dichiarato.
- **C3:** contrasti delle coppie dichiarate, con OKLab nel test per i derivati. Le coppie sono testi su superfici,
  bordo dei campi su campo e card, focus, testo sul marchio, sull'azione e sugli stati. Le eccezioni in attesa della
  designer stanno in un elenco esplicito, così una regressione si vede.
- **C4:** nessuna regola P1 per classe sopravvive alla sua classe (regole morte).

### 4.7 Come si vedono i rimasti indietro

- **Build:** l'uscita del gate riassume le classi legacy per area e i 20 file peggiori. La baseline, ordinata per
  conteggio, è il cruscotto della migrazione: ogni ondata la fa scendere.
- **Rendering:** nella gallery le parti migrate hanno sfondi caldi e i verdi della designer; le altre restano come
  oggi. In scuro le card ardesia sul fondo «notte nel bosco» si riconoscono subito. La gallery di B1 deve uscire
  identica: è la prova che un componente non migrato resta com'è.
- **Lab (proposta per L):** un interruttore di debug «mostra i rimasti indietro», che contorna gli elementi con classi
  legacy (selettori `[class*='-gray-']`, `[class*='-slate-']`, `bg-white`, `libre-`).

## 5. Piloti

### 5.1 Shell: solo classi, nessun riordino del markup

**`routes/(app)/+layout.svelte`**

- I 6 rami `bg-libre-beige dark:bg-slate-900` diventano `bg-lf-app`.
- I testi di caricamento `text-libre-green dark:text-green-400` diventano `text-lf-link`.

**`layout/Sidebar.svelte`**

| Elemento | Oggi | Con i ruoli |
|---|---|---|
| Barra | `bg-libre-green text-white` | `bg-lf-brand text-lf-on-brand` |
| Divisori | `border-white/10`, `/20` | `border-lf-on-brand/10`, `/20` |
| Riquadro del logo | `style="background:#fff"` | `bg-lf-logo` |
| Voce attiva | `bg-white/20 border-r-4 border-white` | `bg-lf-on-brand/20 border-lf-on-brand` |
| Hover delle voci | `hover:bg-white/10` | `hover:bg-lf-on-brand/10` |
| Tooltip a barra chiusa | `bg-gray-900 text-white` | `bg-lf-inverse text-lf-on-inverse` |
| Email e versione | `/50` e `/40` | `text-lf-on-brand/70` (a11y, §3.5) |
| Uscita | `bg-white/10 hover:bg-white/20` | gli stessi gradini su `on-brand` |
| Fondale mobile | `bg-black/50` | `bg-lf-overlay` |

**`layout/Header.svelte`**

- Barra: `bg-libre-beige dark:bg-slate-900 border-gray-200 dark:border-slate-700` diventa
  `bg-lf-app border-lf-subtle`.
- Icona del menu: `text-lf-primary`.
- Punto di sicurezza: `bg-lf-danger ring-lf-app`.
- Caffè: `text-lf-donate hover:bg-lf-hover`. È il possibile conflitto alla riga ~242, già segnalato dalla 1.3.

**Proposti in più (D-T9), solo classi:** `ThemeToggle`, `PrivacyToggle`, `LanguageSelector` (stanno anche nella
pagina di login), `ConnectionSecurityIndicator` (nella barra laterale), `HelpMenu` (A ci aggiunge una condizione). Senza
di loro, i controlli dell'header restano legacy dentro un header migrato.

**Effetto:**

- in chiaro la barra cambia di poco (`#1a4031` → `#1B4334`) e lo sfondo passa da `#f5f4ef` a `#F1EDE3`;
- in scuro la barra passa da `#166534` a `#1B4334` e lo sfondo da `#0f172a` a `#131A17`;
- **tutte le schermate autenticate cambiano nella gallery.** Il contenuto delle pagine resta legacy: è voluto.

### 5.2 Accesso

**`auth/LoginCard.svelte`, `auth/RegisterCard.svelte`**

- Card: `bg-lf-card border border-lf-subtle`. Il render chiaro non mostra il bordo: decide la designer (D-T14).
- Testata: `bg-lf-brand text-lf-on-brand`; riquadro del logo `bg-lf-logo`.
- **Campi:** `border-lf-input bg-lf-field text-lf-primary placeholder:text-lf-placeholder focus:border-lf-focus
  focus:ring-lf-focus`; in errore, `border-lf-danger`, `focus:ring-lf-danger` e messaggio `text-lf-danger`.
- **Icone a sinistra:** `User` per utente ed email nel login, `Mail` per l'email nella registrazione, `Lock` per la
  password, da lucide, con `aria-hidden`.
  - Colore `text-lf-muted`, che diventa `text-lf-primary` quando il campo ha il focus (`group-focus-within`), come
    chiede la designer per lo scuro e per coerenza anche in chiaro.
  - Il campo prende `pl-11`.
- Link «Password dimenticata?» e «Registrati qui»: `text-lf-link`, come nei render.
- Pulsante: `bg-lf-action text-lf-on-action hover:bg-lf-action-hover`.
- Messaggi di successo ed errore: famiglie `success`/`danger` soft, line e on-soft.
- **Via il sottotitolo** («Crea un account», `RegisterCard.svelte:157`), e insieme la chiave:
  `dev.py i18n remove "auth.registerTitle" -f`, poi `i18n check` (4 lingue, sorgente `lib/i18n/auth/`). È l'unico
  uso.

**`ui/input/PasswordInput.svelte`**

- Nuova prop `icon` (un componente lucide, opzionale), via libera della 1.3.
- Classi dei ruoli; occhio `text-lf-muted hover:text-lf-primary`.
- A farà K-17 (aria-label e title tradotti) su righe diverse.

**`ui/input/PasswordStrength.svelte`**

- **Box dei requisiti:** `bg-lf-success-soft border-lf-success-line`.
  - Titolo e requisiti soddisfatti: `text-lf-success-on-soft`.
  - ✓ `text-lf-success`.
  - Requisiti non soddisfatti: ✗ e testo `text-lf-muted`.
  - Restano le icone ✓ e ✗, quindi l'informazione non passa dal solo colore.
- **Barra:** traccia `bg-lf-neutral`. Proposta D-T13: livelli 0–1 errore, 2 avviso, 3–4 successo; etichetta del colore
  dello stato. Il numero di segmenti e l'etichetta dicono comunque il livello.

**Sfondo del login, dopo l'ingresso di G** (`ui/AnimatedBackground.svelte`)

- `.animated-bg` su `var(--lf-surface-page)`; colline e linee su `--lf-art-*`.
- Opacità scure da tarare con la designer sulla gallery: con l'opacità .15 di oggi, `#284238` non si vedrebbe.
- I pallini sulle linee dei render non sono nelle note: li lascio fuori, salvo richiesta.

**Fuori dal mio perimetro, da chiedere (D-T9)**

- `auth/ForgotPasswordCard` (di A): stesso schema del login. Senza, resta l'unica card di accesso legacy.
- La barra in alto di `routes/+page.svelte` (di A): caffè e toggle; nel render c'è anche un separatore.
- `routes/+error.svelte`: stessa card. Non ha un proprietario indicato.

### 5.3 PWA e superfici fuori dall'app (dopo l'ingresso del lotto A di R)

- **Meta `theme-color`**, nei tre scrittori: la coppia passa a `#1B4334`/`#1B4334`, il valore di `--lf-brand` nei due
  temi. Il ternario resta, per la «declinazione del colore» futura.
- **`manifest.json`:** `theme_color` `#1B4334`.
- **`themeColorMeta.gate.test.ts`** (di T dopo l'ingresso):
  - `PAIR` diventa `#1b4334`/`#1b4334`;
  - la (d) legge `--lf-brand` di `tokens.css` (`:root, html.light` e `html.dark`).
  - Così il gate continua a dire «la barra della PWA segue la barra laterale».
- **Splash di `app.html` e `offline.html`:** valori copiati dai ruoli.
  - Splash: sfondo, spinner `--lf-focus`, logo bianco.
  - `offline.html`: la sua palette mappata sui ruoli, cioè `--bg` = page, `--text` = primario, `--btn-bg` = action e
    così via.
  - Un gate gemello (`staticThemeMirrors.gate.test.ts`) li confronta con `tokens.css`.
  - **Sfondo di splash, offline e `background_color`:** D-T7, raccomandato `page` (`#F7F4ED`/`#0F1412`).
- **Se T arriva prima del lotto A**, il merge di R entra in conflitto sulle stesse tre righe. Per questo il passo T-4
  aspetta il lotto A. Nel frattempo, in scuro la barra (`#1B4334`) e la meta (`#156534`) differiscono per un breve
  tratto.

## 6. Interazioni

**R**

- **`themed()`:** in B4 diventa la lettura dei ruoli per revisione del tema, con conversione in sRGB (§3.4). Le chiavi
  delle tabelle di `chartTheme` e `chartPalettes` si mappano su `--lf-chart-*`, sulla palette della designer.
- **`toneClasses`:** in B2 (W3) ogni variante con nome diventa un ruolo, per esempio
  `SIGN_TEXT.market.gain` → `text-lf-gain`. Le divergenze di oggi (emerald o green, red-500 o red-600) si fondono: è un
  cambio visivo che la designer approva sulla gallery. Il file è di R: propongo io la tabella, scrive chi decide il
  coordinatore.
- **`--lf-cmp-*`:** in B5 (W6) ogni gemella `x`/`x-dark` diventa `var(--lf-<ruolo>)`, poi si tolgono le regole
  `:global(.dark)`.
- **`tokens.css`:** sta in `lib/theme/` per eccezione. Nessun file in comune con i lotti A–D.
- **Il gate della meta** (lotto A) passa a T.
- **Il cricchetto M2** può sostituire W10/D7 di R (§4.6), da concordare.

**L**

- **Scanner:**
  - `TW_CUSTOM_RE` va esteso con `lf-[a-z0-9-]+`;
  - la mappa classe → variabile va letta da `@theme inline` di `tokens.css`: `bg-lf-card` → `--color-lf-card` →
    `--lf-surface-card`. Oggi lo scanner punterebbe a `--color-lf-card`, che con `inline` non esiste a runtime.
- **I ruoli `--lf-*`** stanno su `:root, html.light` e `html.dark`, come le `--theme-*` che L1 già gestisce. L1 li
  sovrascrive su `html` con `!important`, e i derivati seguono.
- **Limite noto:** l'override su `html` non entra nei sotto-alberi `.dark` o `.light`, che ridefiniscono i ruoli (oggi
  nessuno li usa).
- **Export dei ruoli** (`designer-lab-apply`): si applica a `tokens.css`, di cui T è l'unico scrittore.
- **Proposta:** l'interruttore «mostra i rimasti indietro» (§4.7).

**G**

- `AnimatedBackground` resta di G fino al suo ingresso: lo sfondo del login viene dopo.
- Le schermate `auth/*` sono instabili senza il congelamento di G.
- Ogni ondata visiva di T chiede una gallery, in calendario col coordinatore (una per volta sulla macchina). Si usano
  le classi di stabilità e le maschere di G.
- Dopo ogni ondata, il coordinatore cattura nuovi riferimenti dello stesso giorno.

**1.3**

- **Nuove schermate:** dall'ingresso di T-1 usano solo le utility del §3.2. La regola «Nuove schermate» del piano 1.3
  va aggiornata dal suo coordinatore. Il cricchetto (R3: un file nuovo nasce a zero) la fa rispettare.
- **Spostamenti (FE2–FE11):** i `git mv` puri non toccano la baseline (R4) e si fondono con le modifiche di T. Le
  ondate W4–W6 partono dopo i tagli FE5, FE6 e FE8, sui file nuovi.
- **A:**
  - `features/auth` si sposta dopo l'ingresso dei piloti di accesso;
  - F13 viene dopo;
  - K-17 in `PasswordInput` si somma alla prop `icon`;
  - restano di A, e non li tocco senza permesso: `routes/+page.svelte`, `ForgotPasswordCard`, `DonationPopupModal`.
- **H (avvisi d'istanza nel layout) e la nota legale nella barra laterale:** righe funzionali loro, classi mie. Chi
  arriva per secondo somma.

## 7. Test (con `test-author`) e selettori

**Nuovi test**

- **Gate del cricchetto e della grammatica**, **contratto dei token**, **specchi statici**: §4.6 e §5.3.
- **Gate della meta:** riscrittura di (b) e (d).
- **Componenti:**
  - `PasswordInput`: icona presente solo con la prop, `aria-hidden`;
  - `RegisterCard`: nessuna chiave `auth.registerTitle` resa;
  - `PasswordStrength`: ✓ e ✗ per requisito, box con il suo `data-testid`.
- **E2E `e2e/layout/theme-roles.spec.ts`**, desktop e mobile, chiaro e scuro, confronti con il valore della variabile
  letto dalla pagina, mai con un hex scritto nel test:
  - **(a)** card di login = `--lf-surface-card`; bordo del campo in scuro = `--lf-border-input`; bordo al focus =
    `--lf-focus`. Prova che l'eccezione P1 funziona, cosa che jsdom non sa vedere;
  - **(b)** shell: barra laterale = `--lf-brand`, sfondo = `--lf-surface-app`;
  - **(c)** controllo negativo: una card legacy `bg-white` in scuro resta `#1e293b`. Prova che il non migrato è
    invariato.
- **Aggiornamenti:** nessuno dei test che fissano classi tocca i piloti; gli altri si aggiornano nelle loro ondate.

**Selettori** (preambolo: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py`)

- `test --test-port 6155 --data-dir /tmp/librefolio-r2-t front-utility core-unit` (gate);
- la categoria delle unit di accesso (`LoginCard`, `RegisterCard`, `DonationPopupModal`) in `front-utility`;
- `front check` (svelte-check), `front format`, `lint --dead-code --scope frontend`;
- `i18n check`; `front build` con diff del CSS compilato;
- la nuova E2E, in corsia;
- la gallery, dal coordinatore.

`npm ci` solo se serve, dopo le 22:45.

## 8. Prove per la designer

- **Gallery prima e dopo, stesso giorno:**
  - B1 identica;
  - piloti: `auth/01–03` in chiaro e scuro, desktop e mobile, più un campione di schermate autenticate (dashboard,
    asset, broker, impostazioni) per la shell;
  - per ogni ondata, le schermate della sua area.
- **Una scheda di contrasti** per ruolo: la tabella del §3.5, con le correzioni proposte accanto ai suoi valori.
- **Il Lab**, quando L entra e conosce le utility `-lf-`: la designer regola i ruoli dal vivo sulla build di T
  (`designer_live.sh`, a cura del coordinatore). Un export si applica a `tokens.css`, poi gallery.

## 9. Rischi

1. **Specificità dell'eccezione P1:** con un `:not()` nudo cambierebbero i campi legacy stilizzati nei `<style>`.
   Mitigazione: `:where()`, diff del CSS compilato, E2E (c).
2. **Elementi misti:** escono da P1 a metà. Mitigazione: G3.
3. **Testo ereditato:** in scuro `body` resta `#f8fafc` fino a B6. Mitigazione: regola dei migratori (ruolo di testo
   alla radice del componente).
4. **Bordo senza colore:** in v4 il default è `currentColor`. Mitigazione: regola dei migratori.
5. **Classi `-lf-` scritte male:** Tailwind le ignora in silenzio. Mitigazione: G2.
6. **Conflitti con i tagli della 1.3** (FE5, FE6, FE8) **e con i lotti di R in corso.** Mitigazione: l'ordine del §4.5.
7. **Aspetto misto fra un'ondata e l'altra:** voluto da D-T3, ma da decidere per i rilasci. Se la 1.3 esce a metà
   migrazione, gli utenti vedono shell calda e contenuti freddi (D-T11).
8. **Contrasti:** con i valori della designer così come sono, 8 coppie restano sotto soglia (§3.5).
9. **ECharts e `color-mix`/`oklch`:** il ponte sRGB di B4 (§3.4).
10. **Carico della gallery:** la shell cambia tutte le schermate, quindi la revisione della designer va guidata da un
    campione.
11. **Lab e sotto-alberi `.dark`:** limite noto (§6, L).
12. **Merge dei lotti di R sul gate della meta:** T-4 dopo il lotto A.

## 10. Stima (dimensioni, nessuna durata)

| Passo | Dimensione | Contenuto |
|---|---|---|
| T-1 B1 | M | 2 file CSS, 3 gate o test, script della baseline, istruzioni |
| T-2 accesso | M | 4 componenti, 1 chiave i18n, test dei componenti, E2E (a) |
| T-3 shell | S–M | 3–8 file, solo classi, E2E (b) e (c) |
| T-4 PWA e statiche | S | 4 sorgenti, 2 gate |
| T-5 sfondo del login | S | 1 componente, dopo G |
| W1–W6 | L | ~11.500 classi in 276 file, 30–40 lotti di sotto-agenti, 6 gallery |
| B6 | M | Con la gallery più importante dopo i piloti |

## 11. Ordine dei passi

1. **T-0:** piano nel repo, sezione T del backlog.
2. **T-1 (B1):** `tokens.css`, `app.css`, gate, baseline, istruzioni. Prova: CSS compilato, gate verdi. Checkpoint.
3. **T-2 accesso:** checkpoint e ingresso subito in `dev_release2`, perché A aspetta.
4. **T-3 shell**, con gli extra di D-T9. Gallery completa e revisione della designer.
5. **T-4 PWA e statiche**, dopo il lotto A di R.
6. **T-5 sfondo del login**, dopo G.
7. **W1, W2**, appena possibile; **W3–W6** man mano che entrano i lotti di R e gli spostamenti della 1.3. Una gallery
   per ondata.
8. **B6**, poi chiusura del programma (MkDocs a colori definiti, `docs-writer`).

## 12. Definition of done

**Prima consegna (T-1…T-4)**

- `tokens.css` con i ruoli del §3.2 e le correzioni decise; utility generate; eccezioni P1.
- **Gallery di B1 identica.**
- Piloti come da §5:
  - icone nei campi;
  - nessun sottotitolo;
  - box dei requisiti leggibile, non solo a colori;
  - chiave tolta nelle 4 lingue, `i18n check` verde;
  - barra laterale verde marchio nei due temi, sfondo app `#F1EDE3`/`#131A17`;
  - meta, manifest e splash concordi, coi gate.
- Gate, contratto, test dei componenti ed E2E verdi; svelte-check 0/0; Prettier; codice morto senza reperti nuovi.
- Gallery dei piloti consegnata alla designer.
- Piano aggiornato passo per passo; sezione T del backlog; nessun server attivo; porta 6155 libera.

**Programma**

- Cricchetto a zero sulle classi legacy, salvo i categoriali fino a B4 e le eccezioni motivate.
- Niente più P1 né `--theme-*`; superfici statiche allineate.
- Gallery finale approvata dalla designer; sito MkDocs aggiornato alla chiusura.

## 13. Decisioni richieste

**Per partire (bloccanti)**

| # | Domanda | Raccomandazione |
|---|---|---|
| D-T4 | Nomi: variabili `--lf-<gruppo>-<nome>`, utility `*-lf-<nome>` con `@theme inline` sul namespace `--color-*` (§3.2). La 1.3 li aspetta | sì, tabella del §3.2 |
| D-T5 | Spazio colore | hex sRGB per i valori della designer, `color-mix(in oklab)` per i derivati, ponte sRGB per i grafici |
| D-T6 | Correzioni di contrasto (§3.5) | applicarle subito, minime e commentate; conferma della designer nel giro 2 |
| D-T8 | Cricchetto | R1–R5, grammatica G1–G4, contratto C1–C4; M2 (colori letterali) in T al posto di W10 di R, se R è d'accordo |
| D-T9 | File extra dei piloti | `ThemeToggle`, `PrivacyToggle`, `LanguageSelector`, `ConnectionSecurityIndicator` sì; `HelpMenu` con l'OK di A; `ForgotPasswordCard`, la barra di `routes/+page.svelte` e `+error.svelte` con l'OK di A, oppure restano legacy |
| D-T12 | Istruzioni per gli agenti: la sezione «Design System» di `.github/instructions/frontend.instructions.md` e la riga «Dark mode» di `.github/copilot-instructions.md` passano ai ruoli; una skill di migrazione in `.github/skills/design-tools/theme-roles/` (cartella di L) | le scrive T in T-1, se il coordinatore lo consente: sono superfici condivise |

**Non bloccanti**

| # | Domanda | Raccomandazione |
|---|---|---|
| D-T7 | Sfondo di splash, `offline.html` e `background_color` del manifest | `page` (`#F7F4ED`/`#0F1412`) |
| D-T10 | Chi migra | T con sotto-agenti, ondata per ondata; più workstream con corsie proprie, se il coordinatore vuole parallelizzare W1 e W2 |
| D-T11 | Rilasci a metà migrazione | nessun tag di rilascio con le ondate W1–W4 a metà; almeno neutri e stati completi |
| D-T13 | Barra della robustezza della password | 3 ruoli: 0–1 errore, 2 avviso, 3–4 successo |
| D-T14 | Bordo della card di accesso in chiaro | `border-lf-subtle` nei due temi; decide la designer |

**Per la designer (giro 2)**

- le correzioni di contrasto;
- i derivati del §3.3: hover, fondale, inverso, tinte degli stati;
- guadagno e perdita;
- l'info `#155EEF`, molto saturo;
- le opacità delle colline in scuro;
- i categoriali e la palette dei grafici.

## 14. Piano e backlog

- **Piano**, dopo l'autorizzazione:
  `LibreFolio_developer_journal/Release_2/Phase_1/10_colorSystem/T-tokensTheme/plan-phase01TokensTheme.prompt.md`.
  Passi T-0…T-5, W1–W6, B6, con note di implementazione e fuori pista dopo ogni passo.
- **Backlog post-1.2:** una sezione «T» in `BACKLOG_POST_1.2.md`, scritta ai checkpoint. Voci già note:
  - a11y: testo per lettori di schermo sullo stato di ogni requisito della password, con nuove chiavi i18n; è di A;
  - lo spazio di 8 px del filtro «Caricato da», segnalato da G: non è un colore;
  - la pagina wiki F-007 da correggere (osservatori, non store).
