# <img src="https://finecobank.com/favicon.ico" alt=""> Fineco

!!! info "Beta"

    Questo plugin è in **Beta** — testato con file di esempio, ma potrebbero esistere casi limite.

## 📥 Come esportare

LibreFolio importa il report **"Movimenti Dossier Titoli"** esportato da FinecoBank.

1. Accedi al tuo account **FinecoBank** (web o app).
2. Apri la sezione **Dossier Titoli** e seleziona l'account/periodo desiderato.
3. Esporta l'elenco dei movimenti. Fineco offre il report come file Excel.
4. Se il file è `.xls`/`.xlsx`, aprilo e **salvalo come CSV** prima di importarlo — il
 plugin legge il formato **CSV**.

## 📝 Note

- **Gli avvisi di importazione sono mostrati in italiano.** L'unica esportazione attualmente supportata è il report italiano
 di FinecoBank *Movimenti Dossier Titoli*, pertanto eventuali avvisi generati durante l'analisi compaiono in
 italiano per coerenza con il report. FinecoBank opera anche nel Regno Unito — se in futuro verrà aggiunto un formato di
 esportazione UK (o altro), i relativi avvisi seguiranno la lingua di quel formato.
- Sono supportati automaticamente due formati di esportazione:
 - **senza commissioni** (11 colonne), e
 - **con commissioni** (15 colonne). Le colonne delle commissioni vengono importate come transazioni
 **commissione** separate.
- Operazioni supportate: acquisti e vendite (*Compravendita titoli*), dividendi
 (*Dividendo*), cedole obbligazionarie (*Stacco Cedole*), rimborsi/scadenze (*Rimborso*),
 e aumenti di capitale (*Aumento capitale*, importati come **aggiustamento** di quantità
 senza movimento di cassa).
- **Obbligazione rimborsata sopra la pari** — quando una riga *Rimborso* riguarda un'obbligazione con prezzo
 **sopra la pari (100)**, l'importo accreditato sopra la pari (un *premio fedeltà* / rivalutazione inflazione) viene contabilizzato come una
 componente **interesse** separata e la **vendita** viene registrata al valore di rimborso 100.
 Ciò rispecchia il trattamento delle cedole (reddito di capitale) e mantiene la plusvalenza realizzata basata
 esclusivamente sul confronto prezzo-costo.
 Le obbligazioni rimborsate alla pari o sotto la pari, e i rimborsi azionari, vengono importati come un'unica vendita.
- **Gli importi sono importati letteralmente** nella valuta indicata da Fineco: la colonna *Divisa*
 di ciascuna riga determina la valuta degli importi di quella riga. Non viene eseguita
 alcuna conversione valutaria e la colonna *Cambio* (tasso di cambio) viene ignorata — i
 numeri arrivano in LibreFolio esattamente come appaiono nel report.
- La *Data valuta* viene utilizzata come data di regolamento della transazione.

## 🔗 Riferimenti per sviluppatori

→ [Provider BRIM — Dettagli implementativi](../../../developer/backend/brim/providers_list.md)
