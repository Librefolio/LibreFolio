# ❓ Domande Frequenti (FAQ)

Benvenuti nella FAQ di LibreFolio. Qui troverete le risposte alle domande più comuni.

## 💬 Domande Generali

### 🤔 Cos'è LibreFolio?
LibreFolio è un tracker di portafoglio open source e self-hosted, progettato per investitori attenti alla privacy. Ti consente di tracciare i tuoi investimenti, analizzare le performance e mantenere il pieno controllo dei tuoi dati finanziari.

### 💰 LibreFolio è gratuito?
Sì! LibreFolio è completamente gratuito e open source sotto licenza [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html).

### 📊 Quali asset posso tracciare?
LibreFolio supporta:

- **Azioni & ETF** — Prezzi recuperati automaticamente tramite provider di dati (es. yfinance)
- **Criptovalute** — In arrivo a breve
- **Obbligazioni** — Inserimento manuale supportato
- **Prestiti peer-to-peer** — Strumenti a rendimento prefissato
- **Contanti & Depositi** — Tracciamento della liquidità

!!! tip "Manca qualcosa? 💡"

    Se c'è un tipo di asset o una funzionalità che vorresti vedere e a cui non abbiamo ancora pensato, faccelo sapere! Apri una [richiesta di miglioramento su GitHub](https://github.com/Alfystar/LibreFolio/issues/new?labels=enhancement) e condividi la tua idea.

## 🚀 Iniziare

### 📦 Come installo LibreFolio?
Consulta la nostra [Guida all'Installazione](developer/dev-installation.md) per istruzioni dettagliate.

### 👤 Come creo un account?
1. Vai alla pagina di login
2. Clicca "Registrati"
3. Compila i tuoi dati
4. Il tuo account è pronto per l'uso!

### 🔑 Ho dimenticato la password, cosa faccio?
Attualmente il reset della password avviene via CLI. Contatta l'amministratore della tua istanza o esegui:

```bash
./dev.py user reset <username> <new_password>
```

## 🔧 Risoluzione dei Problemi

### 📉 I prezzi degli asset non si aggiornano
Verifica che:

1. L'auto-sincronizzazione sia abilitata nelle Impostazioni Globali
2. I tuoi asset abbiano ISIN o simboli validi riconosciuti dal **provider di dati** configurato (es. [yfinance](https://pypi.org/project/yfinance/) per azioni ed ETF)
3. Il servizio del provider sia disponibile (controlla i log del server)

### 💱 I tassi di cambio non si aggiornano
Verifica che:

1. La coppia di valute abbia almeno un [provider di dati configurato](user/fx/detail/provider.md)
2. L'API del provider sia raggiungibile (BCE, FED, BOE, SNB)
3. Sia stata eseguita una [sincronizzazione](user/fx/sync.md) per l'intervallo di date desiderato
4. Controlla la [catena di approvvigionamento](user/fx/detail/provider.md) per le opzioni di fallback

### 🔐 Non riesco ad accedere
- Verifica username e password
- Controlla se il tuo account è attivato
- Cancella i cookie del browser e riprova

## 🆘 Serve Altro Aiuto?
- [Documentazione Completa](index.md)
- [Segnala un Bug](https://github.com/Alfystar/LibreFolio/issues)
- [GitHub Discussions](https://github.com/Alfystar/LibreFolio/discussions)
