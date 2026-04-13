# ![](../../../static/icons/asset-types/bond.png){: width="32" style="vertical-align: middle;" } Bonos

Un **bono** es un valor de renta fija que representa un préstamo de un inversor a un prestatario (gobierno o corporación). El prestatario paga intereses periódicos (**cupones**) y devuelve el principal (**valor nominal**) al vencimiento.

---

## 🔑 Características Clave

| Propiedad | Detalle |
|----------|--------|
| **Código en LibreFolio** | `BOND` |
| **Cotización** | Cotizado como porcentaje del valor nominal (ej. 98.50 = 98.5% del valor nominal) |
| **Moneda** | Denominado en la moneda de emisión |
| **Cupones** | Tasa fija o flotante, pagados semestral o anualmente |
| **Vencimiento** | Fecha fija en la que se devuelve el principal |
| **Proveedores típicos** | Yahoo Finance, Scheduled Investment, Manual |

---

## 📊 Conceptos de Valoración de Bonos

### 💵 Valor Nominal (Par)

La cantidad que el emisor devolverá al vencimiento — típicamente $1,000 o €1,000 por bono.

### 📈 Tasa de Cupón

La tasa de interés anual pagada sobre el valor nominal:

$$
\text{Cupón Anual} = \text{Valor Nominal} \times \text{Tasa de Cupón}
$$

### 📊 Rendimiento al Vencimiento (YTM)

El retorno total esperado si el bono se mantiene hasta el vencimiento, teniendo en cuenta el precio de compra, los pagos de cupones y el valor nominal al vencimiento. La fórmula del YTM es una **aproximación matemática** ampliamente utilizada de cómo el mercado valora los bonos en respuesta a los cambios en las tasas de interés, y sirve como base para muchas otras métricas de renta fija:

$$
P = \sum_{t=1}^{n} \frac{C}{(1 + y)^t} + \frac{F}{(1 + y)^n}
$$

donde $P$ = precio, $C$ = cupón, $F$ = valor nominal, $y$ = YTM, $n$ = periodos.

### 📉 Precio Sucio vs Limpio

- **Precio Limpio**: El precio cotizado, excluyendo los intereses devengados.
- **Precio Sucio**: Precio limpio + intereses devengados (lo que realmente se paga).

$$
\text{Precio Sucio} = \text{Precio Limpio} + \text{Intereses Devengados}
$$

Los intereses devengados dependen de la [Convención de Recuento de Días](../../fundamentals/day-count.md).

---

## 📈 Relación Precio–Rendimiento

Los precios de los bonos se mueven de forma **inversa** a los rendimientos:

- Cuando las tasas de interés suben → los precios de los bonos bajan
- Cuando las tasas de interés bajan → los precios de los bonos suben

Esto se debe a que los bonos existentes con cupones más bajos se vuelven menos atractivos en comparación con los nuevos bonos emitidos a tasas más altas.

---

## 🔗 Relacionado

- 📈 **[Eventos de Interés](../asset-events/interest.md)** — Pagos de cupones y devengo
- 🏁 **[Liquidación por Vencimiento](../asset-events/maturity-settlement.md)** — Retorno de capital al final de la vida del activo
- 📊 **[Ajuste de Precio](../asset-events/price-adjustment.md)** — Mark-to-market y deterioros de valor
- 📅 **[Convenciones de Recuento de Días](../../fundamentals/day-count.md)** — Cómo se calculan los intereses devengados
