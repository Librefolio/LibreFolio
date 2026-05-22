# 📊 Costo Promedio Ponderado (WAC)

## 💡 ¿Qué es el WAC?

El **Costo Promedio Ponderado** (WAC, por sus siglas en inglés *Weighted Average Cost*) es el costo unitario promedio de un activo en una cartera, ponderado por la cantidad adquirida a cada precio.

Responde a la pregunta: _"En promedio, ¿cuánto pagué por unidad de este activo?"_

!!! info "Other names"

    - **PMC** — Prezzo Medio di Carico (Italia)
    - **ACB** — Average Cost Basis (Canadá, EE. UU.)
    - **CMP** — Coût Moyen Pondéré (Francia)

## 🧮 Fórmula

El WAC se computa de forma **iterativa** a medida que se procesa cada transacción cronológicamente:

$$
WAC_{new} = \frac{WAC_{current} \times Q_{pool} + Cost_{unit} \times Q_{tx}}{Q_{pool} + Q_{tx}}
$$

Donde:

- $WAC_{current}$ = costo promedio ponderado actual antes de esta transacción
- $Q_{pool}$ = cantidad total mantenida en el pool antes de esta transacción
- $Cost_{unit}$ = costo de adquisición por unidad de la nueva transacción
- $Q_{tx}$ = cantidad añadida por la nueva transacción

## ⚙️ Cómo computa LibreFolio el WAC

LibreFolio utiliza un **algoritmo iterativo consciente del inventario** que procesa todas las transacciones calificadas para un par dado (bróker, activo) en orden cronológico.

### 🏷️ Efectos de las Transacciones

Cada transacción contribuye al cálculo del WAC de una de estas formas:

| Efecto | Condición | Impacto en el WAC |
|--------|-----------|-------------------|
| **Ponderado** | `qty > 0` y `unit_cost > 0` | El WAC se desplaza hacia el nuevo costo de adquisición |
| **Cantidad reducida** | `qty < 0` | Salidas al WAC actual — WAC sin cambios, el pool se reduce |
| **Dilución** | `qty > 0` pero `unit_cost = 0` | El pool crece, el numerador no cambia → el WAC **disminuye** |

### 📅 Orden del mismo día

Cuando ocurren múltiples transacciones en la misma fecha:

1. **Adiciones primero** (qty > 0) — procesadas antes que las reducciones
2. **Reducciones segundo** (qty < 0) — asegura que el pool no se vuelva negativo transitoriamente

### 🔻 Agotamiento del Pool

- Cuando `new_qty = 0`: el WAC se restablece a 0 (posición cerrada)
- Cuando `new_qty < 0` (caso límite de redondeo): se ajusta a 0

## 📝 Ejemplos Prácticos

??? example "Example 1: Two Buys — WAC rises"

 | Fecha | Tipo | Cant. | Costo Unitario | Cant. Pool | WAC |
 |------|------|-----|-----------|----------|-----|
 | 1 abr | BUY | 10 | $150 | 10 | $150.00 |
 | 15 abr | BUY | 5 | $180 | 15 | $160.00 |

 $$
 WAC = \frac{150 \times 10 + 180 \times 5}{10 + 5} = \frac{2400}{15} = 160.00
 $$

 La segunda compra a un precio más alto **eleva el WAC**.

??? example "Example 2: Buy then Sell — WAC unchanged"

 | Fecha | Tipo | Cant. | Costo Unitario | Cant. Pool | WAC |
 |------|------|-----|-----------|----------|-----|
 | 1 abr | BUY | 10 | $150 | 10 | $150.00 |
 | 15 abr | SELL | -5 | (al WAC) | 5 | $150.00 |

 La venta (SELL) elimina unidades al WAC actual ($150). El WAC permanece **sin cambios**; solo el pool se reduce.

??? example "Example 3: Zero-Cost Acquisition — Dilution"

 | Fecha | Tipo | Cant. | Costo Unitario | Cant. Pool | WAC |
 |------|------|-----|-----------|----------|-----|
 | 1 abr | BUY | 10 | $150 | 10 | $150.00 |
 | 1 may | ADJUSTMENT | +5 | $0 | 15 | $100.00 |

 $$
 WAC = \frac{150 \times 10 + 0 \times 5}{10 + 5} = \frac{1500}{15} = 100.00
 $$

 El WAC se **diluye** porque ingresaron 5 unidades a costo cero (ej. división de acciones, airdrop, regalo).

## 🔄 Anulación del Costo Base (Cost Basis Override)

Para transferencias y ajustes, LibreFolio admite una **anulación del costo base** (`cost basis override`): un costo unitario especificado por el usuario que representa el costo histórico de las unidades transferidas.

**Cuando se define:**

- La transacción entra en el cálculo del WAC como una adquisición ponderada normal
- Esto preserva la continuidad del costo entre brókeres (ej. al transferir del bróker A al bróker B)

**Cuando no se define:**

- La transacción ingresa con `unit_cost = 0` (efecto de dilución)
- Esto es apropiado para divisiones de acciones, regalos o airdrops donde no existe un precio de compra

## 🌍 Manejo Multidivisa

Cuando una cartera contiene adquisiciones en diferentes monedas, LibreFolio:

1. Determina la **moneda objetivo** (la más frecuente entre las adquisiciones)
2. Convierte todos los costos unitarios a la moneda objetivo utilizando tipos de cambio FX históricos
3. Computa el WAC en la moneda objetivo unificada

!!! warning "FX Rate Availability"

    Si falta un tipo de cambio FX requerido, el cálculo del WAC puede estar incompleto. La interfaz de usuario advierte sobre los pares FX faltantes y proporciona acciones rápidas para agregarlos o sincronizarlos.

## 🎯 Dónde se utiliza el WAC en LibreFolio

- **Formulario de transferencia**: sugiere automáticamente el `cost_basis_override` para transferencias salientes
- **Cálculo de P&L**: ganancias realizadas = precio_venta − WAC (FIFO en tiempo de ejecución, WAC para el costo base)
- **Vista de cartera**: precio promedio de entrada por posición
