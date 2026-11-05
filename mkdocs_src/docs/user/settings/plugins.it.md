# 🧩 Impostazioni dei plugin

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="plugins" alt="Impostazioni dei plugin">
</div>

La scheda **Plugin** contiene ciò che richiedono le fonti dei prezzi e dei tassi di cambio: la chiave API di una fonte dati a pagamento, una regione o una tua preferenza. Apri **Impostazioni** (icona a ingranaggio nella barra laterale), poi la scheda **Plugin**, dopo **Preferenze** (su un telefono, la scheda con l'icona a forma di pezzo di puzzle). Ogni utente dispone di questa scheda; ciò che puoi modificare lì dipende da [chi ne è il proprietario](#personal-and-instance). L'icona a forma di libro nella sua parte superiore apre questa pagina.

Vengono elencati solo i plugin che richiedono qualcosa: sotto **Prezzi** i [provider di prezzi](../assets/providers/index.md), sotto **Tassi di cambio** i [provider di tassi di cambio](../fx/providers/index.md); ogni intestazione segue l'icona della propria famiglia (un grafico a colonne per i prezzi, monete per i tassi di cambio). Un'intestazione senza un plugin di questo tipo viene omessa. Dei plugin forniti con LibreFolio, due hanno oggi un'impostazione, una preferenza di ricerca personale ciascuno: **JustETF** e **Borsa Italiana** (vedi [Preferenze di ricerca](#search-preferences)). Un plugin aggiunto alla tua installazione può richiedere altro. La scheda ha anche un gruppo **Strumenti**, per gli [Strumenti](../tools/index.md) dotati di impostazioni proprie; nessuno di essi ne dispone ancora, quindi oggi non lo vedrai. Quando nessun plugin richiede qualcosa, la scheda dice *Nessun plugin installato richiede impostazioni.*

## 🧾 Un plugin, un modulo {: #form }

Ogni plugin ha un proprio modulo: la sua icona e il suo nome (un pezzo di puzzle quando il plugin non ha un'icona), un [badge](#configured) che indica se può funzionare, poi le sue impostazioni. Ogni impostazione mostra il nome, un **\*** rosso quando è obbligatoria, il proprietario — **Personale** o **Intera istanza** — e cosa fa.

- Modifica ciò che ti serve, poi fai clic su **Salva** in fondo al modulo di quel plugin: ogni plugin viene salvato separatamente. **Scarta** elimina le modifiche che non hai salvato.
- **Salva** mantiene tutte le modifiche del plugin, o nessuna: quando una di esse viene rifiutata, non viene salvato nulla e l'impostazione in errore ne spiega il motivo.
- Prima di salvare, LibreFolio verifica ciò che hai digitato in base alle regole del plugin — un numero, un numero intero, un minimo o un massimo, una lunghezza, una delle opzioni — e indica sotto l'impostazione cosa non va, ad esempio *Almeno 8 caratteri*. **Salva** resta disabilitato finché il problema non viene risolto.
- Una modifica salvata si vede nell'impostazione stessa, senza alcun messaggio. Un plugin le cui impostazioni non puoi modificare non ha pulsanti.

??? note "💬 Quando un salvataggio non va a buon fine"

    | Messaggio | Cosa è successo |
    |---|---|
    | *Nulla è stato salvato: controlla le impostazioni qui sotto.* | Un'impostazione è stata rifiutata. Sotto di essa: *Il valore non è valido per questa impostazione.*, *Solo un amministratore può modificare questa impostazione.*, *Una variabile del server la imposta: non può essere modificata qui.* oppure *Questa impostazione non esiste più: ricarica la pagina.* |
    | *Queste impostazioni sono cambiate nel frattempo: sono state ricaricate, salva di nuovo.* | Qualcuno ha salvato le stesse impostazioni nello stesso momento: nessuna delle tue modifiche è stata salvata. Controlla i valori mostrati, poi salva di nuovo. |
    | *I segreti non possono essere salvati: la chiave di questa istanza non può essere usata (vedi i controlli della configurazione).* | Nulla è stato salvato: un segreto non può essere crittografato. Un amministratore trova la causa nei [controlli di avvio](../../admin/configuration_security.md#startup-checks). |
    | *Non è stato possibile salvare le impostazioni.* | Nessuna risposta dal server: riprova. |

---

## 👥 Impostazioni personali e dell'intera istanza {: #personal-and-instance }

Accanto al nome, ogni impostazione ne indica il proprietario:

| | **Personale** | **Intera istanza** |
|---|---|---|
| **Il suo valore** | Il tuo: ogni utente ha il proprio | Uno per tutti su questo LibreFolio |
| **Chi la modifica** | Tu | Un amministratore |
| **Chi la vede** | Solo tu: nemmeno un amministratore | Tutti; gli utenti che non sono amministratori la vedono in sola lettura, con l'indicazione *Solo un amministratore può modificarla.* Di un segreto, vedono solo se è impostato |
| **Cosa cambia** | Ciò che LibreFolio fa solo per te: le tue ricerche e i controlli dei provider nella finestra di dialogo dell'asset, come **Test configurazione** | Tutto ciò che fa il plugin, prezzi e tassi di cambio inclusi |

I prezzi, gli storici dei prezzi e i tassi di cambio sono condivisi da tutti, quindi non dipendono mai dalla scelta di un singolo utente: per essi, un'impostazione personale adotta sempre il valore predefinito del plugin.

!!! info "🛡️ Per gli amministratori"

    Qui modifichi le impostazioni dell'intera istanza, come tutti gli altri modificano le proprie impostazioni personali. Un'impostazione dell'intera istanza può anche essere fornita dalla configurazione del server: vedi [Impostato dal server](#set-by-the-server) e, nel manuale per amministratori, [Impostazioni dei plugin](../../admin/configuration_secrets.md#plugin-settings) per le variabili.

---

## 🔐 Segreti {: #secrets }

Alcune impostazioni sono segreti, come una chiave API. Un segreto è di sola scrittura:

- **Digitalo, poi premi Salva.** Ciò che hai digitato viene inviato una volta, poi rimosso dalla pagina: da quel momento l'impostazione mostra solo *Impostato il* con la data e l'ora in cui è stato salvato, mai il segreto stesso — nemmeno a te. Il campo è contrassegnato come nuova password, così il browser non lo compila con una delle tue password salvate.
- **Sostituisci** apre il campo per un nuovo valore; **Annulla** mantiene quello salvato.
- **Cancella** elimina il segreto quando fai clic su **Salva** (*Verrà eliminato quando salvi.*); **Ripristina** lo mantiene.

Gli utenti che non sono amministratori vedono un segreto dell'intera istanza come *Impostato il …* (*Impostato* quando lo [imposta il server](#set-by-the-server)) o *Non impostato*, e nient'altro. LibreFolio conserva un segreto salvato in forma crittografata: vedi [Segreti salvati e chiave dell'istanza](../../admin/configuration_secrets.md#plugin-secrets).

---

## 🔒 Impostato dal server {: #set-by-the-server }

Un amministratore può anche fornire un'impostazione dell'intera istanza tramite la configurazione del server, con una variabile d'ambiente. L'impostazione mostra quindi il proprio valore in sola lettura, un segreto solo come *Impostato*, con :material-lock-outline: *Impostato dal server*: nessuno può modificarla qui, nemmeno un amministratore. Gli amministratori vedono anche il nome della variabile, preceduto dall'etichetta *Impostato dalla variabile del server*.

Per modificare un'impostazione di questo tipo, un amministratore modifica la variabile e riavvia LibreFolio: vedi [Una variabile blocca l'impostazione](../../admin/configuration_secrets.md#plugin-variable-lock).

---

## ↩️ Torna al valore predefinito {: #use-the-default }

Dopo aver salvato un valore tuo in un'impostazione che puoi modificare, sotto di essa appare **Usa il valore predefinito**. Elimina il valore salvato quando fai clic su **Salva**, e l'impostazione torna al valore predefinito del plugin: *Il valore salvato verrà eliminato quando salvi: si applica il valore predefinito.*, con **Ripristina**. Svuotare un campo di testo che mostra un valore salvato fa lo stesso. Un segreto non ha un valore predefinito: **Cancella** lo elimina ([Segreti](#secrets)).

---

## ⚠️ Quando un'impostazione ha un problema {: #problems }

| L'impostazione dice | Cosa è successo | Cosa fare |
|---|---|---|
| *La variabile del server … non è valida: il plugin resta non configurato finché non viene corretta.* | La variabile che la imposta contiene un valore che l'impostazione rifiuta, oppure indica un file che non può essere letto. LibreFolio non usa mai un fallback su un valore salvato né sul valore predefinito. Gli amministratori vedono il nome della variabile | Un amministratore corregge la variabile e riavvia LibreFolio |
| *Il valore salvato non è più valido: si applica il valore predefinito.* | Il plugin non accetta più il valore salvato in precedenza, ad esempio dopo un aggiornamento | Scegli di nuovo un valore e salvalo, oppure lascia così: nel frattempo si applica il valore predefinito |
| *Salvato, ma la chiave di questa istanza non può leggerlo. Se un amministratore può rimettere la vecchia chiave, questa ha la precedenza; altrimenti inseriscilo di nuovo.* | Un segreto salvato non può più essere letto, perché la chiave di crittografia dell'istanza è cambiata. LibreFolio lo conserva, ma non lo usa mai | Se un amministratore può ancora rimettere la vecchia chiave dell'istanza, questa ha la precedenza: un segreto salvato con la nuova chiave diventerebbe illeggibile una volta ripristinata la vecchia chiave (vedi [Segreti salvati e chiave dell'istanza](../../admin/configuration_secrets.md#plugin-secrets)). Altrimenti, digita di nuovo il segreto e salvalo; per un segreto dell'intera istanza, lo fa un amministratore |

---

## 🚦 Configurato o da configurare {: #configured }

Il badge accanto al nome di ogni plugin indica se può funzionare:

- **Configurato**: ogni impostazione obbligatoria ha un valore che LibreFolio può usare.
- **Da configurare**: un'impostazione obbligatoria non ha un valore utilizzabile — mai impostata, o un segreto che non può più essere letto — oppure una variabile del server che imposta una delle sue impostazioni non è valida.

LibreFolio non chiama un plugin che è **Da configurare**: i suoi prezzi o tassi di cambio non vengono aggiornati, una ricerca dice che deve essere configurato e **Test configurazione** fallisce con ❌ *Questo provider deve essere configurato prima dell'uso*. I plugin forniti con LibreFolio non richiedono impostazioni per funzionare: **JustETF** e **Borsa Italiana** sono sempre **Configurati**.

---

## 🛠️ Configura da un asset {: #configure }

Non devi uscire da un asset per modificare le impostazioni del suo provider: **Configura** apre lo stesso modulo di questa scheda, per quel singolo provider di prezzi, sopra la finestra di dialogo in cui ti trovi.

- **Nella finestra di dialogo dell'asset** (**+ Aggiungi asset**, oppure **Modifica** su un asset), in **Assegnazione provider**: quando il provider scelto ha impostazioni, **Configura** si trova accanto al suo :material-help-circle-outline: link di aiuto — su un telefono, solo la sua icona :material-tune:. Quando il provider non può ancora funzionare, anche lì compare **Da configurare**. Dopo un salvataggio il badge si aggiorna e l'asset che stai modificando resta com'era.
- **In Cerca online**: quando un provider deve essere configurato prima di poter cercare, l'elenco dei risultati inizia con una riga *… deve essere configurato prima di poter cercare*, che indica il nome del provider, e con il suo pulsante **Configura**. Una volta salvato, la ricerca viene eseguita di nuovo. Così un provider che non ha potuto cercare non viene mai confuso con uno che non ha trovato nulla.

---

## 🔎 Preferenze di ricerca: JustETF e Borsa Italiana {: #search-preferences }

Entrambe sono impostazioni **Personali** e mostrano tutto finché non scegli diversamente. Scelgono soltanto quali righe mostrano le tue ricerche: non modificano alcun prezzo, né alcun asset che possiedi già. Nessuno strumento scompare: ciascuno esiste in ogni valuta o lingua, quindi una preferenza ne mantiene solo una riga.

| Plugin | Impostazione | Scelte | Cosa cambia in **Cerca online** |
|---|---|---|---|
| **JustETF** | **Valuta preferita** | **Tutte le valute** (il valore predefinito), 🇪🇺 EUR, 🇺🇸 USD, 🇨🇭 CHF, 🇬🇧 GBP | Con una valuta, ogni fondo compare una volta, in quella valuta. Con **Tutte le valute**, ogni fondo compare quattro volte, una volta per valuta |
| **Borsa Italiana** | **Lingua preferita** | **Entrambe le lingue** (il valore predefinito), 🇮🇹 Italiano, 🇬🇧 Inglese | Con una lingua, ogni strumento compare una volta, in quella lingua: quella in cui sono riportati il suo nome e i suoi dettagli. Con **Entrambe le lingue**, prima l'italiano, poi l'inglese. Il sito di Borsa Italiana viene cercato allo stesso modo qualunque sia la scelta |

Impostale qui, sotto **JustETF** e **Borsa Italiana**, oppure con **Configura** nella finestra di dialogo dell'asset mentre quel provider è selezionato.

### 👑 La corona nei risultati JustETF {: #crown }

👑 contrassegna la valuta propria di un fondo, quella in cui è calcolato il suo NAV — non necessariamente quella in cui fai trading. Ogni volta che un risultato la mostra, una riga in fondo all'elenco lo dice: *👑 la valuta propria del fondo*. Con una valuta preferita, 👑 appare solo sui fondi calcolati in quella valuta: con 🇪🇺 EUR, un fondo calcolato in dollari statunitensi mostra solo 🇪🇺.

Come funziona la valuta di un asset justETF: [Scegli la valuta nella ricerca](../assets/providers/justetf.md).

---

## 🔗 Correlati

- 🎛️ **[Preferenze utente](preferences.md)** — Lingua, valuta di base, tema e guide
- ⚙️ **[Panoramica delle impostazioni](index.md)** — Ogni scheda delle Impostazioni
- 📡 **[justETF](../assets/providers/justetf.md)** e 🇮🇹 **[Borsa Italiana](../assets/providers/borsa-italiana.md)** — I due provider con una preferenza di ricerca
- 🛠️ **[Impostazioni dei plugin per amministratori](../../admin/configuration_secrets.md#plugin-settings)** — Le variabili del server, la chiave dell'istanza e la crittografia dei segreti
- 🧩 **[Impostazioni dei plugin per sviluppatori](../../developer/architecture/patterns/plugin_settings.md)** — Come un plugin dichiara le proprie impostazioni
