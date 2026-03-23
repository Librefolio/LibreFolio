# 🛡️ Manuale dell'Amministratore

Questo manuale è destinato agli amministratori di sistema e agli utenti avanzati che devono eseguire attività di manutenzione, gestire gli utenti o interagire con il sistema tramite la riga di comando.

## 📖 Panoramica

La maggior parte delle attività amministrative viene gestita attraverso lo strumento CLI principale:

1. **`dev.py`**: Lo script di orchestrazione principale per lo sviluppo e la manutenzione. Fornisce una CLI strutturata ad albero per tutte le attività: eseguire test, gestire il database, compilare il frontend, gestione degli utenti, traduzioni e molto altro.

## 📚 Guide

- 🛠️ **[Strumenti CLI](cli_tools.md)**: Documentazione dettagliata sui comandi e sottocomandi di `dev.py`.
- ⚙️ **[Impostazioni Globali](settings.md)**: Configurare i parametri a livello di sistema (TTL sessione, limiti di upload, intervalli di sincronizzazione, impostazioni predefinite).
- 📂 **[Struttura del Filesystem](filesystem.md)**: Capire dove sono archiviati i dati, come eseguire backup e come accedere al sistema dal terminale dell'host.
- 🐳 **[Docker Avanzato](docker_advanced.md)**: Un approfondimento sulla configurazione Docker, inclusi networking, volumi e personalizzazione per ambienti di produzione.
- 🌐 **[Esposizione con Tailscale](tailscale_exposure.md)**: Esporre in modo sicuro l'istanza LibreFolio su Internet utilizzando Tailscale.

## 🔐 Autenticazione

LibreFolio utilizza JWT (JSON Web Token) per l'autenticazione. Il server genera un segreto di firma casuale all'avvio, condiviso tra tutti i worker. I token scadono dopo un numero configurabile di ore (vedi [Impostazioni Globali](settings.md)). Per i dettagli tecnici, consultare [Architettura di Sicurezza](../developer/architecture/security.md).
