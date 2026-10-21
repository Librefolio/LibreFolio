# 📥 Importer depuis un courtier (BRIM)

**BRIM** (Broker Report Import Module) importe vos transactions depuis les fichiers que votre courtier vous permet de télécharger, afin que vous n'ayez pas à les saisir. Pour lancer un import, suivez le **[guide Comment importer](how-to.md)**.

---

## 🏦 Courtiers pris en charge

Choisissez votre courtier pour voir quel fichier exporter et à quoi faire attention. Les importateurs encore en cours de maturation portent une étiquette :

- 🔬 **Alpha** — nouveau : attendez-vous à des imperfections et vérifiez chaque ligne ;
- 🧪 **Bêta** — testé avec des fichiers d'exemple : des cas inhabituels peuvent ne pas être détectés.

Les importateurs sans étiquette sont bien testés et fiables pour les formats qu'ils prennent en charge.

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="ibkr/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.interactivebrokers.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon d'IBKR">
            <span class="card-title" style="margin: 0;">Interactive Brokers</span>
        </div>
        <span class="card-desc">🧪 Bêta · Rapport de transactions au format CSV depuis une Flex Query</span>
    </a>
    <a href="degiro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.degiro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Degiro">
            <span class="card-title" style="margin: 0;">Degiro</span>
        </div>
        <span class="card-desc">L'export du relevé de compte au format CSV</span>
    </a>
    <a href="etoro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.etoro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon d'eToro">
            <span class="card-title" style="margin: 0;">eToro</span>
        </div>
        <span class="card-desc">🧪 Bêta · Relevé de compte au format CSV</span>
    </a>
    <a href="directa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.directa.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Directa SIM">
            <span class="card-title" style="margin: 0;">Directa SIM</span>
        </div>
        <span class="card-desc">Historique des transactions, aux formats CSV ou XLSX</span>
    </a>
    <a href="schwab/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.schwab.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Charles Schwab">
            <span class="card-title" style="margin: 0;">Charles Schwab</span>
        </div>
        <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV</span>
    </a>
    <a href="revolut/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Revolut">
            <span class="card-title" style="margin: 0;">Revolut</span>
        </div>
        <span class="card-desc">🧪 Bêta · Relevé de compte au format CSV</span>
    </a>
    <a href="coinbase/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.coinbase.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Coinbase">
            <span class="card-title" style="margin: 0;">Coinbase</span>
        </div>
        <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV (crypto)</span>
    </a>
    <a href="freetrade/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Freetrade">
            <span class="card-title" style="margin: 0;">Freetrade</span>
        </div>
        <span class="card-desc">🧪 Bêta · Relevé de transactions au format CSV</span>
    </a>
    <a href="finpension/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.finpension.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Finpension">
            <span class="card-title" style="margin: 0;">Finpension</span>
        </div>
        <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV</span>
    </a>
    <a href="trading212/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.trading212.com/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Trading212">
            <span class="card-title" style="margin: 0;">Trading212</span>
        </div>
        <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV</span>
    </a>
    <a href="avanza/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://avanza.se/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon d'Avanza">
    <span class="card-title" style="margin: 0;">Avanza</span>
    </div>
    <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV</span>
    </a>
    <a href="bux/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://bux.com/it/wp-content/themes/vo-theme/assets/images/favicon/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de BUX">
    <span class="card-title" style="margin: 0;">BUX</span>
    </div>
    <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV</span>
    </a>
    <a href="disnat/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://disnat.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Disnat">
    <span class="card-title" style="margin: 0;">Disnat</span>
    </div>
    <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV</span>
    </a>
    <a href="investengine/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.investengine.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon d'InvestEngine">
    <span class="card-title" style="margin: 0;">InvestEngine</span>
    </div>
    <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV</span>
    </a>
    <a href="rabobank/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.rabobank.com/static/msp/global-sites/rds/favicons/favicon-svg.svg" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Rabobank">
    <span class="card-title" style="margin: 0;">Rabobank</span>
    </div>
    <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV</span>
    </a>
    <a href="fineco/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://finecobank.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Fineco">
    <span class="card-title" style="margin: 0;">Fineco</span>
    </div>
    <span class="card-desc">🧪 Bêta · L'export au format CSV « Movimenti Dossier Titoli »</span>
    </a>
    <a href="intesa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.intesasanpaolo.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon d'Intesa Sanpaolo">
    <span class="card-title" style="margin: 0;">Intesa Sanpaolo</span>
    </div>
    <span class="card-desc">🧪 Bêta · Mouvements ou instantané “patrimonio”, au format CSV ou XLSX</span>
    </a>
    <a href="credit_agricole/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.credit-agricole.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon du Crédit Agricole">
    <span class="card-title" style="margin: 0;">Crédit Agricole</span>
    </div>
    <span class="card-desc">Mouvements du compte, au format CSV ou XLSX, plus un export facultatif des titres pour l'historique de plus de 2 ans</span>
    </a>
    <a href="danske-bank/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://danskebank.fi/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Danske Bank">
    <span class="card-title" style="margin: 0;">Danske Bank</span>
    </div>
    <span class="card-desc">🔬 Alpha · Compte d'épargne actions finlandais : le XLSX des titres et le CSV des liquidités, téléversés ensemble comme un seul lot de rapports</span>
    </a>
    <a href="scalable/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="../../../../static/icons/brokers/scalable.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Scalable Capital">
    <span class="card-title" style="margin: 0;">Scalable Capital</span>
    </div>
    <span class="card-desc">Compte-titres (le CSV de Scalable ou l'exportateur LibreFolio) et compte rémunéré (exportateur), comme deux courtiers distincts</span>
    </a>
    <a href="traderepublic/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://traderepublic.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Trade Republic">
    <span class="card-title" style="margin: 0;">Trade Republic</span>
    </div>
    <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV</span>
    </a>
    <a href="xtb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.xtb.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de XTB">
    <span class="card-title" style="margin: 0;">XTB</span>
    </div>
    <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV</span>
    </a>
    <a href="parqet/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://parqet.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Parqet">
    <span class="card-title" style="margin: 0;">Parqet</span>
    </div>
    <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV</span>
    </a>
    <a href="saxo/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://home.saxo/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Saxo">
    <span class="card-title" style="margin: 0;">Saxo</span>
    </div>
    <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV</span>
    </a>
    <a href="swissquote/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.swissquote.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Swissquote">
    <span class="card-title" style="margin: 0;">Swissquote</span>
    </div>
    <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV</span>
    </a>
    <a href="bitvavo/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://bitvavo.com/favicon-32x32.png?v=7ba51b544a17c10de8defa086df79917" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Bitvavo">
    <span class="card-title" style="margin: 0;">Bitvavo</span>
    </div>
    <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV (crypto)</span>
    </a>
    <a href="cryptocom/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://crypto.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Crypto.com">
    <span class="card-title" style="margin: 0;">Crypto.com</span>
    </div>
    <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV (crypto)</span>
    </a>
    <a href="relai/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://relai.app/app/uploads/2023/06/cropped-App-icon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Relai">
    <span class="card-title" style="margin: 0;">Relai</span>
    </div>
    <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV (crypto)</span>
    </a>
    <a href="cointracking/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://cointracking.info/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de CoinTracking">
    <span class="card-title" style="margin: 0;">CoinTracking</span>
    </div>
    <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV (crypto)</span>
    </a>
    <a href="delta/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.google.com/s2/favicons?domain=delta.app&amp;sz=64" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Delta">
    <span class="card-title" style="margin: 0;">Delta</span>
    </div>
    <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV (crypto)</span>
    </a>
    <a href="investimental/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon d'Investimental">
    <span class="card-title" style="margin: 0;">Investimental</span>
    </div>
    <span class="card-desc">🧪 Bêta · Historique des transactions au format CSV</span>
    </a>
    <a href="generic-csv/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" style="color: var(--md-accent-fg-color);"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg>
            <span class="card-title" style="margin: 0;">CSV générique</span>
        </div>
        <span class="card-desc">Votre propre CSV : colonnes reconnues par leurs noms d'en-tête</span>
    </a>
    <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
      <span class="card-title" style="margin: 0;">Demander un nouveau plugin</span>
      </div>
      <span class="card-desc">Votre courtier est manquant ? Demandez un nouveau plugin ou contribuez au code !</span>
    </a>
</div>

!!! tip "Lettres accentuées, signe € et points-virgules"

    Les fichiers écrits par les banques ou réenregistrés avec Excel sous Windows sont lus correctement : lettres accentuées, signe € et colonnes séparées par des points-virgules inclus (LibreFolio comprend les encodages UTF-8, Windows-1252 et Latin-1). Toutefois, téléversez vos fichiers tels que vous les avez téléchargés chaque fois que vous le pouvez : certaines pages de courtiers, comme [Danske Bank](danske-bank.md), demandent exactement cela.

---

## 🗂️ Mappage des actifs {: #asset-mapping }

Chaque titre de votre rapport doit être associé à un actif de votre bibliothèque. LibreFolio le fait automatiquement lorsqu'un seul actif correspond ; pour les autres, vous choisissez l'actif — ou le créez, prérempli à partir du rapport — dans le panneau **Résoudre les actifs** de l'étape [Vérification](how-to.md#review). Jusque-là, la ligne affiche **✗ Non résolu** et l'import attend.

---

## ♻️ Détection des doublons {: #duplicate-detection }

LibreFolio compare chaque ligne avec les transactions déjà enregistrées pour le même courtier : même type, date, quantité et montant, les petites différences d'arrondi étant ignorées.

- Si la description correspond aussi, la ligne est un **⚠ Doublon probable** et arrive décochée.
- Si la description diffère, c'est un **ℹ Doublon possible** et elle reste cochée pour que vous puissiez vérifier.

Les copies entre les fichiers que vous importez ensemble sont traitées de la même manière, et l'étape [Doublons](how-to.md#only-when-needed) vous permet de choisir quelle copie conserver. Vous pouvez toujours cocher ou décocher une ligne vous-même.

---

## ⛔ Avant la date d'ouverture du courtier {: #before-opening }

Si un courtier a une **date d'ouverture**, les lignes antérieures ne peuvent pas être importées ; le jour d'ouverture lui-même est accepté. Si la date est erronée, corrigez-la à l'étape [Vérification](how-to.md#opening-date) et les lignes sont vérifiées à nouveau. Quelle que soit la date d'ouverture, les dates des transactions vont du 1er janvier 1900 à demain : une ligne datée hors de cet intervalle est refusée quand vous enregistrez les lignes importées, avec un message tel que *Date : Entre 1900-01-01 et 2026-10-18*, si nous sommes le 17 octobre 2026.

---

## 🔗 Voir aussi

- 🧙 **[Comment importer](how-to.md)** — l'assistant d'importation, étape par étape
- 📋 **[Transactions](../index.md)** — consulter et gérer les transactions importées
- 🏦 **[Courtiers](../../brokers/index.md)** — configurez d'abord vos comptes courtiers
- 🗂️ **[Fichiers](../../files/index.md)** — vos rapports de courtier téléversés
- 🛠️ **[Liste des fournisseurs BRIM](../../../developer/backend/brim/providers_list.md)** — notes techniques sur chaque importateur, pour les développeurs
