# 📥 Importar desde el Bróker (BRIM)

**BRIM** (Módulo de Importación de Informes de Bróker) te permite importar transacciones directamente desde los archivos de exportación de tu bróker, sin necesidad de entrada manual. Sube un informe CSV y LibreFolio analiza, mapea e importa todas las transacciones en un solo flujo.

Para obtener instrucciones paso a paso sobre el uso del asistente, consulta la **[Guía de Importación](how-to.md)**.

---

## 🏦 Brókers Compatibles

LibreFolio admite la importación de archivos de estado de cuenta de los siguientes brókers:

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
 <a href="ibkr/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.interactivebrokers.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Icono de IBKR">
 <span class="card-title" style="margin: 0;">Interactive Brokers</span>
 </div>
 <span class="card-desc">Importa informes de transacciones usando Flex Queries.</span>
 </a>
 <a href="degiro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.degiro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Icono de Degiro">
 <span class="card-title" style="margin: 0;">Degiro</span>
 </div>
 <span class="card-desc">Importa exportaciones CSV del historial de transacciones de Degiro.</span>
 </a>
 <a href="etoro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.etoro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Icono de eToro">
 <span class="card-title" style="margin: 0;">eToro</span>
 </div>
 <span class="card-desc">Importa archivos XLSX/CSV de estado de cuenta de eToro.</span>
 </a>
 <a href="directa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.directa.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Icono de Directa SIM">
 <span class="card-title" style="margin: 0;">Directa SIM</span>
 </div>
 <span class="card-desc">Importa archivos CSV del historial de transacciones de Directa SIM.</span>
 </a>
 <a href="schwab/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.schwab.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Icono de Charles Schwab">
 <span class="card-title" style="margin: 0;">Charles Schwab</span>
 </div>
 <span class="card-desc">Importa el historial de transacciones CSV de Charles Schwab.</span>
 </a>
 <a href="revolut/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Icono de Revolut">
 <span class="card-title" style="margin: 0;">Revolut</span>
 </div>
 <span class="card-desc">Importa informes PDF/CSV de estado de cuenta de Revolut.</span>
 </a>
 <a href="coinbase/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.coinbase.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Icono de Coinbase">
 <span class="card-title" style="margin: 0;">Coinbase</span>
 </div>
 <span class="card-desc">Importa archivos CSV del historial de transacciones de Coinbase.</span>
 </a>
 <a href="freetrade/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Icono de Freetrade">
 <span class="card-title" style="margin: 0;">Freetrade</span>
 </div>
 <span class="card-desc">Importa estados de cuenta CSV de transacciones de Freetrade.</span>
 </a>
 <a href="finpension/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.finpension.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Icono de Finpension">
 <span class="card-title" style="margin: 0;">Finpension</span>
 </div>
 <span class="card-desc">Importa informes CSV del historial de transacciones de Finpension.</span>
 </a>
 <a href="trading212/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.trading212.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Icono de Trading212">
 <span class="card-title" style="margin: 0;">Trading212</span>
 </div>
 <span class="card-desc">Importa el historial de transacciones CSV de Trading212.</span>
 </a>
 <a href="generic-csv/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" style="color: var(--md-accent-fg-color);"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg>
 <span class="card-title" style="margin: 0;">CSV Genérico</span>
 </div>
 <span class="card-desc">Nuestro analizador fallback con mapeo manual de columnas.</span>
 </a>
 <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
 <span class="card-title" style="margin: 0;">Solicitar Nuevo Plugin</span>
 </div>
 <span class="card-desc">¿Falta tu bróker? ¡Solicita un nuevo plugin o contribuye con código!</span>
 </a>
</div>

??? info "📊 Capacidades del Importador"

    | Bróker | Estado | Formato | Compra/Venta | Dividendos | Depósitos/Efectivo | Comisiones/Impuestos | Notas |
    | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
    | <img src="https://www.interactivebrokers.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Interactive Brokers** | 🧪 Beta | CSV (Flex) | ✅ | ✅ | ✅ | ✅ | Ideal para cuentas multidivisa |
    | <img src="https://www.degiro.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Degiro** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Compatible con el estado de cuenta estándar |
    | <img src="https://www.etoro.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **eToro** | 🧪 Beta | XLSX/CSV | ✅ | ✅ | ✅ | ✅ | Compatible con ganancias realizadas y dividendos |
    | <img src="https://www.directa.it/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Directa SIM** | ✅ Estable | CSV | ✅ | ✅ | ✅ | ✅ | Compatible con declaración de impuestos del bróker italiano |
    | <img src="https://www.schwab.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Charles Schwab** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Estado de actividad estándar de bróker estadounidense |
    | <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Revolut** | 🧪 Beta | PDF/CSV | ✅ | ✅ | ✅ | ✅ | Compatible con transacciones de acciones y cripto |
    | <img src="https://www.coinbase.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Coinbase** | 🧪 Beta | CSV | ✅ | ❌ | ✅ | ✅ | Informes de transacciones solo de cripto |
    | <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Freetrade** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Estados de cuenta simples de bróker del Reino Unido |
    | <img src="https://www.finpension.ch/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Finpension** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Estados de cuenta del pilar 3a suizo |
    | <img src="https://www.trading212.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Trading212** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | CSV de actividad de trading europeo |
    | <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" style="color: var(--md-accent-fg-color); vertical-align: middle; margin-right: 4px;"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> **CSV Genérico** | ✅ Estable | CSV | ✅ | ✅ | ✅ | ✅ | Mapeador manual de columnas como fallback |

---

## 🗂️ Mapeo de Activos {: #asset-mapping }

Durante el paso de vista previa, LibreFolio intenta **emparejar automáticamente** cada nombre de activo de tu informe con un activo ya existente en tu biblioteca.

- ✅ **Emparejado** — se importará contra el activo existente.
- ⚠️ **Sin emparejar** — selecciona o crea el activo de destino antes de importar.
- ❌ **Error** — no se pudo analizar la fila.

---

## ♻️ Detección de Duplicados {: #duplicate-detection }

BRIM verifica si hay **transacciones duplicadas** basándose en la fecha, el tipo, el activo, la cantidad y el importe. Las filas duplicadas se marcan en la vista previa; puedes optar por omitirlas o forzar su importación.

---

## 🔗 Relacionado

- 📋 **[Tabla de Transacciones](../index.md)** — Ver y gestionar las transacciones importadas
- 🗂️ **[Archivos](../../files/index.md)** — Gestionar los archivos de informe de bróker subidos
- 🏦 **[Brókers](../../brokers/index.md)** — Configurar primero tus cuentas de bróker
