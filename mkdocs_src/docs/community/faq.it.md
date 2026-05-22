# ❓ Domande Frequenti (FAQ)

Benvenuti nelle FAQ di LibreFolio. Qui troverete le risposte alle domande più comuni.

## 💬 Domande Generali

### 🤔 Cos'è LibreFolio?

LibreFolio è un tracker di portafoglio open-source che offre una visione completa e privata di tutti i tuoi investimenti. Potenti strumenti di analisi trasformano i tuoi dati in intuizioni concrete, così puoi prendere decisioni informate con piena fiducia e pieno controllo.

### 💰 LibreFolio è gratuito?

Sì! LibreFolio è completamente gratuito e open-source sotto la [licenza AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html). Puoi installarlo sul tuo server e gestire tutto autonomamente senza alcun costo.

!!! info "Prossimamente: piattaforma hosted ☁️"

    Stiamo lavorando a una piattaforma online per coloro che non hanno il tempo, l'interesse o le competenze tecniche per il self-hosting. La versione hosted offrirà tutte le funzionalità senza alcuna configurazione, aggiornamenti automatici e supporto dedicato — disponibile tramite abbonamento a pagamento.

### 🤖 Sono previste funzionalità di IA?

Sì! La nostra roadmap include **assistenti basati su IA** per aiutarti ad analizzare il tuo portafoglio, individuare i trend e prendere decisioni meglio informate.

- **Self-hosted**: puoi collegare i tuoi modelli di IA e gestire tutto indipendentemente
- **Piattaforma hosted**: gli assistenti IA saranno completamente integrati — pronti all'uso senza necessità di configurazione, insieme a un supporto premium

### 📊 Quali asset posso monitorare?

LibreFolio supporta:

- **Azioni e ETF** — Prezzi recuperati automaticamente tramite provider (es. yfinance)
- **Criptovalute** — Prossimamente
- **Obbligazioni** — Supportato l'inserimento manuale
- **P2P Lending** — Asset con rendimenti programmati
- **Liquidità e Depositi** — Monitora la tua liquidità

!!! tip "Manca qualcosa? 💡"

    Se c'è una classe di asset o una funzionalità che vorresti vedere e a cui non abbiamo ancora pensato, ci piacerebbe conoscere la tua opinione! Apri una [richiesta di funzionalità su GitHub](https://github.com/Alfystar/LibreFolio/issues/new?labels=enhancement) e faccelo sapere.

## 🚀 Primi Passi

### 📦 Come installo LibreFolio?

Consulta la nostra [Guida all'Installazione](../developer/dev-installation.md) per istruzioni dettagliate.

### 👤 Come creo un account?

1. Vai alla pagina di login
2. Clicca su "Register"
3. Inserisci i tuoi dati
4. Il tuo account è pronto all'uso!

### 🔑 Ho dimenticato la password, cosa devo fare?

Attualmente, il reset della password viene effettuato via CLI. Contatta l'amministratore della tua istanza o esegui:

```bash
./dev.py user reset <username> <new_password>
```

## 🔧 Risoluzione dei Problemi

### 📉 I prezzi dei miei asset non si aggiornano

Verifica che:

1. L'auto-sync sia abilitato nelle Impostazioni Globali
2. I tuoi asset abbiano ISIN validi o simboli riconosciuti dal **provider** configurato (es. [yfinance](https://pypi.org/project/yfinance/) per azioni ed ETF)
3. Il servizio del provider sia disponibile (controlla i log del server per eventuali errori)

### 💱 I miei tassi FX non si aggiornano

Verifica che:

1. La coppia di valute abbia almeno un [provider configurato](../user/fx/detail/provider.md)
2. L'API del provider sia raggiungibile (ECB, FED, BOE, SNB)
3. Hai eseguito un [sync](../user/fx/sync.md) per l'intervallo di date desiderato
4. Controlla la [catena di fallback del provider](../user/fx/detail/provider.md) per le opzioni di fallback

### 🔐 Non riesco a effettuare il login

- Verifica il tuo nome utente e la password
- Controlla se il tuo account è attivato
- Svuota i cookie del browser e riprova

## 🆘 Hai bisogno di ulteriore aiuto?

- [Documentazione Completa](../index.md)
- [Segnala un Bug](https://github.com/Alfystar/LibreFolio/issues)
- [GitHub Discussions](https://github.com/Alfystar/LibreFolio/discussions)
