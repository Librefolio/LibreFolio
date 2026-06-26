# <img src="https://www.finpension.ch/favicon.ico" alt=""> Finpension

!!! info "Beta"

    Questo plugin è in fase **Beta** — testato con file di esempio, ma potrebbero esserci dei casi limite.

## 📥 Come Esportare

Per esportare le tue transazioni da Finpension:

1. Accedi al tuo [account Finpension](https://app.finpension.ch).
2. Vai alla dashboard del tuo portafoglio/conto attivo.
3. Clicca sulla scheda **Transactions** (Transazioni / Transaktionen).
4. Clicca sul pulsante **Export** o di download e seleziona **CSV**.
5. Salva il file sul tuo computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Finpension Portal - Transactions page and Export button] -->
</div>

## ⚠️ Errori Comuni

!!! warning "Non Modificare i Delimitatori"

    Le esportazioni di Finpension utilizzano il punto e virgola `;` come separatore di colonna e formati tedeschi/svizzeri. Il parser BRIM rileva automaticamente queste impostazioni locali. Evita di aprire il file in editor di fogli di calcolo (come Excel) e di salvarlo nuovamente, poiché ciò potrebbe modificare la struttura grezza del CSV.

## 📝 Note

- Piattaforma pensionistica svizzera.
- Supporta depositi di contanti, acquisti, vendite, ritenute fiscali e commissioni di gestione.
- Denominato in CHF.
