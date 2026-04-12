# ❓ Domande Frequenti (FAQ)

Benvenuti nelle FAQ di LibreFolio. Qui troverete le risposte alle domande più comuni.

## 💬 Domande Generali

### 🤔 Cos'è LibreFolio?

LibreFolio è un tracker di portafoglio open-source e self-hosted progettato per investitori attenti alla privacy. Consente di monitorare i propri investimenti, analizzare le performance e mantenere il pieno controllo dei propri dati finanziari.

### 💰 LibreFolio è gratuito?

Sì! LibreFolio è completamente gratuito e open-source sotto la [licenza AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html).

### 📊 Quali asset posso monitorare?

LibreFolio supporta:

- **Azioni & ETF** — Prezzi recuperati automaticamente tramite provider di dati (es. yfinance)
- **Criptovalute** — In arrivo
- **Obbligazioni** — Supportato l'inserimento manuale
- **P2P Lending** — Asset a rendimento prefissato
- **Contanti & Depositi** — Monitora la tua liquidità

!!! tip "Manca qualcosa? 💡"

    Se c'è una classe di asset o una funzionalità che vorresti vedere e a cui non abbiamo ancora pensato, ci piacerebbe sapere cosa ne pensi! Apri una [richiesta di funzionalità su GitHub](https://github.com/Alfystar/LibreFolio/issues/new?labels=enhancement) e faccelo sapere.

## 🚀 Primi Passi

### 📦 Come si installa LibreFolio?

Consulta la nostra [Guida all'Installazione](developer/dev-installation.md) per istruzioni dettagliate.

### 👤 Come creo un account?

1. Vai alla pagina di login
2. Clicca su "Registrati"
3. Inserisci i tuoi dati
4. Il tuo account è pronto all'uso!

### 🔑 Ho dimenticato la password, cosa devo fare?

Attualmente, il reset della password viene effettuato tramite CLI. Contatta l'amministratore della tua istanza o esegui:

```bash
./dev.py user reset <username> <new_password>
```

## 🔧 Risoluzione dei Problemi

### 📉 I prezzi dei miei asset non si aggiornano

Verifica che:

1. La sincronizzazione automatica sia abilitata nelle impostazioni globali
2. I tuoi asset abbiano ISIN o simboli validi e riconosciuti dal **provider** configurato (es. [yfinance](https://pypi.org/project/yfinance/) per azioni ed ETF)
3. Il servizio del provider sia disponibile (controlla i log del server per eventuali errori)

### 💱 I miei tassi di cambio non si aggiornano

Verifica che:

1. La coppia di valute abbia almeno un [provider configurato](user/fx/detail/provider.md)
2. L'API del provider sia raggiungibile (ECB, FED, BOE, SNB)
3. Tu abbia eseguito una [sincronizzazione](user/fx/sync.md) per l'intervallo di date desiderato
4. Controlla la [supply chain del provider](user/fx/detail/provider.md) per le opzioni di fallback

### 🔐 Non riesco a effettuare il login

- Verifica il tuo nome utente e la password
- Controlla se il tuo account è attivo
- Cancella i cookie del browser e riprova

## 🆘 Hai bisogno di ulteriore aiuto?

- [Documentazione Completa](index.md)
- [Segnala un Bug](https://github.com/Alfystar/LibreFolio/issues)
- [Discussioni su GitHub](https://github.com/Alfystar/LibreFolio/discussions)
