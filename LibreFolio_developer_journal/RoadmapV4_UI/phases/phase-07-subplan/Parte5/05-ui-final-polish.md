# Prompt per Agente: Final Polish UI & Svelte Fixes (Blocco 5)

## Contesto
Questo è il ciclo finale di rifinitura basato sul test dell'ultimo blocco. Alcune modifiche estetiche richiedono piccoli aggiustamenti di CSS (spaziature, flexbox), e il bug di reattività del broker persiste. 

## Task 1: Fix Reattività Broker (`ImportWizardModal.svelte`)
Il broker creato dalla modale continua a non apparire nella tendina dello Step 1 senza un refresh della pagina.
- **Analisi Esatta:** Nel file `ImportWizardModal.svelte`, il componente `<BrokerModal>` attualmente ascolta solo l'evento `onclose`. **Manca un listener `oncreated`**.
- **Azione:** Aggiungi `oncreated={(newBroker) => handleBrokerCreated(newBroker)}` al componente `BrokerModal` dentro `ImportWizardModal.svelte`. Assicurati che il metodo pushi il nuovo broker nello store o nell'array locale (es. `brokers = [...brokers, newBroker]`) per triggerare il render di Svelte 5 e imposti `selectedBrokerId = newBroker.id`.

## Task 2: Layout Asset Card (Step 3 & 4)
I badge degli identificatori (Ticker, ISIN) attualmente vanno a capo sotto il titolo.
- **Azione:** Devono stare sulla stessa linea del titolo se c'è spazio, e andare a capo solo se lo spazio finisce.
- **Fix CSS:** Il contenitore padre deve avere un layout flessibile orizzontale. Rivedi il markup in modo che Titolo e Badge condividano lo stesso `flex flex-wrap items-center gap-x-2` prima di forzare a capo. Assicurati che il titolo abbia `truncate` ma non occupi il 100% della riga forzando i badge giù.

## Task 3: Pulsante Preview in `ParseDetailModal` (Step 3)
Il pulsante "Preview" globale non è dove l'utente se lo aspetta.
- **Azione:** Sposta o aggiungi il pulsante "Preview File" nel **footer** della modale `ParseDetailModal`, allineato a sinistra. 
- **Markup di riferimento (footer):** Deve stare nella stessa div del pulsante "Chiudi" (che è a destra). 
  Esempio: `<div class="flex justify-between p-4 ..."> <button>Preview File</button> <button>Chiudi</button> </div>`

## Task 4: Spaziature Ricerca e Suggerimenti
La sezione "Cerca Online" in `AssetModal` è troppo schiacciata al centro.
- **Azione:** Rivedi le classi di utilità Tailwind. 
  - Rimuovi il `-mt-1` e `-mb-1` dal div dei "Suggerimenti".
  - Aggiungi un leggero margine inferiore (es. `mb-2`) sotto i suggerimenti per distanziarli dall'input di ricerca.
  - Riduci lo spazio eccessivo *sopra* la scritta "Cerca Online".

## Task 5: Tooltip "Prezzo riferito a N asset"
Il testo del tooltip è stato tagliato troppo nella scorsa iterazione, perdendo di significato.
- **Azione:** Ripristina nei file di traduzione (`i18n`) la frase esplicativa completa.
- **Testo esatto da usare in tutte le lingue (tradotto di conseguenza):** *"Specifica a quanti titoli o quote fa riferimento il prezzo di mercato. Per Etf o azioni è tipicamente 1, le obbligazioni tendenzialmente sono quotate su base 100."*

---

## Sessione di implementazione — Fix iterativi aggiuntivi

### Fix 1: Broker reactivity — root cause
**Problema:** il broker creato compariva nel DB ma non nel dropdown Step 1.
**Root cause:** `mergeBrokers({id, ...formData})` non include `user_role`; `getEditableBrokers()` filtra su `canEditWithRole(b.user_role)` → nuovo broker con `user_role: undefined` escluso.
**Fix:** import `refreshAllBrokers` da brokerStore; nel callback `oncreated`, sostituito `brokers = getEditableBrokers()` con `refreshAllBrokers().then(() => { brokers = getEditableBrokers(); })` → refetch completo con `user_role` corretto.

### Fix 2: FilePreviewModal z-index dinamico
**Problema:** la modale di anteprima file rimaneva sotto ParseDetailModal (z=80) e il warning modal (z=85).
**Fix:** aggiunto `previewZIndex = $state(untrack(() => zIndex + 20))`; `openPreview(fileId, callerZIndex?)` aggiorna dinamicamente `previewZIndex = callerZIndex + 20`. Call site nested passano il loro z-index (ParseDetailModal: 80, warning modal: 85). FilePreviewModal usa `{previewZIndex}` invece di un valore hardcoded.

### Fix 3: Pulsante Preview rimosso dall'header Step 3
**Problema:** con 1 file in analisi, compariva un pulsante "Preview File" nell'header della progress bar (indesiderato).
**Fix:** rimosso il blocco `{#if parseDone && parseResults.filter...}` dall'header. Il preview rimane solo come azione sulla riga della DataTable.

### Fix 4: Spaziatura sezione ricerca AssetModal
**Problema 1:** `space-y-5` del container body applicava `margin-top: 20px` sia al div titolo che al div badge (due figli separati).
**Fix 1:** wrappati titolo + badge in un unico `<div class="space-y-1.5">` → un solo figlio di `space-y-5`.

**Problema 2:** `mb-2` sul div badge aggiungeva 8px extra.
**Fix 2:** rimosso `mb-2`.

**Problema 3:** `{#key activeSearchQuery}<AssetSearchAutocomplete>` rimasto figlio diretto di `space-y-5` → 20px tra badge e input.
**Fix 3:** autocomplete spostato DENTRO il wrapper `space-y-1.5` (con `hideTitle={true}`). Aggiunto `{:else}` per il percorso senza badge (autocomplete normale con titolo integrato). Gap uniforme 6px tra titolo, badge e input.
