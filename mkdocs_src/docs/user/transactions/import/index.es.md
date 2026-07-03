# 📥 Importar desde Bróker (BRIM)

**BRIM** (Broker Report Import Module) le permite importar transacciones directamente desde los archivos de exportación de su bróker, sin necesidad de entrada manual. Cargue un informe CSV y LibreFolio analizará, mapeará e importará todas las transacciones en un solo flujo.

---

## 🚀 Cómo Importar

1. Exporte un informe de transacciones desde su bróker (generalmente un archivo CSV; consulte el centro de ayuda de su bróker).
2. En LibreFolio, navegue a la página de **[Transacciones](../index.md)**.
3. Haga clic en el botón **Import** (:material-file-upload:) en el encabezado de la página, o arrastre y suelte el archivo de su extracto directamente en la lista de transacciones.
4. Se abrirá el **Asistente de Importación**.
5. Revise la vista previa: verifique que las fechas, los montos y los nombres de los activos sean correctos.
6. Haga clic en **Import** para confirmar todas las transacciones.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Modal de Importación Rápida" alt="Modal de Importación Rápida">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Paso 1: Cargar archivo de informe" alt="Asistente Paso 1">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Paso 2: Configuración del analizador" alt="Asistente Paso 2">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Paso 3: Análisis" alt="Wizard Paso 3">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🔍 Paso 4: Resolución de activos" alt="Asistente Paso 4">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Paso 4: Detección de duplicados" alt="Detección de Duplicados">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Paso 5: Revisión de carga masiva" alt="Revisión de Carga Masiva">
</div>

!!! tip "Creación de Bróker y Activos al Vuelo"

    Si el informe importado contiene una cuenta de bróker o activos que aún no se han creado en LibreFolio, ¡no es necesario salir del flujo de importación! El asistente le guará para crear los **[Brókers](../../brokers/index.md)** y **[Activos](../../assets/index.md)** faltantes al vuelo, precompletando los detalles extraídos del extracto.

!!! tip "También puede usar la sección de Archivos"

    La sección de **[Archivos](../../files/index.md)** (pestaña BRIM) le permite gestionar los informes de bróker cargados de forma centralizada, volver a importarlos o eliminarlos.

---

## 🧙 Pasos del Asistente de Importación

El asistente guiado contiene 5 pasos operativos diseñados para analizar, validar, resolver e importar su historial de transacciones de forma segura.

### 🧙 Paso 1: Cargar archivo de informe

Este paso acepta informes CSV, XLSX o PDF exportados de su bróker. Puede seleccionar archivos manualmente o arrastrarlos y soltarlos directamente en el asistente.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Asistente Paso 1: Cargar" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⚙️ Paso 2: Configuración del analizador

El sistema detecta automáticamente el formato del bróker (por ejemplo, Degiro, Directa, Interactive Brokers). Si carga una hoja de cálculo genérica, puede utilizar el analizador **Generic CSV** para mapear manualmente sus columnas (fecha, tipo, cantidad, activo, efectivo neto) a los campos de LibreFolio.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Asistente Paso 2: Configuración" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🧠 Paso 3: Análisis y Lectura

El sistema analiza los archivos, validando fechas, números y monedas. Verá una barra de progreso que indica la velocidad y el estado de la lectura. Una vez que se completa el análisis, se mostrará un resumen de cualquier advertencia o error antes de continuar.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Asistente Paso 3: Análisis" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Al finalizar el procesamiento, la tabla muestra un resumen del análisis de cada archivo con las siguientes columnas estadísticas identificadas con emojis:

| Emoji / Columna | Nombre de la Métrica | Significado y Reglas de Poblado |
| :--- | :--- | :--- |
| `📊` | **Transacciones** | El número total de transacciones financieras leídas e identificadas en el archivo. |
| `🏦` | **Activos Identificados** | El número de instrumentos financieros (acciones, ETF, etc.) encontrados en las transacciones analizadas. |
| `✗` | **Activos no Resueltos** | El número de instrumentos en el archivo que no existen en la base de datos de LibreFolio (marcado en rojo si es > 0, requiere mapeo en el Paso 4). |
| `🔴` | **Problemas de Validación** | Errores formales detectados en los datos (por ejemplo, formatos no válidos, fechas incorrectas o campos requeridos vacíos). |
| `🔧` | **Acciones Requeridas (TODO)** | Campos o atributos que requieren revisión (rojo si son bloqueantes, naranja para advertencias/información). No son necesariamente errores: simplemente indican datos ausentes que no pueden ser extraídos de forma automática del reporte, los cuales podrás rellenar manualmente en el formulario de transacciones masivas al final del proceso. |
| `⚠️` | **Advertencias** | Notificaciones generales o mensajes de advertencia generados por el analizador durante el procesamiento. |

### 🔍 Paso 4: Mapeo de Activos y Detección de Duplicados

Esta es la fase de conciliación. El asistente realiza dos comprobaciones principales:

#### 🗂️ Resolución de Activos

Si el extracto contiene símbolos de cotización o ISIN que no están en su biblioteca, el asistente los marca. Puede:
- Mapearlos a un activo existente en su base de datos.
- Crearlos **al vuelo** directamente dentro del asistente.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Asistente Paso 4: Resolución de Activos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### ⚠️ Detección de Duplicados

El sistema compara las entradas analizadas con su base de datos para encontrar posibles duplicados en función del tipo, la fecha, el monto, la cantidad y la descripción.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Asistente Paso 4: Detección de Duplicados" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Los duplicados se agrupan en la interfaz de usuario en dos insignias de estado basándose en 4 niveles de confianza:

| Insignia UI | Nivel de Confianza | Criterios / Reglas de Emparejamiento |
| :--- | :--- | :--- |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY_WITH_ASSET` | Los campos básicos y la descripción coinciden, y el activo se ha resuelto automáticamente (duplicado altamente seguro). |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY` | Los campos básicos y la descripción coinciden, pero el activo no está resuelto. |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE_WITH_ASSET` | Los campos básicos coinciden y el activo se ha resuelto automáticamente (pero la descripción difiere o está vacía). |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE` | Los campos básicos (tipo, fecha, cantidad, monto) coinciden, pero el activo no está resuelto. |
| <span style="background-color: rgba(16, 185, 129, 0.15); color: #10b981; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">✅ ÚNICO</span> | — | La transacción no tiene coincidencias en la base de datos y se considera nueva (duplicado descartado). |
| <span style="background-color: rgba(239, 68, 68, 0.15); color: #ef4444; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">❌ NO RESUELTO</span> | — | El bróker o el instrumento financiero no se han emparejado con entidades existentes en la base de datos (requiere resolución en el Paso 4 antes de importar). |

Por defecto, el asistente desmarca automáticamente las transacciones duplicadas "Probables" para evitar el doble registro, pero puede anular esta opción.

### 📦 Paso 5: Revisión de carga masiva

La revisión final muestra la lista analizada en una cuadrícula similar a una hoja de cálculo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Asistente Paso 5: Revisión General" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La tabla muestra:

- **Date**: La fecha de ejecución.
- **Type**: COMPRA, VENTA, DIVIDENDO, DEPÓSITO, etc.
- **Asset**: El activo emparejado de su biblioteca.
- **Quantity**: El número de unidades/acciones.
- **Price**: El precio unitario.
- **Net Amount**: El impacto total de efectivo.
- **Fees/Taxes**: Comisiones e impuestos incluidos.

Haga clic en **Import** para finalizar la importación y escribir las transacciones en su cartera.

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
    <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
      <span class="card-title" style="margin: 0;">Solicitar Nuevo Plugin</span>
      </div>
      <span class="card-desc">¿Falta tu bróker? ¡Solicita un nuevo plugin o contribuye!</span>
    </a>
</div>

??? info "📊 Capacidades del Importador"

    | Broker | Estado | Formato | Compra/Venta | Dividendos | Depósitos/Efectivo | Comisiones/Impuestos | Notas |
    | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
    | <img src="https://www.interactivebrokers.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Interactive Brokers** | 🧪 Beta | CSV (Flex) | ✅ | ✅ | ✅ | ✅ | Ideal para cuentas multidivisa |
    | <img src="https://www.degiro.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Degiro** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Soporte para estado de cuenta estándar |
    | <img src="https://www.etoro.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **eToro** | 🧪 Beta | XLSX/CSV | ✅ | ✅ | ✅ | ✅ | Soporte para ganancias realizadas y dividendos |
    | <img src="https://www.directa.it/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Directa SIM** | ✅ Stable | CSV | ✅ | ✅ | ✅ | ✅ | Soporte para estado fiscal de bróker italiano |
    | <img src="https://www.schwab.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Charles Schwab** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Estado de actividad estándar de bróker EE. UU. |
    | <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Revolut** | 🧪 Beta | PDF/CSV | ✅ | ✅ | ✅ | ✅ | Soporte para transacciones de acciones y criptoactivos |
    | <img src="https://www.coinbase.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Coinbase** | 🧪 Beta | CSV | ✅ | ❌ | ✅ | ✅ | Informes de transacciones solo de criptoactivos |
    | <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Freetrade** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Estados de corretaje simples del Reino Unido |
    | <img src="https://www.finpension.ch/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Finpension** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | Estados de pensión suiza 3a |
    | <img src="https://www.trading212.com/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> **Trading212** | 🧪 Beta | CSV | ✅ | ✅ | ✅ | ✅ | CSV de actividad de trading europea |
    | <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" style="color: var(--md-accent-fg-color); vertical-align: middle; margin-right: 4px;"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> **Generic CSV** | ✅ Stable | CSV | ✅ | ✅ | ✅ | ✅ | fallback con mapeador manual de columnas |

---

## 🗂️ Mapeo de Activos {: #asset-mapping }

Durante el paso de vista previa, LibreFolio intenta **emparejar automáticamente** cada nombre de activo de su informe con un activo ya existente en su biblioteca.

- ✅ **Matched (Emparejado)** — se importará vinculado al activo existente.
- ⚠️ **Unmatched (Sin emparejar)** — seleccione o cree el activo de destino antes de importar.
- ❌ **Error** — la fila no pudo ser analizada.

---

## ♻️ Detección de Duplicados {: #duplicate-detection }

BRIM busca **transacciones duplicadas** basándose en la fecha, el tipo, el activo, la cantidad y el monto. Las filas duplicadas se marcan en la vista previa; puede elegir omitirlas o forzar su importación.

---

## 🔗 Relacionados

- 📋 **[Tabla de Transacciones](../index.md)** — Ver y gestionar transacciones importadas
- 🗂️ **[Archivos](../../files/index.md)** — Gestionar archivos de informes de bróker cargados
- 🏦 **[Brókers](../../brokers/index.md)** — Configure primero sus cuentas de bróker
