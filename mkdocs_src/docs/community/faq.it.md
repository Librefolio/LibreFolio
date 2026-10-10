# ❓ Domande frequenti (FAQ)

Benvenuto nelle FAQ di LibreFolio. Qui troverai le risposte alle domande più comuni.

## 💬 Domande generali

### 🤔 Cos'è LibreFolio?

LibreFolio è un tracker di portafoglio open-source che ti offre una visione completa e privata di tutti i tuoi investimenti. Potenti strumenti di analisi trasformano i tuoi dati in insight operativi — così puoi prendere decisioni informate con piena fiducia e pieno controllo.

### 💰 LibreFolio è gratuito?

Sì! LibreFolio è completamente gratuito e open-source con licenza [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html). Puoi installarlo sul tuo server e gestire tutto da solo, senza alcun costo.

!!! info "Prossimamente: piattaforma hosted ☁️"

    Stiamo lavorando a una piattaforma online per chi non ha il tempo, l'interesse o le competenze tecniche per il self-hosting. La versione hosted offrirà tutte le funzionalità senza alcuna configurazione, aggiornamenti automatici e supporto dedicato — disponibile come abbonamento a pagamento.

### 🤖 Posso usare LibreFolio con un assistente AI?

Sì. **[AI Export](../user/ai-export/index.md)** copia i tuoi dati come testo pronto da incollare, con una domanda mirata se ne vuoi una, così puoi chiedere all'assistente AI che preferisci informazioni sul tuo portafoglio, un broker, un asset o una coppia di valute. LibreFolio stesso non contatta mai un servizio AI.

Sulla prossima piattaforma hosted, gli assistenti AI saranno completamente integrati: pronti all'uso senza configurazione, con supporto premium.

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

1. Apri la pagina di accesso.
2. Fai clic su **Registrati qui**, accanto a *Non hai un account?*
3. Compila i tuoi dati: il tuo account è pronto all'uso.

Su una nuova istanza, il primo account creato diventa l'amministratore. Dopodiché, la registrazione funziona solo finché l'amministratore mantiene **Abilita registrazione** attivo nelle [Impostazioni globali](../admin/settings.md); altrimenti, chiedi all'amministratore di crearti un account.

### 🔑 Ho dimenticato la password, cosa faccio?

Il recupero via e-mail non è ancora disponibile: chiedi all'amministratore della tua istanza, che può impostare una nuova password dalla riga di comando ([Reimpostare una password](../admin/cli_tools.md#reset-a-password-or-lock-an-account)).

## 🔧 Risoluzione dei problemi

### 📉 I prezzi dei miei asset non si aggiornano

Verifica che:

1. **Scheduler abilitato** sia attivo nelle [Impostazioni globali](../admin/settings.md#market-data-scheduler): esegue gli aggiornamenti automatici
2. I tuoi asset abbiano ISIN o simboli validi riconosciuti dal **provider di dati** configurato (ad es., [yfinance](https://pypi.org/project/yfinance/) per azioni ed ETF)
3. Il servizio del provider sia disponibile (controlla i log del server per errori)

### 💱 I miei tassi FX non si aggiornano

Verifica che:

1. **Scheduler abilitato** sia attivo nelle [Impostazioni globali](../admin/settings.md#market-data-scheduler)
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
