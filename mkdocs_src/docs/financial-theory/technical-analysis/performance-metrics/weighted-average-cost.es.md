# 📊 Precio Medio Ponderado (PMP)

## 💡 ¿Qué es el PMP?

El **Precio Medio Ponderado** (PMP) es el coste unitario medio de un activo en una cartera, ponderado por la cantidad adquirida a cada precio.

Responde a la pregunta: *"En promedio, ¿cuánto pagué por unidad de este activo?"*

!!! info "Otros nombres"

    - **PMC** — Prezzo Medio di Carico (Italia)
    - **ACB** — Average Cost Basis (Canadá, EE. UU.)
    - **CMP** — Coût Moyen Pondéré (Francia)

## 🧮 Fórmula

El PMP se calcula de forma **iterativa** a medida que cada transacción se procesa cronológicamente:

$$
WAC_{new} = \frac{WAC_{current} \times Q_{pool} + Cost_{unit} \times Q_{tx}}{Q_{pool} + Q_{tx}}
$$

Donde:

- $WAC_{current}$ = coste medio ponderado actual antes de esta transacción
- $Q_{pool}$ = cantidad total mantenida en el pool antes de esta transacción
- $Cost_{unit}$ = coste de adquisición por unidad de la nueva transacción
- $Q_{tx}$ = cantidad añadida por la nueva transacción

## ⚙️ Cómo Calcula LibreFolio el PMP

LibreFolio utiliza un **algoritmo iterativo consciente del inventario** que procesa todas las transacciones que califican para un par (bróker, activo) determinado en orden cronológico.

### 🏷️ Efectos de las Transacciones

Cada transacción contribuye al cálculo del PMP de una de estas maneras:

| Efecto | Condición | Impacto en el PMP |
|--------|-----------|---------------|
| **Ponderado** | `qty > 0` y `unit_cost > 0` | El PMP se aproxima al nuevo coste de adquisición |
| **Cantidad reducida** | `qty < 0` | Sale al PMP actual — El PMP no cambia, el pool se reduce |
| **Dilución** | `qty > 0` pero `unit_cost = 0` | El pool crece, el numerador no cambia → el PMP **disminuye** |
| **PMP automático** | `qty > 0`, `cost_basis_mode = "auto"` | El pool no cambia — las unidades entran al PMP actual |

### 📅 Ordenamiento del Mismo Día

Cuando ocurren múltiples transacciones en la misma fecha:

1. **Primero las adiciones** (qty > 0) — se procesan antes que las reducciones
2. **Segundo las reducciones** (qty < 0) — asegura que el pool no se vuelva transitoriamente negativo

### 🔻 Agotamiento del Pool

- Cuando `new_qty = 0`: el PMP se reinicia a 0 (posición cerrada)
- Cuando `new_qty < 0` (caso extremo de redondeo): se limita a 0

## 📝 Ejemplos Prácticos

??? example "Ejemplo 1: Dos Compras — el PMP aumenta"

 | Fecha | Tipo | Cantidad | Coste Unitario | Cantidad en Pool | PMP |
 |------|------|-----|-----------|----------|-----|
 | 1 Abr | BUY | 10 | $150 | 10 | $150.00 |
 | 15 Abr | BUY | 5 | $180 | 15 | $160.00 |

 $$
 WAC = \frac{150 \times 10 + 180 \times 5}{10 + 5} = \frac{2400}{15} = 160.00
 $$

 La segunda compra a un precio más alto **eleva el PMP**.

??? example "Ejemplo 2: Compra luego Venta — el PMP no cambia"

 | Fecha | Tipo | Cantidad | Coste Unitario | Cantidad en Pool | PMP |
 |------|------|-----|-----------|----------|-----|
 | 1 Abr | BUY | 10 | $150 | 10 | $150.00 |
 | 15 Abr | SELL | -5 | (al PMP) | 5 | $150.00 |

 La SELL elimina unidades al PMP actual ($150). El PMP permanece **sin cambios** — solo se reduce el pool.

??? example "Ejemplo 3: Adquisición de Coste Cero — Dilución"

 | Fecha | Tipo | Cantidad | Coste Unitario | Cantidad en Pool | PMP |
 |------|------|-----|-----------|----------|-----|
 | 1 Abr | BUY | 10 | $150 | 10 | $150.00 |
 | 1 May | ADJUSTMENT | +5 | $0 | 15 | $100.00 |

 $$
 WAC = \frac{150 \times 10 + 0 \times 5}{10 + 5} = \frac{1500}{15} = 100.00
 $$

 El PMP se **diluye** porque 5 unidades entraron a coste cero (por ejemplo, split de acciones, airdrop, regalo).

## 🔄 Anulación de la Base de Coste

Para transferencias y ajustes, LibreFolio admite una **anulación de la base de coste**: un coste unitario especificado por el usuario que representa el coste histórico de las unidades transferidas.

**Cuando está establecido (modo manual):**

- La transacción entra en el cálculo del PMP como una adquisición ponderada normal
- Esto preserva la continuidad del coste entre brókers (por ejemplo, al transferir del bróker A al bróker B)

**Cuando no está establecido (sin modo especificado):**

- La transacción entra con `unit_cost = 0` (efecto de dilución)
- Esto es apropiado para splits de acciones, regalos o airdrops donde no existe un precio de compra

**Cuando está en modo automático (`cost_basis_mode = "auto"`):**

- La transacción entra al **PMP actual del pool** — el PMP permanece algebraicamente sin cambios
- Esto es apropiado para transferencias o ajustes donde la base de coste debe heredarse del pool del bróker de origen

$$
WAC_{new} = \frac{WAC \times Q_{pool} + WAC \times Q_{tx}}{Q_{pool} + Q_{tx}} = WAC
$$

!!! tip "PMP Automático en la Interfaz de Usuario"

    En el formulario de transacciones, el interruptor "Automático" utiliza este modo. La tabla de calificación muestra la insignia de efecto **PMP Automático** (o **Auto PMC** en italiano), indicando que las unidades entraron al coste actual del pool sin alterar el PMP.

??? example "Ejemplo 4: Transferencia en Modo Automático — el PMP no cambia"

 | Fecha | Tipo | Cantidad | Coste Unitario | Cantidad en Pool | PMP |
 |------|------|-----|-----------|----------|-----|
 | 1 Abr | BUY | 10 | $150 | 10 | $150.00 |
 | 15 Abr | BUY | 5 | $180 | 15 | $160.00 |
 | 1 May | TRANSFER (auto) | +3 | $160 (=PMP) | 18 | $160.00 |

 $$
 WAC = \frac{160 \times 15 + 160 \times 3}{15 + 3} = \frac{2880}{18} = 160.00
 $$

 El receptor de la transferencia en **modo automático** hereda el PMP actual como su coste unitario. El pool crece pero el PMP permanece **sin cambios**.

## 🌍 Manejo de Múltiples Monedas

Cuando una cartera contiene adquisiciones en diferentes monedas, LibreFolio:

1. Determina la **moneda objetivo** (la más frecuente entre las adquisiciones)
2. Convierte todos los costes unitarios a la moneda objetivo utilizando tipos de cambio históricos
3. Calcula el PMP en la moneda objetivo unificada

!!! warning "Disponibilidad del Tipo de Cambio"

    Si falta un tipo de cambio requerido, el cálculo del PMP puede estar incompleto. La interfaz de usuario advierte sobre pares de divisas faltantes y proporciona acciones rápidas para añadirlos o sincronizarlos.

## 🎯 Dónde se Utiliza el PMP en LibreFolio

- **Base de coste**: $\text{CB}(a,b,t) = q(a,b,t) \times \text{PMP}(a,b,t) \times \text{fx}(\cdot)$
- **P&L realizado en SELL**: $\text{realized} = P_{\text{sell}} - q_{\text{sold}} \times \text{PMP}_{\text{pre-sell}}$
- **Descomposición del pool de efectivo**: SELL devuelve $C = q_{\text{sold}} \times \text{PMP}$ al Pool de Capital
- **Formulario de transferencia**: sugiere automáticamente la anulación de la base de coste para transferencias salientes

!!! warning "El PMP nunca se utiliza para la valoración de activos"

    El PMP es una construcción contable para la base de coste. La cadena de valoración para el valor de mercado utiliza: `MARKET_PRICE → LAST_BUY_PRICE → MISSING`. Ver [NAV](portfolio-engine/nav.md).

## ⚙️ Implementación: Alcance a Nivel de Posición

El PMP se mantiene **por posición** $(a, b)$ — es decir, por par (activo, bróker). El mismo activo mantenido en dos brókers tiene dos pools de PMP independientes.

$$
\text{PMP}(a, b_1, t) \neq \text{PMP}(a, b_2, t) \quad \text{en general}
$$

El motor calcula el PMP en línea durante el bucle diario de transacciones — no se necesitan consultas separadas a la base de datos. Esto logra un coste amortizado O(1) por transacción en lugar del coste O(N) de volver a consultar todo el historial.

### Ordenamiento de transacciones del mismo día

Dentro de la misma fecha, **las adiciones se procesan antes que las reducciones**:

$$
\text{BUY}_1, \text{BUY}_2, \ldots \quad \text{luego} \quad \text{SELL}_1, \text{SELL}_2, \ldots
$$

Esto evita cantidades negativas transitorias y asegura que SELL siempre lea el PMP correcto que incluye las BUY del mismo día.

## 🔗 Relacionado

- 🔬 **[Análisis de Lotes FIFO](fifo-engine/fifo-lot-analysis.md)** — Complemento por lote: rastrea cada lote de adquisición individualmente en lugar de combinarlos en un promedio
- 🔁 **[Compra y Venta](../../instruments/transaction-types/buy-sell.md)** — Transacciones que alimentan el pool del PMP
- 📈 **[NAV / Patrimonio Neto](portfolio-engine/nav.md)** — Cómo el valor contable basado en PMP difiere del NAV a precio de mercado
