# 💸 Transacciones

Las transacciones son el **núcleo de LibreFolio**: cada compra, venta, dividendo, comisión, transferencia y movimiento de efectivo que registres vive aquí. Cada bróker tiene su propia lista de transacciones, accesible desde la página de detalle del bróker.

## 📋 Tabla de Transacciones

La tabla de transacciones muestra todos los movimientos de un bróker en orden cronológico inverso. Cada fila muestra:

| Columna | Descripción |
|--------|-------------|
| **Fecha** | Fecha de ejecución de la transacción |
| **Tipo** | Icono + etiqueta: BUY, SELL, DIVIDEND, FEE, TRANSFER, etc. |
| **Activo** | Nombre del activo vinculado (vacío para operaciones de efectivo) |
| **Cantidad** | Número de unidades compradas/vendidas/transferidas |
| **Precio** | Precio unitario en la ejecución |
| **Importe** | Valor total (cantidad × precio ± comisiones) |
| **Moneda** | Moneda de la transacción |
| **Notas** | Nota opcional del usuario |

### Ordenación y Filtrado

- Haz clic en cualquier **encabezado de columna** para ordenar de forma ascendente/descendente.
- Usa la **barra de búsqueda** para filtrar por nombre de activo, tipo o notas.
- Usa los botones de **filtro de tipo** para mostrar solo tipos de transacciones específicos.

---

## ➕ Añadir Transacciones

Haz clic en **+ Nueva transacción** para abrir el [Formulario de Transacción](form.md). Puedes:

- Crear una **transacción única** (un formulario por operación)
- Crear una **transacción masiva** a través del modal de importación masiva: pega o sube una tabla de filas

---

## ✏️ Editar y Eliminar

- Haz clic en cualquier fila para **abrir el formulario** prellenado con los datos de esa transacción.
- Haz clic en el **icono de papelera** (:material-delete:) para eliminar una transacción.
- Selecciona varias filas con la columna de **casillas de verificación**, luego usa la barra de herramientas para **eliminar en bloque**.

!!! warning "Las eliminaciones son permanentes"

    No hay opción de deshacer para las transacciones eliminadas. Exporta una copia de seguridad primero si no estás seguro.

---

## ✂️ División y Promover

Dos operaciones especiales están disponibles para **transacciones compuestas** (TRANSFER y FX_CONVERSION):

### División { #split }

Una **división** desglosa una transacción compuesta en sus dos partes constituyentes. Utiliza esto cuando una sola fila importada represente en realidad dos eventos separados (por ejemplo, un CSV de un bróker que registra una transferencia entre monedas como una sola línea).

1. Selecciona la fila de la transacción compuesta.
2. Haz clic en **Dividir** en la barra de herramientas de acciones.
3. LibreFolio la separa en dos transacciones independientes.

### Promover

**Promover** convierte un par de transacciones registradas individualmente (por ejemplo, un WITHDRAWAL del bróker A y un DEPOSIT en el bróker B) en un compuesto de **TRANSFER** vinculado. Esta es la forma estándar de registrar un movimiento de activos entre tus propios brókers.

1. Selecciona **exactamente dos transacciones** de tipos compatibles.
2. Haz clic en **Promover** en la barra de herramientas.
3. LibreFolio valida la compatibilidad (mismo activo, direcciones opuestas, cantidad coincidente) y las vincula.

---

## 📊 WAC — Coste Medio Ponderado

La tabla de transacciones integra el **WAC (Weighted Average Cost)** en línea. Cuando añades o editas un BUY/SELL:

- Una **vista previa del WAC** aparece en el formulario mostrando la base de coste proyectada antes de guardar.
- Después de guardar, las filas que afectan a la base de coste se marcan con un **indicador ⚡**.
- El WAC se calcula en tiempo de ejecución utilizando reglas FIFO/WAC; no es necesario ningún paso separado.

Consulta [Teoría Financiera → Coste Medio Ponderado](../../financial-theory/portfolio-theory/weighted-average-cost.md) para conocer la metodología subyacente.

---

## 📥 Importar desde Bróker (BRIM)

En lugar de introducir las transacciones manualmente, puedes importar directamente desde el archivo de exportación de tu bróker. Consulta **[Importar desde Bróker](import/index.md)** para obtener la guía paso a paso.

---

## 🔗 Relacionados

- 📝 **[Formulario de Transacción](form.md)** — Campos, validación y opciones específicas por tipo
- 📥 **[Importar desde Bróker](import/index.md)** — Flujo de trabajo de importación BRIM
- 📖 **[Tipos de Transacción](../../financial-theory/instruments/transaction-types/index.md)** — Teoría financiera detrás de cada tipo
