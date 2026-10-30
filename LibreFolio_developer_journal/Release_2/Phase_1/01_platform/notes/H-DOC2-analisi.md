# DOC-2 — la ricerca della documentazione per lingua: analisi (H, 23/10/2026, base `1fd80c481`)

Solo lettura: nessun file toccato. Misure fatte sul sito costruito in `mkdocs_src/site/` e sul codice installato
(`mkdocs-material 9.7.7`, `mkdocs-static-i18n 1.3.1`, `mkdocs 1.6.1`).

## 1. Com'è oggi

- **Un solo indice per tutte le lingue**: `site/search/search_index.json`, 10,5 MB, 9 429 documenti (una voce per pagina e per
  sezione). Ogni visitatore lo scarica per intero, qualunque sia la sua lingua.
- Le voci sono **per lingua di scrittura**: `en` (indirizzo senza prefisso, 3 902 voci, 5,97 MB se estratte), `it/…`
  (1 843, 1,37 MB), `fr/…` (1 840, 1,45 MB), `es/…` (1 844, 1,39 MB). Le pagine che esistono solo in inglese (per esempio
  `developer/api/`) hanno **solo** la voce inglese: il ripiego in inglese di `mkdocs-static-i18n` (`fallback_to_default`,
  acceso) copia la pagina sotto `/it/` ma **non la mette nell'indice**.
- `mkdocs.yml`: `plugins: - search` e `- i18n:` (`docs_structure: suffix`). `static-i18n` ricalcola `search.lang` con tutte le
  lingue; **non c'è** un filtro di lingua né in `static-i18n` né in Material (le versioni a pagamento hanno i filtri per
  «tag», qui non ci sono). Il campo `location` è il riferimento della voce, **non** un campo di ricerca: non si può dire a
  lunr «solo `it/`» nella query.
- Il browser: Material scarica l'indice con `fetch` su `new URL("search/search_index.json", config.base)` **una volta**
  all'avvio della pagina (bundle `bundle.d7400e89.min.js`, funzione `ks()`), lo passa al web worker che lo indicizza, e
  mostra i risultati nell'ordine di punteggio, con «N documenti trovati» che conta tutte le lingue. `config.base` serve
  anche per le risorse: non si può cambiarlo solo per l'indice.

Conseguenza per l'utente: chi cerca «backup» in italiano vede insieme la pagina italiana, l'inglese, la francese e la
spagnola dello stesso argomento.

## 2. Cosa vuole il developer

Per default **solo** le pagine scritte nella lingua scelta (la lingua dell'interfaccia della pagina: `<html lang>`); un
**pulsante esplicito** nella ricerca («cerca anche nelle altre lingue») allarga a **tutte le altre lingue**, non solo
all'inglese.

## 3. Le strade

### A. Filtrare nel browser i risultati già disegnati
Un piccolo `extra_javascript` con un `MutationObserver` sulla lista dei risultati: nasconde le voci il cui indirizzo non è
della lingua scelta, più un pulsante nella finestra di ricerca.
- ➕ Poco lavoro (~0,5 giorni), nessun cambiamento di build.
- ➖ L'indice resta da 10,5 MB per tutti. ➖ Il conteggio «N documenti trovati» resta sbagliato (conta le altre lingue).
  ➖ Material disegna i risultati a gruppi mentre si scorre: nascondere l'80 % delle voci lascia la lista quasi vuota e il
  caricamento dei gruppi dipende dal vedere il fondo. ➖ Si lega ai nomi delle classi CSS di Material.

### B. Un indice per lingua, scelto prima che Material lo scarichi (**consigliata**)
1. Un hook MkDocs `on_post_build` (`mkdocs_src/hooks/search_language_split.py`, accanto a `jsonld.py` e `fr_typography.py`)
   scrive, dal `search_index.json` appena costruito, un file per lingua: `search/search_index.en.json`, `.it.json`,
   `.fr.json`, `.es.json` (stessa `config`, solo le voci di quella lingua: en = senza prefisso). Il file completo resta.
2. Un piccolo script (`docs/javascripts/search-language.js`, **senza dipendenze**), caricato dal blocco `extrahead` di
   `overrides/main.html` **prima** del bundle di Material, avvolge `window.fetch`: la richiesta di `…/search/search_index.json`
   diventa `…/search/search_index.<lingua>.json`, a meno che l'utente abbia scelto «tutte le lingue» (preferenza in
   `localStorage`, in `try/catch`: senza storage vale il default).
3. Il pulsante «Cerca anche nelle altre lingue» (casella) si aggiunge alla finestra di ricerca; cambiarla salva la
   preferenza e **ricarica la pagina** (il worker di Material si prepara una volta sola), ricordando in `sessionStorage`
   la query e riaprendo la ricerca: l'utente non perde quello che ha scritto.
- ➕ Conteggi, ordine e caricamento dei risultati **esatti**, senza toccare i risultati disegnati.
  ➕ **Scarica meno**: 1,4 MB invece di 10,5 MB per chi legge in italiano, francese o spagnolo (6 MB in inglese).
  ➕ Nessun cambio a `mkdocs.yml` oltre alla riga `hooks:`; la navigazione non cambia.
- ➖ Il ricarico per il pulsante. ➖ Si lega a due fatti di Material 9: l'indirizzo `search/search_index.json` e l'uso di
  `fetch` (versione fissata nel `Pipfile.lock`; un test sull'indice e uno sul sito costruito se ne accorgono se cambiano).
- Lavoro: ~1,5 giorni (**il «1» del kickoff non basta**), compresa la spec E2E.

### C. Cambiare il worker di Material
Scartata: è un file minificato di un pacchetto; patcharlo si rompe a ogni aggiornamento.

## 4. File (strada B)
| File | Cosa |
|---|---|
| `mkdocs_src/hooks/search_language_split.py` (nuovo) | l'hook: divide l'indice per lingua dopo la build |
| `mkdocs_src/mkdocs.yml` | **una riga** in `hooks:` (non la navigazione): serve l'ok del coordinatore |
| `mkdocs_src/docs/javascripts/search-language.js` (nuovo) | il rewriter di `fetch` e il pulsante |
| `mkdocs_src/overrides/main.html` | il tag `<script>` nel blocco `extrahead`, prima del bundle |
| `mkdocs_src/docs/static/extra.css` | lo stile del pulsante, con i colori di Material (variabili `--md-*`) |
| test | pytest dell'hook (la divisione: voci per lingua, nessuna persa né duplicata; le pagine solo-inglese solo in `en`); Vitest della funzione pura che sceglie l'indirizzo; spec Playwright su `/mkdocs/` (ricerca in italiano → solo risultati `it/`; pulsante → compaiono anche `fr/`, `es/` e `en`) |

## 5. Debito di traduzione
L'etichetta del pulsante (una frase corta) serve nelle 4 lingue della documentazione. Propongo di **scriverle tutte e
quattro** nello script (sono sei parole, e una pagina italiana con un pulsante inglese sarebbe peggio del debito): è una
stringa di interfaccia della documentazione, non una pagina; la segno comunque come debito da rivedere con Aphra. Decide il
coordinatore.

## 6. Domande
1. **Strada B** (consigliata) o A? Con la B i giorni passano a ~1,5.
2. L'etichetta del pulsante: le 4 lingue scritte da me, o solo l'inglese e le altre come debito?
3. La riga in `hooks:` di `mkdocs.yml` e l'E2E (serve uno slot) vanno bene?
4. Chi cerca in inglese: oggi il «default» è il solo inglese (le pagine tradotte compaiono comunque nella loro lingua solo con il
   pulsante). Va bene?
