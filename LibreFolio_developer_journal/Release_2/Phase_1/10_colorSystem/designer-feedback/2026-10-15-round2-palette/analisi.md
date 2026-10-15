# Giro 2 della designer: controlli, punti aperti e instradamento (15/10/2026)

> Coordinatore colori, 15/10/2026 pomeriggio. I valori trascritti stanno nel [README](README.md), gli originali nei due
> `.txt`.
>
> Controlli fatti sui valori dell'anteprima (T-6 più L, porta 6160): contrasto WCAG 2.x e distanza CIEDE2000. Script
> fuori repo: `/tmp/libreFolio_round2_checks.py`.

## 0. In breve

- **Approvato dal developer (D-T17).** Supera D-T15: la barra laterale torna verde, nei due temi.
- **15 coppie sotto soglia sui valori proposti.**
  - 14 si chiudono con la politica D-T6, come nel giro 1: correzione minima, commentata in `tokens.css` accanto al
    valore della designer.
  - Una no: il bordo dei campi (N5). La designer chiede di togliere proprio la correzione D-T6, e decide il developer
    (§2).
- **Colori dei grafici:** due coppie quasi uguali e cinque vicine (§4). Vanno alla designer nel giro 3; intanto si
  applicano i suoi valori.
- **Instradamento (§6):**
  - T-8: ruoli e valori;
  - DV, figlio nuovo: i grafici;
  - ondate W1–W6: l'applicazione nei componenti.

## 1. Decisioni

| ID | Decisione | Fonte |
|---|---|---|
| D-T17 | Giro 2 della designer approvato per intero: barra laterale verde, stati, N1–N6, Q2–Q13, GR1–GR5, tabelle dei tipi e dei settori | Developer, 15/10 alle 15:03: «archiviali opportunamente e poi dai mandato ai vari sotto agenti di realizzare quanto pianificato» |
| D-T15 | Superata da D-T17 (N1): la barra laterale non è più neutra | — |
| D-T18 | Bordo dei campi (N5): **aperta**, vedi §2 | Developer e designer stanno confrontando le versioni |
| — | Codice delle sessioni coordinate: una o due lettere maiuscole, libere ovunque. Scritto in `.github/agents/` | Developer, 15/10: «per le lettere se 1 non basta usiamone 2» |

## 2. Bordo dei campi (N5): aperto

Oggi i campi non hanno uno stato al passaggio del mouse: il bordo resta quello a riposo, finché il clic non lo porta al
verde del focus. Per questo, confrontando le versioni, l'hover sembrava uguale.

I numeri sono il contrasto contro il fondo del campo, la card e la superficie secondaria (box e pannelli dove pure
stanno dei campi). La soglia WCAG 1.4.11 per riconoscere un componente è 3:1.

| Versione | Chiaro, riposo | Chiaro, hover | Scuro, riposo | Scuro, hover |
|---|---|---|---|---|
| Designer (N5) | `#94A09B` (2,71 / 2,61 / 2,27) | non indicato | `#43524D` (2,26 / 2,12 / 1,93) | `#606F6A` (3,52 / 3,31 / 3,01) |
| Via di mezzo | `#899490` (3,13 / 3,02 / 2,63) | `#616D67` (5,40 / 5,20 / 4,52) | `#5A6863` (3,18 / 2,99 / 2,72) | `#7F8C87` (5,31 / 4,99 / 4,54) |
| Attuale, 3:1 ovunque, più hover proposto | `#7E8984` (3,62 / 3,49 / 3,04) | `#616D67` (5,40 / 5,20 / 4,52) | `#606F6A` (3,52 / 3,31 / 3,01) | `#7F8C87` (5,31 / 4,99 / 4,54) |

- **Focus**, uguale nelle tre versioni: chiaro `#236B4D` (6,40 / 6,17 / 5,36), scuro `#429E79` (5,66 / 5,32 / 4,84).
- **Hover proposto:** il colore del testo attenuato, che la designer ha già approvato in N5.
- **La versione attuale** è la sola che passa ovunque: è la correzione minima D-T6, calcolata anche sulla superficie
  secondaria.
- **La via di mezzo** passa su campo e card, non sulla superficie secondaria.
- **Pagina di prova** con i campi veri, in chiaro e in scuro:
  [`materiale-inviato/bordi-dei-campi.html`](materiale-inviato/bordi-dei-campi.html).
- **Finché il developer non sceglie,** T lascia i valori attuali e prepara solo il ruolo dell'hover, che oggi non esiste.

## 3. Contrasto: le coppie sotto soglia

| Coppia | Colori | Rapporto | Soglia | Come si chiude |
|---|---|---|---|---|
| Barra verde: testo attenuato (versione, email) | `#8CA89B` su `#1B4334` | 4,31 | 4,5 | T-8, D-T6: schiarire di poco |
| Avviso chiaro sulla superficie secondaria | `#B45309` su `#E8ECE9` | 4,21 | 4,5 | T-8, D-T6, oppure testo su `--lf-warning-on-soft` dove serve |
| Info chiaro sul suo fondo tenue | `#155EEF` su `#DBEAFE` | 4,44 | 4,5 | T-8, D-T6 |
| Pulsante rosso pieno in scuro, testo bianco | `#FFFFFF` su `#F84361` | 3,52 | 4,5 | T-8: riempimento più scuro solo per i pulsanti pieni (ruolo dedicato); il testo resta bianco, come chiede Q3 |
| Lo stesso, al passaggio del mouse | `#FFFFFF` su `#E12D4B` | 4,49 | 4,5 | come sopra |
| Bordo dei campi della designer, chiaro, su campo e su card | `#94A09B` | 2,71 · 2,61 | 3 | aperta, §2 |
| Bordo dei campi della designer, scuro, su campo e su card | `#43524D` | 2,26 · 2,12 | 3 | aperta, §2 |
| Interruttore spento, chiaro: traccia su card, pallino su traccia | `#CBD4D0`, `#FFFFFF` | 1,46 · 1,51 | 3 | T-8: il pallino prende un bordo `--lf-border-input`. Il componente si riconosce a 3:1 e i colori della designer restano |
| Interruttore spento, scuro: traccia su card | `#2C3834` su `#151B19` | 1,43 | 3 | il pallino `#9BA8A2` sulla traccia dà già 4,94 |
| Interruttore acceso, scuro: pallino `#EDF2F0` | su `#429E79` | 2,90 | 3 | T-8: l'altra opzione della designer, `#FFFFFF` (3,29) |
| Avviso nel tooltip del tema scuro | `#B45309` su `#EDF2F0` | 4,44 | 4,5 | T-8, D-T6 |

**Passano:**
- tutti i testi sui fondi tenui nuovi;
- la voce attiva della barra (`#FFFFFF` su `#285E49`, 7,5) e la sua barretta (`#52C493`, 3,47);
- i tre stati sulla barra verde;
- terminale, `<mark>`, viola AI;
- le icone di «Informazioni».

Il bordo delle card in rilievo in scuro (`#2E3B36`) dà 1,62 sulla pagina: è decorativo, non ha soglia.

## 4. Distinguibilità dei colori di categoria: domande per il giro 3

ΔE00 sotto 10: le due fette si confondono, se sono una accanto all'altra. Sotto 6 sono quasi uguali.

| Tavolozza | Coppia | ΔE00 |
|---|---|---|
| Tipi, chiaro | Materia prima `#C25E00` · Immobiliare `#B45309` | **5,0** |
| Tipi, chiaro | Azione `#6D28D9` · Fondo `#4338CA` | 6,4 |
| Tipi, chiaro | Cripto `#D97706` · Materia prima `#C25E00` | 8,9 |
| Tipi, scuro | Azione `#A78BFA` · Fondo `#818CF8` | 7,9 |
| Tipi, scuro | Materia prima `#FB923C` · Immobiliare `#F59E0B` | 9,4 |
| Settori, chiaro | Finanziari `#0F766E` · Liquidità `#2D6A54` | 7,9 |
| Settori, chiaro | Beni voluttuari `#7C3AED` · Telecomunicazioni `#4338CA` | 9,4 |
| Settori, scuro | Immobiliare `#FBBF24` · Energia `#FACC15` | **5,1** |
| Settori, scuro | Beni voluttuari `#A78BFA` · Telecomunicazioni `#818CF8` | 7,9 |
| Settori, scuro | Tecnologia `#60A5FA` · Titoli di Stato `#93C5FD` | 9,1 |

- **«Non classificato»** contro la card è sotto 3:1 (2,61 in chiaro, 2,65 in scuro). Per una fetta con l'etichetta può
  andare: da confermare.
- **Immobiliare in chiaro** (`#B45309`) ha lo stesso esadecimale del nuovo `--lf-warning`. GR2 tiene fuori rosso e
  verde semantici, non l'ambra dell'avviso: da confermare.
- **DV applica i valori come sono:** il giro 3 parte da questa tabella.

## 5. Interpretazioni del coordinatore

- **N2, header mobile.** La designer scrive che barra laterale e header mobile sono verdi, ma oggi l'header mobile è
  neutro.
  - Per la continuità con la barra del telefono che lei chiede, sotto il breakpoint mobile l'header diventa verde
    `#1B4334`, con i colori di testo della barra laterale.
  - Su desktop resta neutro.
  - Da confermare nella revisione di T-8.
- **N5, hover in chiaro:** la designer lo dà solo in scuro (§2).
- **Q2, interruttore:** acceso in scuro con il pallino `#FFFFFF`; spento con il bordo sul pallino (§3).
- **Q3, rosso pieno in scuro:** §3.
- **Q8, ombra delle card in scuro:** non indicata. T propone un valore e lo mette nella revisione.
- **Q13, `#0D1111`:** non è un refuso del ruolo.
  - La tabella del giro 2 leggeva i colori dal browser, e un colore al 60 % letto da un canvas perde un'unità per
    arrotondamento.
  - Il ruolo è già `#0D1110` al 60 %; T lo verifica.
- **GR4, sottotipi.** Delle due regole proposte, DV propone nella sua analisi quella a miscela: col bianco in chiaro,
  verso la card in scuro. È deterministica e non arriva mai al bianco slavato.
- **GR5, oltre il sedicesimo colore.** Nello storico geografico i paesi possono essere più di 16. Al posto della
  ripetizione silenziosa serve una sfumatura derivata: è il rimedio già annotato in `AllocationHistoryChart`.
- **Emoji dei settori.**
  - Oggi le mappe sono due, nel backend (`services/financial_math/portfolio/derived_views.py` e `api/v1/utilities.py`),
    più un ripiego nel frontend (`lib/stores/reference/sectorStore.ts`).
  - DV ne fa una sola.
  - `derived_views.py` sta nella casa della matematica finanziaria: la modifica si concorda con J (1.3).

## 6. Instradamento

| Cosa | Chi | Quando |
|---|---|---|
| Ruoli e valori: barra verde (A), stati (B), N3, N6, Q2, Q3, Q6, Q7, Q8, Q9, Q10, Q11, Q13; correzioni D-T6 (§3) | T-8 | subito |
| Componenti di T: `Sidebar` tutta verde, stato della connessione sulla barra verde, header mobile verde (§5), `AnimatedBackground` (N6), terminale di `ForgotPasswordCard` (Q6; il contenuto è di A9) | T-8 | subito |
| `theme-color` `#1B4334` nei due temi (N2), manifest, `offline.html` | T-4, sbloccato da N2 | con T-8 |
| Applicazione nei componenti degli altri: stato «modificato» (Q4), pallino dello scheduler (Q5), codice nel testo (Q6), `<mark>` (Q7), tour (Q9), avviso nei tooltip (Q10), AI Export (Q11), icone di «Informazioni» (Q12), card scure di Profilo e Allocazione | ondate W1–W6, fatte da T con i sotto-agenti | W2 per impostazioni, onboarding, AI Export e «Informazioni»; W5 per Allocazione e grafici |
| GR1–GR5: colori fissi per tipo e per settore, tavolozze per tema, emoji dei settori | DV, figlio nuovo | analisi subito; codice nell'ordine concordato con Y e J della 1.3 |
| Nuovi ruoli e colori di categoria nel Designer Lab, per il giro 3 | L | dopo T-8 e DV |
| Bordo dei campi | developer | §2 |

## 7. Stato delle ondate al 15/10

Misurato con `node frontend/scripts/theme/theme-roles.mjs --report`.

| | Inizio del cricchetto (T-1, 14/10 alle 23:08) | `dev_release2` (`8fc44558c`) | Ramo di T (`0580c92ab`) |
|---|---|---|---|
| Classi legacy (m1) | 11.435 | 11.216 (−219, −1,9 %) | 11.069 (−366, −3,2 %) |
| Colori letterali (m2) | 1.782 | 92 (−95 %) | 83 (−95 %) |
| File che usano i ruoli | — | 10 | 17 |
| File con colori legacy | — | 282 | 267 |

- **I letterali** sono scesi con R: spostati nei moduli centrali di `lib/theme/`, a parità di aspetto.
- **Le classi** sono scese poco: finora T ha convertito solo i piloti, cioè accesso (T-2), shell (T-3), sfondo del login
  (T-5) e palette (T-6).
- **Le ondate non sono partite.** W1 aspettava T-4, e T-4 la risposta a N2, arrivata ora.
  - W1 (35 file, 1.085 classi, 7 lotti) e W2 (34 file, 1.501 classi, 9 lotti) sono già spacchettate, con i lotti da
    chiedere alla 1.3.
  - W3–W6, circa 8.500 classi, sono ancora da spacchettare.
- **Il ritmo:** i lotti si scrivono in parallelo, ma le prove pesanti passano dal nostro unico slot. T propone come
  raggrupparle.
- **Rilasci:** nessun rilascio della 1.3 con W1–W4 a metà (decisione del 14/10).
