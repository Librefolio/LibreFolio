# Giro 1 della designer: analisi e piano per applicarlo (14/10/2026)

> **Decisioni del developer, 14/10 sera, dopo questa analisi.** Cambiano la strategia del §4.
>
> - **D-T1:** si apre T subito, in parallelo a R.
> - **D-T2:** il developer ha sentito la designer. Testuale: «voleva che il verde della barra menù fosse lo stesso che
>   si vede nella card di login in alto, quella dove c'è il logo, sia in chiaro che in scuro (con la declinazione del
>   colore), l'avorio dovrebbe essere lo sfondo dell'app in chiaro, e l'altro in scuro».
>   - La barra laterale prende il verde della testata nei due temi.
>   - `#F1EDE3`/`#131A17` sono lo **sfondo dell'app**.
>   - «Sfondo pagina» `#F7F4ED`/`#0F1412` resta lo sfondo della pagina di login.
>   - La barra del titolo della PWA segue la barra laterale.
> - **D-T3: soluzione finale subito.** Testuale: «facciamo direttamente quella e attendiamo che i sotto agenti
>   convertano tutti i componenti alla nuova tecnologia, anzi così è più facile vedere componenti che sono rimasti
>   indietro […] o tramite build o tramite rendering».
>   - Quindi niente ritintura delle scale Tailwind né del bianco: la strategia «per leve» del §4 è superata.
>   - Al suo posto: ruoli `--lf-*` e utility semantiche usate dai componenti, con una migrazione a ondate.
>   - Un componente non migrato conserva l'aspetto di oggi. Si riconosce nel rendering (gallery) e nel build (un gate a
>     cricchetto sulle classi di palette).
>
> Il resto dell'analisi (dove vivono i ruoli, contrasti, dipendenze, domande per la designer) resta valido.
>
> Coordinatore colori, 14/10/2026 sera. La richiesta, trascritta, sta nel [README](README.md); l'originale in
> [`note-originali.txt`](note-originali.txt).
>
> Verifiche fatte sul codice di `dev_release2` (`frontend/src` identico alla v1.2) e sull'inventario della v1.2.
> Script fuori repo: `/tmp/libreFolio_designer_round1_check.py` e `/tmp/libreFolio_designer_round1_fix.py`.

## 0. In breve

- **Si può fare subito, e quasi senza toccare i componenti.** I colori dell'app passano da poche leve centrali:
  - le scale di Tailwind, cioè le variabili `--color-gray-*`, `--color-slate-*` eccetera, che le classi leggono a runtime;
  - lo strato del tema scuro di `app.css`, che instrada fondi, testi e bordi su 16 variabili `--theme-*`;
  - i token del marchio `--color-libre-*`.

  Ritingere quelle leve sui suoi valori cambia l'aspetto di tutta l'app, senza toccare le 10.700 classi.
- **Restano a parte:**
  - **i grafici e i componenti con stile proprio.** R li ha raccolti nelle tabelle di `lib/theme/` (lotto B) e li porta in
    variabili `--lf-cmp-*` (lotto C, in corso): si aggiornano lì, dopo l'ingresso dei rispettivi lotti;
  - **le schermate di accesso**, per le richieste di markup: icone, sottotitolo, box dei requisiti.
- **Il Designer Lab diventa lo strumento della designer.** Le leve sono variabili CSS, quindi le modifica dal vivo e
  l'agente applica l'export. La gallery mostra il risultato su tutte le 177 schermate.
- **Proposta:** aprire il workstream **T (token e tema)** con la fase **B1, fondamenta** (`app.css` e un nuovo
  `lib/theme/tokens.css`), nessun componente.
- **Contrasti:** cinque valori vanno corretti di poco (§3). Mancano alcuni ruoli (§6).

## 1. Dove vive oggi ogni suo ruolo

| Ruolo | Chiaro, oggi | Scuro, oggi | Leva per applicare il suo valore |
|---|---|---|---|
| Sfondo pagina | `bg-libre-beige` (`--color-libre-beige` `#f5f4ef`): layout, header, benvenuto, errori | `html.dark .bg-libre-beige` → `--theme-bg-primary` (P1) | `--color-libre-beige`; `--theme-bg-primary` |
| Card | `bg-white` (394 usi) | `html.dark .bg-white` → `--theme-bg-card` | `--color-white`, che però vale anche per `text-white` (210 usi; vedi D-T3); `--theme-bg-card` |
| Card di login e registrazione | `bg-libre-beige`, cioè il colore della pagina | colore della pagina | componente (B3): la card deve usare il ruolo card |
| Superficie secondaria | `bg-gray-50/100` | `--theme-bg-secondary/tertiary` | scala `gray`, gradini 50 e 100; variabili `--theme-*` |
| Menu laterale | `bg-libre-green`, voci `text-white`, attiva `bg-white/20` (`Sidebar.svelte`) | `#166534` forzato | avorio: si rifà il componente (testi, voce attiva, hover); verde: basta il token |
| Testo primario, secondario, attenuato | `text-gray-900/800`, `600/700`, `500/400` | `--theme-text-primary/secondary/muted` (P1) | scala `gray`, gradini 900, 600, 500; variabili `--theme-*` |
| Bordo, bordo dei campi | `border-gray-200/100`; campi `border-gray-300/400` | `--theme-border-primary`; campi `#546175` scritto in `app.css` | scala `gray`, gradini 200 e 300; ruoli in `app.css` |
| Verde marchio e azione | `--color-libre-green` `#1a4031` (`bg-libre-green` in 107 file) | variabile `#00d681` per le varianti; `.bg-libre-green` `#166534`; `.text-libre-green` `#39af50`; anello `#4ade80` | `--color-libre-green`; `--color-libre-banner`, oggi inutilizzato, per le testate; le quattro regole scure di `app.css` |
| Focus | `focus:border/ring-libre-green` | anello `#4ade80`; il bordo di focus dei campi è annullato da `html.dark input` (P1) | ruolo focus; correggere la regola dei campi |
| Stati | scale emerald e green (554 usi), amber (831), red (684), blue e sky (364); le liste di classi sono in `lib/theme/toneClasses.ts` (R, lotto A) | `dark:` delle stesse scale | scale degli stati riancorate ai suoi valori (B2) |
| Grafici | tabelle di `lib/theme/chartTheme.ts`, `chartPalettes.ts` (R, lotto B) | coppie `themed()` | i valori nelle tabelle (B4) |
| Tabelle, media, file, dialoghi | `<style>` dei componenti; diventano `--lf-cmp-*` (R, lotto C) | gemelle `-dark` | i valori `--lf-cmp-*` (B5) |
| Sfondo del login | `AnimatedBackground.svelte`: fondo `#f5f4ef`, colline `#9caf9c` | fondo `#11151c`, colline `#00ff9a`, linee `#4ade80`, gradiente `.animated-bg-gradient` in `app.css` | componente e `app.css` (B3) |
| Requisiti della password | `PasswordStrength.svelte`: ✓ e ✗ già presenti, quindi non solo colore; ✓ `green-600/700`, ✗ `gray-400/500` su `bg-gray-50` | il `green-700` non è riscritto: è il testo poco leggibile che ha notato | componente (B3) |

**Uso delle scale (v1.2, file non di test):**
- `gray` 5.462 usi: base del chiaro, da 50 a 900;
- `slate` 1.788 usi: base dello scuro, soprattutto `dark:` 600–900 (404, 721, 258 e 68 usi);
- `white` 645 usi: `bg` 394, `text` 210;
- nessun uso di `zinc`, `neutral` e `stone`.

## 2. Cosa chiede, in termini di lavoro

| Richiesta | Lavoro | Fase |
|---|---|---|
| Palette chiara e scura per tutto il progetto | scale neutre, marchio, ruoli e strato scuro | B1 |
| Stati (successo, avviso, errore, info) | scale degli stati riancorate | B2 |
| Icone nei campi di login e registrazione | `LoginCard`, `RegisterCard`, `PasswordInput` (icona a sinistra; colore attenuato, avorio al focus in scuro) | B3 |
| Togliere «Crea un account» | `RegisterCard.svelte:157`; la chiave `auth.registerTitle` resta senza usi e va tolta dai cataloghi | B3 |
| Box dei requisiti | `PasswordStrength.svelte`, con i colori del §4 | B3 |
| Colline e linee del login | `AnimatedBackground.svelte`, `app.css` | B3 |
| Grafici e tabelle in scuro (proposta di Gemini) | non definiti: per ora i ruoli neutri, la palette dei dati in un giro successivo | B4, B5 |

## 3. Contrasti (WCAG 2.2: testo 4,5:1, componenti 3:1)

I suoi testi e i suoi stati passano quasi tutti, e spesso con margine: testo primario 12,8:1 in chiaro e 15:1 in scuro,
errore 6,1:1 in chiaro e 5,3:1 in scuro. Restano cinque punti.
Per ognuno, la correzione più piccola: stesso tono e stessa saturazione OKLCH, cambia solo la luminosità.

| Coppia | Ora | Correzione minima | Dopo |
|---|---|---|---|
| Chiaro · bordo dei campi `#B9AE9B` su campo e card | 2,0:1 (componente < 3:1) | `#978C7A` | 3,0:1 |
| Chiaro · testo attenuato `#687066` su superficie 2 `#EEE9DE` | 4,23:1 | `#636B61` | 4,56:1 |
| Chiaro · successo `#18794E` su superficie 2 | 4,47:1 | `#17784D`: invisibile, si può lasciare | 4,53:1 |
| Scuro · testo attenuato `#758078` su card, campo, superficie 2, box requisiti | 3,7–4,4:1 | `#848F87` | 4,52:1 |
| Scuro · bordo dei campi `#38463F` su campo e card | 1,7–1,8:1 | `#5D6C64` | 3,0:1 |

Da sapere, non da correggere per forza:
- **Pulsante d'azione scuro:** `#245A46` su card `#171F1C` ha 2,1:1. Il pulsante si riconosce dal testo (8:1).
- **Testata scura:** `#1B4334` su pagina ha 1,7:1, ma è decorativa.
- **Box dei requisiti in chiaro:** il «fondo verde molto tenue» non ha un valore. Proposta: `#E8F8EE`, su cui
  - testo `#1B4334`: 10:1;
  - ✓ `#18794E`: 4,9:1;
  - non soddisfatto `#687066`: 4,7:1.

## 4. Il piano: ritingere alla fonte, poi i componenti

> ⚠️ **Superato dalla decisione D-T3 del developer** (in testa al documento): niente ritintura delle scale e del bianco;
> ruoli e utility, con la migrazione dei componenti. Il testo resta come storia del ragionamento. Restano validi l'uso
> dei ruoli `--lf-*`, la sequenza B2–B6 e i vincoli.

**B1 · Fondamenta.** Tocca solo `app.css` e il nuovo `lib/theme/tokens.css`: nessun componente.

1. **Ruoli.**
   - `tokens.css` dichiara i 16 ruoli come `--lf-*`, chiari su `:root` e scuri su `html.dark`. Ci sono anche il fondo
     dei campi, l'azione con il suo hover, le colline, le linee e il box dei requisiti.
   - Le variabili `--theme-*` diventano `var(--lf-*)`.
   - I valori scritti nello strato scuro di `app.css` (`#546175`, `#39af50`, `#166534`, `#4ade80` e il gradiente del
     login) diventano ruoli.
2. **Scale neutre ridefinite in `@theme`**, con gli stessi nomi di classe e valori nuovi:
   - **`gray`, «sabbia → carbone oliva»:**
     - 100 = superficie 2 `#EEE9DE`;
     - 200 = bordo `#DDD5C7`;
     - 300 = bordo dei campi;
     - 500 = attenuato;
     - 600 = secondario `#555C53`;
     - 900 = primario `#292D27`;
     - gli altri gradini interpolati in OKLCH.
   - **`slate`, «avorio → notte nel bosco»:**
     - 900 = pagina scura `#0F1412`;
     - 800 = card `#171F1C`;
     - 700 = bordo e superficie 2 scuri;
     - 600 = bordo dei campi;
     - 400 = attenuato;
     - 300 = secondario `#A8B0A8`;
     - 100 = primario `#EAE6DF`;
     - 50 = avorio caldo per i suoi pochi usi in chiaro.

   Le classi `gray` e `slate` già usate nei due temi prendono così i ruoli giusti: `slate` è la base dello scuro, `gray`
   quella del chiaro.
3. **Marchio:**
   - in chiaro `--color-libre-green` `#1B4334`;
   - `--color-libre-banner` `#1B4334` in tutti e due i temi, per le testate: un cambio di classe nelle 3 card di accesso
     e nell'errore;
   - in scuro: varianti, testo e anello `#469E76`; azione `#245A46`.
4. **Pagina:** `--color-libre-beige` `#F7F4ED`. Per il bianco vedi D-T3.
5. **Meta del titolo della PWA:** segue la barra laterale, con il gate di R (lotto A, controllo d) che lo ricorda.

**Effetto:** tutta l'app passa al caldo naturale e alla notte nel bosco in un colpo solo, le classi restano quelle di
oggi, e ogni valore si regola dal vivo nel Lab. Grafici e stili propri restano come oggi fino a B4 e B5.

**B2 · Stati.** Le scale `emerald`/`green`, `amber`, `red`, `blue`/`sky` vengono riancorate ai suoi valori:
- in chiaro, i gradini 600 e 700 su successo `#18794E`, avviso `#895000`, errore `#B42332`, info `#155EEF`;
- in scuro, il gradino 400 su `#3DD68C`, `#F5A623`, `#F25F5C`, `#5899FA`;
- tinte e bordi derivati.

Guadagno e perdita seguono successo ed errore, salvo decisione diversa.

**B3 · Schermate di accesso.**
- icone nei campi;
- via il sottotitolo;
- card sul ruolo card;
- box dei requisiti;
- colline e linee: colline `#14241E`, `#192E26`, `#1F382F` e linee `#284238` in scuro, salvia desaturata in chiaro.

**B4 · Grafici.** Dopo l'ingresso del lotto B di R:
- neutri, tooltip e guadagno/perdita delle tabelle di `lib/theme` sui ruoli (`themed()` è già il punto unico);
- la palette dei dati in un giro della designer.

**B5 · Stili propri.** Dopo il lotto C di R, i valori `--lf-cmp-*` passano sui ruoli.

**B6 · Pulizia di P1.** Lo strato scuro di `app.css` resta la leva del tema scuro finché i componenti non usano i ruoli;
lo si toglie con la migrazione delle pagine (P).

**Chiusura.** Il sito MkDocs, a colori definiti: vedi il README del programma.

## 5. Dipendenze e conflitti

- **R:** in B1 non c'è nessun file in comune. Due punti da ordinare:
  - `lib/theme/tokens.css` passa a T: è una sola eccezione alla proprietà di R su `lib/theme/**`;
  - il gate della meta (lotto A) diventa rosso quando cambiano il verde della barra o il marchio, come previsto: T
    aggiorna insieme la coppia, le tre sorgenti e il manifest.
- **L:** il Lab è lo strumento del giro 2. Scale e ruoli sono variabili CSS, quindi la designer li modifica dal vivo (L1)
  sulla build di T ed esporta per l'agente. Serve che L entri presto in `dev_release2`.
- **G:** `AnimatedBackground` (congelamento a t*). B3 viene dopo G, e la gallery deterministica serve a mostrare il
  risultato alla designer.
- **Coordinatore 1.3:**
  - le card di accesso sono di A, che le sposta in `features/auth` e cambia la registrazione (F13). B3 va concordato:
    T lo fa presto, prima di F13, oppure lo fa A con le specifiche di T;
  - la chiave i18n `auth.registerTitle` sta nei loro cataloghi;
  - le nuove schermate della 1.3 usano i ruoli `--lf-*` appena B1 entra.
- **Corsia proposta per T:** 6155, con `/tmp/librefolio-r2-t`.

## 6. Decisioni aperte

**Del developer, per partire:**
- **D-T1** — aprire T con B1 adesso, in parallelo a R.
- **D-T2** — barra laterale: la sua tabella la vuole avorio `#F1EDE3` in chiaro e `#131A17` in scuro, con il verde bosco
  su testata e pulsanti. È un cambio d'identità e chiede di rifare `Sidebar.svelte`; il titolo della PWA la segue.
  Finché non è confermata, B1 tiene la barra verde.
- **D-T3** — il bianco. Ridefinire `--color-white` come card `#FBF8F1` rende crema le card (come chiede) e anche il testo
  bianco su verde (10,5:1, nel suo spirito di «testi avorio»). In alternativa le card restano bianco puro fino alla
  migrazione ai ruoli.

**Della designer, per il giro 2:**
- le cinque correzioni di contrasto del §3, o una sua alternativa;
- il fondo del box dei requisiti in chiaro;
- **ruoli mancanti:**
  - placeholder e disabilitato;
  - hover e premuto del pulsante in chiaro;
  - tinte e bordi di badge e avvisi per stato;
  - guadagno e perdita, se distinti da successo ed errore;
  - sfondo delle modali;
  - neutri e palette dei grafici;
- **info `#155EEF`:** è molto saturo rispetto al resto della palette calda. È voluto?
