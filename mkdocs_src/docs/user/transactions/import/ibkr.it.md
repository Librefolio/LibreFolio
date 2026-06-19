# <img src="https://www.interactivebrokers.com/favicon.ico" alt=""> Interactive Brokers (IBKR)

!!! info "Beta"

    Questo plugin è in versione **Beta** — testato con file di esempio, ma potrebbero esserci casi limite.

## 📥 Come Esportare

Per esportare le tue transazioni da Interactive Brokers, segui questi passaggi:

1. Accedi al [Client Portal di Interactive Brokers](https://www.interactivebrokers.com).
2. Naviga su **Reports** nel menu superiore, quindi seleziona **Statements**.
3. Nella sezione **Activity**, clicca sulla scheda **Activity Statement**.
4. Seleziona il **Date Range** desiderato (es. Year to Date, Custom) e scegli **CSV** come formato.
5. Clicca su **Run** o scarica il report CSV generato sul tuo computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Interactive Brokers Portal - Statements & Reports menu] -->
</div>

### ⚙️ Utilizzo delle Flex Queries (Consigliato)

Per portafogli più avanzati, puoi configurare una **Flex Query** per esportare dati specifici:

1. Sotto **Reports**, vai su **Flex Queries** e clicca sul pulsante **+ (Create)**.
2. Seleziona **Activity Flex Query**.
3. Aggiungi **Trades**, **Cash Transactions** (per dividendi e commissioni) e **Corporate Actions** alla query.
4. Imposta il formato su **CSV** e salva la query. Puoi eseguire questa query personalizzata in qualsiasi momento.

## ⚠️ Errori Comuni

!!! warning "Formato File"

    Assicurati di esportare come file **CSV**. Gli estratti conto in PDF non sono supportati dal parser e il caricamento fallirà.

!!! warning "Impostazioni Lingua"

    Il parser è progettato per le intestazioni CSV in inglese. Assicurati che la lingua del Client Portal di IBKR sia impostata su inglese prima di eseguire l'esportazione.

## 📝 Note

- Supporta i report di attività standard di IBKR (transazioni, dividendi, ritenute fiscali, commissioni, depositi, prelievi).
- Sono supportati i conti multi-valuta.
- Le azioni societarie (frazionamenti, fusioni) potrebbero richiedere regolazioni manuali all'interno della griglia di staging.

## 🔗 Riferimenti per Sviluppatori

→ [IBKR Provider — Dettagli di Implementazione](../../../developer/backend/brim/providers_list.md)
