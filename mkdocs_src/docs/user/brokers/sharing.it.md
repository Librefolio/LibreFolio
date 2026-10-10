# 🤝 Condivisione del broker

Condividi un broker con le persone che ne hanno bisogno — un partner, un familiare, un consulente o un commercialista. Ogni persona riceve un **ruolo**, che decide cosa può fare, e ogni proprietario una **quota di proprietà**, che decide quanto del conto conta come suo.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="sharing-modal" alt="Modale di condivisione del broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## ➕ Condividi un broker

Apri il pannello di condivisione con il pulsante di condivisione sulla scheda del broker, oppure con **Condividi broker** nella barra degli strumenti del broker (apre la scheda **Info**). Solo un proprietario può modificarlo; tutti gli altri lo vedono in sola lettura.

1. Clicca su **+** (**Aggiungi utente**) e trova la persona **tramite nome utente**.
2. Scegli il **ruolo** e, per un proprietario, la **% di proprietà**. Poi clicca su **Aggiungi utente**.
3. Clicca su **Salva configurazione**. Nulla cambia prima di farlo: fino ad allora, **↺ Reimposta** riporta la lista a com'era.

??? note "✏️ Modifica o rimuovi qualcuno — e quando un salvataggio viene rifiutato"

    Clicca sul chip di una persona per cambiarne il **ruolo** o la **% di proprietà**, oppure clicca su **Rimuovi accesso**; clicca su **Conferma**, poi su **Salva configurazione**.

    Un salvataggio viene rifiutato se dovesse lasciare il broker **senza un proprietario** — quindi l'ultimo proprietario non può essere né rimosso né retrocesso — oppure se la somma delle quote supera **il 100%** (il pannello avvisa *La proprietà totale supera il 100%*).

    Modifiche non salvate: la finestra di dialogo aperta dalla lista dei broker chiede conferma prima di chiudersi, ma nella scheda **Info**, passando a un'altra scheda vengono perse.

---

## 🛡️ Cosa può fare ciascun ruolo

| Cosa puoi fare | visualizzatore | editor | proprietario |
|:--|:--:|:--:|:--:|
| Vedere il broker, le sue transazioni, i report e i grafici | ✅ | ✅ | ✅ |
| Aggiungere, modificare e importare transazioni; caricare ed eliminare file di report | ❌ | ✅ | ✅ |
| Modificare le impostazioni del broker | ❌ | ✅ | ✅ |
| Gestire chi ha accesso | ❌ | ❌ | ✅ |
| Eliminare il broker | ❌ | ❌ | ✅ |

- 👁️ **visualizzatore** — sola lettura, per un commercialista o parenti che devono solo consultare.
- ✏️ **editor** — svolge il lavoro quotidiano, ma non può condividere o eliminare il broker.
- 👑 **proprietario** — controllo completo; un broker può avere diversi proprietari.

---

## 📊 Quota di proprietà

Ogni proprietario ha una **quota** dallo 0% al 100%: la parte del conto che è sua. I visualizzatori e gli editor hanno sempre lo 0%. La somma delle quote può essere inferiore al 100% — per esempio quando un comproprietario non usa LibreFolio — ma mai superiore; il pannello mostra i totali **Assegnato** e **Disponibile** mentre modifichi.

La quota decide cosa conta nei tuoi numeri:

- La **Dashboard** conta solo i broker che **possiedi** con una quota superiore allo 0%, e proporziona i loro importi in base alla tua quota: con il 50%, vedi metà del valore, del reddito e del P&L del broker.
- La scheda **Rischio** della Dashboard copre gli stessi broker: quelli che possiedi con una quota superiore allo 0% (vedi [Scheda Rischio](../dashboard/index.md#risk-tab)).
- I broker in cui sei un visualizzatore o un editor, o che possiedi allo 0%, non sono nella tua Dashboard. La loro pagina li mostra: i visualizzatori e gli editor vedono gli importi **completi**, i proprietari la loro quota.

---

## 💡 Configurazioni comuni

| Chi | Configurazione | Cosa vede |
|:--|:--|:--|
| Coniuge o partner | Due proprietari, 50% ciascuno | Ognuno di voi vede metà del conto sulla propria Dashboard |
| Comproprietario senza un account LibreFolio | Tu come proprietario, 50% | La tua metà; l'altro 50% rimane non assegnato |
| Consulente finanziario o commercialista | visualizzatore | L'intero broker sulla sua pagina, nulla sulla sua Dashboard |
| Familiare che registra operazioni | editor | Aggiunge e importa transazioni, ma non può condividere o eliminare il broker |

---

## 🚪 Lasciare un broker o rinunciare al ruolo

Non serve mai un proprietario per lasciare il broker. Sotto **Il tuo accesso** nel pannello di condivisione, dopo una conferma:

- **Lascia il broker** rimuove immediatamente il tuo accesso, e il broker scompare dalle tue liste;
- **Passa a visualizzatore** (solo editor) rinuncia alla modifica; un proprietario può renderti di nuovo un editor.

!!! danger "Ultimo proprietario: lasciare elimina il broker"

    Se sei l'**unico proprietario** rimasto, il pulsante diventa **Lascia ed elimina il broker**: lasciare *elimina permanentemente il broker insieme a tutte le sue transazioni e ai file di report importati*. Questa operazione non può essere annullata. Per mantenere il broker, assegna prima a un altro utente il ruolo di proprietario, poi lascia.

L'eliminazione del tuo account segue la stessa regola — vedi [Profilo](../settings/profile.md).

Per ottenere accesso al broker di qualcun altro, chiedi a uno dei suoi proprietari. I broker che non puoi aprire sono elencati sotto **Altri broker esistenti** nella pagina [Broker](index.md), e il loro pulsante di condivisione mostra chi ha accesso. Ogni utente autenticato di questo LibreFolio può vedere chi ha accesso a qualsiasi broker, così le persone che condividono un'istanza possono trovarsi a vicenda.
