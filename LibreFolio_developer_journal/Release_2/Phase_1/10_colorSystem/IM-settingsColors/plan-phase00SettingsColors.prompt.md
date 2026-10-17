# IM · Colori delle impostazioni — piano (analisi d'implementazione e avanzamento)

> Workstream IM del programma colori (D-T28, 16/10/2026): migrazione 1:1 ai ruoli di colore di impostazioni, supporto
> e aggiornamenti, senza decisioni di design. Coordinatore: sessione «UI color analysis»
> (`aec04834-1532-4d86-9e3f-f942e82aca89`). Backlog: sezione «IM · Colori delle impostazioni» di
> [`BACKLOG_POST_1.2.md`](../../../Phase_0/BACKLOG_POST_1.2.md), ID `IM-n`.
> Piano generale: [`plan-phase00ColorSystemThemeLab.prompt.md`](../plan-phase00ColorSystemThemeLab.prompt.md).
> Stato: **in esecuzione** dal 16/10 (vedi «Avanzamento», in fondo).

## Decisioni e via

- **Kickoff del coordinatore (16/10, 10:41):** solo migrazione 1:1, i colori della designer, l'elemento intero (G3),
  niente ruoli inventati; `DonationPopupModal` solo con l'OK esplicito di A; `SettingToggle` al lotto unico degli
  interruttori di T.
- **Via del developer (16/10, ~11:00):** piano approvato dalla sessione (approvazione del piano nell'app).
- **Conferma della 1.3, girata dal coordinatore (16/10, ~11:05):** «La 1.3 conferma IM-1…IM-6, compresa la riga
  `GlobalSettingsTab.test.ts:937`: nessun loro lotto è aperto su quei file. L'OK di A su `DonationPopupModal` arriva a
  parte.» Per IM-2: A8 («Security») toccherà più avanti `routes/(app)/settings/+page.svelte` e forse `SettingsLayout`,
  quindi IM-2 deve entrare presto; A7b lavora su `features/settings/users/**`, fuori dai lotti.
- **Regole:** dal 16/10 la fonte è lo skill comune `design-system` (D-T29, `.github/skills/design-tools/design-system/`),
  con `theme-roles` per la conversione e il baseline.

## 0. Riferimenti

| Voce | Valore |
|---|---|
| Worktree | `/Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-improved-funicular` |
| Ramo | `e-alfy-im-settings-colors` |
| HEAD | analisi su `8f2824046` (baseline del kickoff ✅); base portata dal coordinatore a **`6e569084a`** (fast-forward: target `b82e7765f` + skill D-T29 `c59e92dfb`), nessun file dell'area cambiato |
| Corsia | `--test-port 6159`, `--data-dir /tmp/librefolio-r2-im` |
| Coordinatore | `aec04834-1532-4d86-9e3f-f942e82aca89` |
| Fonti | skill `design-system` (D-T29) e `theme-roles` (regole 1–8), `tokens.css`, designer giro 2 (Q2–Q13, D-T17), blocchi W2-c/e/f del piano di T, devWiki `problems/tailwind4-same-property-utilities-sorted-by-name` |
| Bootstrap | `frontend/node_modules` assente (atteso; `npm ci` approvato una volta), `graphify-out/graph.json` assente (letti i file del devWiki) |

## 1. Inventario dal baseline (`--report`, m1 8.249 / m2 54 sul tree, ratchet e grammatica puliti)

Area IM: **22 file con colori legacy, m1 1.048, m2 6**. Coincide riga per riga con `themeRoles.baseline.tsv`.
Gli altri 19 file dell'area (users/*, UsersTab, AccountDeletionDialog, PreferencesTab, i `.ts`) misurano 0/0.

Divisione per significato (letta a mano, non per famiglia di colore):

| File | m1 | m2 | neutri | marchio | stati | segni | categorie | interruttori | resta |
|---|---:|---|---:|---:|---|---:|---:|---:|---:|
| `settings/SettingActions.svelte` | 15 | – | 7 | 2 | 6 warning (reset, Q4) | 0 | 0 | 0 | 0 |
| `settings/SettingBulkActions.svelte` | 15 | – | 7 | 2 | 6 warning (reset, Q4) | 0 | 0 | 0 | 0 |
| `settings/SettingCurrency.svelte` | 8 | – | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| `settings/SettingNumber.svelte` | 28 | – | 22 | 2 | 4 warning (soglia) | 0 | 0 | 0 | 0 |
| `settings/SettingSelect.svelte` | 8 | – | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| `settings/SettingTheme.svelte` | 19 | – | 14 | 5 (opzione scelta) | 0 | 0 | 0 | 0 | 0 |
| `settings/SettingToggle.svelte` | 18 | – | 10 | 0 | 4 warning (badge «Coming soon») | 0 | 0 | 4 | **18 (lotto di T)** |
| `settings/SettingsLayout.svelte` | 61 | – | 40 | 9 | 12 (lucchetto: 6 danger, 6 success) | 0 | 0 | 0 | 0 |
| `settings/CachePanel.svelte` | 34 | – | 28 | 2 | 4 danger (svuota) | 0 | 0 | 0 | 0 |
| `settings/tabs/GlobalSettingsTab.svelte` | 110 | – | 86 | 15 | 9 (lucchetto 6 warning, pallino 3) | 0 | 0 | 0 | 0 |
| `routes/(app)/settings/+page.svelte` | 3 | – | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| `settings/SchedulerConfigModal.svelte` | 112 | – | 87 | 14 | 11 (1 danger; 10 smeraldo decorativo → success per tinta) | 0 | 0 | 0 | 0 |
| `settings/SchedulerLogModal.svelte` | 114 | – | 76 | 1 | 37 (16 success, 12 danger, 3 warning, 6 info) | 0 | 0 | 0 | 0 |
| `settings/tabs/ProfileTab.svelte` | 153 | – | 121 | 16 | 16 (12 warning, 4 danger) | 0 | 0 | 0 | 1 (`text-white` sul fondale dell'avatar) |
| `settings/PasswordChangeModal.svelte` | 31 | – | 22 | 2 | 7 (6 success, 1 danger) | 0 | 0 | 0 | 0 |
| `settings/tabs/AboutTab.svelte` | 157 | `#ffffff` | 125 | 1 (link) | 9 (diagnostica 7, copiato 2); + 9 icone decorative (Q12) e 1 cuore decorativo | 0 | 12 (famiglie di plugin) | 0 | 21 (12 categorie + 8 neutri delle loro 4 card + 1 cuore) |
| `support/SupportActions.svelte` | 11 | – | 8 | 0 | 3 (caffè → `donate`) | 0 | 0 | 0 | 0 |
| `support/SocialShareModal.svelte` | 57 | – | 42 | 3 | 12 (6 warning, 6 danger) | 0 | 0 | 0 | 1 (anello del bottone copia, col marchio) |
| `support/supportLinks.ts` | 14 | – | 14 nei `brandClass` | 0 | 0 | 0 | 0 | 0 | **14 (marchi di terzi)** |
| `support/DonationPopupModal.svelte` | 28 | `#ffffff` | 23 | 2 | 3 (caffè → `donate`, nota) | 0 | 0 | 0 | 0 (**serve l'OK di A**) |
| `update-check/AskAdminModal.svelte` | 27 | – | 18 | 3 | 6 (4 warning, 2 success) | 0 | 0 | 0 | 0 |
| `update-check/UpdateAvailableModal.svelte` | 25 | `#334155×2 #e2e8f0×2` | 17 | 5 | 3 (verde scuro dei link) | 0 | 0 | 0 | 0 |
| **Totale** | **1.048** | **6** | | | | **0** | **12** | **4** | **55** (83 senza Donation) |

- Segni (guadagno/perdita): nessuno nell'area. I «+N» del log dello scheduler sono conteggi, non segni.
- Elementi già sui ruoli, da lasciare: Z7c-2 (`text-lf-warning` in `SchedulerLogModal` ×8, `GlobalSettingsTab` ×1),
  A6e (password per l'email in `ProfileTab` ×7).
- Previsione dopo i sei lotti: **m1 1.048 → 55** (≈95 % migrato), **m2 6 → 0** (83 e 1 senza l'OK di A su Donation).

## 2. Catene di classi

- **Entranti, da fuori area, lasciate:**
  - `lib/utils/providerHelpers.ts` → `PROVIDER_COLORS` / `DEFAULT_PROVIDER_COLOR` → badge del provider FX in
    `SchedulerLogModal:588`. Categoriale (ECB, Frankfurter, Fixed, Manual) e di un altro proprietario: lo span non ha
    classi colore proprie, segue la tabella quando migra.
  - `lib/utils/colors.ts` → `getStringBadgeStyle()` → badge di versione di `UpdateAvailableModal` (variabili inline,
    generatore in eccezione). IM cambia solo i fallback del `<style>`, come T in `TagInput`.
- **Interna, lasciata:** `supportLinks.ts` `brandClass` → bottoni social di `SupportActions`, badge e bottone «copia»
  di `SocialShareModal`. Marchi di terzi: restano legacy per intero (G3). I test leggono la costante, non il valore.
- **Uscenti (consumatori fuori area, nessuna prop di classe):** `SettingCurrency`/`SettingSelect` in
  `onboarding/WelcomeForm` (T, già sui ruoli); `DonationPopupModal`/`UpdateAvailableModal` in
  `onboarding/DeferredAppPopups`; `AskAdminModal` in `layout/ChangelogModal` (W2-b). Cambia solo l'aspetto delle loro
  scene.
- **Prop di classe:** nessuna con colori. `ModalBase` senza `contentClass`, `InfoBanner class="mb-4"`, `TabBar`
  `className: 'sm:ml-auto'`, `SupportActions class` mai passata.

## 3. Test che asseriscono classi di colore

| Test | Cosa legge | Proprietario | Azione |
|---|---|---|---|
| `tabs/GlobalSettingsTab.test.ts:937` | `closest('div.bg-gray-50')` (riga del selettore) | zona 1.3 (A; Z7c-2 sul componente) | **OK richiesto**; `test-author`: `closest('[data-testid^="global-setting-"]')` (il wrapper ha già il testid) |
| `support/SocialShareModal.test.ts:184,217`, `SupportActions.test.ts:64` | `brandClass` dalla costante | A | nessuna: la costante non cambia |
| `SchedulerConfigModal.test.ts:673`, `SchedulerLogModal.test.ts:851` | `.border-b` (layout) | Z | nessuna: `border-b` resta |
| `ProfileTab.test.ts` (`.setting-row`), `page.tabs.test.ts` (`hidden sm:inline`, `sm:ml-auto`), `SupportActions.test.ts:54` (`flex-wrap`) | classi non di colore | A | nessuna |
| E2E | nessuno asserisce classi di colore dell'area; `support-copy-and-go:150–180` confronta la vernice dell'icona e del bottone (stesso `brandClass`) | – | nessuna |

## 4. File dell'area aperti altrove (verificati in sola lettura, solo ref git)

- Rami nominati con commit nell'area oltre HEAD: solo `e-alfy-h-piattaforma` (`9ddecbde0`), commit `c1ecdc389`
  «About absence checks can fail» su `tabs/AboutTab.test.ts` (+31/−5, nessun selettore di classe). Nessun conflitto con
  IM-5, che tocca solo `AboutTab.svelte`.
- E, `users/linkShareActions.ts` non committato: non letto (worktree altrui). Misura 0/0: nessun lotto IM lo tocca.
- A (`356a01d4d`), Z (`a3e8e73f7`, già nel target), E (`44d4d7e8e`): nessun commit nell'area oltre HEAD.

## 5. Lotti (file disgiunti, ognuno validabile da solo)

| Lotto | File (esatti) | m1 → resta | Proprietario 1.3 | Vitest leggere | E2E (corsia pesante) | Galleria |
|---|---|---|---|---|---|---|
| **IM-1** controlli | `features/settings/SettingActions.svelte`, `SettingBulkActions.svelte`, `SettingCurrency.svelte`, `SettingNumber.svelte`, `SettingSelect.svelte`, `SettingTheme.svelte` | 93 → 0 | A | `SettingControls`, `PreferencesTab`, `onboarding/WelcomeForm`, `WelcomePage` | `front-utility settings`, `onboarding-tour` | settings/user-preferences, global-settings; onboarding/welcome-setup |
| **IM-2** pagina e globali | `features/settings/SettingsLayout.svelte`, `features/settings/CachePanel.svelte`, `features/settings/tabs/GlobalSettingsTab.svelte`, `routes/(app)/settings/+page.svelte`; test `GlobalSettingsTab.test.ts:937` (test-author, con OK) | 208 → 0 | A (+ Z7c-2) | `SettingsLayout`, `GlobalSettingsTab`, `GlobalSettingsTab.verification`, `settingsTabs`, `page.tabs`, `PreferencesTab` | `settings`, `scheduler`, `email-verification` | **tutte** le scene settings (la card della rotta), cache-panel |
| **IM-3** modali dello scheduler | `features/settings/SchedulerConfigModal.svelte`, `features/settings/SchedulerLogModal.svelte` | 226 → 0 | Z | `SchedulerConfigModal`, `SchedulerLogModal` | `scheduler` | settings/scheduler-config, scheduler-log |
| **IM-4** profilo e password | `features/settings/tabs/ProfileTab.svelte`, `features/settings/PasswordChangeModal.svelte` | 184 → 1 | A | `ProfileTab`, `PasswordChangeModal`, `AccountDeletionDialog` | `settings`, `front-user account-deletion`, `image-crop` (avatar) | settings/profile, password-modal |
| **IM-5** informazioni | `features/settings/tabs/AboutTab.svelte` | 157 (+`#ffffff`) → 21 | H | `AboutTab` | `settings`, `support-copy-and-go` | settings/about, about-plugin-diagnostics, about-tool-diagnostics |
| **IM-6** supporto e aggiornamenti | `features/support/SupportActions.svelte`, `SocialShareModal.svelte`, `features/update-check/AskAdminModal.svelte`, `UpdateAvailableModal.svelte`; **+ `DonationPopupModal.svelte` solo con l'OK di A**; `supportLinks.ts` invariato | 120 (+m2 4) → 1; Donation 28 (+m2 1) → 0 | A | `support/*`, `update-check/*`, `layout/ChangelogModal`, `onboarding/DeferredAppPopups` | `support-copy-and-go`, `auth`, `changelog-locale`, `app-start-auth` | support/donation-popup, social-share-modal; auth/update-available-modal |

- **Fuori dai lotti:** `SettingToggle.svelte` (lotto unico degli interruttori di T); `supportLinks.ts` (marchi).
- **Ordine proposto** (per «chi parte prima»): IM-1 → IM-2 → IM-3 → IM-4 → IM-5 → IM-6. Scrittura **in parallelo**,
  un sotto-agente per lotto, appena il coordinatore conferma che nessuna sessione della 1.3 ha annunciato quei file; un
  lotto annunciato va in fondo, gli altri partono.
- **Validazione pesante accumulata:** uno slot unico per i sei lotti (stima ≤45 min: `api sync`, `front check`,
  `component-unit`, ~170 test E2E); se non ci sta, S1 = IM-1…IM-5, S2 = IM-6.

### Mappatura comune (dalla skill, dalle risposte Q della designer, dai precedenti di T)

- Neutri per gradino: tabella della skill. Card della pagina `bg-lf-card text-lf-primary border border-lf-subtle
  shadow-sm shadow-lf-shadow-card`; tendine e modali fatte a mano `bg-lf-card border border-lf-raised shadow-lf-shadow`
  (N3, Q8); fondali `bg-lf-overlay` (Q13).
- Bottone primario `bg-lf-action text-lf-on-action hover:bg-lf-action-hover`; secondario grigio `bg-lf-panel
  text-lf-secondary hover:bg-lf-neutral` (precedente di T, 10 usi).
- Campi `border-lf-input bg-lf-field text-lf-primary hover:border-lf-input-hover focus:ring-lf-focus
  focus:border-lf-focus` (D-T18); idle e stato della stessa proprietà nei due rami di un ternario (regola 8).
- Selezione: voce di lista `bg-lf-selected text-lf-link`; segmento o chip pieno scelto `bg-lf-checked
  text-lf-on-checked` (D-T16, come `ViewModeToggle`); opzione bordata scelta `border-lf-checked bg-lf-selected
  text-lf-link`.
- Stati: avvisi e chip su tinta `bg-lf-X-soft border-lf-X-line text-lf-X-on-soft` (come `InfoBanner`), icone e testi
  liberi `text-lf-X`, pieni `bg-lf-X text-lf-on-status`; bottoni tinti `bg-lf-X-soft text-lf-X hover:bg-lf-X-line`
  (precedente di T).
- «Modificato» e «reset» arancio/ambra → ruoli `warning` (Q4); pallino inattivo `bg-lf-muted` (Q5); rosso pieno
  `bg-lf-danger-solid text-lf-on-danger-solid hover:bg-lf-danger-hover` (Q3); ambra pieno `bg-lf-warning
  text-lf-on-status hover:bg-lf-warning-hover` (Q3); caffè `bg-lf-donate text-lf-on-status hover:bg-lf-donate-hover`.
- `bg-libre-beige` nelle modali → `bg-lf-card`; piastrella del logo `style="background:#fff"` → `bg-lf-logo`; header
  verde della Donation `bg-lf-brand text-lf-on-brand` (come la card di login).
- Radice di ogni componente migrato: `text-lf-primary` (regola 3). Niente `dark:` sui ruoli, niente esadecimali.

### Casi per lotto e «da rivedere» per il developer

- **IM-1:** reset arancio → ambra `warning` (Q4: la tinta passa da arancio ad ambra); avviso di soglia di
  `SettingNumber` su `warning`; tema scelto `border-lf-checked bg-lf-selected text-lf-link`; bordi dei campi più
  scuri (3:1, D-T18). Da rivedere: tinta del reset.
- **IM-2:** categoria scelta nella colonna desktop `bg-lf-checked text-lf-on-checked` (oggi verde pieno, in scuro
  `#00d681` con testo bianco); nel menu mobile `bg-lf-selected text-lf-link`; lucchetto di `SettingsLayout`
  rosso/verde tinti, di `GlobalSettingsTab` neutro/ambra; pallino dello scheduler `bg-lf-success|warning|danger`; il
  campo stringa generico oggi ha `border` senza colore (currentColor in chiaro): `border-lf-input`, bloccato
  `border-lf-subtle`, come `SettingNumber`. Le righe booleane restano miste finché T non migra `SettingToggle`.
  Da rivedere: colonna delle categorie, bordo del campo generico.
- **IM-3:** tessere decorative dell'header per tinta, come `SyncModalBase` di T: configurazione smeraldo →
  `bg-lf-success-soft text-lf-success`, log blu → `info`; chip degli orari → `success` soft; «aggiungi orario»
  `text-lf-link hover:bg-lf-selected`; giorni scelti `bg-lf-checked text-lf-on-checked border-lf-checked`; spinner
  `border-lf-neutral border-t-lf-focus`, quello nel bottone `border-lf-on-action/30 border-t-lf-on-action`; «+N»
  prezzi e punti `text-lf-success`, eventi `text-lf-info`; tendina dei fusi `border-lf-raised shadow-lf-shadow`.
  Da rivedere: tessere e chip decorativi su ruoli di stato.
- **IM-4:** modifica attiva ambra → `warning` soft; righe modificate `bg-lf-warning-soft/50` (Q4); «Elimina
  account» rosso pieno (Q3); «Scarta e blocca» ambra pieno (Q3); dialogo di scarto fatto a mano: fondale
  `bg-lf-overlay` (più scuro, Q13), pannello con `border-lf-raised` (+2 px come W1-e) e `shadow-lf-shadow`;
  fondale dell'avatar `bg-lf-overlay`, icona della fotocamera `text-white` lasciata (ruolo mancante). Da rivedere:
  dialogo di scarto, icona sul fondale.
- **IM-5:** icone di «Informazioni» senza arcobaleno: `text-lf-link` (il verde del focus, «accent icons» dello skill
  D-T29) su tessere `bg-lf-panel` (Q12, cambio ben
  visibile); logo `bg-lf-logo`; diagnostica `danger`/`success` soft; **famiglie di plugin lasciate** (accenti
  categoriali: asset verde, cambi blu, import ambra, segnali viola; bordo al passaggio e badge delle iniziali), con le
  loro 4 card legacy per intero (G3: in scuro restano blu notte dal rimappaggio); cuore rosso decorativo lasciato.
  Da rivedere: card dei plugin miste in scuro, cuore.
- **IM-6:** corpi beige → `bg-lf-card`; caffè su `donate` (in chiaro da ambra viva `#f59e0b` a `#ae4e00` con testo
  chiaro; in scuro testo scuro su `#f59e0b`); campi della condivisione `border-lf-input`; righe degli admin
  `bg-lf-panel border-lf-warning-line`; «Più tardi» `bg-lf-panel text-lf-secondary hover:bg-lf-neutral`; fallback dei
  badge di versione sui ruoli (m2 → 0, invisibile: le variabili ci sono sempre). Marchi social e anello del bottone
  copia lasciati. Con Donation, **gate C4**: tolgo da `app.css` `html.dark .bg-libre-beige` e
  `html.dark .text-libre-dark` (ultimi 8 + 4 usi, tutti in IM) e lo dichiaro. Da rivedere: tinta del caffè.

### Ruoli che sembrano mancare (al coordinatore, per T)

1. Testo/icona su fondale scuro (`text-white` sulla fotocamera dell'avatar, `ProfileTab`).
2. Testo su colore di marchio di terzi e il nero di X/TikTok (`supportLinks.ts`, 14 classi).
3. Cuore decorativo di «Fatto con ❤» (oppure va bene `text-lf-danger`?).
4. Categoriali: famiglie di plugin (`AboutTab`), provider FX (`PROVIDER_COLORS`, fuori area).

## 6. Rischi e dipendenze

- **Chi parte prima con la 1.3:** A (quasi tutto), Z (modali dello scheduler), H (About), E (utenti: nessun lavoro
  IM). Lista dei lotti da confermare prima di scrivere.
- **OK necessari:** A per `DonationPopupModal`; zona 1.3 per `GlobalSettingsTab.test.ts:937`.
- **Dipendenze:** T per `SettingToggle` (interruttori) e per i ruoli mancanti; DV/T per i categoriali. Nessuna
  dipendenza bloccante per IM-1…IM-5.
- **Superficie condivisa:** `app.css` solo per C4 (IM-6 con Donation), dichiarato nel checkpoint. Baseline: `--update`
  al checkpoint; ai merge `--resolve` del coordinatore.
- **Regola 8:** controllo a mano dei ternari (stessi proprietà in un solo ternario) in ogni diff, con l'elenco dei
  punti caldi: input di `SettingNumber` e del campo generico, opzioni di `SettingTheme`, voci di categoria, giorni e
  fusi dello scheduler, box d'errore della condivisione, lucchetti.
- **Aspetto misto temporaneo:** righe booleane (SettingToggle), card dei plugin in About, marchi social.
- **Infrastruttura:** `npm ci` prima delle prime prove; per gli E2E servono build di debug e sito MkDocs (il backend
  condiviso ha 300 s di avvio): vanno nello slot pesante o prima, con il via. Se il runner chiede `.env`, mi fermo e lo
  segnalo. Prove leggere solo con carico < 50, sotto `nice -n 10`.
- **D-T29:** se lo skill comune di T arriva prima della scrittura, i sotto-agenti lo leggono e lo seguono.

## 7. Piano operativo (dopo il via)

1. Scrivere questo piano nel journal (`IM-settingsColors/plan-phase00SettingsColors.prompt.md`); `npm ci` in
   `frontend/` (una volta).
2. Con l'OK: `test-author` su `GlobalSettingsTab.test.ts:937` (testid al posto della classe).
3. Sei sotto-agenti `general-purpose` in parallelo, uno per lotto, sui soli file del lotto (prompt §8). Non lanciano
   prove, build né git.
4. Rilettura di ogni diff (G3, regola 8, catene, `text-lf-primary` sulle radici); poi prove leggere in serie: `--check`,
   gate Vitest, Prettier sui file, `git diff --check`, Vitest dei lotti.
5. Slot pesante assegnato: `api sync`, `front check`, `front-utility component-unit`, E2E dei lotti.
6. `--update` del baseline (solo stringe); C4 se chiesto; voci IM-n nel backlog; piano aggiornato.
7. Checkpoint al coordinatore (file, prove, esclusioni, conflitti, messaggio di commit, «dove guardarlo»), poi FROZEN.

Definition of done: i file dei lotti approvati senza classi legacy oltre i «resta» dichiarati; `--check` e gate verdi;
`front check` 0/0; Vitest e E2E dei lotti verdi; porta 6159 libera; voci IM-n per i residui; checkpoint consegnato.

## 8. Prompt dei sotto-agenti (comune, più il blocco del lotto)

```text
You convert ONE lot of LibreFolio frontend files to the colour roles. Workstream IM, lot <ID>.
Worktree only: /Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-improved-funicular. Never read another
checkout. Edit ONLY these files: <files>.
Read first: .github/skills/design-tools/theme-roles/SKILL.md (rules 1–8), frontend/src/lib/theme/tokens.css,
.github/instructions/frontend.instructions.md («Design System»), and .github/skills/design-tools/design-system/SKILL.md.
Rules: convert by meaning and step; every `light dark:` pair becomes ONE role without `dark:`; an element migrates
whole (G3): never a role next to a palette class in the same class string or tag; leave categorical colours and the
elements listed below as «leave» entirely legacy and list them; every `border` names its role; the component root
gets `text-lf-primary`; idle and state colours of one property are the two branches of ONE ternary (rule 8); no hex,
rgb(), colour names or arbitrary colours (only var(--lf-…)); class names stay whole literals; do not touch classes
from lib/theme tables, lib/utils/providerHelpers or supportLinks brandClass; no markup reordering, no prop, behaviour
or i18n change; do not edit tests.
Commands: none (no tests, builds, servers, npm/pipenv, git). The lead runs the gates.
Report: per file the classes before/after, elements left legacy and why, roles that seemed missing, tests that read
a class you changed, every ternary you touched.
```

## Avanzamento

| Passo | Stato |
|---|---|
| A0 · Analisi al coordinatore | ✅ 16/10 |
| A1 · Piano nel journal, `npm ci` | ✅ 16/10 |
| A2 · Test `GlobalSettingsTab.test.ts:937` (test-author) | ✅ 16/10 |
| A3 · Lotti IM-1…IM-6 (sotto-agenti in parallelo; Donation all'OK di A) | ✅ 16/10 (Donation con l'OK di A, checkpoint 2) |
| A4 · Rilettura dei diff e prove leggere | ✅ 16/10 |
| A5 · Slot pesante | ✅ 16/10, 12:24–13:06 su `53b6dd352`: tutto verde |
| A6 · `--update`, backlog IM-n, checkpoint | ✅ checkpoint 1 = `b5abcbdaa`, base merge `d95d6236c` |
| A7 · Fotocamera, `DonationPopupModal`, C4 | ✅ checkpoint 2 = `8636a368f`, base merge `53b6dd352` |

### A0 · Analisi ✅ 16/10

> **Note implementazione**: inventario con `--report` sul baseline `8f2824046` (m1 8.249, m2 54; area IM 22 file, m1
> 1.048, m2 6, uguale al baseline riga per riga), classificazione a mano per significato (§1), catene (§2), test (§3),
> rami aperti verificati solo con `git diff --name-status HEAD...<ramo>` (§4). Mandata al coordinatore alle ~10:58.
>
> **⚠️ Fuori pista**: la sessione era in plan mode, che vieta di scrivere nel repo; il piano è stato copiato qui al via.
> Il carico della macchina era 70–79 all'inizio: il `--report` è partito a carico 41, sotto `nice -n 10`.

### A1 · Piano nel journal e `npm ci` ✅ 16/10

> **Note implementazione**: piano copiato da quello della sessione con le decisioni del via; `npm ci` in `frontend/`
> (approvato una volta dal kickoff): 433 pacchetti, `svelte-kit sync` eseguito, `vitest`, `prettier`, `svelte-check` e
> `@esbuild/darwin-arm64` presenti, worktree pulito.
>
> **⚠️ Fuori pista**:
> - Il coordinatore ha portato il ramo a `6e569084a` (fast-forward con lo skill D-T29) dopo l'analisi: verificato,
>   nessun file dell'area, del baseline, di `tokens.css` o di `app.css` cambiato. Lo skill `design-system` diventa la
>   fonte delle regole; conferma la mappatura e corregge un dettaglio: le icone di Q12 vanno su `text-lf-link` («accent
>   icons»), non su `text-lf-focus`.
> - npm 11 non ha eseguito gli script d'installazione di `esbuild` e `fsevents` (`allowScripts`): il binario di esbuild
>   arriva comunque da `@esbuild/darwin-arm64`. Verificato: i test dei gate girano (65/65, 2,6 s).

### A2 · Test `GlobalSettingsTab.test.ts:937` ✅ 16/10

> **Note implementazione**: `test-author` ha sostituito `closest('div.bg-gray-50')` con
> `closest('[data-testid^="global-setting-"]')`, il wrapper che ogni riga pubblica già. Ha verificato sul DOM che i tre
> selettori (lingua, valuta, tema) arrivano allo stesso elemento di prima. Ha corretto anche il commento: «la label che
> dà la scheda», perché due etichette su tre non vengono dal dizionario del test. Nessun'altra lettura di classi colore
> nel file; le `btn-warning|danger|primary` (righe 351–353) sono varianti di `ConfirmModal`, fuori area.

### A3 · Lotti IM-1…IM-6 ✅ 16/10 (Donation in attesa dell'OK di A)

> **Note implementazione**: sei sotto-agenti `general-purpose` in parallelo, uno per lotto, sui soli file del lotto,
> con il controllo leggero `im_selfcheck.mjs` (classi rimaste, letterali, G1–G4 dei soli file) della cartella di
> sessione. Rilettura dei diff e controllo della regola 8 con `im_rule8.mjs` (stessa proprietà sempre attiva e
> condizionale, o in due parti condizionali): **0 casi** su tutti i file.
>
> | Lotto | m1 | m2 | Resta |
> |---|---|---|---|
> | IM-1 controlli (6 file) | 93 → 0 | – | – |
> | IM-2 pagina e globali (4 file) | 208 → 0 | – | – |
> | IM-3 modali dello scheduler (2 file) | 226 → 0 | – | badge provider FX (catena da `providerHelpers.ts`, nessuna classe nel file) |
> | IM-4 profilo e password (2 file) | 184 → 1 | – | `text-white` della fotocamera sul fondale |
> | IM-5 informazioni (1 file) | 157 → 21 | `#ffffff` → – | 4 card delle famiglie di plugin (8 neutri + 4 bordi categoriali), 4 badge (8), cuore |
> | IM-6 supporto e aggiornamenti (4 file) | 120 → 1 | 4 → – | anello scuro del bottone «copia» (porta il `brandClass`) |
>
> Da rivedere, oltre a quelli del §5:
> - IM-2: il campo stringa bloccato è `bg-lf-panel` dentro un wrapper `bg-lf-panel`: prima era un gradino più scuro
>   (gray-100 su gray-50), ora lo separa solo il bordo `subtle`. Lo stesso vale per `SettingNumber` bloccato (IM-1).
> - IM-3: il segnaposto del campo dei fusi prende `placeholder:text-lf-placeholder`: col ruolo l'input esce dal
>   rimappaggio scuro dei segnaposto di `app.css`. L'ha aggiunto il sotto-agente; è la mappatura della skill.
> - IM-4: il bordo al passaggio del mouse compare anche sui campi bloccati (disabilitati).
> - IM-6: le righe degli admin passano dal bianco al `panel` (un gradino più scure della card in chiaro).
>
> **⚠️ Fuori pista**:
> - Il lancio di IM-5 si è troncato (limite di uscita): le regole comuni sono passate in un file di sessione
>   (`im_common_rules.md`) e i prompt di IM-5 e IM-6 lo citano.
> - Prima Vitest dei componenti fallita prima della raccolta: `Failed to resolve import "./generated" from
>   "src/lib/api/index.ts"` (client API ignorato da git, worktree nuovo). Nessun DB, file o server toccato. Il
>   coordinatore ha autorizzato `api sync` fuori slot (11:20): `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc nice -n 10
>   pipenv run python dev.py api sync`, esito 0, solo file ignorati. **L'ho lanciato con carico 70**, non sotto 50 come
>   chiesto: è durato meno di un minuto, ma la condizione non era rispettata. Da rilanciare dopo ogni base merge.

### A4 · Rilettura e prove leggere ✅ 16/10

> **Note implementazione** (tutto sotto `nice -n 10`, dalla radice o da `frontend/`):
> - `node frontend/scripts/theme/theme-roles.mjs --check`: pulito, 19 file sotto il loro record;
> - `vitest run src/themeRoles.gate.test.ts src/themeTokens.gate.test.ts`: 65/65;
> - `prettier --check` sui 20 file: 5 file non conformi **introdotti** dalle nuove stringhe (conformi nella base,
>   verificato con `git show 6e569084a:… | prettier --check`) → `prettier --write` sui 5, poi tutti conformi;
> - `git diff --check`: pulito;
> - regola 8 (`im_rule8.mjs`) e colori solo `dark:` per elemento (`im_darkonly.mjs`, base contro lavoro): 0 casi;
>   `dark_only_check.py` del coordinatore (per riga): 2 falsi positivi verificati (`class` su due righe nelle tendine
>   mobili di `SettingsLayout:103` e `GlobalSettingsTab:484`, bordo chiaro sulla riga prima);
> - `vitest run` su `features/settings`, `features/support`, `features/update-check`, `routes/(app)/settings`,
>   `WelcomeForm`, `WelcomePage`, `DeferredAppPopups`, `ChangelogModal`: **31 file, 1.108 test verdi**.
> - `--update`: baseline m1 8.249 → 7.284, m2 54 → 49; cambiano solo le righe dell'area IM (area 1.048 → 83: 18
>   `SettingToggle`, 14 `supportLinks`, 28 + `#ffffff` `DonationPopupModal`, 21 `AboutTab`, 1 `ProfileTab`, 1
>   `SocialShareModal`).
> - Backlog: voci IM-1…IM-6 nella sezione IM.
>
> **⚠️ Fuori pista**: la Vitest dei lotti è partita mentre il carico tornava a 86 (era 44 un minuto prima, al primo
> controllo); è durata pochi secondi. Non eseguiti: `front check`, `component-unit`, E2E (slot pesante).

### A6 · Checkpoint 1 ✅ 16/10

> **Note implementazione**: il coordinatore ha committato i lotti IM-1…IM-6 (senza Donation) come **`b5abcbdaa`**
> (23 file) e ha fatto la base merge con `e36e45f0d`, che porta i ruoli nuovi di T (`text-lf-on-overlay`,
> `*-gain-soft`, `*-loss-soft`, `success-hover`, `info-hover`): **`d95d6236c`**, `--check` pulito, nessun `--resolve`.
> Dopo la merge, `api sync` rilanciato con carico 49,6 (esito 0, solo file ignorati).

### A7 · Fotocamera, `DonationPopupModal`, C4 ✅ 16/10

> **Note implementazione**:
> - `ProfileTab`: l'icona della fotocamera sul fondale passa da `text-white` a `text-lf-on-overlay` (ruolo provvisorio
>   di T, `f043c1b58`): 1 → 0 classi.
> - `DonationPopupModal`, con l'OK di A (16/10, girato dal coordinatore: nessun lavoro di A aperto su quei file),
>   seguendo la testata di `LoginCard`:
>   - testata `bg-lf-brand`, logo `bg-lf-logo` al posto di `style="background:#fff"`, nome `text-lf-on-brand`;
>   - corpo, area di supporto e piede `bg-lf-card`; caffè `text-lf-donate`; titolo `text-lf-primary`; messaggio
>     `text-lf-secondary`; nota della donazione `text-lf-link`;
>   - riquadro di `SupportActions`: da `bg-white/70` a `bg-lf-panel border border-lf-subtle shadow-sm
>     shadow-lf-shadow-card`;
>   - «Più tardi» `bg-lf-panel text-lf-secondary hover:bg-lf-neutral`.
>
>   Risultato: 28 → 0 classi, `#ffffff` → nessun colore scritto a mano.
> - **C4**: con Donation spariscono gli ultimi usi di `bg-libre-beige` e `text-libre-dark` (tutti nell'area IM). Il gate
>   (`p1Classes` contro `classUses`) le dava morte: tolte da `app.css` le due regole `html.dark .bg-libre-beige` e
>   `html.dark .text-libre-dark`, e nient'altro (diff di 10 righe, solo cancellazioni).
> - Prove leggere, sotto `nice -n 10` con carico < 50: `--check` pulito; gate 66/66 (C4 compreso); Prettier sui 3
>   file conforme; `git diff --check` pulito; regola 8 e colori solo `dark:` per elemento: 0 casi; `dark_only_check.py`
>   del coordinatore: 0. Vitest `features/support/**`, `ProfileTab`, `DeferredAppPopups`, `themeModeReads.gate`: 8
>   file, 194 test verdi.
> - `--update`: m1 7.284 → 7.255, m2 49 → 48. Area IM: m1 1.048 → **54**, m2 6 → **0**. Restano `SettingToggle` 18
>   (interruttori, T), `supportLinks` 14 (marchi), `AboutTab` 21 (famiglie di plugin, cuore), `SocialShareModal` 1
>   (bottone «copia» col marchio).
> - Backlog: IM-1 e IM-2 chiuse.
>
> **⚠️ Fuori pista**:
> - Togliendo le due regole da `app.css` ho cancellato per errore anche `html.dark .text-libre-green`, che ha ancora
>   usi fuori area. L'ho rimessa identica subito dopo, prima di ogni prova; il diff finale contiene solo le due regole
>   morte.
> - Fra le 11:53 e le 11:57 la rete è caduta e il turno si è chiuso con errore. Le tre modifiche erano già su disco;
>   ripreso alle 12:00 con lo stato verificato da `git status`.
>
> Il coordinatore l'ha committato come **`8636a368f`** (6 file; `app.css` controllato: solo le due regole morte) e ha
> fatto la base merge con `be911db7e` (G-18, fix dello scanner di T): **`53b6dd352`**, `--check` pulito.

### A5 · Slot pesante ✅ 16/10

> **Note implementazione**: slot 1 della 1.3, assegnato dal coordinatore alle 12:24 con taglio alle 13:15 e nessun
> passo nuovo dopo le 13:08. HEAD `53b6dd352` pulito, corsia `--test-port 6159` + `--data-dir /tmp/librefolio-r2-im`,
> in serie con lo script `im_heavy_slot.sh` della cartella di sessione (log completi in `heavy/`). Due Playwright
> worker erano permessi con carico < 35: alla partenza di ogni E2E il carico era fra 44 e 150, quindi sempre 1 worker.
>
> | Passo | Comando (`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py …`) | Esito | Durata | Carico |
> |---|---|---|---|---|
> | client API | `api sync` | 0 | 47 s | 32 |
> | build | `server --test --build-only --port 6159 --data-dir /tmp/librefolio-r2-im` (frontend di debug, MkDocs, cache JS, nessun bind) | 0 | 7 min 25 s | 36→128 |
> | tipi | `front check` | 0 errori, 0 avvisi | 60 s | 128 |
> | Vitest | `test … front-utility component-unit` | 154 file, **4.027 test** verdi | 4 min 52 s | 119 |
> | E2E | `test … front-utility settings` | **56/56** (con fx-chart-settings e plugin-settings, per il filtro di Playwright) | 7 min 19 s | 122 |
> | E2E | `… front-utility scheduler` | **17/17** | 2 min 25 s | 132 |
> | E2E | `… front-utility support-copy-and-go` | **16/16** | 2 min 43 s | 150 |
> | E2E | `… front-utility image-crop "Avatar - Profile Settings"` | **6/6** | 1 min 12 s | 56 |
> | E2E | `… front-user account-deletion` | **1/1** | 1 min 41 s | 48 |
> | E2E | `… front-utility auth` | **34/34** | 4 min 18 s | 46 |
> | E2E | `… front-utility changelog-locale` | **2/2** | 1 min 25 s | 116 |
> | E2E | `… front-utility app-start-auth` | **3/3** | 55 s | 81 |
> | E2E | `… front-utility onboarding-tour` | **10/10** | 1 min 33 s | 74 |
> | E2E | `… front-utility email-verification` | **5/5** | 58 s | 48 |
> | E2E | `… front-utility document-title` | **22/22** | 3 min 16 s | 45 |
>
> Totale E2E: **172 test, 0 rossi, 0 flaky, 0 saltati**; slot finito alle 13:06:35 (2.509 s). Porta 6159 libera
> (`lsof -nP -iTCP:6159 -sTCP:LISTEN` vuoto), worktree pulito. Artefatti ignorati da git: build del frontend, sito
> MkDocs, client API generato, log e snapshot del DB del runner (cartella dei log di prova), dati in
> `/tmp/librefolio-r2-im` (29 MB).
>
> **⚠️ Fuori pista**: nessuno. Il carico alto (fino a 150, altre corsie) ha allungato la build, non ha dato rossi.

## Chiusura

- **Area IM (16/10, dopo `8636a368f`):** m1 1.048 → **54**, m2 6 → **0**. Restano solo elementi lasciati di proposito,
  ognuno con la sua voce nel backlog:
  - `SettingToggle` 18: interruttore, lotto unico di T;
  - `supportLinks.ts` 14 e il bottone «copia» di `SocialShareModal` 1: marchi dei social (IM-5);
  - `AboutTab` 21: famiglie di plugin categoriali (IM-3) e il cuore (IM-4).
- **Catene:** il badge del provider nel log dello scheduler segue `PROVIDER_COLORS` (IM-6, fuori area).
- **Definition of done:**
  - file dei lotti senza classi legacy oltre i «resta» dichiarati;
  - `--check` e gate verdi, `front check` 0/0, Vitest e E2E dei lotti verdi;
  - porta libera, voci IM-n per i residui.
- **Resta da fare, fuori da IM:**
  - la revisione dell'aspetto del developer, dal foglio di confronto della galleria (D-T21), con i «da rivedere» del §5
    e di A3;
  - la galleria di fine giornata di G.
