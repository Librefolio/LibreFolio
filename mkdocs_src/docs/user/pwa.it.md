# 📱 Installa come app (PWA)

LibreFolio può essere installato come **Progressive Web App (PWA)** sul tuo telefono, tablet o computer:
si apre come un'app nativa, dalla sua icona, senza app store.

---

## ✅ Cosa ottieni

- 🖥️ **Schermo intero** — nessuna barra degli indirizzi e nessuna barra degli strumenti del browser.
- 🏠 **Icona nella schermata Home** — avvia LibreFolio come qualsiasi altra app.
- 👆 **Nessun gesto accidentale** — lo swipe indietro e lo zoom con doppio tocco sono disattivati.
- 🔐 **Rimani autenticato** tra un avvio e l'altro, finché la tua sessione non scade.

!!! note "Solo online"

    L'app necessita di una connessione al tuo server LibreFolio: non esiste una modalità offline — i tuoi dati
    risiedono sul tuo server. Se apri l'app mentre il server non è raggiungibile, appare una pagina
    **Server non raggiungibile** che riprova da sola.

---

## 📲 Come installare

### 🤖 Android (Chrome / Edge)

1. Apri LibreFolio in Chrome o Edge.
2. Apri il menu **Aiuto e Supporto** (❓, in alto a destra) e tocca **Installa App**.
3. Conferma con **Installa**: LibreFolio appare nella schermata Home.

Nessuna finestra di installazione? Usa il menu **⋮** del browser → **Installa app** o **Aggiungi a schermata Home**.

### 🍎 iOS (Safari)

1. Apri LibreFolio in **Safari**.
2. Tocca il pulsante **Condividi** (quadrato con freccia).
3. Scorri verso il basso, tocca **Aggiungi a schermata Home**, poi **Aggiungi**.

iOS non ha una finestra di installazione: su iPhone o iPad, **Installa App** nel menu Aiuto e Supporto mostra
invece queste istruzioni.

### 💻 Desktop (Chrome / Edge)

1. Apri LibreFolio in Chrome o Edge.
2. Clicca **Installa App** nel menu **Aiuto e Supporto**, oppure l'icona di installazione (⊕) nella barra degli indirizzi.
3. LibreFolio si apre in una finestra propria.

---

## 🌐 HTTP vs HTTPS

| Indirizzo | Installa come app | Finestra di installazione da **Installa App** |
|---|---|---|
| `https://…` (Tailscale, reverse proxy) | ✅ | ✅ |
| `http://localhost` | ✅ | ✅ |
| `http://192.168.x.x` (LAN) | ❌ HTTPS richiesto | ❌ solo un suggerimento |

!!! warning "Requisito di connessione HTTPS per la PWA"

    I browser installano un'app solo da un indirizzo sicuro **HTTPS** — `localhost` e `127.0.0.1` sono
    le uniche eccezioni. Su HTTP semplice nella tua rete (ad esempio `http://192.168.1.100:6040`)
    LibreFolio funziona comunque nel browser, ma non può essere installato.

    Qualsiasi configurazione HTTPS va bene. L'opzione più semplice e gratuita è la nostra
    **[Guida all'esposizione con Tailscale](../admin/service_exposure.md)**: un indirizzo HTTPS sicuro senza
    certificati SSL da gestire né porte del router da aprire.

---

## 🔧 Risoluzione dei problemi

| Problema | Soluzione |
|---------|----------|
| **Installa App** non è nel menu | Sei già nell'app installata: la voce è nascosta in essa |
| **Installa App** mostra un suggerimento invece di installare | Il browser non ha proposto l'installazione: verifica di usare HTTPS (o `localhost`), o che l'app non sia già installata, poi segui il suggerimento |
| iOS: manca **Aggiungi a schermata Home** | Apri la pagina in **Safari** e guarda nel suo menu **Condividi** |
| L'app non si aggiorna | Chiudi e riapri l'app — carica sempre l'ultima versione dal tuo server |
| Disconnesso dopo un aggiornamento | Accedi di nuovo — un riavvio del server può terminare ogni sessione |

---

## 🔗 Correlati

- 🌐 **[Guida all'esposizione con Tailscale](../admin/service_exposure.md)** — Un indirizzo HTTPS gratuito per la tua istanza
- 🛠️ **[Ottimizzazioni PWA e mobile](../developer/frontend/pwa.md)** — Come è costruita la parte app (per sviluppatori)
