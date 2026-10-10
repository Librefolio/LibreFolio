# 📥 Transazioni del broker

La scheda **Transazioni** di un broker elenca tutte le sue transazioni, dalla più recente alla più vecchia. Mostra sempre l'intera cronologia del broker: l'intervallo di date nella barra degli strumenti non la filtra.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="transactions-tab" alt="Scheda Transazioni del broker">
</div>

Sopra l'elenco trovi **Report caricati**, **Visualizza in Transazioni** e il selettore di colonne. I proprietari e gli editor hanno anche **Importa** e **Aggiungi transazione**.

---

## ➕ Aggiungi una transazione

1. Fai clic su **Aggiungi transazione**. Il workspace delle transazioni si apre su un modulo **Nuova transazione**, con questo broker già selezionato.
2. Scegli il **Tipo** e compila i campi obbligatori — vedi [Modulo transazione](../transactions/form.md).
3. Fai clic su **Applica** per inserire la riga nel workspace, poi su **Salva tutto** per salvarla.

Nulla viene salvato prima di **Salva tutto**: fino ad allora puoi aggiungere altre righe, modificarle o annullare (vedi [Il workspace bulk](../transactions/index.md#bulk-workspace)).

---

## 🔎 Aprire, modificare o eliminare transazioni

- **Fai doppio clic** su una riga per aprirla in sola lettura.
- Per modificare, clonare o eliminare righe, fai clic su **Visualizza in Transazioni**: si apre la pagina [Transazioni](../transactions/index.md), filtrata su questo broker e sui filtri di colonna che hai impostato qui.

---

## 🧙 Importa un estratto conto

**Importa** apre il workspace insieme alla **Procedura guidata di importazione** (BRIM, il modulo di importazione dei report del broker). La procedura guidata legge i file esportati dal tuo broker, ti consente di controllare ogni riga e passa il risultato al workspace: nulla viene scritto fino a **Salva tutto**.

- 📥 **[Importazione da broker](../transactions/import/index.md)** — broker e formati supportati.
- 🧙 **[Come importare le transazioni](../transactions/import/how-to.md)** — la procedura guidata, passo dopo passo.

La stessa procedura guidata si apre dalla voce **Importa** nella pagina [Transazioni](../transactions/index.md).

??? tip "🧩 Il tuo broker non è ancora supportato — cosa puoi fare"

    - **Richiedi un plugin**: apri una [richiesta di plugin](https://github.com/Librefolio/LibreFolio/issues/new?template=plugin_request.yml) su GitHub e allega un campione anonimizzato dell'esportazione del broker.
    - **Scrivi un plugin**: la [Guida ai plugin BRIM](../../developer/architecture/patterns/brim_plugin_guide.md) spiega il contratto del plugin, e [Contribuisci](../../community/contribute.md) spiega il flusso di lavoro.
    - Se le righe importate continuano a sembrare errate, il passo **Correzioni** della procedura guidata rimanda a GitHub così puoi segnalare un possibile bug dell'importatore.

---

## 🗂️ Report caricati

**Report caricati** apre i file dei report memorizzati per questo broker:

- **Carica** file CSV o Excel: vengono assegnati a questo broker ed elencati nel passo **Seleziona file** della procedura guidata. I file che carichi insieme formano un unico set — è così che vengono importate le banche che dividono un conto su più esportazioni, come Danske Bank.
- **Anteprima** o **Elimina** un file. L'eliminazione di un report non elimina mai le transazioni importate da esso.
- Controlla i badge **Stato** e **Set di report** di ciascun file — vedi [Set di report](../files/index.md#report-sets).
- **Gestisci tutti i file** apre la pagina [File e caricamenti](../files/index.md#broker-reports), filtrata su questo broker.

Caricare ed eliminare report richiede l'accesso al broker come Proprietario o Editor.
