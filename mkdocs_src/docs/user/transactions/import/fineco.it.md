# 📥 <img src="https://finecobank.com/favicon.ico" alt=""> Fineco

!!! info "Beta"

    Questo plugin è in **Beta** — testato con file di esempio ma potrebbero esistere casi limite.

LibreFolio importa il report **Movimenti Dossier Titoli** di FinecoBank — i movimenti del tuo
dossier titoli — salvato come CSV.

## 📥 Come esportare

1. Accedi al tuo conto **FinecoBank** (web o app).
2. Apri i movimenti del **Dossier Titoli** e scegli il conto e il periodo desiderati.
3. Esporta l'elenco: Fineco ti fornisce un file Excel.
4. Aprilo e **salvalo come CSV**. Mantieni le righe sopra la tabella (**Dossier:**,
   **Intestatario:**) e i nomi delle colonne: LibreFolio riconosce il report da questi.

## 🔄 Cosa viene importato

| Nel report (**Descrizione**) | Importato come |
|:--------------------------------|:------------|
| *Compravendita titoli*, con **Segno** `A` o `V` | **Acquisto** o **Vendita** |
| *Dividendo* | **Dividendo** |
| *Stacco Cedole* | **Interesse** (cedola obbligazionaria) |
| *Rimborso* | **Vendita** (rimborso o scadenza) |
| *Aumento capitale* | **Rettifica** della quantità, senza movimenti di cassa |
| Colonne delle commissioni, quando il report le contiene | Una **Commissione** separata per riga, in euro |

Qualsiasi altra operazione viene saltata con un avviso.

**Obbligazioni rimborsate sopra la pari.** Quando un'obbligazione viene rimborsata sopra la pari (100) — un *premio fedeltà* o una
rivalutazione inflazionistica — la vendita viene registrata alla pari e l'importo eccedente come un
**Interesse** separato, come una cedola, così il tuo guadagno riflette solo il prezzo. LibreFolio riconosce le obbligazioni dal
loro nome (BTP, BOT, CCT…). Le obbligazioni rimborsate alla pari o sotto la pari, e gli altri rimborsi, restano un'unica
**Vendita**.

## ⚠️ Buono a sapersi

- **Entrambi i layout funzionano**, con o senza le colonne delle commissioni: LibreFolio li distingue da
  sé.
- **Importi così come scritti.** Ogni riga mantiene la propria valuta (**Divisa**), senza conversione; la
  colonna **Cambio** viene ignorata.
- **Date.** LibreFolio usa la data valuta (**Data valuta**), o la data di negoziazione quando questa manca.

## 🔗 Riferimenti per sviluppatori

→ [Architettura BRIM — note su Fineco](../../../developer/backend/brim/architecture.md#plugin-fineco)
