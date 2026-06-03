# 📝 Formulario de Transacciones

El Formulario de Transacciones se abre siempre que **creas** o **editas** una transacción. Se adapta dinámicamente al tipo de transacción seleccionado, mostrando únicamente los campos relevantes para esa operación.

---

## 🏷️ Tipos de Transacciones

| Tipo | Icono | Descripción |
|------|------|-------------|
| **BUY** | 🟢 | Compra de un activo |
| **SELL** | 🔴 | Venta de un activo |
| **DIVIDEND** | 💰 | Dividendo en efectivo recibido |
| **INTEREST** | 📈 | Ingresos por intereses (bonos, P2P) |
| **FEE** | 💸 | Comisión del bróker o cargo de plataforma |
| **DEPOSIT** | ⬇️ | Efectivo depositado en la cuenta del bróker |
| **WITHDRAWAL** | ⬆️ | Efectivo retirado de la cuenta del bróker |
| **ADJUSTMENT** | 🔧 | Corrección manual de cantidad o precio |
| **TRANSFER** | 🔄 | Activo movido entre dos brókeres (compuesta) |
| **FX_CONVERSION** | 💱 | Cambio de moneda dentro de un bróker (compuesta) |

Consulte [Teoría Financiera → Tipos de Transacciones](../../financial-theory/instruments/transaction-types/index.md) para obtener la definición conceptual de cada tipo.

---

## 📋 Campos Comunes

Estos campos aparecen en **todos** los tipos de transacciones:

| Campo | Requerido | Descripción |
|-------|:--------:|-------------|
| **Type** | ✅ | Selector del tipo de transacción |
| **Date** | ✅ | Fecha de ejecución (AAAA-MM-DD) |
| **Currency** | ✅ | Moneda de la transacción |
| **Amount** | ✅ | Monto bruto total |
| **Fee** | ❌ | Comisión del bróker o impuesto retenido |
| **Notes** | ❌ | Nota de texto libre |

---

## 🏦 Operaciones con Activos (BUY / SELL / TRANSFER)

Cuando interviene un activo, aparecen campos adicionales:

| Campo | Requerido | Descripción |
|-------|:--------:|-------------|
| **Asset** | ✅ | El activo negociado (con búsqueda) |
| **Quantity** | ✅ | Número de unidades |
| **Unit Price** | ✅ | Precio por unidad |

!!! tip "Autocálculo"

    Si completa la **Quantity** y el **Unit Price**, el **Amount** se calcula automáticamente, y viceversa.

---

## 💰 Vista Previa del WAC

Para las transacciones **BUY** y **SELL**, aparece un panel de **vista previa del WAC (Weighted Average Cost)** debajo de los campos principales. Muestra en tiempo real:

- El **costo base actual** antes de esta transacción
- El **nuevo costo base proyectado** después de guardar
- La **ganancia/pérdida realizada** (solo para SELL)

Esta vista previa se calcula en vivo; no es necesario guardar primero.

!!! note "Anulación Manual del WAC"

    Puede cambiar el modo de WAC de **Auto** (calculado por LibreFolio) a **Manual** (ingrese su propio costo base). Esto es útil al migrar datos históricos desde otro sistema.

---

## 🔄 Transacciones Compuestas

**TRANSFER** y **FX_CONVERSION** son *compuestas*: vinculan dos etapas:

- **TRANSFER**: especifica un **bróker de origen** y un **bróker de destino**, además del activo y la cantidad. LibreFolio registra ambas etapas atómicamente.
- **FX_CONVERSION**: especifica el **monto de la moneda de origen** y el **monto de la moneda de destino** dentro del mismo bróker.

Para dividir una transacción compuesta nuevamente en dos transacciones independientes, utilice la operación [División](index.md#split) en la tabla de transacciones.

---

## ✅ Validación

El formulario se valida al guardar:

- Las fechas deben estar en un rango válido (por defecto, no en el futuro).
- La cantidad y el precio deben ser positivos.
- Para SELL: la cantidad no puede exceder la posición actual (advertencia, no es un bloqueo total).
- El monto debe coincidir con cantidad × precio dentro de una tolerancia pequeña.

---

## 🔗 Relacionados

- 📋 **[Tabla de Transacciones](index.md)** — Vista de lista, filtrado, operaciones masivas
- 📥 **[Importar desde Bróker](import/index.md)** — Evite la entrada manual con la importación BRIM
