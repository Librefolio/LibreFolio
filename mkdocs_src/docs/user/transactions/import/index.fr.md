# 📥 Importer depuis le courtier (BRIM)

<style>
/* Importer capabilities table: Broker icon+name on one line, cells vertically centered, Notes 50% wider */
.md-typeset details table th:first-child,
.md-typeset details table td:first-child { min-width: 9rem; white-space: nowrap; }
.md-typeset details .md-typeset__table table td { vertical-align: middle; }
.md-typeset details table th:last-child,
.md-typeset details table td:last-child { min-width: 24rem; }
/* Broker icon fallback: the letter tile sits after the image, hidden; onerror swaps them */
.broker-icon-fallback { display: inline-flex; align-items: center; vertical-align: middle; margin-right: 4px; }
.broker-icon-fallback > span { display: none; width: 16px; height: 16px; align-items: center; justify-content: center; font-size: 9px; font-weight: 700; color: var(--md-accent-fg-color); }
</style>

**BRIM** (Broker Report Import Module) vous permet d'importer des transactions directement depuis les fichiers d'exportation de votre courtier — sans saisie manuelle. Téléchargez un rapport CSV et LibreFolio analyse, fait correspondre et importe toutes les transactions en une seule opération.

Pour des instructions étape par étape sur le fonctionnement de l'assistant, consultez le **[Guide d'importation](how-to.md)**.

---

## 🏦 Courtiers pris en charge

LibreFolio prend en charge l'importation de fichiers de relevés provenant des courtiers suivants :

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
 <a href="ibkr/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.interactivebrokers.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="IBKR favicon">
 <span class="card-title" style="margin: 0;">Interactive Brokers</span>
 </div>
 <span class="card-desc">Importez des rapports de transactions à l'aide de Flex Queries.</span>
 </a>
 <a href="degiro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.degiro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Degiro favicon">
 <span class="card-title" style="margin: 0;">Degiro</span>
 </div>
 <span class="card-desc">Importez les exportations CSV de l'historique des transactions depuis Degiro.</span>
 </a>
 <a href="etoro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.etoro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="eToro favicon">
 <span class="card-title" style="margin: 0;">eToro</span>
 </div>
 <span class="card-desc">Importez les fichiers CSV de relevé de compte depuis eToro.</span>
 </a>
 <a href="directa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.directa.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Directa SIM favicon">
 <span class="card-title" style="margin: 0;">Directa SIM</span>
 </div>
 <span class="card-desc">Importez les fichiers CSV ou XLSX de l'historique des transactions depuis Directa SIM.</span>
 </a>
 <a href="schwab/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.schwab.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Charles Schwab favicon">
 <span class="card-title" style="margin: 0;">Charles Schwab</span>
 </div>
 <span class="card-desc">Importez l'historique des transactions CSV depuis Charles Schwab.</span>
 </a>
 <a href="revolut/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Revolut favicon">
 <span class="card-title" style="margin: 0;">Revolut</span>
 </div>
 <span class="card-desc">Importez les rapports CSV de relevé de compte depuis Revolut.</span>
 </a>
 <a href="coinbase/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.coinbase.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Coinbase favicon">
 <span class="card-title" style="margin: 0;">Coinbase</span>
 </div>
 <span class="card-desc">Importez les fichiers CSV de l'historique des transactions depuis Coinbase.</span>
 </a>
 <a href="freetrade/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Freetrade favicon">
 <span class="card-title" style="margin: 0;">Freetrade</span>
 </div>
 <span class="card-desc">Importez les relevés de transactions CSV depuis Freetrade.</span>
 </a>
 <a href="finpension/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.finpension.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Finpension favicon">
 <span class="card-title" style="margin: 0;">Finpension</span>
 </div>
 <span class="card-desc">Importez les rapports CSV de l'historique des transactions depuis Finpension.</span>
 </a>
 <a href="trading212/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.trading212.com/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Trading212 favicon">
 <span class="card-title" style="margin: 0;">Trading212</span>
 </div>
 <span class="card-desc">Importez l'historique des transactions CSV depuis Trading212.</span>
 </a>
 <a href="avanza/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://avanza.se/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Avanza">
 <span class="card-title" style="margin: 0;">Avanza</span>
 </div>
 <span class="card-desc">Importez l'export CSV de l'historique des transactions depuis Avanza.</span>
 </a>
 <a href="bux/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://bux.com/it/wp-content/themes/vo-theme/assets/images/favicon/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon BUX">
 <span class="card-title" style="margin: 0;">BUX</span>
 </div>
 <span class="card-desc">Importez l'export CSV de l'historique des transactions depuis BUX.</span>
 </a>
 <a href="disnat/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://disnat.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Disnat">
 <span class="card-title" style="margin: 0;">Disnat</span>
 </div>
 <span class="card-desc">Importez l'export CSV de l'historique des transactions depuis Disnat.</span>
 </a>
 <a href="investengine/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.investengine.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon InvestEngine">
 <span class="card-title" style="margin: 0;">InvestEngine</span>
 </div>
 <span class="card-desc">Importez l'export CSV de l'historique des transactions depuis InvestEngine.</span>
 </a>
 <a href="rabobank/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.rabobank.com/static/msp/global-sites/rds/favicons/favicon-svg.svg" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Rabobank">
 <span class="card-title" style="margin: 0;">Rabobank</span>
 </div>
 <span class="card-desc">Importez l'export CSV de l'historique des transactions depuis Rabobank.</span>
 </a>
 <a href="fineco/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://finecobank.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Fineco">
 <span class="card-title" style="margin: 0;">Fineco</span>
 </div>
 <span class="card-desc">Importez l'export CSV "Movimenti Dossier Titoli" depuis Fineco.</span>
 </a>
    <a href="intesa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.intesasanpaolo.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Intesa Sanpaolo">
    <span class="card-title" style="margin: 0;">Intesa Sanpaolo</span>
    </div>
    <span class="card-desc">Importez les mouvements CSV/XLSX ou les exports de patrimoine d'Intesa Sanpaolo.</span>
    </a>
    <a href="credit_agricole/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.credit-agricole.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Crédit Agricole">
    <span class="card-title" style="margin: 0;">Crédit Agricole</span>
    </div>
    <span class="card-desc">Importez les mouvements de compte de Crédit Agricole — trésorerie réelle, frais, impôts et coupons/dividendes ; export titres optionnel pour l'historique de plus de 2 ans.</span>
    </a>
 <a href="traderepublic/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://traderepublic.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Trade Republic">
 <span class="card-title" style="margin: 0;">Trade Republic</span>
 </div>
 <span class="card-desc">Importez l'export CSV de l'historique des transactions depuis Trade Republic.</span>
 </a>
 <a href="xtb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.xtb.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon XTB">
 <span class="card-title" style="margin: 0;">XTB</span>
 </div>
 <span class="card-desc">Importez l'export CSV de l'historique des transactions depuis XTB.</span>
 </a>
 <a href="parqet/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://parqet.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Parqet">
 <span class="card-title" style="margin: 0;">Parqet</span>
 </div>
 <span class="card-desc">Importez l'export CSV de l'historique des transactions depuis Parqet.</span>
 </a>
 <a href="saxo/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://home.saxo/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Saxo">
 <span class="card-title" style="margin: 0;">Saxo</span>
 </div>
 <span class="card-desc">Importez l'export CSV de l'historique des transactions depuis Saxo.</span>
 </a>
 <a href="swissquote/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.swissquote.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Swissquote">
 <span class="card-title" style="margin: 0;">Swissquote</span>
 </div>
 <span class="card-desc">Importez l'export CSV de l'historique des transactions depuis Swissquote.</span>
 </a>
 <a href="bitvavo/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://bitvavo.com/favicon-32x32.png?v=7ba51b544a17c10de8defa086df79917" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Bitvavo">
 <span class="card-title" style="margin: 0;">Bitvavo</span>
 </div>
 <span class="card-desc">Importez l'export CSV de l'historique des transactions depuis Bitvavo (crypto).</span>
 </a>
 <a href="cryptocom/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://crypto.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Crypto.com">
 <span class="card-title" style="margin: 0;">Crypto.com</span>
 </div>
 <span class="card-desc">Importez l'export CSV de l'historique des transactions depuis Crypto.com (crypto).</span>
 </a>
 <a href="relai/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://relai.app/app/uploads/2023/06/cropped-App-icon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Relai">
 <span class="card-title" style="margin: 0;">Relai</span>
 </div>
 <span class="card-desc">Importez l'export CSV de l'historique des transactions depuis Relai (crypto).</span>
 </a>
 <a href="cointracking/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://cointracking.info/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon CoinTracking">
 <span class="card-title" style="margin: 0;">CoinTracking</span>
 </div>
 <span class="card-desc">Importez l'export CSV de l'historique des transactions depuis CoinTracking (crypto).</span>
 </a>
 <a href="delta/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.google.com/s2/favicons?domain=delta.app&amp;sz=64" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Delta">
 <span class="card-title" style="margin: 0;">Delta</span>
 </div>
 <span class="card-desc">Importez l'export CSV de l'historique des transactions depuis Delta (crypto).</span>
 </a>
 <a href="investimental/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon Investimental">
 <span class="card-title" style="margin: 0;">Investimental</span>
 </div>
 <span class="card-desc">Importez l'export CSV de l'historique des transactions depuis Investimental.</span>
 </a>
 <a href="generic-csv/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" style="color: var(--md-accent-fg-color);"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg>
 <span class="card-title" style="margin: 0;">CSV Générique</span>
 </div>
 <span class="card-desc">Notre analyseur fallback avec mappage manuel des colonnes.</span>
 </a>
 <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
 <span class="card-title" style="margin: 0;">Demander un nouveau plugin</span>
 </div>
 <span class="card-desc">Votre courtier est manquant ? Demandez un nouveau plugin ou contribuez au code !</span>
 </a>
</div>

??? info "📊 Capacités de l'importateur"

    | Courtier | Statut | Format | Achat/Vente | Dividendes | Dépôts/Espèces | Frais/Taxes | Remarques |
    | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.interactivebrokers.com/favicon.ico" width="16" height="16" style=""><span>IB</span></span> **Interactive Brokers** | 🧪 Bêta | CSV (Flex) | ✅ | ✅ | ✅ | ✅ | Meilleur pour les comptes multi-devises |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.degiro.com/favicon.ico" width="16" height="16" style=""><span>DE</span></span> **Degiro** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Prise en charge des relevés de compte standard |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.etoro.com/favicon.ico" width="16" height="16" style=""><span>ET</span></span> **eToro** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Prise en charge des plus-values réalisées et des dividendes |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.directa.it/favicon.ico" width="16" height="16" style=""><span>DS</span></span> **Directa SIM** | ✅ Stable | CSV/XLSX | ✅ | ✅ | ✅ | ✅ | Prise en charge des relevés fiscaux des courtiers italiens |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.schwab.com/favicon.ico" width="16" height="16" style=""><span>CS</span></span> **Charles Schwab** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Relevé d'activité standard des courtiers américains |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="16" height="16" style=""><span>RE</span></span> **Revolut** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Prise en charge des transactions d'actions et de crypto |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.coinbase.com/favicon.ico" width="16" height="16" style=""><span>CO</span></span> **Coinbase** | 🧪 Bêta | CSV | ✅ | ❌ | ✅ | ✅ | Rapports de transactions crypto uniquement |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="16" height="16" style=""><span>FR</span></span> **Freetrade** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Relevés de courtage britanniques simples |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.finpension.ch/favicon.ico" width="16" height="16" style=""><span>FI</span></span> **Finpension** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Relevés du pilier 3a suisse |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.trading212.com/favicon-32x32.png" width="16" height="16" style=""><span>TR</span></span> **Trading212** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | CSV d'activité de trading européen |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://avanza.se/favicon.ico" width="16" height="16" style=""><span>AV</span></span> **Avanza** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Écrit à partir des fichiers d'exemple |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://bux.com/it/wp-content/themes/vo-theme/assets/images/favicon/favicon-32x32.png" width="16" height="16" style=""><span>BU</span></span> **BUX** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Écrit à partir des fichiers d'exemple |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://disnat.com/favicon.ico" width="16" height="16" style=""><span>DI</span></span> **Disnat** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Écrit à partir des fichiers d'exemple |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.investengine.com/favicon.ico" width="16" height="16" style=""><span>IN</span></span> **InvestEngine** | 🧪 Bêta | CSV | ✅ | ✅ | ❌ | ❌ | Écrit à partir des fichiers d'exemple |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.rabobank.com/static/msp/global-sites/rds/favicons/favicon-svg.svg" width="16" height="16" style=""><span>RA</span></span> **Rabobank** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Écrit à partir des fichiers d'exemple |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://finecobank.com/favicon.ico" width="16" height="16" style=""><span>FI</span></span> **Fineco** | 🧪 Beta | CSV | ✅ | ✅ | ❌ | ✅ | Les deux modèles d'exportation ; montants dans la devise du rapport |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.intesasanpaolo.com/favicon.ico" width="16" height="16" style=""><span>IS</span></span> **Intesa Sanpaolo** | 🧪 Beta | CSV/XLSX | ❌ | ✅ | ✅ | ✅ | Mouvements coupons/dividendes/frais/taxes ; l'instantané patrimoine alimente le cash lorsqu'il est présent + positions |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.credit-agricole.it/favicon.ico" width="16" height="16" style=""><span>CA</span></span> **Crédit Agricole** | ✅ Stable | CSV/XLSX | ✅ | ✅ | ✅ | ✅ | Les mouvements de compte apportent du cash réel, frais, taxes et coupons/dividendes ; l'export titres optionnel récupère l'historique sur 2 ans ; contre-entrées auto de cash, échéances et ajustements de succession |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://traderepublic.com/favicon.ico" width="16" height="16" style=""><span>TR</span></span> **Trade Republic** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Écrit à partir des fichiers d'exemple |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.xtb.com/favicon.ico" width="16" height="16" style=""><span>XT</span></span> **XTB** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Écrit à partir des fichiers d'exemple |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://parqet.com/favicon.ico" width="16" height="16" style=""><span>PA</span></span> **Parqet** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Écrit à partir des fichiers d'exemple |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://home.saxo/favicon.ico" width="16" height="16" style=""><span>SA</span></span> **Saxo** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Écrit à partir des fichiers d'exemple |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.swissquote.com/favicon.ico" width="16" height="16" style=""><span>SW</span></span> **Swissquote** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Écrit à partir des fichiers d'exemple |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://bitvavo.com/favicon-32x32.png?v=7ba51b544a17c10de8defa086df79917" width="16" height="16" style=""><span>BI</span></span> **Bitvavo** | 🧪 Bêta | CSV | ✅ | ❌ | ✅ | ✅ | Plateforme crypto — écrit à partir des fichiers d'exemple |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://crypto.com/favicon.ico" width="16" height="16" style=""><span>CC</span></span> **Crypto.com** | 🧪 Bêta | CSV | ✅ | ❌ | ❌ | ❌ | Plateforme crypto — écrit à partir des fichiers d'exemple |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://relai.app/app/uploads/2023/06/cropped-App-icon-32x32.png" width="16" height="16" style=""><span>RE</span></span> **Relai** | 🧪 Bêta | CSV | ✅ | ❌ | ❌ | ✅ | Plateforme crypto — écrit à partir des fichiers d'exemple |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://cointracking.info/favicon.ico" width="16" height="16" style=""><span>CO</span></span> **CoinTracking** | 🧪 Bêta | CSV | ✅ | ❌ | ✅ | ✅ | Plateforme crypto — écrit à partir des fichiers d'exemple |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.google.com/s2/favicons?domain=delta.app&amp;sz=64" width="16" height="16" style=""><span>DE</span></span> **Delta** | 🧪 Bêta | CSV | ✅ | ✅ | ✅ | ✅ | Plateforme crypto — écrit à partir des fichiers d'exemple |
    | <span class="broker-icon-fallback"><img onerror="this.style.display='none';this.nextElementSibling.style.display='inline-flex'" src="https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico" width="16" height="16" style=""><span>IN</span></span> **Investimental** | 🧪 Bêta | CSV | ✅ | ❌ | ❌ | ✅ | Écrit à partir des fichiers d'exemple |
    | <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" style="color: var(--md-accent-fg-color); vertical-align: middle; margin-right: 4px;"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> **CSV Générique** | ✅ Stable | CSV | ✅ | ✅ | ✅ | ✅ | Analyseur fallback avec mappage manuel des colonnes |

---

## 🗂️ Mappage des actifs {: #asset-mapping }

Lors de l'étape de prévisualisation, LibreFolio tente de **faire correspondre automatiquement** chaque nom d'actif de votre rapport à un actif déjà présent dans votre bibliothèque.

- ✅ **Correspondant** — sera importé par rapport à l'actif existant.
- ⚠️ **Non correspondant** — sélectionnez ou créez l'actif cible avant d'importer.
- ❌ **Erreur** — la ligne n'a pas pu être analysée.

---

## ♻️ Détection des doublons {: #duplicate-detection }

BRIM vérifie les **transactions en double** au sein du même courtier en comparant **le type, la date, la quantité et le montant/la devise de trésorerie** (avec de petites tolérances pour les arrondis). Une **description** correspondante fait passer un signalement de *possible* à *probable* ; un **actif** correspondant — lorsque la ligne du rapport a été automatiquement associée à votre bibliothèque — augmente également le niveau de confiance. Les lignes en double sont signalées dans l'aperçu — vous pouvez choisir de les ignorer ou de les forcer à être importées.

---

## ⛔ Avant la date d'ouverture du courtier {: #before-opening }

Si un courtier a une **date d'ouverture** définie, toute transaction datée d'**avant** cette date est signalée dans l'aperçu comme **"Avant l'ouverture"** et ne peut pas être importée (sa case à cocher est désactivée). Le jour de l'ouverture reste valide. Si une ligne est signalée par erreur, utilisez l'action **Modifier la date du courtier**, puis **réessayez / actualisez** pour réévaluer chaque ligne.

---

## 🔗 Liens connexes

- 📋 **[Tableau des transactions](../index.md)** — Visualiser et gérer les transactions importées
- 🗂️ **[Fichiers](../../files/index.md)** — Gérer les fichiers de rapports de courtier téléchargés
- 🏦 **[Courtiers](../../brokers/index.md)** — Configurez d'abord vos comptes de courtier
