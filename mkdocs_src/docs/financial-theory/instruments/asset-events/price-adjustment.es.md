# 📊 Ajuste de Precio

Un evento de **ajuste de precio** representa un cambio no monetario en el valor razonable de un activo, como un ajuste a la baja (write-down), una corrección de mark-to-market, un recorte (haircut) o una recalificación (re-rating).

---

## 📖 Definición

Los ajustes de precio capturan cambios de valor que **no son causados por operaciones de mercado** y **no implican flujo de caja** para el inversor. Son modificaciones algebraicas (positivas o negativas) al valor razonable calculado del activo.

Estos eventos son más relevantes para activos que no tienen una cotización de mercado continua, como la deuda privada, instrumentos ilíquidos o activos rastreados a través del proveedor Scheduled Investment.

### Escenarios Comunes

| Escenario | Importe | Descripción |
|----------|--------|-------------|
| **Ajuste a la baja (Write-down)** | Negativo | Reducción del valor contable debido a un deterioro |
| **Mark-to-market** | +/− | Revaluación periódica para reflejar el valor razonable actual |
| **Recorte (Haircut)** | Negativo | Reducción forzada (p. ej., durante una reestructuración de deuda) |
| **Recalificación (Re-rating)** | Positivo | Revisión al alza del valor razonable tras eventos positivos |
| **Ajuste de NAV** | +/− | Corrección del Valor Liquidativo (NAV) para fondos cerrados |

---

## 📉 Impacto en el Precio de Mercado

Para **activos con precio de mercado** (acciones, ETF), los ajustes de precio son poco comunes y normalmente informativos; el precio de mercado ya refleja el evento.

Para **activos con precio basado en modelo** (Scheduled Investment, manual), el ajuste modifica directamente el precio calculado:

$$
\text{price}(d) = \text{base{\_}value}(d) + \sum_{i : d_i \leq d} \text{PRICE{\_}ADJUSTMENT}_i
$$

!!! example "Ejemplo: Ajuste a la baja de un bono"

    Un bono corporativo valorado originalmente en 1.000 € se reduce parcialmente después de que el emisor informe de dificultades financieras.

    - **Antes del ajuste**: Valor calculado = 1.000 €
    - **Evento de ajuste de precio**: importe = −200
    - **Después del ajuste**: Valor calculado = 800 €

    Esto no es una transacción de mercado, sino una corrección al modelo de valor razonable.

!!! example "Ejemplo: Recorte (Haircut) de préstamo P2P"

    A un préstamo peer-to-peer de 5.000 € se le aplica un recorte del 20% durante una reestructuración de deuda.

    - **Evento de ajuste de precio**: importe = −1.000
    - **Nuevo valor razonable**: 4.000 €

---

## 📊 Cuándo usar Ajustes de Precio

Use `PRICE_ADJUSTMENT` cuando:

- ✅ El valor razonable del activo cambie sin una transacción de mercado
- ✅ Necesite registrar un ajuste a la baja o deterioro
- ✅ El activo tenga un precio basado en modelo (Scheduled Investment) y necesite una corrección manual
- ✅ Una reestructuración de deuda afecte al valor del principal

**No** lo use para:

- ❌ Cambios regulares en el precio de mercado (estos son capturados por los puntos de datos de precio)
- ❌ Pagos en efectivo (use `DIVIDEND` o `INTEREST` en su lugar)
- ❌ Cambios en la cantidad de acciones (use `SPLIT` en su lugar)

---

## 🧮 Cómo maneja LibreFolio los Ajustes de Precio

En LibreFolio, un evento `PRICE_ADJUSTMENT` se registra con:

- **Fecha**: La fecha efectiva del ajuste
- **Importe**: El cambio algebraico (positivo para incrementos, negativo para decrementos)
- **Moneda**: La moneda del ajuste
- **Notas**: Descripción del motivo (p. ej., "Reducción parcial debido al impago del emisor")

Para el proveedor **Scheduled Investment**, los ajustes de precio son parte de la fórmula principal:

$$
\text{price}(d) = \text{initial{\_}value} + \text{accrued{\_}interest}(d) - \sum \text{INTEREST} + \sum \text{PRICE{\_}ADJUSTMENT}
$$

---

## 🔗 Relacionado

- 📅 **[Descripción general de eventos de activos](index.md)** — Todos los tipos de eventos
- 📈 **[Interés](interest.md)** — Pagos de intereses periódicos
- 🏁 **[Liquidación al vencimiento](maturity-settlement.md)** — Retorno final de capital
