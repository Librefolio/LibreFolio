# <img src="https://www.etoro.com/favicon.ico" alt=""> eToro

!!! info "Beta"

    Questo plugin è in **Beta** — testato con file di esempio, ma potrebbero esserci casi limite.

## 📥 Come Esportare

Per esportare la cronologia delle transazioni da eToro:

1. Accedi al tuo [account eToro](https://www.etoro.com).
2. Clicca su **Portafoglio** nella barra laterale sinistra, quindi clicca sull'icona dell'orologio per aprire **History**.
3. Clicca sull'icona dell'ingranaggio delle impostazioni in alto a destra e seleziona **Account Statement**.
4. Scegli la data di inizio e di fine per il tuo estratto conto, quindi clicca su **Create**.
5. Seleziona l'opzione di esportazione **Excel** o **CSV**. Salva il file sul tuo computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: eToro Portfolio History - Account Statement creation and export] -->
</div>

## ⚠️ Errori Comuni

!!! warning "Non Utilizzare Estratti PDF"

    eToro consente di scaricare gli estratti conto come PDF. I file PDF non possono essere elaborati dall'importatore BRIM. Assicurati di selezionare il formato foglio di calcolo (XLSX o CSV).

!!! warning "CFD vs Asset Reali"

    eToro supporta sia i CFD (contratti per differenza) che gli asset reali. Il parser importerà le transazioni CFD, ma poiché i CFD non rappresentano azioni sottostanti, la base di costo e la logica PMC potrebbero richiedere una validazione manuale nella griglia delle transazioni.

## 📝 Note

- Supporta operazioni su azioni, ETF, crypto e CFD, dividendi pagati, depositi, prelievi e aggiustamenti delle commissioni.
- Tutti i valori nei file esportati da eToro sono denominati in USD.

## 🔗 Riferimento per Sviluppatori

→ [eToro Provider — Dettagli di Implementazione](../../../developer/backend/brim/providers_list.md)
