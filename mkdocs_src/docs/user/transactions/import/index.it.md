# 📥 Importazione da Broker (BRIM)

**BRIM** (Broker Report Import Module) importa le tue transazioni dai file che il tuo broker ti permette di scaricare, così non devi digitarle. Per eseguire un'importazione, segui la **[Guida all'importazione](how-to.md)**.

---

## 🏦 Broker supportati

Scegli il tuo broker per vedere quale file esportare e a cosa fare attenzione. Gli importatori ancora in fase di maturazione hanno un'etichetta:

- 🔬 **Alpha** — nuovo: aspettati imperfezioni e controlla ogni riga;
- 🧪 **Beta** — testato con file di esempio: i casi insoliti potrebbero sfuggire.

Gli importatori senza etichetta sono ben testati e affidabili per i formati che supportano.

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="ibkr/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.interactivebrokers.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di IBKR">
            <span class="card-title" style="margin: 0;">Interactive Brokers</span>
        </div>
        <span class="card-desc">🧪 Beta · Report delle operazioni CSV da una Flex Query</span>
    </a>
    <a href="degiro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.degiro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Degiro">
            <span class="card-title" style="margin: 0;">Degiro</span>
        </div>
        <span class="card-desc">L'esportazione CSV dell'estratto conto</span>
    </a>
    <a href="etoro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.etoro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di eToro">
            <span class="card-title" style="margin: 0;">eToro</span>
        </div>
        <span class="card-desc">🧪 Beta · Estratto conto CSV</span>
    </a>
    <a href="directa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.directa.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Directa SIM">
            <span class="card-title" style="margin: 0;">Directa SIM</span>
        </div>
        <span class="card-desc">Cronologia delle transazioni, CSV o XLSX</span>
    </a>
    <a href="schwab/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.schwab.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Charles Schwab">
            <span class="card-title" style="margin: 0;">Charles Schwab</span>
        </div>
        <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV</span>
    </a>
    <a href="revolut/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Revolut">
            <span class="card-title" style="margin: 0;">Revolut</span>
        </div>
        <span class="card-desc">🧪 Beta · Estratto conto CSV</span>
    </a>
    <a href="coinbase/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.coinbase.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Coinbase">
            <span class="card-title" style="margin: 0;">Coinbase</span>
        </div>
        <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV (crypto)</span>
    </a>
    <a href="freetrade/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Freetrade">
            <span class="card-title" style="margin: 0;">Freetrade</span>
        </div>
        <span class="card-desc">🧪 Beta · Estratto conto delle transazioni CSV</span>
    </a>
    <a href="finpension/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.finpension.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Finpension">
            <span class="card-title" style="margin: 0;">Finpension</span>
        </div>
        <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV</span>
    </a>
    <a href="trading212/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.trading212.com/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Trading212">
            <span class="card-title" style="margin: 0;">Trading212</span>
        </div>
        <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV</span>
    </a>
    <a href="avanza/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://avanza.se/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Avanza">
    <span class="card-title" style="margin: 0;">Avanza</span>
    </div>
    <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV</span>
    </a>
    <a href="bux/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://bux.com/it/wp-content/themes/vo-theme/assets/images/favicon/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di BUX">
    <span class="card-title" style="margin: 0;">BUX</span>
    </div>
    <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV</span>
    </a>
    <a href="disnat/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://disnat.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Disnat">
    <span class="card-title" style="margin: 0;">Disnat</span>
    </div>
    <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV</span>
    </a>
    <a href="investengine/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.investengine.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di InvestEngine">
    <span class="card-title" style="margin: 0;">InvestEngine</span>
    </div>
    <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV</span>
    </a>
    <a href="rabobank/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.rabobank.com/static/msp/global-sites/rds/favicons/favicon-svg.svg" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Rabobank">
    <span class="card-title" style="margin: 0;">Rabobank</span>
    </div>
    <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV</span>
    </a>
    <a href="fineco/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://finecobank.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Fineco">
    <span class="card-title" style="margin: 0;">Fineco</span>
    </div>
    <span class="card-desc">🧪 Beta · L'esportazione CSV "Movimenti Dossier Titoli"</span>
    </a>
    <a href="intesa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.intesasanpaolo.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Intesa Sanpaolo">
    <span class="card-title" style="margin: 0;">Intesa Sanpaolo</span>
    </div>
    <span class="card-desc">🧪 Beta · Movimenti o snapshot del patrimonio, CSV o XLSX</span>
    </a>
    <a href="credit_agricole/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.credit-agricole.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Crédit Agricole">
    <span class="card-title" style="margin: 0;">Crédit Agricole</span>
    </div>
    <span class="card-desc">Movimenti del conto, CSV o XLSX, più un'esportazione opzionale dei titoli per la cronologia antecedente a 2 anni</span>
    </a>
    <a href="danske-bank/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://danskebank.fi/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Danske Bank">
    <span class="card-title" style="margin: 0;">Danske Bank</span>
    </div>
    <span class="card-desc">🔬 Alpha · Conto di risparmio azionario finlandese: il file XLSX dei titoli e il CSV della liquidità, caricati insieme come un unico set di report</span>
    </a>
    <a href="scalable/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="../../../../static/icons/brokers/scalable.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Scalable Capital">
    <span class="card-title" style="margin: 0;">Scalable Capital</span>
    </div>
    <span class="card-desc">Conto broker (il CSV di Scalable o l'esportatore LibreFolio) e conto deposito (esportatore), come due broker</span>
    </a>
    <a href="traderepublic/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://traderepublic.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Trade Republic">
    <span class="card-title" style="margin: 0;">Trade Republic</span>
    </div>
    <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV</span>
    </a>
    <a href="xtb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.xtb.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di XTB">
    <span class="card-title" style="margin: 0;">XTB</span>
    </div>
    <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV</span>
    </a>
    <a href="parqet/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://parqet.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Parqet">
    <span class="card-title" style="margin: 0;">Parqet</span>
    </div>
    <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV</span>
    </a>
    <a href="saxo/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://home.saxo/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Saxo">
    <span class="card-title" style="margin: 0;">Saxo</span>
    </div>
    <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV</span>
    </a>
    <a href="swissquote/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.swissquote.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Swissquote">
    <span class="card-title" style="margin: 0;">Swissquote</span>
    </div>
    <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV</span>
    </a>
    <a href="bitvavo/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://bitvavo.com/favicon-32x32.png?v=7ba51b544a17c10de8defa086df79917" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Bitvavo">
    <span class="card-title" style="margin: 0;">Bitvavo</span>
    </div>
    <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV (crypto)</span>
    </a>
    <a href="cryptocom/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://crypto.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Crypto.com">
    <span class="card-title" style="margin: 0;">Crypto.com</span>
    </div>
    <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV (crypto)</span>
    </a>
    <a href="relai/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://relai.app/app/uploads/2023/06/cropped-App-icon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Relai">
    <span class="card-title" style="margin: 0;">Relai</span>
    </div>
    <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV (crypto)</span>
    </a>
    <a href="cointracking/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://cointracking.info/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di CoinTracking">
    <span class="card-title" style="margin: 0;">CoinTracking</span>
    </div>
    <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV (crypto)</span>
    </a>
    <a href="delta/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.google.com/s2/favicons?domain=delta.app&amp;sz=64" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Delta">
    <span class="card-title" style="margin: 0;">Delta</span>
    </div>
    <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV (crypto)</span>
    </a>
    <a href="investimental/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon di Investimental">
    <span class="card-title" style="margin: 0;">Investimental</span>
    </div>
    <span class="card-desc">🧪 Beta · Cronologia delle transazioni CSV</span>
    </a>
    <a href="generic-csv/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" style="color: var(--md-accent-fg-color);"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg>
            <span class="card-title" style="margin: 0;">CSV generico</span>
        </div>
        <span class="card-desc">Il tuo CSV: colonne riconosciute dai nomi delle loro intestazioni</span>
    </a>
    <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
      <span class="card-title" style="margin: 0;">Richiedi nuovo plugin</span>
      </div>
      <span class="card-desc">Il tuo broker non c'è? Richiedi un nuovo plugin o contribuisci al codice!</span>
    </a>
</div>

!!! tip "Lettere accentate, il simbolo € e i punti e virgola"

    I file scritti dalle banche o risalvati con Excel su Windows vengono letti correttamente, comprese le lettere accentate, il simbolo € e le colonne separate da punti e virgola (LibreFolio comprende le codifiche UTF-8, Windows-1252 e Latin-1). Tuttavia, carica i tuoi file così come li hai scaricati quando puoi: alcune pagine broker, come [Danske Bank](danske-bank.md), lo richiedono espressamente.

---

## 🗂️ Mappatura degli asset {: #asset-mapping }

Ogni titolo nel tuo report deve essere associato a un asset della tua libreria. LibreFolio lo fa
da solo quando esattamente un asset è adatto; per gli altri scegli l'asset — o crealo, compilato
dal report — nel pannello **Risolvi Asset** del passaggio [Revisione](how-to.md#review). Fino
ad allora la riga mostra **✗ Non risolto** e l'importazione attende.

---

## ♻️ Rilevamento duplicati {: #duplicate-detection }

LibreFolio confronta ogni riga con le transazioni già salvate per lo stesso broker: stesso tipo,
data, quantità e importo, ignorando piccole differenze di arrotondamento.

- Se anche la descrizione corrisponde, la riga è un **⚠ Probabile dup** e arriva non spuntata.
- Se la descrizione differisce, è un **ℹ Possibile dup** e rimane spuntata per un tuo controllo.

Le copie tra i file che importi insieme sono gestite allo stesso modo, e il passaggio [Duplicati](how-to.md#only-when-needed) ti permette di scegliere quale copia mantenere. Puoi sempre spuntare o togliere la spunta a una riga da solo.

---

## ⛔ Prima della data di apertura del broker {: #before-opening }

Se un broker ha una **data di apertura**, le righe datate prima non possono essere importate; il giorno di apertura
stesso va bene. Se la data è sbagliata, correggila nel passaggio
[Revisione](how-to.md#opening-date) e le righe vengono ricontrollate. Qualunque sia la data di apertura,
le date delle transazioni vanno dal 1° gennaio 1900 a un anno da oggi: una riga con una data fuori da questo
intervallo è rifiutata quando salvi le righe importate, con un messaggio come *Data: Tra 1900-01-01 e
2027-10-17*, se oggi è il 17 ottobre 2026.

---

## 🔗 Correlati

- 🧙 **[Come importare](how-to.md)** — la procedura guidata di importazione, passo dopo passo
- 📋 **[Transazioni](../index.md)** — visualizza e gestisci le transazioni importate
- 🏦 **[Broker](../../brokers/index.md)** — configura prima i tuoi conti broker
- 🗂️ **[File](../../files/index.md)** — i report del broker che hai caricato
- 🛠️ **[Elenco provider BRIM](../../../developer/backend/brim/providers_list.md)** — note tecniche su ogni importatore, per sviluppatori
