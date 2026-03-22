# ❓ Domande Frequenti (FAQ)

Benvenuti nella FAQ di LibreFolio. Qui troverete le risposte alle domande più comuni.

## 💬 Domande Generali

### 🤔 Cos'è LibreFolio?
LibreFolio è un tracker di portafoglio open source e self-hosted, progettato per investitori attenti alla privacy. Ti consente di tracciare i tuoi investimenti, analizzare le performance e mantenere il pieno controllo dei tuoi dati finanziari.

### 💰 LibreFolio è gratuito?
Sì! LibreFolio è completamente gratuito e open source sotto licenza MIT.

### 📊 Quali asset posso tracciare?
LibreFolio supporta:

- **Azioni & ETF** - Prezzi recuperati automaticamente da yfinance
- **Criptovalute** - In arrivo a breve
- **Obbligazioni** - Inserimento manuale supportato
- **Prestiti peer-to-peer** - Strumenti a rendimento prefissato
- **Contanti & Depositi** - Tracciamento della liquidità

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

### 📉 I miei prezzi non si aggiornano
Verifica che:

1. L'auto-sincronizzazione sia abilitata nelle Impostazioni Globali
2. I tuoi asset abbiano ISIN o simboli validi
3. Il provider yfinance funzioni (controlla i log)

### 🔐 Non riesco ad accedere
- Verifica username e password
- Controlla se il tuo account è attivato
- Cancella i cookie del browser e riprova

## 🆘 Serve Altro Aiuto?
- [Documentazione Completa](index.md)
- [Segnala un Bug](https://github.com/Alfystar/LibreFolio/issues)
- [GitHub Discussions](https://github.com/Alfystar/LibreFolio/discussions)
