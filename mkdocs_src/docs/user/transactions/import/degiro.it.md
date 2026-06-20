# <img src="https://www.degiro.com/favicon.ico" alt=""> Degiro

!!! info "Beta"

    Questo plugin è in **Beta** — testato con file di esempio, ma potrebbero esserci casi limite.

## 📥 Come Esportare

Per esportare le tue transazioni da Degiro:

1. Accedi al [Portale Clienti Degiro](https://www.degiro.eu).
2. Vai su **Inbox** (o Account) nella barra laterale sinistra, quindi clicca su **Account Statement**.
3. Seleziona la **Data di inizio** e la **Data di fine** desiderate per coprire la cronologia delle transazioni.
4. Clicca sul pulsante **Export** e seleziona il formato **CSV**.
5. Salva il file sul tuo computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Degiro Portal - Inbox and Account Statement page] -->
</div>

## ⚠️ Criticità comuni

!!! warning "Report Separati"

    Degiro ha diverse opzioni di esportazione nel menu. Assicurati di scaricare l'**Account Statement** (che registra tutti i movimenti di cassa, acquisti, vendite e dividendi) piuttosto che la semplice lista "Transactions", che potrebbe omettere gli eventi di cassa.

!!! warning "Formati Linguistici"

    Il parser supporta diversi template locali di Degiro (Inglese, Olandese, Italiano, Tedesco, ecc.). Tuttavia, assicurati di non modificare manualmente le intestazioni delle colonne o i delimitatori CSV dopo l'esportazione.

## 📝 Note

- Supporta operazioni di acquisto/vendita, dividendi, commissioni di transazione, depositi e prelievi.
- Le conversioni valutarie effettuate da Degiro vengono elaborate automaticamente.

## 🔗 Riferimenti per Sviluppatori

→ [Degiro Provider — Dettagli di Implementazione](../../../developer/backend/brim/providers_list.md)
