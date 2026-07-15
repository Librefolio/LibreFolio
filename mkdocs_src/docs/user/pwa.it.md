# 📱 Installa come App (PWA)

LibreFolio può essere installato come **Progressive Web App (PWA)** sul tuo dispositivo. Questo ti offre un'esperienza simile a un'app: modalità a schermo intero, nessuna barra degli indirizzi del browser e un'icona nella schermata home — senza dover scaricare nulla da un app store.

---

## ✅ Cosa Ottieni

| Funzionalità | Descrizione |
|---------|-------------|
| **Modalità a schermo intero** | Nessuna barra degli indirizzi o interfaccia del browser invadente |
| **Icona nella schermata home** | Avvia LibreFolio come un'app nativa |
| **Nessuna interferenza con i gesti** | Scorri-indietro e zoom con doppio tocco disabilitati |
| **Sessione persistente** | Rimane connesso tra un avvio e l'altro |

!!! note "Solo Online"

    LibreFolio PWA richiede una connessione di rete attiva. Non esiste una modalità offline — i tuoi dati risiedono sul tuo server.

---

## 📲 Come Installare

### Android (Chrome / Edge)

1. Apri LibreFolio in Chrome o Edge
2. Cerca il pulsante **"Install App"** nel menu **Help & Support** (icona ❓ in alto a destra)
3. Tocca **Install** quando richiesto
4. LibreFolio apparirà nella tua schermata home

!!! tip "Metodo alternativo"

    Se il pulsante Install non appare, tocca il menu **⋮ del browser → "Add to Home screen"** oppure **"Install app"**.

### iOS (Safari)

1. Apri LibreFolio in **Safari** (richiesto — gli altri browser non supportano PWA su iOS)
2. Tocca il pulsante **Share** (quadrato con freccia)
3. Scorri verso il basso e tocca **"Add to Home Screen"**
4. Tocca **Add**

!!! warning "Limitazione iOS"

    Il prompt di installazione automatica non è disponibile su iOS. Usa il menu Share come descritto sopra. Il menu Help mostrerà le istruzioni se sei su un dispositivo iOS.

### Desktop (Chrome / Edge)

1. Apri LibreFolio in Chrome o Edge
2. Clicca sul pulsante **"Install App"** nel menu Help & Support
3. Oppure clicca sull'icona di installazione (⊕) nella barra degli indirizzi del browser
4. LibreFolio si apre in una finestra dedicata

---

## 🌐 HTTP vs HTTPS

<table style="width: 100%; border-collapse: collapse; margin-top: 1rem; margin-bottom: 1rem;">
 <thead>
 <tr style="background-color: #f3f4f6;">
 <th style="width: 45%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">Configurazione</th>
 <th style="width: 25%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">Installazione PWA</th>
 <th style="width: 30%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">Prompt automatico</th>
 </tr>
 </thead>
 <tbody>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; white-space: nowrap;"><code>https://</code> (Tailscale, proxy inverso)</td>
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
 <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(244, 67, 54, 0.04);">❌ Non disponibile (richiede HTTPS)</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(244, 67, 54, 0.04);">❌ Nessun prompt automatico</td>
 </tr>
 </tbody>
</table>

!!! warning "Requisito di connessione HTTPS per PWA"

    Per installare LibreFolio come PWA, **i browser moderni richiedono strettamente una connessione HTTPS sicura** (tranne quando si accede tramite `localhost` o `127.0.0.1` per lo sviluppo locale).

    Se apri LibreFolio su HTTP semplice sulla tua rete locale (ad esempio, `http://192.168.1.100:6040`), l'installazione PWA non sarà disponibile e l'app non potrà funzionare in modalità autonoma.

    Puoi scegliere qualsiasi metodo preferisci per abilitare HTTPS sulla tua istanza, ma raccomandiamo vivamente la nostra semplice guida gratuita: **[Tailscale Exposure Guide](../admin/service_exposure.md)**. Ti fornisce un URL HTTPS sicuro senza configurare certificati SSL o aprire porte del router.

---

## 🔧 Risoluzione dei problemi

| Problema | Soluzione |
|---------|----------|
| Il pulsante Installa non appare | Potresti averlo già installato, oppure sei su HTTP in LAN |
| iOS: nessuna opzione di installazione | Devi usare **Safari** — Chrome/Firefox su iOS non supportano PWA |
| L'app non si aggiorna | Chiudi e riapri l'app — recupera sempre l'ultima versione |
| Sessione persa dopo l'aggiornamento | Accedi di nuovo — è normale dopo il riavvio del server |
