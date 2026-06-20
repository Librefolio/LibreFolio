# <img src="https://www.coinbase.com/favicon.ico" alt=""> Coinbase

!!! info "Beta"

    Questo plugin è in **Beta** — testato con file di esempio, ma potrebbero esserci casi limite.

## 📥 Come Esportare

Per esportare l'estratto conto delle tue transazioni da Coinbase:

1. Accedi al tuo [account Coinbase](https://www.coinbase.com).
2. Clicca sulla tua immagine del profilo nell'angolo in alto a destra, quindi seleziona **Taxes** o **Statements**.
3. Nella sezione **Reports**, individua **Transaction History**.
4. Clicca su **Generate Report**, seleziona **CSV** come tipo di file e scegli l'intervallo di date desiderato.
5. Una volta che il report è pronto, scarica il file CSV sul tuo computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Coinbase Taxes/Reports - Generate Transaction History CSV report] -->
</div>

## ⚠️ Errori Comuni

!!! warning "Tipo di Report Errato"

    Assicurati di scaricare il report **Transaction History**. Altri report (come Tax Statements, Balance Summaries o report specifici dell'Asset Ledger) hanno una struttura diversa e non verranno analizzati correttamente.

!!! warning "Conversioni USD/EUR"

    Il parser di Coinbase elabora operazioni di trading di criptovalute, acquisti, vendite e commissioni. Assicurati che la valuta di visualizzazione del tuo account coincida con la valuta principale del tuo portafoglio LibreFolio per evitare discrepanze FX.

## 📝 Note

- Supporta acquisti, vendite, conversioni, invii, ricezioni, premi di staking e l'addebito delle commissioni.
- Supporta le principali valute fiat di base (USD, EUR, GBP).

## 🔗 Riferimenti per Sviluppatori

→ [Coinbase Provider — Dettagli di Implementazione](../../../developer/backend/brim/providers_list.md)
