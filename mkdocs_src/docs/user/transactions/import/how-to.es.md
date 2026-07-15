# 🧙 Cómo Importar Transacciones

Aprende a usar el Módulo de Importación de Informes de Brókeres (BRIM) para importar tus transacciones paso a paso.

---

## 🚀 Guía Paso a Paso

1. Exporta un informe de transacciones desde tu bróker (generalmente un archivo CSV — consulta el centro de ayuda de tu bróker).
2. En LibreFolio, navega a la página **[Transacciones](../index.md)** .
3. Haz clic en el botón **Importar** (:material-file-upload:) en el encabezado de la página, o arrastra y suelta tu archivo de estado de cuenta directamente en la lista de transacciones.
4. Se abrirá el **Asistente de Importación**.
5. Revisa la vista previa — verifica que las fechas, montos y nombres de activos se vean correctos.
6. Haz clic en **Importar** para confirmar todas las transacciones.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Modal de Importación Rápida" alt="Modal de Importación Rápida">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Paso 1: Subir Archivo de Informe" alt="Asistente Paso 1">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Paso 2: Configuración del Analizador" alt="Asistente Paso 2">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Paso 3: Análisis" alt="Asistente Paso 3">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🔍 Paso 4: Resolución de Activos" alt="Asistente Paso 4">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Paso 4: Detección de Duplicados" alt="Detección de Duplicados">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Paso 5: Revisión de Transacciones en Etapa" alt="Revisión Masiva de Transacciones">
</div>

!!! tip "Creación de Brókeres y Activos Sobre la Marcha"

    Si el informe importado contiene una cuenta de bróker o activos que aún no están creados en LibreFolio, ¡no es necesario que salgas del flujo de importación! El asistente te guiará para crear los **[Brókeres](../../brokers/index.md)** y **[Activos](../../assets/index.md)** faltantes sobre la marcha, completando previamente los detalles desde el estado de cuenta.

!!! tip "También puedes usar la sección Archivos"

    La sección **[Archivos](../../files/index.md)** (pestaña BRIM) te permite gestionar los informes de bróker subidos de forma centralizada, reimportarlos o eliminarlos.

---

## 🧙 Pasos del Asistente de Importación

El asistente guiado contiene 5 pasos operativos diseñados para analizar, validar, resolver e importar tu historial de transacciones de forma segura.

### 🧙 Paso 1: Subir Archivo de Informe

Este paso acepta informes CSV, XLSX o PDF exportados desde tu bróker. Puedes seleccionar archivos manualmente o arrastrarlos y soltarlos directamente en el asistente.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Asistente Paso 1: Subir" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⚙️ Paso 2: Configuración del Analizador

El sistema detecta automáticamente el formato del bróker (ej. Degiro, Directa, Interactive Brokers). Si subes una hoja de cálculo genérica, puedes usar el analizador **CSV Genérico** para mapear manualmente tus columnas (fecha, tipo, cantidad, activo, efectivo neto) a los campos de LibreFolio.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Asistente Paso 2: Configuración del Analizador" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🧠 Paso 3: Análisis y Procesamiento

El sistema procesa los archivos, validando fechas, números y monedas. Verás una barra de progreso que indica la velocidad y el estado del procesamiento. Una vez que el análisis se complete, cualquier advertencia o error en el procesamiento se resumirá antes de continuar.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Asistente Paso 3: Análisis" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Al final del procesamiento, la tabla muestra un resumen del procesamiento de cada archivo con las siguientes columnas estadísticas marcadas por emojis:

| Emoji / Columna | Nombre de la Métrica | Significado y Reglas de Población |
| :--- | :--- | :--- |
| `📊` | **Transacciones** | El número total de transacciones financieras leídas e identificadas dentro del archivo. |
| `🏦` | **Activos Identificados** | El número de instrumentos financieros (acciones, ETFs, etc.) encontrados dentro de las transacciones procesadas. |
| `✗` | **Activos No Resueltos** | El número de instrumentos en el archivo que no se encontraron en la base de datos de LibreFolio (marcado en rojo si > 0, requiere mapeo en el Paso 4). |
| `🔴` | **Problemas de Validación** | Errores formales detectados en los datos (ej. formatos inválidos, fechas incorrectas, datos obligatorios faltantes). |
| `🔧` | **Acción Requerida (PENDIENTES)** | Campos o atributos que requieren atención (rojo si bloquean, naranja para acciones de nivel de advertencia/información). No son necesariamente errores: simplemente indican datos faltantes que no se pueden extraer automáticamente solo del estado de cuenta, y que puedes completar fácilmente de forma manual en el formulario de transacciones masivas al final del asistente. |
| `⚠️` | **Advertencias** | Notificaciones generales o mensajes de advertencia generados por el analizador durante el procesamiento. |

### 🔍 Paso 4: Mapeo de Activos y Detección de Duplicados

Esta es la fase de conciliación. El asistente realiza dos comprobaciones principales:

#### 🗂️ Resolución de Activos

Si el estado de cuenta contiene símbolos de cotización o ISIN que no están en tu biblioteca, el asistente los marca. Puedes:

- Mapearlos a un activo existente en tu base de datos.
- Crearlos **sobre la marcha** directamente dentro del asistente.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Asistente Paso 4: Resolución de Activos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### ⚠️ Detección de Duplicados

El sistema compara las entradas procesadas con tu base de datos para encontrar posibles duplicados basándose en el tipo, fecha, monto, cantidad y descripción.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Asistente Paso 4: Detección de Duplicados" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Los duplicados se marcan en la interfaz de usuario usando dos insignias de estado basadas en 4 niveles de confianza:

| Insignia UI | Nivel de Confianza | Criterios / Reglas de Coincidencia |
| :--- | :--- | :--- |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ PROBABLE</span> | `LIKELY_WITH_ASSET` | Los campos básicos y la descripción coinciden, y el activo se resolvió automáticamente (duplicado altamente probable). |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ PROBABLE</span> | `LIKELY` | Los campos básicos y la descripción coinciden, pero el activo no está resuelto. |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSIBLE</span> | `POSSIBLE_WITH_ASSET` | Los campos básicos coinciden y el activo se resolvió automáticamente (pero la descripción difiere o está vacía). |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSIBLE</span> | `POSSIBLE` | Los campos básicos (tipo, fecha, cantidad, monto) coinciden, pero el activo no está resuelto. |
| <span style="background-color: rgba(16, 185, 129, 0.15); color: #10b981; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">✅ ÚNICO</span> | — | La transacción no tiene registros coincidentes en la base de datos y se clasifica como nueva (no se detectó duplicado). |
| <span style="background-color: rgba(239, 68, 68, 0.15); color: #ef4444; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">❌ NO RESUELTO</span> | — | El bróker o instrumento financiero no coincidió con una entidad existente en la base de datos (requiere resolución en el Paso 4 antes de importar). |

Por defecto, el asistente desmarca automáticamente los duplicados "Probables" para evitar la doble entrada, pero puedes anular esta elección.

### 📦 Paso 5: Revisión de Transacciones en Etapa

La revisión final muestra la lista procesada en una cuadrícula similar a una hoja de cálculo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Asistente Paso 5: Revisión Masiva de Transacciones" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La tabla muestra:

- **Fecha**: La fecha de ejecución.
- **Tipo**: COMPRA, VENTA, DIVIDENDO, DEPÓSITO, etc.
- **Activo**: El activo coincidente de tu biblioteca.
- **Cantidad**: El número de unidades/acciones.
- **Precio**: El precio unitario.
- **Monto Neto**: El impacto total en efectivo.
- **Comisiones/Impuestos**: Comisiones e impuestos incluidos.

Haz clic en **Importar** para finalizar la importación y escribir las transacciones en tu libro mayor.
