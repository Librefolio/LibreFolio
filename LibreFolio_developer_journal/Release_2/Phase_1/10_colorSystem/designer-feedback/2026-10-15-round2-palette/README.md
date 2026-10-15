# Designer · giro 2 — palette «Pietra e Salvia» / «Ardesia e Salvia», domande N1–N6 e Q2–Q13, grafici GR1–GR5 (15/10/2026)

> Ricevuto dal developer il 15/10/2026 alle 15:03 e registrato dal coordinatore colori. Le risposte sono due, perché il
> materiale è partito in due invii:
>
> 1. [`risposta-1-originale.txt`](risposta-1-originale.txt): sulle schermate 01–08 e sulla tabella dei ruoli, con le
>    domande N1–N6 e Q2–Q13.
> 2. [`risposta-2-grafici-originale.txt`](risposta-2-grafici-originale.txt): sulle schermate 09–10 e sulla sezione
>    «Grafici» del documento aggiornato. È un'appendice alla prima.
>
> Il materiale inviato sta in [`materiale-inviato/`](materiale-inviato/):
> - il documento [`tabella-ruoli-e-domande.md`](materiale-inviato/tabella-ruoli-e-domande.md), nella versione finale
>   con la sezione «Grafici»;
> - le 10 schermate annotate;
> - il confronto dei bordi dei campi preparato dopo, [`bordi-dei-campi.html`](materiale-inviato/bordi-dei-campi.html).
>
> La versione HTML del documento, con le miniature della gallery, sta fuori dal repo, in
> `LibreFolio_visual_review/package/round2-palette-2026-10-15/`.
>
> **Decisione del developer, 15/10 alle 15:03 (D-T17).** Testuale: «archiviali opportunamente e poi dai mandato ai vari
> sotto agenti di realizzare quanto pianificato».
> - Il giro 2 è approvato e supera D-T15: la barra laterale torna verde.
> - Il bordo dei campi (N5) resta al 3:1, con un hover nuovo (D-T18); l'header è verde anche su desktop (D-T19). Vedi
>   [`analisi.md`](analisi.md) §1, §2 e §5.
>
> Controlli, interpretazioni e instradamento stanno in [`analisi.md`](analisi.md). Qui sotto c'è la trascrizione
> ordinata dei valori: dove sembra diversa dall'originale, vale l'originale.

## Cosa ha visto

- **Risposta 1:** schermate 01–08, cioè accesso, registrazione, app e telefono, in chiaro e in scuro. Poi la tabella
  dei 52 ruoli e le domande.
- **Risposta 2:** schermate 09 (torta «Ora») e 10 («Storico») e la sezione «Grafici»: 11 tipi, 14 settori, le
  tavolozze di oggi e le scelte GR1–GR5.

## Osservazioni sulle schermate

1. La barra laterale è ancora grigia (`#EDF0EE` / `#111615`): deve diventare verde (vedi A).
2. In scuro le card dentro l'app non sono migrate e restano blu notte.
   - Il riquadro «Profilo / Informazioni Profilo» va su `--lf-surface-card` `#151B19`, con bordo `--lf-border-subtle`
     `#222C28`.
   - La card «Allocazione Patrimoniale» (schermate 09–10, `#18202F`) va su `--lf-surface-card`, con i pulsanti attivi
     su `--lf-action` `#215240` invece del vecchio verde acceso.
3. Le tinte tenue degli stati, calcolate con la ricetta, in scuro sembrano grigio o fango: servono tinte vere (vedi B).

## A · Barra laterale verde, nei due temi (supera N1 e D-T15)

| Ruolo | Valore, chiaro e scuro | Uso |
|---|---|---|
| `--lf-surface-sidebar` | `#1B4334` | fondo della barra, desktop e mobile |
| `--lf-sidebar-border` | `#265946` | divisori interni; bordo destro solo in scuro |
| `--lf-sidebar-text` | `#CFE0D8` | voci inattive (icona e testo), informazioni secondarie |
| `--lf-sidebar-text-muted` | `#8CA89B` | versione dell'app, email sotto il nome |
| `--lf-sidebar-hover` | `#21503E` | passaggio del mouse su una voce inattiva |
| `--lf-sidebar-active-bg` | `#285E49` | voce attiva |
| `--lf-sidebar-active-text` | `#FFFFFF` | testo e icona della voce attiva |
| `--lf-sidebar-active-bar` | `#52C493` | barretta verticale a sinistra della voce attiva |
| `--lf-sidebar-logout-bg` | `#153529`, hover `#21503E` | pulsante «Esci» |

- **Bordo destro:** non serve in chiaro, perché lo stacco col fondo dell'app basta. In scuro, `1px` `#265946`.
- **Stato della connessione** sulla barra verde: sempre i colori di stato del tema scuro. Sicura `#36D399`, locale
  `#FBBF24`, non sicura `#F87171`.
- **Riquadro del logo:** resta bianco (`--lf-surface-logo` `#FFFFFF`), per far risaltare lo scudo sul verde.

## B · Colori degli stati

Le tinte tenue diventano valori espliciti, al posto della ricetta 8/25/60 % in chiaro e 6/22/37 % in scuro.

| Ruolo | Chiaro | Scuro | Nota |
|---|---|---|---|
| `--lf-warning` | `#B45309` | `#F59E0B` | in chiaro era `#9A5B00`: ambra viva, meno marrone |
| `--lf-warning-soft` | `#FEF3C7` | `#291E0C` | |
| `--lf-warning-line` | `#FDE68A` | `#54380E` | |
| `--lf-warning-on-soft` | `#92400E` | `#FCD34D` | |
| `--lf-danger-soft` | `#FEE2E2` | `#2A1417` | |
| `--lf-danger-line` | `#FECACA` | `#581C24` | |
| `--lf-danger-on-soft` | `#991B1B` | `#FCA5A5` | |
| `--lf-info-soft` | `#DBEAFE` | `#131F33` | |
| `--lf-info-line` | `#BFDBFE` | `#1E3A5F` | |
| `--lf-info-on-soft` | `#1E40AF` | `#93C5FD` | |
| `--lf-success-soft` | `#E6F4ED` | `#13261E` | |
| `--lf-success-line` | `#B8DFCA` | `#1F4435` | |
| `--lf-success-on-soft` | `#145937` | `#86EFAC` | |

## N1–N6

- **N1 · Barra laterale:** risolta da A.
- **N2 · Barra del telefono con l'app installata (`theme-color`):** `#1B4334` nei due temi. La sua premessa: «essendo
  ora la sidebar e l'header mobile verdi `#1B4334`, l'integrazione con la status bar del telefono sarà continua».
- **N3 · Bordo della card di accesso in scuro:** un valore intermedio, dedicato alle card in rilievo (accesso, modali,
  menu a tendina).
  - Chiaro: resta `#D8E0DC` (`--lf-border-subtle`).
  - Scuro: `#2E3B36`.
- **N4 · Sottotitolo «Crea un account»:** confermato, non torna.
- **N5 · I sei valori corretti per la leggibilità:**
  - approvati `--lf-text-muted` (`#616D67` / `#7F8C87`), `--lf-danger` scuro (`#F84361`), `--lf-info` scuro
    (`#3F86FA`);
  - **bordo dei campi:** chiede di ammorbidirlo, `#94A09B` in chiaro e `#43524D` in scuro, «passando a `#606F6A` solo
    in `:hover`». **Deciso dal developer (D-T18):** restano `#7E8984` / `#606F6A`, con hover `#616D67` / `#7F8C87`;
    vedi [`analisi.md`](analisi.md) §2.
- **N6 · Colline e linee del login:**
  - niente pallini sulle linee;
  - chiaro: invariato (`#9BAF9B` al 25, 18 e 12 %, linea `#1A4235` al 30 %);
  - scuro: `--lf-art-hill-1` `#16221D`, `--lf-art-hill-2` `#121C18`, `--lf-art-hill-3` `#0F1714`, `--lf-art-line`
    `#3B5249` (oppure `#4A665B` al 55 %).

## Q2–Q13

- **Q2 · Interruttore spento:** mai verde.
  - Chiaro: traccia `#CBD4D0`, pallino `#FFFFFF` con bordo o ombra leggera.
  - Scuro: traccia `#2C3834`, pallino `#9BA8A2`.
  - Acceso in scuro: pallino `#FFFFFF` o `#EDF2F0` sulla traccia `#429E79`.
- **Q3 · Pulsanti pieni al passaggio del mouse:**
  - errore: chiaro `#A81F2D`, scuro `#E12D4B`, testo bianco `#FFFFFF` sui pulsanti rossi pieni (per esempio «Elimina
    account»);
  - avviso e donazione: chiaro `#92400E`, scuro `#D97706`.
- **Q4 · Stato «modificato» nelle impostazioni:** i ruoli dell'avviso (`--lf-warning`, `-soft`, `-line`).
- **Q5 · Pallino «inattivo» del log dello scheduler:** `--lf-text-muted`.
- **Q6 · Codice e terminale:**
  - codice nel testo: fondo `--lf-surface-panel`, bordo `--lf-border-subtle`, testo `--lf-text-primary`;
  - blocco terminale: sempre scuro nei due temi. Fondo `#0D1110`, bordo `#222C28`, testo `#EDF2F0`, prompt e comandi
    `#36D399`.
- **Q7 · Evidenziazione dei risultati (`<mark>`):**
  - chiaro: fondo `#FDE68A`, testo `#1C2420`;
  - scuro: fondo `#78350F`, bordo sottile `#B45309`, testo `#FEF3C7`.
- **Q8 · Ombre:** finestre modali e menu a tendina `#0D1110` al 25 % in chiaro e al 50 % in scuro; card della pagina
  in chiaro al 6–8 %.
- **Q9 · Tour guidato:** alone in `--lf-focus` al 40 %; sfondo = `--lf-surface-overlay`.
- **Q10 · Avviso dentro un tooltip:** l'avviso del tema opposto, perché il tooltip ha il fondo invertito. `#F59E0B` sul
  tooltip scuro del tema chiaro, `#B45309` sul tooltip chiaro del tema scuro.
- **Q11 · Viola dell'AI Export:** resta un accento distinto per le funzioni AI.
  - Chiaro: principale `#6D28D9`, fondo tenue `#F3E8FF`, bordo `#DDD6FE`.
  - Scuro: principale `#A78BFA`, fondo tenue `#1E1B2E`, bordo `#3B3054`.
- **Q12 · Icone della scheda «Informazioni»:** niente arcobaleno. Tutte uguali: badge su `--lf-surface-panel`, icona
  in `--lf-focus`.
- **Q13 · Fondale delle finestre:** `#0D1110` al 60 % nei due temi. Il `#0D1111` della tabella era un errore di misura
  (vedi `analisi.md` §5).

## GR1–GR5 · Grafici (risposta 2)

- **GR1 · Colore fisso per categoria: sì.** Uguale tra torta («Ora») e storico, in ogni portafoglio, broker e periodo.
- **GR2 · Niente rosso e verde semantici nelle categorie.**
  - Fuori il rosso di errore e perdita (`#C82838` / `#F84361`) e il verde acceso di guadagno (`#36D399` / `#4ADE80`).
  - Il verde del marchio solo per la Liquidità.
  - Toni caldi su ambra e oro, rame e terracotta, rosa malva e prugna.
- **GR3 · Liquidità:** colore suo, fisso. Chiaro `#2D6A54`, scuro `#429E79`.
- **GR4 · Sottotipi:** sfumature della famiglia nell'anello esterno della torta, con una regola deterministica.
  - Chiaro: luminosità HSL +8, +15, +22 %, oppure miscela col bianco al 15, 30, 45 %.
  - Scuro: luminosità −10, +10, −20 %, oppure miscela verso `--lf-surface-card` `#151B19` al 18, 32, 45 %, così non
    diventano mai slavati.
- **GR5 · Tutte le altre tavolozze seguono la famiglia nuova, ciascuna con la sua versione scura.**
  1. Mappa geografica, 6 verdi:
     - chiaro `#E6F2ED` → `#C2E0D3` → `#94C7B2` → `#62AB8E` → `#378567` → `#1B4334`;
     - scuro `#182923` → `#1F3B30` → `#275241` → `#316B54` → `#3D876A` → `#4FB38B`.
  2. Semi-ciambella delle quote e indicatori tecnici: i primi 8 colori della tavolozza nuova, secondo il tema attivo.
  3. Matrice di correlazione: centro `--lf-surface-panel` (`#E8ECE9` / `#1B2421`); estremi `--lf-danger` (`#C82838` /
     `#F84361`) e `--lf-info` (`#155EEF` / `#3F86FA`).
  - Storico geografico e classifiche senza chiave fissa: i colori dei settori nell'ordine della tabella, 16 tinte prima
    di ripetersi.

### Tipi di asset (11 + Liquidità)

| # | Chiave | Nome | Emoji | Chiaro | Scuro | Tinta |
|---|---|---|---|---|---|---|
| 1 | `STOCK` | Azione | 📈 | `#6D28D9` | `#A78BFA` | viola ametista |
| 2 | `ETF` | ETF | 📊 | `#1D5BD8` | `#60A5FA` | blu cobalto |
| 3 | `BOND` | Obbligazione | 🏛️ | `#0E7490` | `#22D3EE` | ottanio |
| 4 | `CRYPTO` | Cripto | 🪙 | `#D97706` | `#FBBF24` | ambra, oro |
| 5 | `FUND` | Fondo | 💼 | `#4338CA` | `#818CF8` | indaco |
| 6 | `HOLD` | Bene detenuto | ⏸️ | `#5F6B7A` | `#94A3B8` | blu ardesia |
| 7 | `CROWDFUND` | Crowdfunding | 🤝 | `#0D9488` | `#2DD4BF` | verde acqua |
| 8 | `COMMODITY` | Materia prima | 🛢️ | `#C25E00` | `#FB923C` | rame, terracotta |
| 9 | `REAL_ESTATE` | Immobiliare | 🏠 | `#B45309` | `#F59E0B` | ocra, mattone |
| 10 | `INDEX` | Indice | 📉 | `#A21CAF` | `#E879F9` | prugna, orchidea |
| 11 | `OTHER` | Altro | 📦 | `#6E7A74` | `#7F8C87` | grigio pietra |
| + | `Liquidity` | Liquidità | 💰 | `#2D6A54` | `#429E79` | verde salvia del marchio |

### Settori (14 + Liquidità + Non classificato), con le emoji unificate tra torta e storico

| # | Chiave | Nome | Emoji | Chiaro | Scuro | Tinta |
|---|---|---|---|---|---|---|
| 1 | `Industrials` | Industriali | 🏭 | `#475569` | `#94A3B8` | acciaio, ardesia |
| 2 | `Technology` | Tecnologia | 💻 | `#1D5BD8` | `#60A5FA` | blu cobalto |
| 3 | `Financials` | Finanziari | 🏦 | `#0F766E` | `#2DD4BF` | verde acqua |
| 4 | `Consumer Discretionary` | Beni voluttuari | 🛍️ | `#7C3AED` | `#A78BFA` | viola |
| 5 | `Health Care` | Sanità | 🏥 (unificata) | `#0284C7` | `#38BDF8` | azzurro ceruleo |
| 6 | `Real Estate` | Immobiliare | 🏠 (unificata; 🏢 resta alle obbligazioni societarie) | `#B45309` | `#FBBF24` | ocra, ambra |
| 7 | `Basic Materials` | Materie prime | ⛏️ | `#9A3412` | `#FB923C` | terracotta, rame |
| 8 | `Energy` | Energia | ⚡ | `#D97706` | `#FACC15` | oro, giallo |
| 9 | `Consumer Staples` | Beni di consumo | 🛒 | `#4D7C0F` | `#A3E635` | oliva, lime |
| 10 | `Telecommunication` | Telecomunicazioni | 📡 | `#4338CA` | `#818CF8` | indaco |
| 11 | `Utilities` | Servizi pubblici | 💡 (unificata) | `#0E7490` | `#22D3EE` | ottanio |
| 12 | `Corporate Bonds` | Obbligazioni societarie | 🏢 | `#86198F` | `#E879F9` | prugna |
| 13 | `Government Bonds` | Titoli di Stato | 🏛️ | `#1E3A8A` | `#93C5FD` | blu navy |
| 14 | `Other` | Altro | 📦 | `#6E7A74` | `#7F8C87` | grigio pietra |
| + | `Liquidity` | Liquidità | 💰 (unificata con i tipi) | `#2D6A54` | `#429E79` | verde salvia del marchio |
| + | `Unknown` | Non classificato | ❓ | `#94A09B` | `#52605B` | grigio nebbia |

Alla fine la designer chiede se gli abbinamenti principali (ETF blu, Azione viola, Obbligazione ottanio, Cripto oro,
Liquidità salvia) corrispondono al modo in cui il developer legge il suo portafoglio.
