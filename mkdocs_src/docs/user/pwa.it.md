# 📱 Installa come App (PWA)

LibreFolio può essere installato come **Progressive Web App (PWA)** sul tuo dispositivo. Questo ti offre un'esperienza simile a quella di un'app: modalità a schermo intero, nessuna barra degli indirizzi del browser e un'icona sulla schermata home — senza dover scaricare nulla da uno store di app.

---

## ✅ Cosa Ottieni

| Funzionalità | Descrizione |
|---------|-------------|
| **Modalità a schermo intero** | Nessuna barra degli indirizzi o elementi superflui dell'interfaccia del browser |
| **Icona sulla schermata home** | Avvia LibreFolio come un'app nativa |
| **Nessuna interferenza dei gesti** | Swipe-back e zoom con doppio tocco disabilitati |
| **Sessione persistente** | Resta collegato tra un avvio e l'altro |

!!! note "Online Only"

    La PWA di LibreFolio richiede una connessione di rete attiva. Non esiste una modalità offline: i tuoi dati risiedono sul tuo server.

---

## 📲 Come Installare

### Android (Chrome / Edge)

1. Apri LibreFolio in Chrome o Edge
2. Cerca il pulsante **"Install App"** nel menu **Help & Support** (icona ❓ in alto a destra)
3. Tocca **Installa** quando richiesto
4. LibreFolio apparirà sulla tua schermata home

!!! tip "Metodo alternativo"

    Se il pulsante di Installazione non appare, tocca il **menu ⋮ del browser → "Aggiungi alla schermata Home"** o **"Installa app"**.

### iOS (Safari)

1. Apri LibreFolio in **Safari** (obbligatorio — gli altri browser non supportano le PWA su iOS)
2. Tocca il pulsante **Condividi** (quadrato con freccia)
3. Scorri verso il basso e tocca **"Aggiungi alla schermata Home"**
4. Tocca **Aggiungi**

!!! warning "iOS Limitation"

    Il prompt di installazione automatica non è disponibile su iOS. Usa il menu Condividi come descritto sopra. Il menu Help mostrerà le istruzioni se ti trovi su un dispositivo iOS.

### Desktop (Chrome / Edge)

1. Apri LibreFolio in Chrome o Edge
2. Clicca sul pulsante **"Install App"** nel menu Help & Support
3. Oppure clicca sull'icona di installazione (⊕) nella barra degli indirizzi del browser
4. LibreFolio si aprirà in una finestra dedicata

---

## 🌐 HTTP vs HTTPS

| Configurazione | Installazione PWA | Prompt Automatico |
|-------|-------------|-------------|
| `https://` (Tailscale, reverse proxy) | ✅ Supporto completo | ✅ Chrome mostra il banner |
| `http://localhost` | ✅ Funziona | ✅ Funziona |
| `http://192.168.x.x` (LAN) | ⚠️ Solo manuale | ❌ Nessun prompt automatico |

!!! info "Self-hosted su LAN"

    Se accedi a LibreFolio tramite HTTP sulla tua rete locale (es. `http://192.168.1.100:6040`), il prompt di installazione automatica non apparirà. Puoi comunque installarlo manualmente:

    - **Android**: Menu browser → "Aggiungi alla schermata Home"
    - **iOS**: Condividi → "Aggiungi alla schermata Home"
    - **Desktop**: Non disponibile su HTTP (usa Tailscale per HTTPS)

    Per il pieno supporto PWA, esponi la tua istanza tramite [Tailscale](../admin/tailscale_exposure.md) (HTTPS gratuito e semplice).

---

## 🔧 Risoluzione dei Problemi

| Problema | Soluzione |
|---------|----------|
| Pulsante di installazione non visibile | Potresti averlo già installato, oppure sei su HTTP LAN |
| iOS: nessuna opzione di installazione | È necessario usare **Safari** — Chrome/Firefox su iOS non supportano le PWA |
| L'app non si aggiorna | Chiudi e riapri l'app — scarica sempre l'ultima versione |
| Sessione persa dopo l'aggiornamento | Effettua nuovamente il login — è normale dopo il riavvio del server |
