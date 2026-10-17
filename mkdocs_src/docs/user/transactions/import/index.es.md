# 📥 Importar desde un bróker (BRIM)

**BRIM** (Broker Report Import Module) importa tus transacciones desde los archivos que tu bróker te permite
descargar, para que no tengas que escribirlas. Para realizar una importación, sigue la
**[guía de cómo importar](how-to.md)**.

---

## 🏦 Brókeres compatibles

Elige tu bróker para ver qué archivo exportar y a qué prestar atención. Los importadores que aún están
en desarrollo llevan una etiqueta:

- 🔬 **Alpha** — nuevo: espera encontrar detalles sin pulir y revisa cada fila;
- 🧪 **Beta** — probado con archivos de ejemplo: los casos inusuales pueden pasar desapercibidos.

Los importadores sin etiqueta están bien probados y son fiables para los formatos que admiten.

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="ibkr/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.interactivebrokers.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de IBKR">
            <span class="card-title" style="margin: 0;">Interactive Brokers</span>
        </div>
        <span class="card-desc">🧪 Beta · Informe de operaciones CSV de una Flex Query</span>
    </a>
    <a href="degiro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.degiro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Degiro">
            <span class="card-title" style="margin: 0;">Degiro</span>
        </div>
        <span class="card-desc">La exportación CSV del extracto de cuenta</span>
    </a>
    <a href="etoro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.etoro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de eToro">
            <span class="card-title" style="margin: 0;">eToro</span>
        </div>
        <span class="card-desc">🧪 Beta · Extracto de cuenta CSV</span>
    </a>
    <a href="directa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.directa.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Directa SIM">
            <span class="card-title" style="margin: 0;">Directa SIM</span>
        </div>
        <span class="card-desc">Historial de transacciones, CSV o XLSX</span>
    </a>
    <a href="schwab/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.schwab.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Charles Schwab">
            <span class="card-title" style="margin: 0;">Charles Schwab</span>
        </div>
        <span class="card-desc">🧪 Beta · Historial de transacciones CSV</span>
    </a>
    <a href="revolut/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Revolut">
            <span class="card-title" style="margin: 0;">Revolut</span>
        </div>
        <span class="card-desc">🧪 Beta · Extracto de cuenta CSV</span>
    </a>
    <a href="coinbase/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.coinbase.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Coinbase">
            <span class="card-title" style="margin: 0;">Coinbase</span>
        </div>
        <span class="card-desc">🧪 Beta · Historial de transacciones CSV (cripto)</span>
    </a>
    <a href="freetrade/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Freetrade">
            <span class="card-title" style="margin: 0;">Freetrade</span>
        </div>
        <span class="card-desc">🧪 Beta · Extracto de transacciones CSV</span>
    </a>
    <a href="finpension/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.finpension.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Finpension">
            <span class="card-title" style="margin: 0;">Finpension</span>
        </div>
        <span class="card-desc">🧪 Beta · Historial de transacciones CSV</span>
    </a>
    <a href="trading212/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.trading212.com/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Trading212">
            <span class="card-title" style="margin: 0;">Trading212</span>
        </div>
        <span class="card-desc">🧪 Beta · Historial de transacciones CSV</span>
    </a>
    <a href="avanza/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://avanza.se/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Avanza">
    <span class="card-title" style="margin: 0;">Avanza</span>
    </div>
    <span class="card-desc">🧪 Beta · Historial de transacciones CSV</span>
    </a>
    <a href="bux/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://bux.com/it/wp-content/themes/vo-theme/assets/images/favicon/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de BUX">
    <span class="card-title" style="margin: 0;">BUX</span>
    </div>
    <span class="card-desc">🧪 Beta · Historial de transacciones CSV</span>
    </a>
    <a href="disnat/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://disnat.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Disnat">
    <span class="card-title" style="margin: 0;">Disnat</span>
    </div>
    <span class="card-desc">🧪 Beta · Historial de transacciones CSV</span>
    </a>
    <a href="investengine/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.investengine.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de InvestEngine">
    <span class="card-title" style="margin: 0;">InvestEngine</span>
    </div>
    <span class="card-desc">🧪 Beta · Historial de transacciones CSV</span>
    </a>
    <a href="rabobank/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.rabobank.com/static/msp/global-sites/rds/favicons/favicon-svg.svg" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Rabobank">
    <span class="card-title" style="margin: 0;">Rabobank</span>
    </div>
    <span class="card-desc">🧪 Beta · Historial de transacciones CSV</span>
    </a>
    <a href="fineco/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://finecobank.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Fineco">
    <span class="card-title" style="margin: 0;">Fineco</span>
    </div>
    <span class="card-desc">🧪 Beta · La exportación CSV "Movimenti Dossier Titoli"</span>
    </a>
    <a href="intesa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.intesasanpaolo.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Intesa Sanpaolo">
    <span class="card-title" style="margin: 0;">Intesa Sanpaolo</span>
    </div>
    <span class="card-desc">🧪 Beta · Movimientos o instantánea de patrimonio, CSV o XLSX</span>
    </a>
    <a href="credit_agricole/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.credit-agricole.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Crédit Agricole">
    <span class="card-title" style="margin: 0;">Crédit Agricole</span>
    </div>
    <span class="card-desc">Movimientos de cuenta, CSV o XLSX, más una exportación opcional de valores para historial de más de 2 años</span>
    </a>
    <a href="danske-bank/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://danskebank.fi/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Danske Bank">
    <span class="card-title" style="margin: 0;">Danske Bank</span>
    </div>
    <span class="card-desc">🔬 Alpha · Cuenta de ahorro de renta variable finlandesa: el XLSX de valores y el CSV de efectivo, subidos juntos como un conjunto de informes</span>
    </a>
    <a href="scalable/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="../../../../static/icons/brokers/scalable.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Scalable Capital">
    <span class="card-title" style="margin: 0;">Scalable Capital</span>
    </div>
    <span class="card-desc">Cuenta de valores (el CSV de Scalable o el exportador de LibreFolio) y cuenta remunerada (exportador), como dos brókeres</span>
    </a>
    <a href="traderepublic/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://traderepublic.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Trade Republic">
    <span class="card-title" style="margin: 0;">Trade Republic</span>
    </div>
    <span class="card-desc">🧪 Beta · Historial de transacciones CSV</span>
    </a>
    <a href="xtb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.xtb.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de XTB">
    <span class="card-title" style="margin: 0;">XTB</span>
    </div>
    <span class="card-desc">🧪 Beta · Historial de transacciones CSV</span>
    </a>
    <a href="parqet/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://parqet.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Parqet">
    <span class="card-title" style="margin: 0;">Parqet</span>
    </div>
    <span class="card-desc">🧪 Beta · Historial de transacciones CSV</span>
    </a>
    <a href="saxo/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://home.saxo/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Saxo">
    <span class="card-title" style="margin: 0;">Saxo</span>
    </div>
    <span class="card-desc">🧪 Beta · Historial de transacciones CSV</span>
    </a>
    <a href="swissquote/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.swissquote.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Swissquote">
    <span class="card-title" style="margin: 0;">Swissquote</span>
    </div>
    <span class="card-desc">🧪 Beta · Historial de transacciones CSV</span>
    </a>
    <a href="bitvavo/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://bitvavo.com/favicon-32x32.png?v=7ba51b544a17c10de8defa086df79917" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Bitvavo">
    <span class="card-title" style="margin: 0;">Bitvavo</span>
    </div>
    <span class="card-desc">🧪 Beta · Historial de transacciones CSV (cripto)</span>
    </a>
    <a href="cryptocom/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://crypto.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Crypto.com">
    <span class="card-title" style="margin: 0;">Crypto.com</span>
    </div>
    <span class="card-desc">🧪 Beta · Historial de transacciones CSV (cripto)</span>
    </a>
    <a href="relai/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://relai.app/app/uploads/2023/06/cropped-App-icon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Relai">
    <span class="card-title" style="margin: 0;">Relai</span>
    </div>
    <span class="card-desc">🧪 Beta · Historial de transacciones CSV (cripto)</span>
    </a>
    <a href="cointracking/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://cointracking.info/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de CoinTracking">
    <span class="card-title" style="margin: 0;">CoinTracking</span>
    </div>
    <span class="card-desc">🧪 Beta · Historial de transacciones CSV (cripto)</span>
    </a>
    <a href="delta/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.google.com/s2/favicons?domain=delta.app&amp;sz=64" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Delta">
    <span class="card-title" style="margin: 0;">Delta</span>
    </div>
    <span class="card-desc">🧪 Beta · Historial de transacciones CSV (cripto)</span>
    </a>
    <a href="investimental/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
    <div style="display: flex; align-items: center; gap: 0.75rem;">
    <img src="https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de Investimental">
    <span class="card-title" style="margin: 0;">Investimental</span>
    </div>
    <span class="card-desc">🧪 Beta · Historial de transacciones CSV</span>
    </a>
    <a href="generic-csv/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" style="color: var(--md-accent-fg-color);"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg>
            <span class="card-title" style="margin: 0;">CSV genérico</span>
        </div>
        <span class="card-desc">Tu propio CSV: columnas reconocidas a partir del nombre de sus encabezados</span>
    </a>
    <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
      <span class="card-title" style="margin: 0;">Solicitar nuevo plugin</span>
      </div>
      <span class="card-desc">¿Falta tu bróker? ¡Solicita un nuevo plugin o contribuye con código!</span>
    </a>
</div>

!!! tip "Letras acentuadas, el signo € y los puntos y coma"

    Los archivos escritos por bancos o vueltos a guardar con Excel en Windows se leen correctamente, y ello incluye letras acentuadas,
    el signo € y columnas separadas por puntos y coma (LibreFolio entiende las codificaciones UTF-8,
    Windows-1252 y Latin-1). Aun así, sube tus archivos tal como los descargaste siempre que puedas:
    algunas páginas de brókeres, como [Danske Bank](danske-bank.md), piden exactamente eso.

---

## 🗂️ Asignación de activos {: #asset-mapping }

Cada valor en tu informe debe asignarse a un activo de tu biblioteca. LibreFolio lo hace por sí solo cuando exactamente un activo coincide; para los demás, tú eliges el activo — o lo creas, rellenado desde el informe — en el panel **Resolver activos** del paso [Revisar](how-to.md#review). Hasta entonces, la fila muestra **✗ Sin resolver** y la importación espera.

---

## ♻️ Detección de duplicados {: #duplicate-detection }

LibreFolio compara cada fila con las transacciones ya guardadas para el mismo bróker: mismo tipo, fecha, cantidad e importe, ignorando pequeñas diferencias de redondeo.

- Si la descripción también coincide, la fila es **⚠ Probable dup** y llega sin marcar.
- Si la descripción difiere, es **ℹ Posible dup** y permanece marcada para que la revises.

Las copias entre los archivos que importas juntos se manejan de la misma manera, y el paso [Duplicados](how-to.md#only-when-needed) te permite elegir qué copia conservar. Siempre puedes marcar o desmarcar una fila tú mismo.

---

## ⛔ Antes de la fecha de apertura del bróker {: #before-opening }

Si un bróker tiene una **fecha de apertura**, las filas con fecha anterior no se pueden importar; el propio día de apertura sí es válido. Si la fecha es incorrecta, corrígela desde el paso [Revisar](how-to.md#opening-date) y las filas se comprueban de nuevo. Sea cual sea la fecha de apertura, las fechas de las transacciones van del 1 de enero de 1900 a un año a partir de hoy: una fila con una fecha fuera de ese intervalo se rechaza al guardar las filas importadas, con un mensaje como *Fecha: Entre 1900-01-01 y 2027-10-17*, si hoy es 17 de octubre de 2026.

---

## 🔗 Relacionado

- 🧙 **[Cómo importar](how-to.md)** — el asistente, paso a paso
- 📋 **[Transacciones](../index.md)** — visualiza y gestiona las transacciones importadas
- 🏦 **[Brókeres](../../brokers/index.md)** — configura primero tus cuentas de bróker
- 🗂️ **[Archivos](../../files/index.md)** — tus informes de bróker subidos
- 🛠️ **[Lista de proveedores BRIM](../../../developer/backend/brim/providers_list.md)** — notas técnicas sobre cada importador, para desarrolladores
