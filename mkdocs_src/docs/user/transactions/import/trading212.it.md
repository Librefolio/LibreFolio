# <img src="https://www.trading212.com/favicon.ico" alt=""> Trading212

!!! info "Beta"

    Questo plugin è in versione **Beta** — testato con file di esempio, ma potrebbero esserci casi limite.

## 📥 Come Esportare

Per esportare il tuo estratto conto delle transazioni da Trading212:

1. Accedi al [Portale Clienti Trading212](https://www.trading212.com) (o apri l'app sul tuo dispositivo mobile).
2. Vai alla sezione menu/profilo e clicca su **History**.
3. Clicca sul pulsante **Export** (solitamente rappresentato da un'icona di esportazione o di documento nella parte superiore della scheda History).
4. Seleziona le colonne desiderate (assicurati che tutti i campi come ticker, data, quantità, prezzo e valuta siano selezionati).
5. Scegli **CSV** come formato e clicca su **Export**. Salva il file sul tuo computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Trading212 Portal - History and CSV Export modal] -->
</div>

## ⚠️ Insidie Comuni

!!! warning "Transazioni Pie"

    Trading212 supporta le "Pies" (panieri di asset gestiti automaticamente). Se effettui operazioni all'interno di una Pie, l'esportazione riporta queste operazioni come transazioni separate degli asset sottostanti. Il parser BRIM elabora automaticamente queste singole operazioni, ma assicurati che i saldi della tua Pie siano completamente sincronizzati nella griglia di staging prima di confermare.

## 📝 Note

- Supporta acquisti e vendite di azioni/ETF, dividendi, interesse sulla liquidità, depositi, prelievi e commissioni di conversione valutaria.
- Sono supportati gli account multi-valuta.

## 🔗 Riferimento per Sviluppatori

→ [Trading212 Provider — Dettagli di Implementazione](../../../developer/backend/brim/providers_list.md)
