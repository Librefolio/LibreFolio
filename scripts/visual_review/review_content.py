"""Content of the LibreFolio v1.2 colour review (October 2026), kept apart from the tools.

The builders (``build_designer_package``, ``build_review_notes``) are generic; everything here is
review-specific: area order and titles, the per-area hints drawn from the code analysis, the
"already known" list, the questions for the designer, the current-palette table and the
Markdown templates of the team notes. Update it before the next review: the hints quote file
lines and colour values that were true at commit 27228466c and will drift with the code.

Strings are Italian on purpose: they are read by the designer, not by developers.
"""

# Area order follows the app navigation; titles are what the designer reads.

ORDER = ["auth", "onboarding", "dashboard", "security", "settings", "tools", "support", "files", "transactions", "brokers", "media", "fx", "assets", "risk"]
TITLES = {
    "auth": "Accesso e registrazione",
    "onboarding": "Onboarding (primo accesso, tour, guide)",
    "dashboard": "Dashboard",
    "security": "Sicurezza connessione",
    "settings": "Impostazioni",
    "tools": "Strumenti (PAC Allocator)",
    "support": "Supporto e donazioni",
    "files": "File",
    "transactions": "Transazioni",
    "brokers": "Broker e importazioni",
    "media": "Immagini e upload",
    "fx": "Cambi (FX)",
    "assets": "Asset",
    "risk": "Laboratorio di rischio",
}

# Shots that exist only on one viewport by design (not a capture failure).
MOBILE_ONLY = {"menu-open"}

# Per-area hints from the code analysis (Markdown inline: `code`, **bold**, *italic*).
LOOK = {
    "auth": [
        "Riquadro bianco del logo identico anche in scuro, ora sul ruolo `bg-lf-logo` (`LoginCard.svelte:45`, `RegisterCard.svelte:153`, `ForgotPasswordCard.svelte:16`) — P10.",
        "Indicatore di robustezza password solo con colori chiari, senza varianti scure (`PasswordStrength.svelte`).",
        "Campi in scuro: bordo fisso `#546175`, il verde di focus non compare (P1); contrasto del bordo 2.3:1 (P9).",
        "Bottone primario: `#1a4031` in chiaro; in scuro `#166534` a riposo e `#00d681` al passaggio del mouse (P1, P4).",
        "Sfondo animato del login: gradiente scuro definito a parte in `app.css` (`.animated-bg-gradient`).",
    ],
    "onboarding": [
        "Card di benvenuto scritta come `bg-white dark:bg-slate-900`, ma in scuro diventa `#1e293b` per l'override globale (P1).",
        "Coachmark del tour: colore di anello, fumetto ed evidenziazione.",
        "Avatar con le iniziali: colore generato automaticamente dal testo; verificarne la leggibilità.",
    ],
    "dashboard": [
        "Guadagni e perdite qui sono `green-600/400`, mentre in Asset, FX e Broker sono `emerald` (P4). Le barre KPI invertono le sfumature tra chiaro e scuro (`KpiSection.svelte:223,264`).",
        "Grafico di crescita: linea NAV `#1a4031` / `#4ade80` (diverso dal verde brand scuro `#00d681`); costi arancio qui ma rossi nel grafico Performance; dividendi oro `#b08d00` / `#facc15` (decisione di ottobre 2026); interessi viola.",
        "Allocazione: le palette di «Ora» (torta) e «Storico» hanno ordini diversi, quindi la stessa categoria cambia colore (P6). Lo slot rosso `#dc2626` sembra una perdita (P5). Sottotipi = sfumature del colore padre (decisione D71).",
        "Mappa posizioni (treemap): scala rosso/verde per intensità. In chiaro le perdite più grandi diventano *più chiare*, all'opposto dei guadagni (`ExposureTreemap.svelte:488`). Distinzione solo rosso/verde (daltonismo, P9).",
        "Banner qualità dati: errori e avvisi sono entrambi ambra (`DataQualityBanner.svelte:80`) (P4).",
        "Lotti FIFO: colori dei broker generati dalla posizione in lista, quindi cambiano se si elimina un broker. SPLIT nel Gantt è `#ca8a04` (contrasto 2.94:1, già scartato a ottobre) (P9). Il grafico WAC usa verdi e rossi chiari diversi (`#86efac` / `#fca5a5`).",
        "Scheda Rischio: istogrammi, sott'acqua, simulazioni; confrontare i colori con quelli di Asset e Laboratorio di rischio.",
        "Menu laterale (mobile `menu-open`): `bg-libre-green`, forzato in scuro a `#166534`.",
        "Attenzione: quasi tutta la dashboard della gallery usa dati registrati (REPLAY); dal vivo i numeri e le forme saranno diversi.",
    ],
    "security": [
        "Indicatore di sicurezza della connessione: nessuna variante scura nel componente (`ConnectionSecurityIndicator.svelte`); verificarlo in scuro.",
        "Dal vivo appare solo aprendo l'app da un nome di rete locale, non da `localhost`.",
    ],
    "settings": [
        "Scheda Informazioni: 147 classi colore e solo 4 varianti scure, quindi in scuro si appoggia all'override globale (P1). Riquadro bianco del logo (`AboutTab.svelte:258`).",
        "Log dello scheduler: stati ok, parziale, fallito e saltato senza varianti scure (`syncHelpers.ts:97`). Badge dei provider: ECB blu, MANUAL ambra… (P4).",
        "La pagina Impostazioni non ha varianti scure nel proprio file (`routes/(app)/settings/+page.svelte`).",
        "Changelog, pannello cache, diagnostica: badge di stato e livelli di superficie.",
    ],
    "tools": [
        "PAC: badge e avvisi con una palette propria (successo smeraldo, info sky, avviso ambra, errore rosso) (`planner/ui.ts:80`).",
        "Barre degli obiettivi: «bilanciato» usa il verde brand; eccesso e mancanza non hanno varianti scure (`TargetsStep.svelte:29`).",
        "Barre di esposizione: unico grafico che usa il verde brand scuro `#00d681` (`ExposureBars.svelte:30`). Mappe di esposizione con la scala verde copiata dalla dashboard.",
    ],
    "support": [
        "Popup donazione: riquadro bianco del logo anche in scuro (P10); pulsanti social.",
        "Modale di condivisione: livelli di superficie e campo messaggio.",
    ],
    "files": [
        "Sistema CSS parallelo: `FilesTable`, `FileGrid` e `FilePreviewModal` usano colori esadecimali propri nei blocchi `<style>` (P8). Confrontarli con le altre tabelle e modali.",
        "Etichette con colori generati dal testo (`getStringColor`); badge dei set di report (`FileSetBadges.svelte`: indaco, ambra, grigio, smeraldo, rosso).",
    ],
    "transactions": [
        "Tabella: `DataTable` ha un proprio sistema di colori nei `<style>` (circa 140 righe di hex) (P8): intestazione, righe alternate, hover, selezione, filtri.",
        "Celle importo con bordo verde o rosso di coerenza del segno, senza variante scura (`CompactCashCell.svelte:200`).",
        "Modali (form, editor multiplo, azioni, promozione): sono le più dense di classi colore; controllare la coerenza di bottoni e avvisi.",
        "Non esiste una palette per tipo di transazione (acquisto, vendita, dividendo…): decidere se serve.",
    ],
    "brokers": [
        "Card broker: guadagno smeraldo, perdita `red-600` (altrove `red-500`) (P4).",
        "Colori dei broker generati dalla posizione in lista, usati in badge e grafici dei lotti (P6).",
        "Wizard di importazione: il file con più colori dell'app (527 classi) e una classe inesistente `slate-750`, il cui hover non fa nulla (P3).",
        "Storico importazioni (`BrokerImportFilesModal`) e modale di mancata corrispondenza con hex propri (P8).",
        "Card dei set di report: «completo» in `green`, mentre altrove il successo è smeraldo (P4).",
    ],
    "media": [
        "Modali immagini (modifica, selettore, upload): sistema CSS parallelo con hex propri (P8).",
        "Testo di errore inline `#dc2626` senza variante scura (`AssetPickerModal.svelte:265`).",
    ],
    "fx": [
        "Badge provider: due schemi diversi (`getProviderColor` in HSL e `PROVIDER_COLORS` Tailwind); MANUAL è rosso nel primo e ambra nel secondo (P4).",
        "Card e tabella: variazioni smeraldo e rosso. La linea del grafico sopra o sotto la base usa `#16a34a` / `#ef4444`, un rosso diverso da quello della dashboard (`#dc2626`) (P4).",
        "Segnali: palette di default e colori di ruolo uguali in chiaro e scuro, poco contrastati su sfondo scuro (P9).",
        "Modale di avanzamento della sincronizzazione: stati senza varianti scure.",
    ],
    "assets": [
        "Badge del tipo di asset: 13 tinte diverse (STOCK blu, ETF smeraldo, BOND ambra, CRYPTO viola…) (`assetTypes.ts:109`).",
        "Grafico: candele `#16a34a` / `#ef4444`; il Δ nel tooltip usa un altro verde (`#10b981`) (P4).",
        "Segnali (EMA, RSI, MACD, Bollinger, drawdown): colori scelti per distanza di tinta; ruoli positivo e negativo fissi `#16a34a` / `#dc2626`; misura arancio `#f97316`; uguali in entrambi i temi (P9).",
        "Dettaglio asset: hover con la classe inesistente `slate-750` (`assets/[id]/+page.svelte:3361`) (P3).",
        "Modale di creazione e modifica, editor delle distribuzioni (settori, geografia): colori delle barre.",
    ],
    "risk": [
        "Correlazione rosso↔blu: qui il rosso significa correlazione negativa, non perdita. Enfasi neutra sulla cella selezionata (decisione «hue-free», settembre 2026).",
        "Rischio/rendimento: portafoglio sky, benchmark ambra, punto selezionato verde (`scatterChartHelpers.ts`).",
        "Diversificazione: colori invertiti, valore alto = rosso (`L2Diversification.svelte:312`).",
        "Pannello di analisi: barre rosse e blu senza varianti scure (`RiskAnalysisPanel.svelte:682`).",
    ],
}

# Current palette (de-facto values). A swatch is "#hex" or "tw:<name>" (Tailwind v4 value read from the build).
PALETTE_PIE_LIGHT = "#1a4031 #2563eb #7c3aed #dc2626 #d97706 #0d9488 #be185d #4f46e5 #059669 #ea580c #6366f1 #0891b2 #ca8a04 #9333ea".split()
PALETTE_PIE_DARK = "#4ade80 #60a5fa #a78bfa #f87171 #fbbf24 #2dd4bf #f472b6 #818cf8 #34d399 #fb923c #a5b4fc #22d3ee #facc15 #c084fc".split()
PALETTE_HIST_LIGHT = "#1a4031 #3b82f6 #f59e0b #ef4444 #8b5cf6 #06b6d4 #84cc16 #ec4899 #f97316 #14b8a6 #6366f1 #a3a3a3 #a21caf #7e22ce".split()
PALETTE_HIST_DARK = "#4ade80 #60a5fa #fbbf24 #f87171 #a78bfa #22d3ee #a3e635 #f472b6 #fb923c #2dd4bf #818cf8 #d4d4d4 #e879f9 #c084fc".split()

# (role, kind, light swatches, dark swatches, note); kind: surface | text | fill.
ROLES = [
    ("Sfondo pagina", "surface", ["#f5f4ef"], ["#0f172a"], "chiaro: beige del marchio"),
    ("Superficie (card, modali)", "surface", ["#ffffff"], ["#1e293b"], "in scuro forzata da app.css"),
    ("Superficie secondaria / hover", "surface", ["tw:gray-50", "tw:gray-100"], ["#334155"], ""),
    ("Menu laterale", "surface", ["#1a4031"], ["#166534"], ""),
    ("Testo primario", "text", ["tw:gray-900"], ["#f8fafc"], ""),
    ("Testo secondario", "text", ["tw:gray-600", "tw:gray-700"], ["#cbd5e1"], ""),
    ("Testo attenuato", "text", ["tw:gray-500", "tw:gray-400"], ["#94a3b8"], "gray-400 su bianco ≈ 2.5:1 (insufficiente)"),
    ("Placeholder / disabilitato", "text", ["tw:gray-400"], ["#64748b"], ""),
    ("Bordo", "fill", ["tw:gray-200"], ["#334155"], ""),
    ("Bordo dei campi", "fill", ["tw:gray-300"], ["#546175"], "scuro ≈ 2.3:1 (insufficiente)"),
    ("Marchio / azione primaria", "fill", ["#1a4031"], ["#166534", "#39af50", "#00d681"], "in scuro: pieno · testo · bordi e trasparenze"),
    ("Focus", "fill", ["#1a4031"], ["#4ade80"], ""),
    ("Successo / guadagno (testo)", "text", ["tw:emerald-600", "tw:green-600"], ["tw:emerald-400", "tw:green-400"], "due famiglie in uso"),
    ("Avviso", "text", ["tw:amber-500", "tw:amber-600"], ["tw:amber-400"], ""),
    ("Errore / perdita (testo)", "text", ["tw:red-500", "tw:red-600"], ["tw:red-400"], ""),
    ("Info", "text", ["tw:sky-600", "tw:blue-500"], ["tw:sky-400", "tw:blue-400"], "famiglie in uso (indicativo)"),
    ("Guadagno / perdita (grafici)", "fill", ["#16a34a", "#dc2626", "#ef4444"], ["#4ade80", "#f87171"], "hex sRGB, diversi dalle classi"),
    ("Palette categorie — torta allocazione", "fill", PALETTE_PIE_LIGHT, PALETTE_PIE_DARK, "14 colori"),
    ("Palette categorie — storico allocazione", "fill", PALETTE_HIST_LIGHT, PALETTE_HIST_DARK, "14 colori, ordine diverso"),
]

# Findings the designer does not need to report again (HTML inline allowed).
KNOWN = [
    "In tema scuro alcune regole globali sovrascrivono i colori scritti nei singoli componenti: ciò che si vede in scuro non è sempre quello previsto.",
    "Due grigi diversi convivono: grigio neutro (<i>gray</i>) e grigio-blu (<i>slate</i>).",
    "Lo stesso significato ha colori diversi: guadagno verde nella dashboard e verde smeraldo altrove; errori a volte in ambra; il verde del marchio ha 8 varianti in scuro.",
    "Lo stesso colore ha significati diversi nei grafici: il rosso delle perdite è anche una fetta dell'allocazione.",
    "Le palette dei grafici differiscono tra loro; i colori dei broker cambiano se se ne elimina uno.",
    "Tabelle, file, immagini e conferme hanno uno stile colori proprio.",
    "Accessibilità: testi grigio chiaro poco leggibili; guadagno e perdita distinti solo da rosso e verde.",
    "Splash, pagina offline, icona dell'app e riquadro del logo non seguono il tema.",
    "Lo stesso nome di colore esiste in due versioni: le classi dell'interfaccia (OKLCH, più sature) e i colori dei grafici (hex sRGB). Sugli schermi Mac recenti l'app dal vivo può apparire più satura di questi screenshot.",
]

# First-round questions for the designer.
ASKS = [
    "Colori di sfondo, superfici, testi e bordi, in chiaro e in scuro (la tabella «Palette attuale» qui sotto è il punto di partenza).",
    "Un solo verde del marchio per tema.",
    "Colori per successo, avviso, errore e informazione.",
    "Colori per guadagno e perdita, leggibili anche da chi non distingue il rosso dal verde.",
    "Una palette per le categorie dei grafici: quanti colori e in che ordine.",
    "Il livello di contrasto da garantire (per esempio WCAG AA).",
]

# Markdown templates of the team notes (build_review_notes). Placeholders: commit, date, snap_rel, n_shots.
NOTES_HEADER = """# Note della designer — Review colori LibreFolio

> Versione analizzata: **v1.2** (branch `dev_release2`, commit `{commit}`). Schermate catturate il **{date}**.
> Questo è il file di lavoro della designer: scrivere nei campi **✏️**. Gli sviluppatori lo leggono
> per preparare i token colore e le correzioni. La sintesi tecnica è in il report di sintesi della review.

## 0. Come usare questo file

1. **Prima giornata, giro sui ruoli:** sfogliare la gallery (§1.1) in chiaro e in scuro, poi compilare
   il **vocabolario dei ruoli** (§3) e le **decisioni di base** (§4). Servono valori indicativi, non definitivi.
2. **Giri successivi, schermata per schermata:** per ogni area (§5) ci sono come arrivarci, cosa guardare
   e una riga ✏️ per ogni schermata.
3. Per citare una schermata usare il suo codice, ad es. `dashboard/kpi-top`, aggiungendo tema e
   dispositivo se serve: `dashboard/kpi-top · scuro · mobile`.
4. Spuntare `[x]` le schermate già riviste. Le idee generali vanno in §6.

## 1. Come vedere le cose

### 1.1 Gallery statica (consigliata per iniziare)
- Aprire nel browser **`{snap_rel}/index.html`**: ogni schermata è mostrata in chiaro e in scuro
  affiancate. Ci sono le pagine desktop e mobile, in italiano e in inglese. Cliccando su un'immagine la si vede a piena grandezza.
- Ogni schermata ha un'àncora, ad es. `desktop-it.html#dashboard/kpi-top`. I link «🖥» e «📱» delle tabelle sotto puntano lì.
- Dispositivi: **desktop 1280×720** (alcune schermate desktop sono più alte per mostrare un blocco intero;
  dal vivo bisogna scorrere) e **mobile 430×932** (iPhone 14 Pro Max).
- Le schermate hanno animazioni ferme, puntatore fuori dall'area e dati di esempio. Alcune usano dati
  **REPLAY/MOCK** (indicati nelle tabelle) che dal vivo non si vedono identici.
- I file originali sono in `{snap_rel}/png/<dispositivo>/<lingua>/<tema>/<area>/<nome>.png`.

### 1.2 App dal vivo (per hover, focus, menu e interazioni)
Uno sviluppatore avvia in un terminale:
```bash
scripts/visual_review/designer_live.sh     # dalla radice del repository
```
- Indirizzo: **http://localhost:6160** (server di test con gli stessi dati della gallery; nessun dato reale).
- Accesso: **`e2e_test_admin` / `E2eAdminPass123!`**. È l'utente usato da quasi tutte le schermate.
  `e2e_test_user` / `E2eTestPass123!` è un utente normale.
- **Tema:** pulsante sole/luna nella barra in alto, oppure Impostazioni → Preferenze → Tema (chiaro / scuro / automatico).
- **Lingua:** selettore lingua nella barra in alto.
- Per fermarlo: `Ctrl+C` nel terminale.

### 1.3 Strumenti del browser utili (Chrome / Edge)
- **Colore reale di un elemento:** tasto destro → *Ispeziona* → pannello *Computed* → `color` / `background-color`
  → la freccia mostra quale regola vince. Se la regola è `html.dark …` in `app.css`, è l'override globale (P1):
  in tema scuro il colore scritto nel componente **non** è quello mostrato.
- **Panoramica colori della pagina:** DevTools → ⋮ → *More tools* → **CSS Overview** → *Capture overview*.
  Elenca tutti i colori usati e i problemi di contrasto.
- **Daltonismo:** DevTools → ⋮ → *More tools* → **Rendering** → *Emulate vision deficiencies*
  (protanopia, deuteranopia, tritanopia, acromatopsia).
- **Contrasto puntuale:** nel selettore colore di un elemento (pannello *Styles*) compare il rapporto di contrasto AA/AAA.

## 2. Legenda dei problemi già trovati (dettagli nei report della review)

| Codice | In breve |
|---|---|
| **P1** | In tema scuro alcune regole globali di `app.css` vincono sui colori scritti nei componenti: testi, sfondi bianchi/grigi, bordi dei riquadri arrotondati, bordi e focus dei campi. Va giudicato a schermo. |
| **P2** | Le variabili di tema esistono ma nessun componente le usa; i colori sono scritti a mano ovunque. |
| **P3** | Due scale di grigi mescolate (gray e slate); livelli di superficie scura incoerenti; classi inesistenti. |
| **P4** | Stesso significato, colori diversi: guadagno green o emerald, errore rosso o ambra, info blue o sky, 8 verdi brand in scuro… |
| **P5** | Stesso colore, significati diversi nei grafici: il rosso perdita è anche una fetta di allocazione, ecc. |
| **P6** | Palette dei grafici duplicate, con ordini diversi; colori dei broker che dipendono dalla posizione in lista. |
| **P7** | Logica dei colori duplicata nel codice (badge, stati, segno). |
| **P8** | Tabelle, modali file/immagini e conferme con un sistema di colori proprio. |
| **P9** | Accessibilità: testo grigio chiaro 2.5:1, bordi dei campi scuri 2.3:1, solo rosso/verde per guadagno/perdita. |
| **P10** | Splash, pagina offline, icona dell'app (PWA) e riquadro del logo non allineati al tema. |
| **P11** | Lo stesso nome di colore esiste in due versioni: classi Tailwind v4 (OKLCH, più sature) e hex dei grafici (sRGB). Su un Mac recente l'app dal vivo è più satura degli screenshot. |

## 3. Vocabolario dei ruoli (giro 1)

Ogni riga è un *ruolo*: un colore con uno scopo, che diventerà un token. «Attuale» è il valore più usato
oggi. ✏️ Proporre il valore, oppure lasciare vuoto e scrivere un'indicazione nelle note. Aggiungere o togliere righe liberamente.

| Ruolo | Dove | Attuale chiaro | Attuale scuro | ✏️ Proposta chiaro | ✏️ Proposta scuro | ✏️ Note |
|---|---|---|---|---|---|---|
| Sfondo pagina | dietro a tutto | `#f5f4ef` (beige) | `#0f172a` | | | |
| Superficie (card, modali) | card, pannelli | `#ffffff` | `#1e293b` | | | |
| Superficie secondaria / hover | righe, campi, hover | `#f9fafb` · `#f3f4f6` | `#334155` | | | |
| Menu laterale | sidebar | `#1a4031` | `#166534` | | | |
| Testo primario | titoli, valori | `#111827` | `#f8fafc` | | | |
| Testo secondario | descrizioni | `#4b5563` | `#cbd5e1` | | | |
| Testo attenuato | etichette, note | `#6b7280` · `#9ca3af` | `#94a3b8` | | | `#9ca3af` su bianco: 2.5:1 |
| Placeholder / disabilitato | campi vuoti | `#9ca3af` | `#64748b` | | | |
| Bordo | separatori, card | `#e5e7eb` | `#334155` | | | |
| Bordo campi | input, select | gray-300 / gray-200 | `#546175` | | | scuro: 2.3:1 |
| Brand / azione primaria | bottoni, link | `#1a4031` | `#166534` (pieno) · `#39af50` (testo) · `#00d681` (resto) | | | 8 verdi in scuro |
| Focus | anello di focus | `#1a4031` | `#4ade80` | | | |
| Successo | conferme, stato ok | emerald-600 `#059669` (anche green) | emerald-400 `#34d399` | | | |
| Avviso | attenzione | amber-500 `#f59e0b` / 600 | amber-400 `#fbbf24` | | | |
| Errore / pericolo | errori, elimina | red-500 `#ef4444` / 600 `#dc2626` | red-400 `#f87171` | | | |
| Info | suggerimenti | sky / blue-500 | sky-300/400 | | | |
| Guadagno (testo) | variazioni + | emerald-600 · green-600 | emerald-400 · green-400 | | | |
| Perdita (testo) | variazioni − | red-500 · red-600 | red-400 | | | |
| Guadagno / perdita (grafici) | candele, barre | `#16a34a` / `#dc2626` · `#ef4444` | `#4ade80` / `#f87171` | | | serve un secondo segnale per i daltonici? |
| Neutri grafici | assi, griglia, tooltip | 4 set diversi | 4 set diversi | | | |
| Palette categoriale | allocazioni, serie | 14 colori (torta) ≠ 14 (storico) | 14 + 14 | | | quanti colori servono? |
| Sfondo modale (overlay) | dietro le modali | nero 45–50% | nero 45–50% | | | |

## 4. Decisioni di base (giro 1)

Per ognuna: ✏️ **Decisione** e ✏️ **Perché**. Le domande vengono dalla sintesi tecnica (il report di sintesi della review, §4).

**A — Fondamenta**
- **A1.** Usiamo un solo insieme di colori con un nome per ruolo (i token del §3) al posto delle classi scritte a mano? → ✏️
- **A2.** Scala di grigi unica (più fredda *slate* o più neutra *gray*), uguale in chiaro e in scuro? → ✏️
- **A3.** Un solo verde brand per tema (pieno, testo, focus, sfumature)? Ruolo di beige, salvia `#9caf9c` e scuro `#111111`? → ✏️
- **A4.** Lo sfondo pagina chiaro resta beige o diventa bianco/grigio chiaro? → ✏️
- **A5.** Obiettivo di contrasto: AA (4.5:1 testo, 3:1 grafica e bordi dei campi)? → ✏️

**B — Significati**
- **B6.** Colori di successo, avviso, errore, info, neutro e disabilitato (famiglia e sfumatura, in chiaro e in scuro). → ✏️
- **B7.** Guadagno e perdita (testo, barre, linee) + un secondo segnale per i daltonici (▲▼, motivi, blu/arancio?). → ✏️
- **B8.** Un solo stile per badge, avvisi, toast, focus e overlay; meno livelli di trasparenza. → ✏️
- **B9.** Serve un colore per tipo di transazione (acquisto, vendita, dividendo, commissione…)? → ✏️

**C — Grafici**
- **C10.** Una palette categoriale unica: quanti colori, in che ordine, escludendo i colori riservati (brand, guadagno, perdita). → ✏️
- **C11.** Colori fissi per entrate, costi, dividendi, interessi, portafoglio e benchmark. → ✏️
- **C12.** Assi, griglie e tooltip dei grafici con gli stessi neutri dell'interfaccia. → ✏️
- **C13.** Colori dei broker e dei lotti: stabili e scelti a mano, o generati? → ✏️

## 5. Schermate per area ({n_shots} schermate)

Ogni area ha: tabella di navigazione (🖥 desktop · 📱 mobile apre la gallery), «Cosa guardare» (spunti
dall'analisi, da confermare a schermo) e le righe ✏️ per le note.
**REPLAY/MOCK** = dati finti o registrati: dal vivo non si vede identico.
"""

NOTES_FOOTER = """
## 6. Note generali e idee
✏️

## 7. Registro dei giri di review
| Data | Giro | Partecipanti | Cosa si è deciso |
|---|---|---|---|
| | 1 — ruoli | | |
"""
