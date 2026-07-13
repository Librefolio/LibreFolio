# 📱 Installa come App (PWA)

LibreFolio può essere installato come **Progressive Web App (PWA)** sul tuo dispositivo. Questo ti offre un'esperienza simile a quella di un'app: modalità a schermo intero, nessuna barra degli indirizzi del browser e un'icona nella schermata home — senza dover scaricare nulla da un app store.

---

## ✅ Cosa Ottieni

| Funzionalità | Descrizione |
|--------------|-------------|
| **Modalità a schermo intero** | Nessuna barra degli indirizzi o elementi dell'interfaccia del browser |
| **Icona nella schermata home** | Avvia LibreFolio come un'app nativa |
| **Nessuna interferenza dei gesti** | Swipe-back e zoom con doppio tocco disabilitati |
| **Sessione persistente** | Rimane collegato tra un avvio e l'altro |

!!! note "Solo Online"

    La PWA di LibreFolio richiede una connessione di rete attiva. Non esiste una modalità offline — i tuoi dati risiedono sul tuo server.

---

## 📲 Come Installare

### Android (Chrome / Edge)

1. Apri LibreFolio in Chrome o Edge
2. Cerca il pulsante **"Installa App"** nel menu **Help & Support** (icona ❓ in alto a destra)
3. Tocca **Installa** quando richiesto
4. LibreFolio apparirà nella tua schermata home

!!! tip "Metodo alternativo"

    Se il pulsante Installa non appare, tocca il **menu ⋮ del browser → "Aggiungi a schermata Home"** o **"Installa app"**.

### iOS (Safari)

1. Apri LibreFolio in **Safari** (richiesto — gli altri browser non supportano la PWA su iOS)
2. Tocca il pulsante **Condividi** (quadrato con freccia)
3. Scorri verso il basso e tocca **"Aggiungi alla schermata Home"**
4. Tocca **Aggiungi**

!!! warning "Limitazione iOS"

    Il prompt di installazione automatica non è disponibile su iOS. Usa il menu Condividi come descritto sopra. Il menu Help & Support mostrerà le istruzioni se ti trovi su un dispositivo iOS.

### Desktop (Chrome / Edge)

1. Apri LibreFolio in Chrome o Edge
2. Clicca sul pulsante **"Installa App"** nel menu Help & Support
3. Oppure clicca sull'icona di installazione (⊕) nella barra degli indirizzi del browser
4. LibreFolio si aprirà in una finestra dedicata

---

## 🌐 HTTP vs HTTPS

<table style="width: 100%; border-collapse: collapse; margin-top: 1rem; margin-bottom: 1rem;">
 <thead>
 <tr style="background-color: #f3f4f6;">
 <th style="width: 45%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">Configurazione</th>
 <th style="width: 25%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">Installazione PWA</th>
 <th style="width: 30%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">Auto-prompt</th>
 </tr>
 </thead>
 <tbody style="padding: 10px; border: 1px solid #e5e7eb;">
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; white-space: nowrap;"><code>https://</code> (Tailscale, reverse proxy)</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Supporto completo</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Chrome mostra il banner</td>
 </tr>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; white-space: nowrap;"><code>http://localhost</code></td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Funziona</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Funziona</td>
 </tr>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; white-space: nowrap; background-color: rgba(244, 67, 54, 0.04);"><code>http://192.168.x.x</code> (LAN)</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(244, 67, 54, 0.04);">❌ Non disponibile (richiesto HTTPS)</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(244, 67, 54, 0.04);">❌ Nessun auto-prompt</td>
 </tr>
 </tbody>
</table>

!!! warning "Requisito di connessione HTTPS per PWA"

    Per installare LibreFolio come PWA, **i browser moderni richiedono rigorosamente una connessione sicura HTTPS** (eccetto quando si accede tramite `localhost` o `127.0.0.1` per lo sviluppo locale).

    Se apri LibreFolio tramite semplice HTTP sulla tua rete locale (per esempio, `http://192.168.1.100:6040`), l'installazione della PWA non sarà disponibile e l'app non potrà essere eseguita in modalità standalone.

    Puoi scegliere qualsiasi metodo preferisci per abilitare HTTPS sulla tua istanza, ma consigliamo vivamente la nostra guida semplice e gratuita: **[Guida all'esposizione di Tailscale](../admin/tailscale_exposure.md)**. Ti fornisce un URL HTTPS sicuro senza dover configurare certificati SSL o aprire porte del router.

---

## 🔧 Risoluzione dei Problemi

| Problema | Soluzione |
|----------|-----------|
| Il pulsante di installazione non viene visualizzato | Potresti aver già installato l'app, oppure sei su una rete LAN HTTP |
| iOS: nessuna opzione di installazione | Devi usare **Safari** — Chrome/Firefox su iOS non supportano la PWA |
| L'app non si aggiorna | Chiudi e riapri l'app — scarica sempre l'ultima versione |
| Sessione persa dopo l'aggiornamento | Effettua nuovamente il login — è normale dopo il riavvio del server |
