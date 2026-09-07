# 📥 Transacciones del bróker

La pestaña **Transacciones** es el centro de control para modificar el libro mayor del bróker. Enumera todas las operaciones financieras registradas (compras, ventas, dividendos, depósitos, retiros, transferencias y conversiones de divisa) acotadas a este bróker.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="transactions-tab" alt="Broker Transactions Tab">
</div>

Desde esta pestaña, puedes registrar transacciones manualmente o iniciar importaciones masivas de estados de cuenta.

---

## ➕ Transacciones manuales

Haz clic en el botón **Agregar Transacción** (ícono `Plus`) para abrir el asistente modal de transacción individual. Esto te permite registrar manualmente:

- **Compra / Venta**: Negociar activos, especificando fecha, precio, cantidad y moneda.
- **Dividendo / Ingreso**: Ingresos recibidos por tenencias de activos.
- **Depósito / Retiro**: Entradas o salidas de efectivo externas hacia/desde el saldo de efectivo del bróker.
- **Transferencia**: Transferencia de efectivo o activos entre brókeres (p. ej., aportar fondos a la cuenta desde un bróker bancario).
- **Conversión de divisa**: Intercambios de divisas dentro de la cuenta del bróker.

Para una explicación detallada de los campos de transacción y las reglas de validación, consulta la guía **[Formulario de Transacción](../transactions/form.md)**.

---

## 🧙 Importación masiva (BRIM)

El botón **Importar** (ícono `Upload`) abre el asistente **BRIM** (Módulo de Importación de Reportes de Bróker), que importa de forma masiva los estados de cuenta exportados por tu bróker: analiza los archivos, valida cada fila, unifica los valores encontrados, detecta duplicados y te permite revisarlo todo antes de que se escriba nada. Las filas aprobadas terminan en el **editor masivo**, donde un **Guardar Todo** final las confirma en el libro mayor.

El mismo asistente también está disponible desde la página global de **[Transacciones](../transactions/index.md)**. Para ver el recorrido completo, consulta las guías dedicadas:

- 📥 **[Importar desde el bróker (BRIM)](../transactions/import/index.md)** — brókeres compatibles, formatos y notas por plugin.
- 🧙 **[Cómo Importar Transacciones](../transactions/import/how-to.md)** — el asistente, paso a paso.

---

## 🧩 ¿Te falta tu bróker?

Si tu bróker aún no tiene un plugin de importación, puedes ayudar:

- **Solicitar un plugin** — abre una [solicitud de plugin](https://github.com/Librefolio/LibreFolio/issues/new?template=plugin_request.yml) en GitHub, adjuntando una muestra anonimizada del archivo de exportación del bróker para que se pueda entender el formato. (El paso de Correcciones del asistente también incluye un banner "abrir un issue" para reportar filas que parezcan incorrectas.)
- **Escribir un plugin** — la [Guía de Plugins BRIM](../../developer/architecture/patterns/brim_plugin_guide.md) orienta a los desarrolladores a través del contrato del proveedor; consulta [Contribuir](../../community/contribute.md) para el flujo de trabajo general.

---

## 🗂️ Reportes subidos

Haz clic en el botón **Reportes subidos** (ícono `FileText`) para gestionar los archivos de reportes BRIM almacenados para este bróker. El modal te permite:

- Revisar los reportes subidos (nombre, fecha de subida, tamaño, estado), con una **vista previa** rápida del contenido de cada archivo.
- **Subir** nuevos reportes directamente — se asignan automáticamente a este bróker y quedan disponibles en el paso Seleccionar Archivos del asistente.
- **Eliminar** los reportes que ya no necesites.
- Ir a la página completa de **[Archivos y Subidas](../files/index.md#broker-reports)**, prefiltrada por este bróker.
