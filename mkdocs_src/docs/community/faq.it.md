# ❓ Domande Frequenti (FAQ)

Benvenuti nelle FAQ di LibreFolio. Qui troverete le risposte alle domande più comuni.

## 💬 Domande Generali

### 🤔 Cos'è LibreFolio?

LibreFolio è un tracker di portafoglio open-source che vi offre una visione completa e privata di tutti i vostri investimenti. Potenti strumenti di analisi trasformano i vostri dati in informazioni strategiche, permettendovi di prendere decisioni informate con piena fiducia e pieno controllo.

### 💰 LibreFolio è gratuito?

Sì! LibreFolio è completamente gratuito e open-source sotto la [licenza AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html). Potete installarlo sul vostro server e gestire tutto autonomamente senza alcun costo.

!!! info "Prossimamente: piattaforma hosted ☁️"

    Stiamo lavorando a una piattaforma online per coloro che non hanno il tempo, l'interesse o le competenze tecniche per il self-hosted. La versione hosted offrirà tutte le funzionalità con installazione zero, aggiornamenti automatici e supporto dedicato — disponibile tramite abbonamento a pagamento.

### 🤖 Sono previste funzionalità di AI?

Sì! La nostra roadmap include **assistenti basati su AI** per aiutarvi ad analizzare il vostro portafoglio, individuare trend e prendere decisioni meglio informate.

- **Self-hosted**: potete collegare i vostri modelli di AI e gestire tutto in modo indipendente
- **Piattaforma hosted**: gli assistenti AI saranno completamente integrati — pronti all'uso senza necessità di configurazione, insieme a un supporto premium

### 📊 Quali asset posso monitorare?

LibreFolio supporta:

- **Azioni & ETF** — Prezzi recuperati automaticamente tramite provider di dati (es. yfinance)
- **Criptovalute** — Prossimamente
- **Obbligazioni** — Supportato l'inserimento manuale
- **P2P Lending** — Asset con investimento programmato
- **Liquidità & Depositi** — Monitorate la vostra liquidità

!!! tip "Manca qualcosa? 💡"

    Se c'è una classe di asset o una funzionalità che vorreste vedere e a cui non abbiamo ancora pensato, ci piacerebbe saperlo! Aprite una [richiesta di funzionalità su GitHub](https://github.com/Alfystar/LibreFolio/issues/new?labels=enhancement) e fatecelo sapere.

## 🚀 Guida Rapida

### 📦 Come installo LibreFolio?

Consultate la nostra [Guida all'Installazione](../developer/dev-installation.md) per istruzioni dettagliate.

### 👤 Come creo un account?

1. Navigate alla pagina di login
2. Cliccate su "Registrati"
3. Inserite i vostri dati
4. Il vostro account è pronto all'uso!

### 🔑 Ho dimenticato la password, cosa devo fare?

Al momento, il reset della password viene effettuato tramite CLI. Contattate l'amministratore della vostra istanza o eseguite:

```bash
./dev.py user reset <username> <new_password>
```

## 🔧 Risoluzione dei Problemi

### 📉 I prezzi dei miei asset non si aggiornano

Verificate che:

1. La sincronizzazione automatica dei prezzi sia abilitata nelle impostazioni globali
2. I vostri asset abbiano ISIN o simboli validi riconosciuti dal **provider** configurato (es. [yfinance](https://pypi.org/project/yfinance/) per azioni ed ETF)
3. Il servizio del provider sia disponibile (controllate i log del server per eventuali errori)

### 💱 I miei tassi di cambio non si aggiornano

Verificate che:

1. La coppia di valute abbia almeno un [provider configurato](../user/fx/detail/provider.md)
2. L'API del provider sia raggiungibile (ECB, FED, BOE, SNB)
3. Abbiate eseguito una [sincronizzazione](../user/fx/sync.md) per l'intervallo di date desiderato
4. Controllate la [gerarchia dei provider](../user/fx/detail/provider.md) per le opzioni di fallback

### 🔐 Non riesco a effettuare il login

- Verificate username e password
- Controllate se il vostro account è attivato
- Cancellate i cookie del browser e riprovate

### 📱 Posso usare LibreFolio come app mobile?

Sì! LibreFolio supporta l'installazione come **PWA (Progressive Web App)**. Potete aggiungerlo alla schermata home su Android, iOS o desktop per un'esperienza a schermo intero simile a un'app — senza bisogno di app store.

Consultate la guida [Installa come App (PWA)](../user/pwa.md) per le istruzioni passo dopo passo.

## 🆘 Serve altro aiuto?

- [Documentazione Completa](../index.md)
- [Segnala un Bug](https://github.com/Alfystar/LibreFolio/issues)
- [GitHub Discussions](https://github.com/Alfystar/LibreFolio/discussions)
