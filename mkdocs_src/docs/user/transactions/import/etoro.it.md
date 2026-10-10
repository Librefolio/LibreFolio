# 📥 <img src="https://www.etoro.com/favicon.ico" alt=""> eToro

!!! info "Beta"

    Questo plugin è in **Beta** — testato con file di esempio ma potrebbero esistere casi limite.

LibreFolio legge il foglio **Account Activity** dell'estratto conto di eToro, salvato come CSV.

## 📥 Come esportare

1. Accedi al tuo [account eToro](https://www.etoro.com).
2. Apri **Portafoglio**, poi **History** (l'icona dell'orologio).
3. Clicca l'icona delle impostazioni in alto a destra e scegli **Account Statement**.
4. Scegli le date di inizio e fine, poi clicca **Create**.
5. Scarica l'estratto conto con l'icona **XLS**.
6. Apri il file in un foglio di calcolo, vai al foglio **Account Activity** e salvalo come **CSV**,
   mantenendo i nomi delle colonne sulla prima riga. LibreFolio non legge file PDF o Excel.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: eToro Portfolio History - Account Statement creation and export] -->
</div>

## 🔄 Cosa viene importato

| Nel foglio Account Activity (**Type**) | Importato come |
|:-------------------------------|:------------|
| Open Position | **Acquisto** |
| Position closed | **Vendita** |
| Dividend | **Dividendo** |
| Interest Payment | **Interesse** |
| Deposit | **Deposito** |
| Withdraw Request | **Prelievo** |
| Withdraw Fee, Withdrawal Conversion Fee, Conversion Fee | **Commissione**, quando l'importo non è zero |

Lo strumento proviene da **Details** (ad esempio `NKE/USD`) e la quantità da **Units**.

**Non importati**: **Overnight fee** e **Overnight refund** (finanziamento CFD) e **SDRT** (imposta di bollo britannica) vengono saltati senza un avviso, quindi aggiungili manualmente se ne tieni traccia. Qualsiasi altro tipo viene saltato con un avviso.

## ⚠️ Insidie comuni

!!! warning "Controlla la valuta degli strumenti non quotati in USD"

    LibreFolio registra ogni riga nella valuta dopo la barra in **Details** (`KER/EUR` in euro),
    e ogni altra riga in dollari USA. eToro indica i suoi importi nella valuta del tuo account (solitamente
    USD): controlla le righe degli strumenti quotati in un'altra valuta prima di salvarle.

- **Mantieni le date di eToro**: giorno/mese/anno, con o senza l'ora. Una riga la cui data non può essere letta
  viene saltata con un avviso.
- **Commissioni di conversione per prelievo.** Una commissione diversa da zero diventa una **Commissione** separata, accanto al
  **Withdraw Request** completo. Confronta entrambi con il tuo estratto conto: se la commissione era già stata detratta dal
  denaro prelevato, deselezionala in [Riepilogo](how-to.md#review).
- I **CFD** diventano normali acquisti e vendite dello strumento, come azioni reali, senza le loro
  commissioni overnight: controlla quelle posizioni e i loro costi.

## 🔗 Riferimenti per sviluppatori

→ [Architettura BRIM — note su eToro](../../../developer/backend/brim/architecture.md#plugin-etoro)
