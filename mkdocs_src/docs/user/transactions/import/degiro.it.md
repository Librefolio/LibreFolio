# 📥 <img src="https://www.degiro.com/favicon.ico" alt=""> Degiro

LibreFolio importa l'**Estratto conto** di DEGIRO: il CSV che registra ogni movimento del tuo conto — operazioni, commissioni, dividendi, interessi, depositi, prelievi e conversioni di valuta — in qualsiasi lingua DEGIRO offra.

## 📥 Come esportare

1. Accedi al [Portale Clienti Degiro](https://www.degiro.eu).
2. Apri **Posta in arrivo** nella barra laterale sinistra, poi **Estratto conto**.
3. Scegli la **Data di inizio** e la **Data di fine**: dal tuo primo deposito a oggi per la cronologia completa.
4. Clicca **Esporta**, scegli **CSV** e salva il file (di solito `Account.csv`).

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: Degiro Portal - Inbox and Account Statement page] -->
</div>

## ⚠️ Errori comuni

!!! warning "Estratto conto, non Transazioni"

    L'esportazione **Transazioni** di DEGIRO elenca solo i tuoi ordini: nessun dividendo, deposito, prelievo o conversione di valuta. Se la carichi, LibreFolio la riconosce, non importa nulla e ti chiede l'Estratto conto.

- **Mantieni il file così come esportato.** Qualsiasi lingua va bene, purché tu non aggiunga, rimuova o riordini colonne, né modifichi le date giorno-mese-anno di DEGIRO.
- **Avvisi nella lingua del file.** Gli avvisi di importazione sono nella lingua dell'estratto conto, qualunque lingua usi LibreFolio: inglese, olandese, tedesco, francese o spagnolo, e inglese per qualsiasi altra.

## 🔄 Cosa viene importato

| Nell'estratto conto | Importato come |
|:-----------------|:------------|
| Acquisti e vendite, come `Buy 5 APPLE INC@180,25 USD`, in qualsiasi lingua | **Acquisto** o **Vendita**: il segno dell'importo indica la direzione, la descrizione indica la quantità |
| Commissioni sull'ordine (`DEGIRO Transaction and/or third party fees`) e commissioni di connessione al mercato | **Commissione** |
| Imposta di bollo e imposte sulle transazioni finanziarie su un ordine | **Imposta** |
| Dividendi e la relativa ritenuta fiscale (`Dividend`, `Dividend Tax`) | **Dividendo** e **Imposta**, ciascuno nella propria valuta |
| Depositi e prelievi | **Deposito** e **Prelievo** |
| Interesse (`Flatex Interest Income`) | **Interesse**; l'interesse a tuo carico diventa una **Commissione** |
| Crediti promozionali e di cortesia (`DEGIRO courtesy`) | **Interesse**, mantenendo la descrizione di DEGIRO |
| Conversioni di valuta (`FX Debit` e `FX Credit`) | Una coppia collegata di **conversioni FX** (vedi sotto) |

Gli importi vengono importati così come DEGIRO li riporta, ciascuno nella valuta della propria riga.

### 💱 Conversioni di valuta

DEGIRO registra una conversione come due righe: il denaro che esce da una valuta e il denaro che arriva nell'altra. LibreFolio le importa come un'unica coppia collegata: nel [Riepilogo](how-to.md#review) della procedura guidata è una singola riga che mostra **Da**, **A** e il tasso di cambio che i due importi implicano, selezionata e importata per intero. Conta come due transazioni in **Importa N transazioni**. Il costo AutoFX di DEGIRO è già incluso nell'importo addebitato, quindi non viene aggiunta alcuna commissione separata.

## 🚫 Cosa non viene importato

Ogni tipo elencato di seguito viene segnalato in un avviso durante l'importazione, con le sue righe originali, così puoi verificarle:

- **Operazioni societarie** (cambi di prodotto o ISIN, split, fusioni, dividendi in azioni e i relativi regolamenti in contanti), righe di **fondi monetari** e **rimborsi di capitale**: LibreFolio non li importa automaticamente — controlla le posizioni che interessano.
- **Righe di prelievo flatex** (`flatex Withdrawal`): LibreFolio non può stabilire se il denaro ha davvero lasciato il tuo conto. Se è successo, aggiungi il prelievo manualmente.
- **Righe di conversione di valuta senza una controparte**: l'altra gamba manca dal file o non può essere identificata.
- **Righe con un segno inatteso** per il loro tipo, come un dividendo negativo.
- **Operazioni la cui quantità non può essere letta** dalla descrizione.
- **Righe non riconosciute**: qualsiasi altra cosa che LibreFolio non è riuscito a classificare.

Ignorate senza un avviso: le righe informative senza importo, le registrazioni interne di DEGIRO (spostamenti di liquidità, giroconti da o verso flatexDEGIRO Bank, prenotazioni) e le righe con importo zero che non indicano alcun prodotto, come un interesse pari a zero.

## 🔗 Riferimento per sviluppatori

→ [Architettura BRIM — note su DEGIRO](../../../developer/backend/brim/architecture.md#plugin-degiro)
