# 📥 <img src="https://www.etoro.com/favicon.ico" alt=""> eToro

!!! info "Beta"

    Questo plugin è in **Beta** — testato con file di esempio, ma potrebbero esistere casi limite.

LibreFolio legge il foglio **Account Activity** dell'estratto conto di eToro, salvato come CSV.

## 📥 Come esportare

1. Accedi al tuo [account eToro](https://www.etoro.com).
2. Apri **Portafoglio**, poi **Cronologia** (l'icona dell'orologio).
3. Clicca sull'icona delle impostazioni in alto a destra e scegli **Estratto conto**.
4. Scegli le date di inizio e fine, poi clicca su **Crea**.
5. Scarica l'estratto conto con l'icona **XLS**.
6. Apri il file in un foglio di calcolo, vai al foglio **Account Activity** e salvalo come **CSV**,
   mantenendo i nomi delle colonne sulla prima riga. LibreFolio non legge file PDF o Excel.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: eToro Portfolio History - Account Statement creation and export] -->
</div>

## 🔄 Cosa viene importato

| In Account Activity (**Type**) | Importato come |
|:-------------------------------|:------------|
| Open Position | **Acquisto** |
| Position closed | **Vendita** |
| Dividend | **Dividendo** |
| Interest Payment | **Interesse** |
| Deposit | **Deposito** |
| Withdraw Request | **Prelievo** |
| Withdraw Fee, Withdrawal Conversion Fee, Conversion Fee | **Commissione**, quando l'importo non è zero |
| Overnight fee (CFD financing) | **Commissione**, quando l'importo non è zero: un costo del denaro, senza asset |
| Overnight refund (CFD financing given back) | **Interesse**: denaro restituito (importo positivo), senza asset e con la descrizione *Overnight refund* |
| SDRT (UK stamp duty) | **Imposta**, sullo strumento della riga |

Lo strumento proviene da **Details** (ad esempio `NKE/USD`) e la quantità da **Units**.

Qualsiasi altro tipo viene saltato con un avviso.

## ⚠️ Insidie comuni

!!! warning "Controlla la valuta degli strumenti non quotati in USD"

    LibreFolio registra ogni riga nella valuta che segue la barra in **Details** (`KER/EUR` in euro),
    e ogni altra riga in dollari statunitensi. eToro indica i suoi importi nella valuta del tuo conto
    (di solito USD): controlla le righe degli strumenti quotati in un'altra valuta prima di salvarle.

- **Mantieni le date di eToro**: giorno/mese/anno, con o senza l'ora. Una riga la cui data non è
  leggibile viene saltata con un avviso.
- **Commissioni di conversione dei prelievi.** Una commissione non nulla diventa una **Commissione**
  separata, accanto alla **Withdraw Request** completa. Confronta entrambe con il tuo estratto conto:
  se la commissione era già stata detratta dal denaro prelevato, deselezionala in [Review](how-to.md#review).
- **I CFD** diventano normali acquisti e vendite dello strumento, come vere azioni. Le loro
  **commissioni overnight** vengono importate come transazioni separate di tipo **Commissione**, senza asset:
  controlla quelle posizioni e i relativi costi rispetto al tuo estratto conto.
- **Commissioni e rimborsi overnight.** Le commissioni vengono importate come **Commissione** e i rimborsi
  come **Interesse**: il costo overnight che hai effettivamente pagato, al netto dei rimborsi, è dato
  dalle commissioni meno i rimborsi. Un rimborso compare come entrata, quindi un report delle tue
  entrate lo include.

## 🚧 Limitazioni note {: #known-limitations }

- **Importi nella valuta del tuo conto.** Vedi l'avviso sopra: controlla la valuta degli strumenti
  non quotati in USD prima di salvarli.
- **Qualcosa non torna?** Per favore [apri una issue](https://github.com/Librefolio/LibreFolio/issues)
  con un file di esempio anonimizzato.

## 🔗 Riferimenti per gli sviluppatori

→ [Architettura BRIM — note su eToro](../../../developer/backend/brim/architecture.md#plugin-etoro)
