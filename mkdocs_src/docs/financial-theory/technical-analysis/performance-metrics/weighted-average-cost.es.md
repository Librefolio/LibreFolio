# 📊 Coste Medio Ponderado (WAC)

## 💡 ¿Qué es el WAC?

El **Coste Medio Ponderado** (WAC, por sus siglas en inglés *Weighted Average Cost*) es el coste unitario promedio de un activo en una cartera, ponderado por la cantidad adquirida a cada precio.

Responde a la pregunta: _"En promedio, ¿cuánto pagué por unidad de este activo?"_

!!! info "Otros nombres"

    - **PMC** — Prezzo Medio di Carico (Italia)
    - **ACB** — Average Cost Basis (Canadá, EE. UU.)
    - **CMP** — Coût Moyen Pondéré (Francia)

## 🧮 Fórmula

El WAC se calcula de forma **iterativa** a medida que se procesa cada transacción cronológicamente:

$$
WAC_{new} = \frac{WAC_{current} \times Q_{pool} + Cost_{unit} \times Q_{tx}}{Q_{pool} + Q_{tx}}
$$

Donde:

- $WAC_{current}$ = coste medio ponderado actual antes de esta transacción
- $Q_{pool}$ = cantidad total mantenida en el pool antes de esta transacción
- $Cost_{unit}$ = coste de adquisición por unidad de la nueva transacción
- $Q_{tx}$ = cantidad añadida por la nueva transacción

## ⚙️ Cómo calcula LibreFolio el WAC

LibreFolio utiliza un **algoritmo iterativo consciente del inventario** que procesa todas las transacciones cualificadas para un par (bróker, activo) determinado en orden cronológico.

### 🏷️ Efectos de las Transacciones

Cada transacción contribuye al cálculo del WAC de una de estas formas:

| Efecto | Condición | Impacto en el WAC |
|--------|-----------|---------------|
| **Ponderado** | `qty > 0` y `unit_cost > 0` | El WAC se desplaza hacia el nuevo coste de adquisición |
| **Cantidad reducida** | `qty < 0` | Salidas al WAC actual — WAC sin cambios, el pool disminuye |
| **Dilución** | `qty > 0` pero `unit_cost = 0` | El pool crece, el numerador no cambia → el WAC **disminuye** |
| **Auto WAC** | `qty > 0`, `cost_basis_mode = "auto"` | Pool sin cambios — las unidades entran al WAC actual |

### 📅 Orden del Mismo Día

Cuando ocurren múltiples transacciones en la misma fecha:

1. **Primero las adiciones** (qty > 0) — se procesan antes que las reducciones
2. **Segundo las reducciones** (qty < 0) — asegura que el pool no se vuelva transitoriamente negativo

### 🔻 Agotamiento del Pool

- Cuando `new_qty = 0`: el WAC se restablece a 0 (posición cerrada)
- Cuando `new_qty < 0` (caso límite de redondeo): se limita a 0

## 📝 Ejemplos Prácticos

??? example "Ejemplo 1: Dos compras — el WAC sube"

    | Fecha | Tipo | Cant. | Coste Unitario | Cant. Pool | WAC |
    |------|------|-----|-----------|----------|-----|
    | 1 abr | COMPRA | 10 | $150 | 10 | $150.00 |
    | 15 abr | COMPRA | 5 | $180 | 15 | $160.00 |

    $$
    WAC = \frac{150 \times 10 + 180 \times 5}{10 + 5} = \frac{2400}{15} = 160.00
    $$

    La segunda compra a un precio más alto **eleva el WAC**.

??? example "Ejemplo 2: Compra y luego Venta — WAC sin cambios"

    | Fecha | Tipo | Cant. | Coste Unitario | Cant. Pool | WAC |
    |------|------|-----|-----------|----------|-----|
    | 1 abr | COMPRA | 10 | $150 | 10 | $150.00 |
    | 15 abr | VENTA | -5 | (al WAC) | 5 | $150.00 |

    La VENTA elimina unidades al WAC actual ($150). El WAC permanece **sin cambios**; solo disminuye el pool.

??? example "Ejemplo 3: Adquisición de Coste Cero — Dilución"

    | Fecha | Tipo | Cant. | Coste Unitario | Cant. Pool | WAC |
    |------|------|-----|-----------|----------|-----|
    | 1 abr | COMPRA | 10 | $150 | 10 | $150.00 |
    | 1 may | AJUSTE | +5 | $0 | 15 | $100.00 |

    $$
    WAC = \frac{150 \times 10 + 0 \times 5}{10 + 5} = \frac{1500}{15} = 100.00
    $$

    El WAC se **diluye** porque 5 unidades entraron con coste cero (p. ej., división de acciones, airdrop, regalo).

## 🔄 Anulación de la Base de Coste (Cost Basis Override)

Para transferencias y ajustes, LibreFolio admite una **anulación de la base de coste**: un coste unitario especificado por el usuario que representa el coste histórico de las unidades transferidas.

**Cuando está configurado (modo manual):**

- La transacción entra en el cálculo del WAC como una adquisición ponderada normal
- Esto preserva la continuidad del coste entre brókers (p. ej., al transferir del bróker A al bróker B)

**Cuando no está configurado (sin modo especificado):**

- La transacción entra con `unit_cost = 0` (efecto de dilución)
- Esto es apropiado para divisiones de acciones, regalos o airdrops donde no existe un precio de compra

**Cuando el modo auto está activo (`cost_basis_mode = "auto"`):**

- La transacción entra al **WAC actual del pool** — el WAC permanece algebraicamente sin cambios
- Esto es apropiado para transferencias o ajustes donde la base de coste debe heredarse del pool del bróker de origen

$$
WAC_{new} = \frac{WAC \times Q_{pool} + WAC \times Q_{tx}}{Q_{pool} + Q_{tx}} = WAC
$$

!!! tip "Auto WAC en la interfaz de usuario"

    En el formulario de transacciones, el interruptor "Auto" utiliza este modo. La tabla de cualificación muestra la etiqueta de efecto **Auto WAC** (o **Auto PMC** en italiano), indicando que las unidades entraron al coste actual del pool sin alterar el WAC.

??? example "Ejemplo 4: Transferencia en Modo Auto — WAC sin cambios"

    | Fecha | Tipo | Cant. | Coste Unitario | Cant. Pool | WAC |
    |------|------|-----|-----------|----------|-----|
    | 1 abr | COMPRA | 10 | $150 | 10 | $150.00 |
    | 15 abr | COMPRA | 5 | $180 | 15 | $160.00 |
    | 1 may | TRANSFERENCIA (auto) | +3 | $160 (=WAC) | 18 | $160.00 |

    $$
    WAC = \frac{160 \times 15 + 160 \times 3}{15 + 3} = \frac{2880}{18} = 160.00
    $$

    El receptor de la transferencia en **modo auto** hereda el WAC actual como su coste unitario. El pool crece, pero el WAC permanece **sin cambios**.

## 🌍 Gestión Multi-divisa

Cuando una cartera contiene adquisiciones en diferentes divisas, LibreFolio:

1. Determina la **divisa objetivo** (la más frecuente entre las adquisiciones)
2. Convierte todos los costes unitarios a la divisa objetivo utilizando los tipos de cambio FX históricos
3. Calcula el WAC en la divisa objetivo unificada

!!! warning "Disponibilidad de Tipos de Cambio FX"

    Si falta un tipo de cambio FX requerido, el cálculo del WAC puede quedar incompleto. La interfaz de usuario advierte sobre los pares FX faltantes y proporciona acciones rápidas para añadirlos o sincronizarlos.

## 🎯 Dónde se utiliza el WAC en LibreFolio

- **Formulario de transferencia**: sugiere automáticamente el `cost_basis_override` para transferencias salientes
- **Cálculo de P&L**: ganancias realizadas = precio_venta − WAC (FIFO en tiempo de ejecución, WAC para la base de coste)
- **Vista de cartera**: precio medio de entrada por posición
