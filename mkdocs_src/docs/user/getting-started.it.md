# 🚀 Per iniziare

Benvenuto in LibreFolio! Questa guida ti accompagna nella registrazione di un account, nell'accesso e nella creazione del tuo primo broker — tutto ciò che ti serve per iniziare a monitorare il tuo portafoglio.

---

## 📝 1. Registra il tuo account

Vai all'URL di LibreFolio (es. `http://localhost:8000`) e vedrai la pagina di login. Clicca su **Registrati** per creare un nuovo account.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Modulo di Registrazione" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Compila i tuoi dati:

- 👤 **Nome utente**: Il tuo nome visuale (unico nel sistema)
- 📧 **Email**: Un indirizzo email valido
- 🔑 **Password**: Una password sicura (l'indicatore di forza della password ti aiuta)

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registrazione con Indicatore di Forza della Password" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "Il primo utente = amministratore"
    Il primissimo utente che si registra diventa automaticamente l'**amministratore di sistema** (superutente). Questo utente può gestire le impostazioni globali, promuovere altri utenti e accedere a tutte le funzionalità di amministrazione.

---

## 🔐 2. Accedi

Dopo la registrazione, verrai reindirizzato alla pagina di login. Inserisci le tue credenziali per accedere alla tua dashboard.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="01-login" alt="Pagina di Login" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🏦 3. Crea il tuo primo broker

Un **broker** in LibreFolio rappresenta un conto di intermediazione — il luogo in cui sono custoditi i tuoi investimenti (es. Interactive Brokers, Degiro, un conto bancario, ecc.).

!!! note "Perché ho bisogno di un broker?"
    Tutte le transazioni in LibreFolio sono collegate a un broker. È il contenitore che raggruppa le tue transazioni, importazioni e report. Hai bisogno di almeno un broker prima di poter iniziare a monitorare qualsiasi cosa.

### 📋 Passaggi

1. Vai alla pagina **broker** dal menu laterale
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="list" alt="Elenco broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>
2. Clicca sul pulsante **Nuovo broker**
3. Compila i dettagli del broker:
 - 🏷️ **Nome**: Un nome descrittivo (es. "Il Mio Conto Degiro")
 - 💰 **Valuta base**: La valuta del conto (es. EUR, USD)
 - 🖼️ **Icona** *(opzionale)*: Carica un logo o un avatar per il broker
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Modifica broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>
4. Una volta creato, puoi cliccare su un broker per vederne i dettagli, importare report e gestire le transazioni.
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="detail" alt="Dettaglio broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

---

## 🔮 4. E adesso?

Ora che hai un account e un broker, puoi:

- 📤 **[Caricare report del broker](files/index.md)** — Importa file CSV/Excel dal tuo broker per l'analisi automatica delle transazioni
- 🤝 **[Condividere il tuo broker](brokers/sharing.md)** — Dai accesso a familiari, consulenti o commercialisti
- 💱 **[Configurare i tassi di cambio](fx/index.md)** — Imposta la conversione valuta per portafogli multi-valuta
- ⚙️ **[Personalizzare le impostazioni](../admin/settings.md)** — Modifica lingua, tema e preferenze di sistema

!!! tip "Calcoli del portafoglio"
    I broker sono utilizzati anche per i calcoli di aggregazione del portafoglio. Quando condividi un broker con un altro utente e imposti una **percentuale di condivisione**, il sistema può calcolare la quota di ciascun utente sul valore totale del portafoglio. Questa funzionalità è in fase di sviluppo attivo.
