# 📥 Transacciones del bróker

La pestaña **Transacciones** de un bróker enumera todas sus transacciones, las más recientes primero. Siempre muestra todo el historial del bróker: el rango de fechas de la barra de herramientas no filtra la lista.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="transactions-tab" alt="Pestaña Transacciones del bróker">
</div>

Por encima de la lista encontrarás **Informes subidos**, **Ver en Transacciones** y el selector de columnas. Los propietarios y editores también disponen de **Importar** y **Añadir transacción**.

---

## ➕ Añadir una transacción

1. Haz clic en **Añadir transacción**. El espacio de trabajo de transacciones se abre en un formulario **Nueva transacción**, con este bróker ya seleccionado.
2. Elige el **Tipo** y completa los campos obligatorios — consulta [Formulario de transacción](../transactions/form.md).
3. Haz clic en **Aplicar** para colocar la fila en el espacio de trabajo, y luego en **Guardar todo** para escribirla.

No se guarda nada antes de **Guardar todo**: hasta entonces puedes añadir más filas, cambiarlas o cancelar (consulta [El espacio de trabajo masivo](../transactions/index.md#bulk-workspace)).

---

## 🔎 Abrir, editar o eliminar transacciones

- **Haz doble clic** en una fila para abrirla en modo solo lectura.
- Para editar, clonar o eliminar filas, haz clic en **Ver en Transacciones**: se abre la página [Transacciones](../transactions/index.md), filtrada por este bróker y por los filtros de columna que establezcas aquí.

---

## 🧙 Importar un extracto

**Importar** abre el espacio de trabajo junto con el **Asistente de importación** (BRIM, el módulo de importación de informes del bróker). El asistente lee los archivos exportados por tu bróker, te permite revisar cada fila y entrega el resultado al espacio de trabajo: no se escribe nada hasta **Guardar todo**.

- 📥 **[Importar desde bróker](../transactions/import/index.md)** — brókers y formatos compatibles.
- 🧙 **[Cómo importar transacciones](../transactions/import/how-to.md)** — el asistente, paso a paso.

El mismo asistente se abre desde **Importar** en la página [Transacciones](../transactions/index.md).

??? tip "🧩 Tu bróker aún no es compatible — qué puedes hacer"

    - **Solicitar un plugin**: abre una [solicitud de plugin](https://github.com/Librefolio/LibreFolio/issues/new?template=plugin_request.yml) en GitHub y adjunta una muestra anonimizada de la exportación del bróker.
    - **Escribir un plugin**: la [Guía de plugins de BRIM](../../developer/architecture/patterns/brim_plugin_guide.md) explica el contrato de plugins, y en [Contribuir](../../community/contribute.md) se describe el flujo de trabajo.
    - Si las filas importadas siguen viéndose mal, el paso **Correcciones** del asistente enlaza a GitHub para que puedas informar de un posible error del importador.

---

## 🗂️ Informes subidos

**Informes subidos** abre los archivos de informes almacenados para este bróker:

- **Subir** archivos CSV o Excel: se asignan a este bróker y aparecen en el paso **Seleccionar archivos** del asistente. Los archivos que subes juntos forman un conjunto — así se importan bancos que dividen una cuenta en varias exportaciones, como Danske Bank.
- **Previsualizar** o **Eliminar** un archivo. Eliminar un informe nunca elimina las transacciones importadas de él.
- Comprueba las insignias **Estado** y **Conjunto de informes** de cada archivo — consulta [Conjuntos de informes](../files/index.md#report-sets).
- **Gestionar todos los archivos** abre la página [Archivos y subidas](../files/index.md#broker-reports), filtrada por este bróker.

Subir y eliminar informes requiere acceso de propietario o editor al bróker.
