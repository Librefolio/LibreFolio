# ℹ️ Informazioni

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="about" alt="Informazioni">
</div>

La scheda **Informazioni** mostra:

- **Versione** corrente di LibreFolio
- **Licenza** (AGPL-3.0)
- Collegamenti al **repository GitHub** e alla **documentazione**
- Una griglia di **informazioni di sistema** (versione di Python, sistema operativo, modalità di deployment — Docker o locale — browser, viewport, tema e lingua) con un pulsante **copia per segnalazione** che racchiude questi dettagli in un report di bug pronto da incollare
- I **plugin installati**: elenchi comprimibili dei provider dei prezzi degli asset, dei provider di tassi FX, dei plugin di importazione broker e degli indicatori di segnale rilevati all'avvio

---

## 🧩 Diagnostica plugin

La sezione comprimibile **Diagnostica plugin** riporta lo stato di salute dei quattro registri di plugin — **provider asset**, **provider FX**, **importatori broker** e **indicatori di segnale**.

Ogni registro è contrassegnato come **completamente caricato** (verde) oppure elenca i **plugin che non sono riusciti a caricarsi** (rosso), con il nome del file e l'errore sottostante. Se un provider, un importatore o un indicatore che ti aspettavi manca dal resto dell'applicazione, questo pannello ti dice perché: un plugin che non riesce a caricarsi all'avvio semplicemente non viene registrato.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="about-plugin-diagnostics" alt="Sezione comprimibile della diagnostica plugin nella scheda Informazioni">
</div>

---

## 📜 Modale del changelog {: #changelog-modal }

Il **modale del changelog** integrato nell'app visualizza il `CHANGELOG.md` incluso. Puoi raggiungerlo da due punti:

- dal **numero di versione in fondo alla barra laterale** (in qualsiasi pagina), e
- dall'**etichetta della versione subito sotto il titolo di questa pagina Informazioni** (Impostazioni → Informazioni).

- Un **pannello comprimibile per ogni release** — solo la release più recente inizia aperta; anche le sezioni e le sottosezioni si comprimono.
- Un **indice delle versioni** con chip nella parte superiore: cliccando su una versione, questa si espande e la pagina scorre automaticamente fino ad essa.
- Una **casella di ricerca** che si addentra tra le sezioni comprimibili: le sezioni corrispondenti si aprono automaticamente e i chip cliccabili dei risultati saltano al punto esatto.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="changelog-modal-search" alt="Ricerca nel modale del changelog che apre le sezioni corrispondenti">
</div>

- Pulsanti **Espandi tutto / Comprimi tutto** e un collegamento al file del changelog su GitHub.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="changelog-modal" alt="Modale del changelog con release comprimibili e ricerca">
</div>

### 🔄 Verifica degli aggiornamenti

L'intestazione del modale contiene anche un pulsante **verifica aggiornamenti**, che interroga GitHub per la release stabile più recente. Quello che succede dopo dipende dal tuo ruolo:

- Se LibreFolio è **aggiornato**, appare un toast di conferma.
- Se esiste una release più recente e sei un **amministratore**, si apre il **modale aggiornamento-disponibile**: la versione attuale e quella più recente affiancate, con collegamenti alla [guida all'aggiornamento](../installation.md#updating) e alla pagina delle release su GitHub. Puoi chiuderlo con **Più tardi** (verrai avvisato al prossimo accesso) oppure **Salta questa versione** (non verrai più avvisato per quella release). Per gli amministratori la verifica avviene anche automaticamente all'accesso — consulta [Notifiche di aggiornamento](../../admin/index.md#update-notifications) per il flusso lato amministratore.
- Se esiste una release più recente e **non sei un amministratore**, una finestra di dialogo elenca gli **amministratori** dell'istanza — con gli indirizzi e-mail quando disponibili, ciascuno con un collegamento mailto e un pulsante di copia — così sai a chi chiedere l'aggiornamento. I non amministratori non vengono mai verificati automaticamente.

---

## 🔗 Correlati

- ⚙️ **[Panoramica delle Impostazioni](index.md)** — Riepilogo generale delle impostazioni
- 👤 **[Profilo](profile.md)** — Nome utente, email, avatar, password
- 🎛️ **[Preferenze dell'utente](preferences.md)** — Lingua, valuta di base e tema
- 🛡️ **[Impostazioni globali](../../admin/settings.md)** — Opzioni di amministrazione e scheduler
