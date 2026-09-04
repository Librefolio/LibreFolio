# 💸 Transacciones

Las transacciones representan cada actividad financiera dentro de su cartera. Cada compra, venta, dividendo, comisión, transferencia de activos y movimiento de efectivo se registra aquí para mantener actualizadas las estadísticas, el rendimiento y los registros fiscales de su cartera.

Cada cuenta de bróker en LibreFolio tiene su propio registro de transacciones dedicado, que muestra todos los movimientos en orden cronológico inverso.

<div class="screenshot-container">
 <img class="gallery-img" data-category="transactions" data-name="list" alt="Lista de Transacciones">
</div>

---

## 🚀 Primeros Pasos

Gestionar sus transacciones es sencillo:

* 📝 **Entrada Manual y Edición**: Abra el **[Formulario de Transacción](form.md)** interactivo para añadir, editar o ajustar manualmente operaciones individuales.
* 📥 **Importación de Bróker Muy Sencilla**: ¡No necesita escribir todo a mano! LibreFolio le permite cargar exportaciones en CSV o XLSX de su bróker y mapearlas e importarlas automáticamente en segundos. Obtenga más información en la guía de **[Importación desde Bróker](import/index.md)**.

---

## 🛠️ Características de la Página

Aquí tiene un resumen de las operaciones y herramientas disponibles directamente en la página de transacciones:

| Característica | Descripción | Referencia |
|---------|-------------|-----------|
| **Añadir y Editar** | Haga clic en **Añadir Transacción** para abrir el formulario, o haga clic en cualquier fila existente para editar sus detalles. | [Formulario de Transacción](form.md) |
| **Importación de Bróker** | Haga clic en **Importar** para subir un extracto de bróker e importar su historial automáticamente. | [Importación desde Bróker](import/index.md) |
| **Ordenación y Filtrado** | Haga clic en cualquier encabezado de columna para ordenar la lista. Use la barra de búsqueda para filtrar por nombre del activo, tipo o notas. | |
| **Eliminación y Acciones Masivas** | Haga clic derecho en cualquier fila para abrir el Menú Contextual para acciones rápidas. Eliminar una sola fila y marcar varias filas para eliminación masiva abren ambos el mismo **espacio de trabajo masivo**, donde las filas se preparan para su eliminación antes de confirmar; un socio vinculado (operación FX o tramo de transferencia) se prepara automáticamente junto con la fila elegida. | |

La duplicación funciona del mismo modo: **Clonar** desde el menú contextual prepara una copia en el espacio de trabajo masivo — manteniendo la **fecha original** (la clonación es la forma en que una fila histórica mal clasificada se corrige, por lo que la fecha debe sobrevivir) — donde la ajusta y la guarda.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="clone-flow" alt="Bulk workspace with a cloned transaction row">
</div>

| **Transacciones Compuestas y Promoción** | Vincule operaciones individuales en una **Transacción Compuesta** mediante **Promoción** para permitir un seguimiento y análisis más sofisticados, o divida una transacción compuesta de nuevo en operaciones individuales. | [Formulario de Transacción](form.md#composite-transactions) |

---

## 🔗 Relacionado

* 📝 **[Formulario de Transacción](form.md)** — Campos, validación y opciones específicas por tipo
* 📥 **[Importación desde Bróker](import/index.md)** — Flujo de trabajo de importación BRIM
* 📖 **[Tipos de Transacción](../../financial-theory/instruments/transaction-types/index.md)** — Teoría financiera detrás de cada tipo
