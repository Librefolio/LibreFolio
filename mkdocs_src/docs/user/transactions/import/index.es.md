# 📥 Importar desde Bróker (BRIM)

**BRIM** (Broker Report Import Module) le permite importar transacciones directamente desde los archivos de exportación de su bróker, sin necesidad de entrada manual. Cargue un informe CSV y LibreFolio analizará, mapeará e importará todas las transacciones en un solo flujo.

---

## 🚀 Cómo Importar

1. Exporte un informe de transacciones desde su bróker (generalmente un archivo CSV; consulte el centro de ayuda de su bróker).
2. En LibreFolio, navegue a su página de **Bróker**.
3. Haga clic en el botón **Import** (:material-file-upload:) en el encabezado del bróker.
4. Se abrirá el **Modal de Importación**.
5. **Arrastre y suelte** o haga clic para seleccionar su archivo.
6. LibreFolio **detecta automáticamente** el formato del bróker y muestra una **vista previa** de las transacciones analizadas.
7. Revise la vista previa: verifique que las fechas, los montos y los nombres de los activos sean correctos.
8. Haga clic en **Import** para confirmar todas las transacciones.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Modal de Importación Rápida" alt="Modal de Importación Rápida">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Paso 1: Cargar archivo de informe" alt="Asistente Paso 1">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Paso 2: Configuración del analizador" alt="Asistente Paso 2">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🔍 Paso 3: Resolución de activos" alt="Asistente Paso 3">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Detección de duplicados" alt="Detección de Duplicados">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Revisión de carga masiva" alt="Revisión de Carga Masiva">
</div>

!!! tip "También puede usar la sección de Archivos"

    La sección de **[Archivos](../../files/index.md)** (pestaña BRIM) le permite gestionar los informes de bróker cargados de forma centralizada, volver a importarlos o eliminarlos.

---

## 🏦 Brókers Soportados

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
 <a href="ibkr/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.interactivebrokers.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="IBKR favicon">
 <span class="card-title" style="margin: 0;">Interactive Brokers</span>
 </div>
 <span class="card-desc">Importe informes de transacciones usando Flex Queries.</span>
 </a>
 <a href="degiro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.degiro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Degiro favicon">
 <span class="card-title" style="margin: 0;">Degiro</span>
 </div>
 <span class="card-desc">Importe exportaciones CSV del historial de transacciones de Degiro.</span>
 </a>
 <a href="etoro/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.etoro.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="eToro favicon">
 <span class="card-title" style="margin: 0;">eToro</span>
 </div>
 <span class="card-desc">Importe archivos XLSX/CSV de estados de cuenta de eToro.</span>
 </a>
 <a href="directa/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.directa.it/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Directa SIM favicon">
 <span class="card-title" style="margin: 0;">Directa SIM</span>
 </div>
 <span class="card-desc">Importe archivos CSV del historial de transacciones de Directa SIM.</span>
 </a>
 <a href="schwab/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.schwab.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Charles Schwab favicon">
 <span class="card-title" style="margin: 0;">Charles Schwab</span>
 </div>
 <span class="card-desc">Importe el historial de transacciones CSV de Charles Schwab.</span>
 </a>
 <a href="revolut/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Revolut favicon">
 <span class="card-title" style="margin: 0;">Revolut</span>
 </div>
 <span class="card-desc">Importe informes PDF/CSV de estados de cuenta de Revolut.</span>
 </a>
 <a href="coinbase/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.coinbase.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Coinbase favicon">
 <span class="card-title" style="margin: 0;">Coinbase</span>
 </div>
 <span class="card-desc">Importe archivos CSV del historial de transacciones de Coinbase.</span>
 </a>
 <a href="freetrade/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Freetrade favicon">
 <span class="card-title" style="margin: 0;">Freetrade</span>
 </div>
 <span class="card-desc">Importe estados de transacciones CSV de Freetrade.</span>
 </a>
 <a href="finpension/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.finpension.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Finpension favicon">
 <span class="card-title" style="margin: 0;">Finpension</span>
 </div>
 <span class="card-desc">Importe informes CSV del historial de transacciones de Finpension.</span>
 </a>
 <a href="trading212/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.trading212.com/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Trading212 favicon">
 <span class="card-title" style="margin: 0;">Trading212</span>
 </div>
 <span class="card-desc">Importe el historial de transacciones CSV de Trading212.</span>
 </a>
 <a href="generic-csv/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" style="color: var(--md-accent-fg-color);"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg>
 <span class="card-title" style="margin: 0;">Generic CSV</span>
 </div>
 <span class="card-desc">Nuestro analizador fallback con mapeo manual de columnas.</span>
 </a>
</div>

### 📊 Capacidades del Importador

| Broker | Formato | Compra/Venta | Dividendos | Depósitos/Efectivo | Comisiones/Impuestos | Notas |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **Interactive Brokers** | CSV (Flex) | ✅ | ✅ | ✅ | ✅ | Ideal para cuentas multidivisa |
| **Degiro** | CSV | ✅ | ✅ | ✅ | ✅ | Soporte para estado de cuenta estándar |
| **eToro** | XLSX/CSV | ✅ | ✅ | ✅ | ✅ | Soporte para ganancias realizadas y dividendos |
| **Directa SIM** | CSV | ✅ | ✅ | ✅ | ✅ | Soporte para estado fiscal de bróker italiano |
| **Charles Schwab** | CSV | ✅ | ✅ | ✅ | ✅ | Estado de actividad estándar de bróker EE. UU. |
| **Revolut** | PDF/CSV | ✅ | ✅ | ✅ | ✅ | Soporte para transacciones de acciones y criptoactivos |
| **Coinbase** | CSV | ✅ | ❌ | ✅ | ✅ | Informes de transacciones solo de criptoactivos |
| **Freetrade** | CSV | ✅ | ✅ | ✅ | ✅ | Estados de corretaje simples del Reino Unido |
| **Finpension** | CSV | ✅ | ✅ | ✅ | ✅ | Estados de pensión suiza 3a |
| **Trading212** | CSV | ✅ | ✅ | ✅ | ✅ | CSV de actividad de trading europea |
| **Generic CSV** | CSV | ✅ | ✅ | ✅ | ✅ | fallback con mapeador manual de columnas |

!!! note "Todos los proveedores están en Beta"

    Los complementos de importación son mantenidos por la comunidad y mejoran con el tiempo. Si un formato de informe específico presenta errores, el proveedor **[Generic CSV](generic-csv/)** permite el mapeo manual de columnas como fallback.

---

## 🗂️ Mapeo de Activos

Durante el paso de vista previa, LibreFolio intenta **emparejar automáticamente** cada nombre de activo de su informe con un activo ya existente en su biblioteca.

- ✅ **Matched (Emparejado)** — se importará vinculado al activo existente.
- ⚠️ **Unmatched (Sin emparejar)** — seleccione o cree el activo de destino antes de importar.
- ❌ **Error** — la fila no pudo ser analizada.

---

## ♻️ Detección de Duplicados

BRIM busca **transacciones duplicadas** basándose en la fecha, el tipo, el activo, la cantidad y el monto. Las filas duplicadas se marcan en la vista previa; puede elegir omitirlas o forzar su importación.

---

## 🔗 Relacionados

- 📋 **[Tabla de Transacciones](../index.md)** — Ver y gestionar transacciones importadas
- 🗂️ **[Archivos](../../files/index.md)** — Gestionar archivos de informes de bróker cargados
- 🏦 **[Brókers](../../brokers/index.md)** — Configure primero sus cuentas de bróker
