# 📊 Precio Medio Ponderado (PMP)

## 💡 ¿Qué es el PMP?

El **Precio Medio Ponderado** (PMP) es el coste unitario promedio de un activo en una cartera, ponderado por la cantidad adquirida a cada precio.

Responde a la pregunta: _"En promedio, ¿cuánto pagué por unidad de este activo?"_

!!! info "Otros nombres"

    - **PMC** — Prezzo Medio di Carico (Italia)
    - **ACB** — Average Cost Basis (Canadá, EE. UU.)
    - **PMP** — Prix Moyen Pondéré (Francia)

## 🧮 Fórmula

El PMP se calcula de forma **iterativa** a medida que se procesa cada transacción cronológicamente:

$$
PMP_{\text{nuevo}} = \frac{PMP_{\text{actual}} \times Q_{\text{pool}} + Coste_{\text{unit}} \times Q_{\text{tx}}}{Q_{\text{pool}} + Q_{\text{tx}}}
$$

Donde:

- $PMP_{\text{actual}}$ = precio medio ponderado actual antes de esta transacción
- $Q_{\text{pool}}$ = cantidad total mantenida en el pool antes de esta transacción
- $Coste_{\text{unit}}$ = coste de adquisición por unidad de la nueva transacción
- $Q_{\text{tx}}$ = cantidad añadida por la nueva transacción

## ⚙️ Cómo calcula LibreFolio el PMP

LibreFolio utiliza un **algoritmo iterativo consciente del inventario** que procesa todas las transacciones cualificadas para un par (bróker, activo) determinado en orden cronológico.

### 🏷️ Efectos de las Transacciones

Cada transacción contribuye al cálculo del PMP de una de estas formas:

| Efecto | Condición | Impacto en el PMP |
|--------|-----------|---------------|
| **Ponderado** | `qty > 0` y `unit_cost > 0` | El PMP se desplaza hacia el nuevo coste de adquisición |
| **Cantidad reducida** | `qty < 0` | Salidas al PMP actual — PMP sin cambios, el pool disminuye |
| **Dilución** | `qty > 0` pero `unit_cost = 0` | El pool crece, el numerador no cambia → el PMP **disminuye** |
| **Auto PMP** | `qty > 0`, `cost_basis_mode = "auto"` | Pool sin cambios — las unidades entran al PMP actual |

### 📅 Orden del Mismo Día

Cuando ocurren múltiples transacciones en la misma fecha:

1. **Primero las adiciones** (qty > 0) — se procesan antes que las reducciones
2. **Segundo las reducciones** (qty < 0) — asegura que el pool no se vuelva transitoriamente negativo

### 🔻 Agotamiento del Pool

- Cuando `new_qty = 0`: el PMP se restablece a 0 (posición cerrada)
- Cuando `new_qty < 0` (caso límite de redondeo): se limita a 0

## 📝 Ejemplos Prácticos

??? example "Ejemplo 1: Dos compras — el PMP sube"

    | Fecha | Tipo | Cant. | Coste Unitario | Cant. Pool | PMP |
    |------|------|-----|-----------|----------|-----|
    | 1 abr | COMPRA | 10 | $150 | 10 | $150.00 |
    | 15 abr | COMPRA | 5 | $180 | 15 | $160.00 |

    $$
    PMP = \frac{150 \times 10 + 180 \times 5}{10 + 5} = \frac{2400}{15} = 160.00
    $$

    La segunda compra a un precio más alto **eleva el PMP**.

??? example "Ejemplo 2: Compra y luego Venta — PMP sin cambios"

    | Fecha | Tipo | Cant. | Coste Unitario | Cant. Pool | PMP |
    |------|------|-----|-----------|----------|-----|
    | 1 abr | COMPRA | 10 | $150 | 10 | $150.00 |
    | 15 abr | VENTA | -5 | (al PMP) | 5 | $150.00 |

    La VENTA elimina unidades al PMP actual ($150). El PMP permanece **sin cambios**; solo disminuye el pool.

??? example "Ejemplo 3: Adquisición de Coste Cero — Dilución"

    | Fecha | Tipo | Cant. | Coste Unitario | Cant. Pool | PMP |
    |------|------|-----|-----------|----------|-----|
    | 1 abr | COMPRA | 10 | $150 | 10 | $150.00 |
    | 1 may | AJUSTE | +5 | $0 | 15 | $100.00 |

    $$
    PMP = \frac{150 \times 10 + 0 \times 5}{10 + 5} = \frac{1500}{15} = 100.00
    $$

    El PMP se **diluye** porque 5 unidades entraron con coste cero (p. ej., división de acciones, airdrop, regalo).

## 🔄 Anulación de la Base de Coste (Cost Basis Override)

Para transferencias y ajustes, LibreFolio admite una **anulación de la base de coste**: un coste unitario especificado por el usuario que representa el coste histórico de las unidades transferidas.

**Cuando está configurado (modo manual):**

- La transacción entra en el cálculo del PMP como una adquisición ponderada normal
- Esto preserva la continuidad del coste entre brókers (p. ej., al transferir del bróker A al bróker B)

**Cuando no está configurado (sin modo especificado):**

- La transacción entra con `unit_cost = 0` (efecto de dilución)
- Esto es apropiado para divisiones de acciones, regalos o airdrops donde no existe un precio de compra

**Cuando el modo auto está activo (`cost_basis_mode = "auto"`):**

- La transacción entra al **PMP actual del pool** — el PMP permanece algebraicamente sin cambios
- Esto es apropiado para transferencias o ajustes donde la base de coste debe heredarse del pool del bróker de origen

$$
PMP_{\text{nuevo}} = \frac{PMP \times Q_{\text{pool}} + PMP \times Q_{\text{tx}}}{Q_{\text{pool}} + Q_{\text{tx}}} = PMP
$$

!!! tip "Auto PMP en la interfaz de usuario"

    En el formulario de transacciones, el interruptor "Auto" utiliza este modo. La tabla muestra la etiqueta de efecto **Auto PMP** (en español), indicando que las unidades entraron al coste actual del pool sin alterar el PMP.

??? example "Ejemplo 4: Transferencia en Modo Auto — PMP sin cambios"

    | Fecha | Tipo | Cant. | Coste Unitario | Cant. Pool | PMP |
    |------|------|-----|-----------|----------|-----|
    | 1 abr | COMPRA | 10 | $150 | 10 | $150.00 |
    | 15 abr | COMPRA | 5 | $180 | 15 | $160.00 |
    | 1 may | TRANSFERENCIA (auto) | +3 | $160 (=PMP) | 18 | $160.00 |

    $$
    PMP = \frac{160 \times 15 + 160 \times 3}{15 + 3} = \frac{2880}{18} = 160.00
    $$

    El receptor de la transferencia en **modo auto** hereda el PMP actual como su coste unitario. El pool crece, pero el PMP permanece **sin cambios**.

## 🌍 Gestión Multi-divisa

Cuando una cartera contiene adquisiciones en diferentes divisas, LibreFolio:

1. Determina la **divisa objetivo** (la más frecuente entre las adquisiciones)
2. Convierte todos los costes unitarios a la divisa objetivo utilizando los tipos de cambio FX históricos
3. Calcula el PMP en la divisa objetivo unificada

!!! warning "Disponibilidad de Tipos de Cambio FX"

    Si falta un tipo de cambio FX requerido, el cálculo del PMP puede quedar incompleto. La interfaz de usuario advierte sobre los pares FX faltantes y proporciona acciones rápidas para añadirlos o sincronizarlos.

## 🎯 Dónde se utiliza el PMP en LibreFolio

- **Base de costo**: $\text{CB}(a,b,t) = q(a,b,t) \times \text{PMP}(a,b,t) \times \text{fx}(\cdot)$
- **P&L realizado en la VENTA**: $\text{realizado} = P_{\text{venta}} - q_{\text{vendida}} \times \text{PMP}_{\text{pre-venta}}$
- **Descomposición del pool de efectivo**: la VENTA devuelve $C = q_{\text{vendida}} \times \text{PMP}$ al Pool de Capital
- **Formulario de transferencia**: sugiere automáticamente el `cost_basis_override` para transferencias salientes

!!! warning "El PMP nunca se utiliza para la valoración de activos"

    El PMP es un constructo contable para la base de costo. La cadena de valoración para el valor de mercado utiliza: `MARKET_PRICE → LAST_BUY_PRICE → MISSING`. Ver [NAV](nav.md).

## ⚙️ Implementación: Alcance a Nivel de Posición

El PMP se mantiene **por posición** $(a, b)$ — es decir, por par (activo, bróker). El mismo activo mantenido en dos brókers tiene dos pools de PMP independientes.

$$
\text{PMP}(a, b_1, t) \neq \text{PMP}(a, b_2, t) \quad \text{en general}
$$

El motor calcula el PMP en línea durante el ciclo de transacciones diario, sin necesidad de consultas a la base de datos independientes. Esto logra un costo amortizado de O(1) por transacción en lugar del costo O(N) de volver a consultar el historial completo.

### Orden de las transacciones el mismo día

Dentro de la misma fecha, **las adiciones (compras) se procesan antes de las reducciones (ventas)**:

$$
\text{COMPRA}_1, \text{COMPRA}_2, \ldots \quad \text{luego} \quad \text{VENTA}_1, \text{VENTA}_2, \ldots
$$

Esto evita cantidades negativas transitorias y asegura que la VENTA siempre lea el PMP correcto que incluye las COMPRAS del mismo día.
