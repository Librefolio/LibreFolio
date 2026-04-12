# 🚀 Getting Started

Benvenuto in LibreFolio! Questa guida ti accompagnerà nella registrazione di un account, nell'accesso e nella creazione del tuo primo broker: tutto ciò di cui hai bisogno per iniziare a monitorare il tuo portafoglio.

---

## 📝 1. Register Your Account

Vai all'URL di LibreFolio (es. `http://localhost:8000`) e vedrai la pagina di login. Clicca su **Register** per creare un nuovo account.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Registration Form" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Inserisci i tuoi dati:

- 👤 **Username**: Il tuo nome visualizzato (unico all'interno del sistema)
- 📧 **Email**: Un indirizzo email valido
- 🔑 **Password**: Una password sicura (l'indicatore di forza ti aiuterà)

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registration with Password Strength" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "First User = Admin"

    Il primo utente a registrarsi diventa automaticamente l'**amministratore di sistema** (superuser). Questo utente può gestire le impostazioni globali, promuovere altri utenti e accedere a tutte le funzionalità di amministrazione.

---

## 🔐 2. Log In

Dopo la registrazione, verrai reindirizzato alla pagina di login. Inserisci le tue credenziali per accedere alla tua dashboard.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="01-login" alt="Login Page" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🏦 3. Create Your First Broker

Un **broker** in LibreFolio rappresenta un conto di intermediazione: il luogo in cui risiedono i tuoi investimenti (es. Interactive Brokers, Degiro, un conto bancario, ecc.).

!!! note "Why do I need a Broker?"

    Tutte le transazioni in LibreFolio sono collegate a un broker. È il contenitore che raggruppa le tue transazioni, le importazioni e i report. È necessario almeno un broker prima di poter iniziare a monitorare qualsiasi attività.

### 📋 Passaggi

1. Vai alla pagina **Brokers** dal menu della barra laterale
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="list" alt="Broker List" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>
2. Clicca sul pulsante **"New Broker"**
3. Compila i dettagli del broker:
 - 🏷️ **Name**: Un nome descrittivo (es. "Mio Conto Degiro")
 - 💰 **Base Currency**: La valuta del conto (es. EUR, USD)
 - 🖼️ **Icon** *(opzionale)*: Carica un logo o un avatar del broker
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Broker List" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>
4. Una volta creato, puoi cliccare su un broker per vederne i dettagli, importare report e gestire le transazioni.
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="detail" alt="Broker Detail" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

---

## 🔮 4. What's Next?

Ora che hai un account e un broker, puoi:

- 📤 **[Caricare i report del broker](files/index.md)** — Importa file CSV/Excel dal tuo broker per l'analisi automatica delle transazioni
- 🤝 **[Condividere il tuo broker](brokers/sharing.md)** — Dai l'accesso a familiari, consulenti o commercialisti
- 💱 **[Configurare i tassi di cambio](fx/index.md)** — Configura la conversione valutaria per portafogli multi-valuta
- ⚙️ **[Personalizzare le impostazioni](../admin/settings.md)** — Regola lingua, tema e preferenze di sistema

!!! tip "Portfolio Calculations"

    I broker vengono utilizzati anche per i calcoli di aggregazione del portafoglio. Quando condividi un broker con un altro utente e imposti una **percentuale di condivisione**, il sistema può calcolare la quota di ogni utente sul valore totale del portafoglio. Questa funzionalità è in fase di sviluppo attivo.
