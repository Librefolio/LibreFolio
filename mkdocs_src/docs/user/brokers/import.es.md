# 📥 Transacciones del bróker

La pestaña **Transacciones** es el centro de control para modificar el libro de contabilidad del bróker. Enumera todas las operaciones financieras registradas (compras, ventas, dividendos, depósitos, retiros, transferencias y conversiones FX) limitadas a este bróker.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="transactions-tab" alt="Pestaña de Transacciones del Bróker">
</div>

Desde esta pestaña, puede realizar transacciones manuales o iniciar importaciones masivas de extractos.

---

## ➕ Transacciones Manuales

Haga clic en el botón **Agregar Transacción** (icono `Plus`) para abrir el asistente modal de transacción única. Esto le permite registrar manualmente:

- **Compra / Venta**: Comerciar activos, especificando fecha, precio, cantidad y moneda.
- **Dividendo / Ingreso**: Ingresos recibidos de las tenencias de activos.
- **Depósito / Retiro**: Entradas o salidas de efectivo externas con origen o destino en el saldo de efectivo del bróker.
- **Transferencia**: Transferencia de efectivo o activos entre brókers (ej. financiar la cuenta desde un bróker bancario).
- **Conversión FX**: Intercambios de moneda dentro de la cuenta del bróker.

Para una explicación detallada de los campos de transacción y las reglas de validación, consulte la guía **[Formulario de Transacción](../transactions/form.md)**.

---

## 🧙 BRIM: Módulo de Importación de Extractos del Bróker

El botón **Importar** (icono `Upload`) inicia el asistente **BRIM**. Este módulo le permite importar los extractos exportados de su bróker (formatos CSV o Excel) de forma masiva, ejecutar validaciones automáticas de cordura y mapear tickers a activos locales antes de la confirmación final.

### El Flujo de Importación

<div class="lf-screenshot-carousel" data-carousel="carousel-broker-import" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Modal de Importación Rápida" alt="Modal de Importación">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Asistente — Paso 1: Carga" alt="Asistente de Importación Paso 1">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Asistente — Paso 2: Config. del Analizador" alt="Asistente de Importación Paso 2">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Asistente — Paso 3: Análisis" alt="Asistente de Importación Paso 3">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🔍 Asistente — Paso 4: Resolución de Activos" alt="Resolución de Activos del Asistente de Importación">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Detección de Duplicados" alt="Detección de Duplicados del Asistente de Importación">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Preparación Masiva" alt="Preparación Masiva de Importación">
</div>

El asistente avanza a través de los siguientes pasos:

1. **Seleccionar Archivo y Analizador**: Elija el archivo de extracto y seleccione la configuración de analizador adecuada (ej. Interactive Brokers, Degiro, Directa, Charles Schwab, CSV genérico, etc.).
2. **Verificar Encabezados y Mapeo**: Muestra los encabezados CSV para confirmar que el analizador se alinea correctamente con las columnas.
3. **Análisis de Operaciones**: Procesa el archivo y muestra una cuadrícula de vista previa de las operaciones analizadas (Compras, Ventas, Dividendos, etc.).
 * **Insignias**: Las operaciones se etiquetan como `UNIQUE` (nueva operación), `DUPLICATE` (ya existe en la base de datos) o `UNRESOLVED` (requiere mapeo de ticker/ISIN).
 * **Notas TODO**: Resaltan campos que requieren atención o elementos que no pudieron analizarse automáticamente.
4. **Resolución de Activos**: Si el extracto contiene tickers o ISINs que no existen en su registro de activos local, BRIM muestra un paso de mapeo. Puede:
 * Mapear el ticker a un activo existente.
 * Crear un nuevo activo directamente desde esta pantalla, prellenado con los detalles extraídos del extracto.
5. **Preparación Masiva y Confirmación**: Revise la lista de verificación preparada de transacciones limpias y únicas. Desmarque cualquier operación que desee excluir, luego haga clic en **Confirmar** para escribir los registros en su libro de contabilidad de cartera.

---

## 📑 Historial de Importaciones

Haga clic en el botón **Mostrar Historial de Importaciones** (icono `FileText`) para ver un registro completo de tareas de importación anteriores. Muestra:

- Nombre y tamaño del archivo cargado.
- Filas procesadas y transacciones totales confirmadas.
- Marca de tiempo de carga.
- Usuario que realizó la importación.
