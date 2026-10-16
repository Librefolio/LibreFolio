# ⚙️ Impostazioni globali

Le impostazioni globali si applicano all'intera istanza e a ogni utente. Sono archiviate nel database:
tutti possono leggerle, solo gli amministratori possono modificarle.

---

## ✏️ Modificare un'impostazione

### 🔓 1. Sblocca la scheda

Apri **Impostazioni** (icona a forma di ingranaggio nella barra laterale), poi la scheda **Amministrazione**: il suo pannello **Impostazioni globali**
raggruppa le impostazioni per categoria. Fai clic sull'**icona a forma di lucchetto** (🔒) nell'intestazione per sbloccarla.
Solo gli amministratori (superutenti) hanno il lucchetto; tutti gli altri ottengono una vista di sola lettura.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Impostazioni globali" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 💾 2. Modifica e salva

- Niente viene scritto finché non fai clic su **Salva** accanto a un'impostazione, o su **Salva tutto** nell'intestazione.
  **Ripristina** e **Annulla Tutto** riportano indietro i valori salvati.
- **Ripristina** e **Ripristina Tutto** inseriscono i valori predefiniti, pronti per essere salvati.
- I valori salvati vengono applicati immediatamente, senza riavvio.

??? note "🔒 Blocco con modifiche non salvate — quando una finestra di dialogo chiede prima"

    Facendo clic sul lucchetto con modifiche non salvate viene chiesto se scartarle. **Annulla** mantiene le
    modifiche; **Scarta** riporta indietro i valori salvati e blocca la scheda.

??? tip "💻 Impostazioni mancanti — ricrearle dalla riga di comando"

    Ogni avvio del server ricrea qualsiasi impostazione mancante con il suo valore predefinito. Per farlo senza un
    riavvio, esegui lo [strumento da riga di comando](cli_tools.md):

    ```bash
    pipenv run ./dev.py user init-settings
    ```

    I valori che hai modificato vengono mantenuti.

---

## 📋 Cosa fa ogni impostazione

| Categoria | Impostazione | Predefinito | Cosa fa — quando modificarla |
|---|---|---|---|
| ⏳ Sessione | **Durata sessione** | 24 ore | Per quanto tempo gli utenti restano connessi. Accorciala su dispositivi condivisi; un nuovo valore si applica dal login successivo di ogni utente. |
| 🛡️ Sicurezza | **Abilita registrazione** | Attiva | Consente a nuove persone di registrarsi. Disattivala una volta che tutti hanno un account, soprattutto se l'istanza è raggiungibile da Internet. Il primo account di una nuova istanza può sempre essere creato. |
| 🛡️ Sicurezza | **Richiedi verifica email** | Disattivata | I nuovi account devono aprire un link inviato via email al loro indirizzo prima di poter accedere; il primo account non aspetta mai, e gli account esistenti non cambiano. Si attiva solo mentre l'email funziona e `LIBREFOLIO_PUBLIC_URL` è utilizzabile: fino ad allora l'interruttore resta disabilitato. Vedi *Email Verification* in [Email](email.md). |
| 🔄 Job di aggiornamento | **Scheduler abilitato** | Attivo | Attiva o disattiva gli aggiornamenti automatici di prezzi e tassi di cambio: vedi [Scheduler dei dati di mercato](#market-data-scheduler). |
| 🧠 Memoria | **Dimensione Max Upload** | 10 MB | Il file più grande che gli utenti possono caricare, incluso il report del broker. Aumentala se un'esportazione di grandi dimensioni viene rifiutata. |
| 🌍 Predefiniti | **Valuta predefinita** | `EUR` | La valuta in cui i nuovi utenti registrano i propri dati. |
| 🌍 Predefiniti | **Lingua predefinita** | `en` | 🇬🇧 `en`, 🇮🇹 `it`, 🇫🇷 `fr` o 🇪🇸 `es`. |
| 🌍 Predefiniti | **Tema predefinito** | `auto` | ☀️ `light`, 🌙 `dark`, o 🖥️ `auto`, che segue il dispositivo. |

I nuovi utenti partono dai tre valori predefiniti: la [Configurazione iniziale](../user/getting-started.md#welcome-setup)
mostra lingua e valuta precompilate. Modificare un valore predefinito in seguito lascia invariate le
[Preferenze](../user/settings/preferences.md) degli utenti esistenti.

---

## 🕐 Scheduler dei dati di mercato {: #market-data-scheduler }

Lo scheduler mantiene aggiornati prezzi e tassi di cambio da solo, anche quando nessuno è connesso:

- 💰 **Aggiornamento Prezzi Correnti** — ogni pochi minuti, l'ultimo prezzo di ogni asset attivo che ha
  un provider di prezzi.
- 📊 **Sincronizzazione Storico** — nei giorni e negli orari che scegli, i prezzi giornalieri di quegli asset e i
  tassi di ogni coppia FX con un provider, almeno nell'**Orizzonte di recupero**, per colmare eventuali lacune.
  Per un asset o una coppia il cui ultimo prezzo o tasso salvato è più vecchio, risale fino a quel giorno, al massimo
  di un anno; un asset senza ancora prezzi salvati ha solo l'orizzonte, perché lo scheduler non scarica mai uno
  storico intero. Le coppie con soli tassi manuali vengono saltate.

Se all'orario di una sincronizzazione il server è spento o sospeso, la sincronizzazione dello storico
che ha saltato parte appena il server torna attivo, senza aspettare l'orario successivo: un server spento per
settimane colma tutta la sua lacuna.

### ⚙️ Configura la pianificazione

Sblocca la scheda, apri **Job di aggiornamento** e fai clic su **Configura…** nella riga **Configurazione Schedule**.
La finestra di dialogo ha il proprio pulsante **Salva**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Modale di configurazione dello scheduler" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Campo | Predefinito | Cosa imposta |
|---|---|---|
| **Fuso orario** | `UTC` | Il fuso orario degli orari e dei giorni sottostanti; l'orologio UTC del server è mostrato accanto. |
| **Aggiorna ogni** | 10 minuti | Ogni quanto vengono aggiornati i prezzi correnti, da 1 a 1440 minuti. |
| **Orari di sincronizzazione** | `06:00`, `23:00` | Quando viene eseguita la sincronizzazione storica; **Aggiungi orario** aggiunge uno slot. |
| **Giorni di sincronizzazione** | Lun–Sab | I giorni della sincronizzazione storica. |
| **Orizzonte di recupero** | 14 giorni | Quanti giorni passati controlla almeno ogni sincronizzazione storica, da 1 a 365. Risale più indietro, fino a un anno, quando l'ultimo prezzo o tasso salvato di un asset o di una coppia è più vecchio. |

Mantieni almeno un orario e un giorno. Suggerimento: una sincronizzazione storica dopo la chiusura dei mercati (ad esempio
`22:00`) ottiene i dati più completi.

??? warning "🌍 Modifica del fuso orario — i job si spostano nel tempo"

    Gli orari e i giorni mantengono i loro valori ma vengono conteggiati nel nuovo fuso orario, quindi i job vengono eseguiti in un altro
    momento. Seguono anche l'ora legale del nuovo fuso: `06:00` in `Europe/Rome` viene eseguito alle 05:00 UTC
    in inverno e alle 04:00 UTC in estate.

### 📜 Leggi il log dello scheduler

La riga **Stato Scheduler** mostra l'ultimo aggiornamento del prezzo corrente, con un punto per il risultato.
Quando è previsto un nuovo tentativo, una riga in più ne indica l'ora: **Non riuscito: nuovo tentativo alle …** dopo un
aggiornamento che non si è potuto concludere, altrimenti **Elementi in pausa ritentati alle …** per i prezzi rimandati
perché il loro fornitore è in pausa.
Fai clic sulla riga (o su **Dettagli…**) per aprire il **Log Esecuzione Scheduler**. Solo gli amministratori possono
leggere lo stato e il log.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Modale del log dello scheduler" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- Ogni voce è un'esecuzione: job, ora, durata e quanti elementi sono riusciti. 🟢 **OK**: tutti, o niente da
  fare; 🟡 **Parziale**: alcuni non riusciti, o rimandati perché il loro fornitore è in pausa dopo troppe richieste;
  🔴 **Errore**: nessuno riuscito e nessuno rimandato.
- Fai clic su una voce per vedere ciascun asset o coppia FX, il relativo provider e i prezzi modificati (**Delta**).
  Passa il mouse su un errore per leggerlo per intero; fai doppio clic (pressione prolungata su un telefono) per copiarlo.
- Un elemento rimandato mostra un'icona di pausa e **Rimandato: fornitore in pausa**: passa il mouse sull'etichetta per
  leggere il messaggio del fornitore. La voce conta gli elementi rimandati con ⏸, accanto a ✓ e ✗ (per esempio
  `3/5 ✓ · 1 ⏸ · 1 ✗`), e **Nuovo tentativo alle …** nella sua intestazione indica l'ora fissata per ritentarli.
- Filtra per job, stato o periodo, dall'ultima ora agli ultimi 30 giorni. Vengono conservate solo le esecuzioni più recenti.

---

## 🗄️ Cache del server {: #server-caches }

Per rimanere veloce, LibreFolio conserva in memoria le risposte recenti dei provider e i risultati calcolati. Il
pannello **Stato della cache**, in fondo alla categoria **Memoria**, elenca ciascuna cache con **Dim. / Max** e il suo **TTL** (per quanto tempo una voce viene conservata). Fai clic sull'intestazione di una colonna per ordinare;
**Aggiorna** aggiorna i numeri.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="cache-panel" alt="Pannello cache del server in Impostazioni globali (categoria Memoria)">
</div>

Tutti possono vedere il pannello. Un amministratore, con la scheda sbloccata, può svuotare una cache con
**Svuota** o tutte con **Svuota tutto**, per forzare dati freschi senza riavvio. Anche un riavvio
svuota tutte le cache.

!!! warning "Svuotare una cache rallenta il recupero successivo"

    Entrambe le azioni chiedono prima conferma. Dopo uno svuotamento, la richiesta successiva per quei dati torna
    ai provider, quindi aspettati un rallentamento simile a un riavvio del server mentre le cache si riempiono
    di nuovo.

??? note "🧵 Più worker — quando il server viene eseguito con `--workers`"

    Ogni processo worker ha le proprie cache. Il pannello mostra e svuota quelle del worker che ha
    risposto; riavvia il server per svuotarle tutte.

---

## 🔗 Correlati

- 📝 **[Variabili d'ambiente](configuration.md)** — Le impostazioni che risiedono invece in `.env`
- 👤 **[Preferenze utente](../user/settings/preferences.md)** — Cosa ogni utente può modificare per sé
- 🧑‍💻 Per sviluppatori: **[Sistema delle impostazioni](../developer/architecture/settings.md)**,
  **[Registro delle cache](../developer/architecture/settings_cache.md)** e
  **[Scheduler dei dati di mercato](../developer/backend/scheduler.md)**
