# ❓ Domande frequenti (FAQ)

Benvenuto nelle FAQ di LibreFolio. Qui troverai le risposte alle domande più comuni.

## 💬 Domande generali

### 🤔 Cos'è LibreFolio?

LibreFolio è un tracker di portafoglio open-source che ti offre una visione completa e privata di tutti i tuoi investimenti. Potenti strumenti di analisi trasformano i tuoi dati in insight operativi — così puoi prendere decisioni informate con piena fiducia e pieno controllo.

### 💰 LibreFolio è gratuito?

Sì! LibreFolio è completamente gratuito e open-source con licenza [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html). Puoi installarlo sul tuo server e gestire tutto da solo, senza alcun costo.

### 🤖 Posso usare LibreFolio con un assistente AI?

Sì. **[AI Export](../user/ai-export/index.md)** copia i tuoi dati come testo pronto da incollare, con una domanda mirata se ne vuoi una, così puoi chiedere all'assistente AI che preferisci informazioni sul tuo portafoglio, un broker, un asset o una coppia di valute. LibreFolio stesso non contatta mai un servizio AI.

### 📊 Quali asset posso monitorare?

LibreFolio supporta:

- **Azioni, ETF e fondi** — prezzi recuperati automaticamente da provider di dati (ad es., yfinance)
- **Obbligazioni** — prezzi da un provider, oppure inseriti manualmente
- **Asset cripto** — monitorati come asset di portafoglio, non come valute
- **Crowdfunding e prestiti P2P** — valutati con un rendimento programmato
- **Materie prime, immobili** e asset senza prezzo di mercato (arte, oggetti da collezione, azioni non quotate)
- **Liquidità** — il saldo di ogni broker, in ogni valuta

L'elenco completo è in [Tipi di asset](../financial-theory/instruments/asset-types/index.md).

!!! tip "Manca qualcosa? 💡"

    Se c'è una classe di asset o una funzionalità che vorresti vedere e a cui non abbiamo ancora pensato, ci piacerebbe sentirti! Apri una [richiesta di funzionalità su GitHub](https://github.com/Librefolio/LibreFolio/issues/new?labels=enhancement) e faccelo sapere.

## 🚀 Per iniziare

### 📦 Come installo LibreFolio?

Segui la [Guida all'installazione Docker](../user/installation.md), il metodo consigliato, oppure la [Guida all'installazione su host](../admin/host_installation.md) per eseguirlo con Pipenv.

### 👤 Come creo un account?

1. Apri la pagina di accesso e fai clic su **Registrati qui**, accanto a *Non hai un account?* Se un amministratore ti ha inviato un link d'invito, apri invece quel link.
2. Compila i tuoi dati, poi fai clic su **Registrati**.
3. Torni alla pagina di accesso: accedi con il tuo nuovo account.

Se la pagina di accesso non mostra **Registrati qui**, questo server accetta nuovi account solo tramite un link d'invito, oppure non ne accetta affatto: chiedi all'amministratore. Su una nuova istanza, il primo account creato diventa l'amministratore. Dettagli: [Guida introduttiva](../user/getting-started.md#invitation-link) e, per gli amministratori, [Chi può registrarsi](../admin/settings.md#registration).

### 🔑 Ho dimenticato la password, cosa faccio?

Nella pagina di accesso, fai clic su **Password dimenticata?**. Se la tua istanza può inviare e-mail, inserisci lì il tuo nome utente o il tuo indirizzo e-mail e ricevi un link di reimpostazione valido per 30 minuti ([come funziona](../user/getting-started.md#forgot-password)). Altrimenti chiedi all'amministratore della tua istanza. Può inviarti un link di reimpostazione della password, con cui scegli tu stesso la nuova password ([come funziona](../user/getting-started.md#password-reset-link)), oppure impostarti una nuova password dalla riga di comando ([Reimpostare una password](../admin/cli_tools.md#reset-a-password-or-lock-an-account)).

## 🔧 Risoluzione dei problemi

### 📉 I prezzi dei miei asset non si aggiornano

Verifica che:

1. **Scheduler abilitato** sia attivo nelle [Impostazioni globali](../admin/settings.md#market-data-scheduler): esegue gli aggiornamenti automatici. Solo gli amministratori hanno quella scheda: se non lo sei, chiedi al tuo amministratore di controllare
2. I tuoi asset abbiano ISIN o simboli validi riconosciuti dal **provider di dati** configurato (ad es., [yfinance](https://pypi.org/project/yfinance/) per azioni ed ETF)
3. Il servizio del provider sia disponibile (controlla i log del server per errori)

### 💱 I miei tassi FX non si aggiornano

Verifica che:

1. **Scheduler abilitato** sia attivo nelle [Impostazioni globali](../admin/settings.md#market-data-scheduler). Solo gli amministratori hanno quella scheda: se non lo sei, chiedi al tuo amministratore di controllare
2. La coppia di valute abbia almeno un [provider di dati configurato](../user/fx/detail/provider.md)
3. L'API del provider sia raggiungibile (ECB, FED, BOE, SNB)
4. Hai eseguito una [sincronizzazione](../user/fx/sync.md) per l'intervallo di date desiderato
5. Controlla la [catena di fornitura del provider](../user/fx/detail/provider.md) per opzioni di fallback

### 🔐 Non riesco ad accedere

- Verifica il tuo nome utente e la password
- Con una password errata ricevi sempre lo stesso messaggio *Nome utente o password non validi*, indipendentemente dal fatto che l'account esista o meno; con la password corretta, se l'account è disabilitato ti viene segnalato: chiedi all'amministratore di riabilitarlo
- Cancella i cookie del browser e riprova

### 📱 Posso usare LibreFolio come app mobile?

Sì! LibreFolio supporta l'installazione come **PWA (Progressive Web App)**. Puoi aggiungerla alla schermata Home su Android, iOS o desktop per un'esperienza a schermo intero, simile a un'app — senza bisogno di un app store.

Consulta la guida [Installa come app (PWA)](../user/pwa.md) per istruzioni passo passo.

## 🆘 Serve altro aiuto?

- [Documentazione completa](../index.md)
- [Segnala un bug](https://github.com/Librefolio/LibreFolio/issues)
- [Discussioni GitHub](https://github.com/Librefolio/LibreFolio/discussions)
