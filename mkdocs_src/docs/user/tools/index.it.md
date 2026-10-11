---
title: Strumenti
description: Che cos'è uno Strumento, quali strumenti sono disponibili oggi e come aprirne uno.
---

# 🧰 Strumenti

Uno **Strumento** è un calcolo a sé stante: fornisci i dati per una singola operazione ed esso restituisce un risultato o un errore strutturato. Non è un'istruzione per modificare il tuo portafoglio.

La piattaforma degli Strumenti è **sperimentale**. Il catalogo attualmente offre esattamente
**uno** strumento:

| Strumento | Cosa fa |
|---|---|
| [allocatore PAC](pac-allocator/index.md) | Pianifica quali acquisti portano un'allocazione il più vicino possibile al suo obiettivo, usando la liquidità e i contributi disponibili al momento. |

La sua scheda apre un pianificatore guidato. La sua pagina dedicata spiega come usarlo e cosa
fa il motore di calcolo che vi sta dietro.

!!! note "Un secondo strumento è stato rimosso"

    Il catalogo offriva in precedenza un Ribilanciatore di portafoglio accanto
    all'allocatore PAC. Entrambi erano prototipi ed entrambi sono stati rimossi.
    Finora è stato ricostruito solo l'allocatore PAC, quindi un segnalibro alla
    pagina di documentazione del Ribilanciatore non si risolve più.

## 🖱️ Aprire uno strumento

Apri **Strumenti** dalla barra laterale per vedere il catalogo come una griglia di schede. Per uno strumento pronto, l'**intera scheda** è cliccabile, non solo il suo titolo o un'icona; un indicatore a freccia lo segnala come apribile. Uno strumento la cui interfaccia è assente non presenta nessuno dei due, e sulla scheda indica invece la propria situazione.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="hub" alt="Catalogo Strumenti con la scheda dell'allocatore PAC, la sua coppia di versioni e le azioni Documentazione e Ricarica">
</div>

Sia il catalogo sia uno strumento aperto mostrano:

- un'azione **Documentazione** che rimanda alla pagina di quello strumento, con un'etichetta che compare accanto all'icona su schermi più larghi e si riduce a un controllo con sola icona su schermi stretti;
- un'azione **Ricarica** che ricarica il catalogo (dall'hub) o l'interfaccia dello strumento corrente (da uno strumento aperto), con lo stesso comportamento responsive di sola icona; ricaricare uno strumento aperto chiede prima conferma (**Ricaricare lo strumento?**), perché sostituisce l'interfaccia e scarta la sua bozza corrente;
- la coppia di compatibilità dello strumento, `Backend/API <contract_version> · UI <ui.version>`, senza alcun numero separato di build o implementazione mostrato accanto.

Quando alcune voci del catalogo o alcune interfacce non sono disponibili, l'hub dice quante sono e rimanda a **Impostazioni → Informazioni → Diagnostica plugin**.

## ℹ️ Da sapere

- **Uno strumento non modifica mai il tuo portafoglio.** Non registra transazioni, non effettua ordini e
  non salva nulla nel tuo portafoglio: agire in base al suo risultato spetta a te.
- **Server occupato o limite di tempo raggiunto?** Non ottieni alcun risultato, e questo non dice nulla sui
  tuoi dati: attendi un momento, poi riprova.
- **Uno strumento manca o non può essere aperto?** Controlla in **Impostazioni → Informazioni → Diagnostica plugin**:
  il suo pannello **Strumenti** dice, strumento per strumento, se è disponibile e, in caso contrario, perché. Vedi
  [Informazioni](../settings/about.md).
