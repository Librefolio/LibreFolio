# <img src="../../../static/icons/transactions/dividend.png" width="32" style="vertical-align: middle;" /> Dividendo (Transacción)

Una **transacción de dividendo** registra el pago en efectivo recibido por mantener una posición en un activo que paga dividendos (acción o ETF de distribución). Representa el impacto a nivel de cartera de un [evento de dividendo](../asset-events/dividend.md).

---

## 🔑 Propiedades Clave

| Propiedad | Detalle |
|----------|--------|
| **Código** | `DIVIDEND` |
| **Efecto en el saldo** | ⬆️ Aumenta el saldo |
| **Efecto en el activo** | — (cantidad sin cambios) |
| **Evento fiscal** | Sí (ingreso imponible en la mayoría de las jurisdicciones) |

---

## 📊 Evento vs Transacción

| Concepto | Evento de Dividendo | Transacción de Dividendo |
|---------|---------------|---------------------|
| **Alcance** | Global — afecta el precio del activo | Personal — afecta su cartera |
| **Ejemplo** | "Apple declaró $0.25/acción" | "Recibí $12.50 por mis 50 acciones" |
| **Registrado por** | Proveedor o manual (Data Editor) | Reporte del bróker (importación BRIM) |
| **Impacto en gráfico** | Marcador de diamante (◆) en el gráfico de precios | No visible en el gráfico |

---

## 📐 Monto del Dividendo

El monto recibido depende del número de acciones en posición en la **fecha de registro**:

$$
\text{Dividendo Recibido} = \text{Acciones en Posición} \times \text{Dividendo por Acción}
$$

### 💰 Impuesto de Retención

Muchas jurisdicciones aplican un impuesto de retención sobre los dividendos, especialmente para acciones extranjeras:

$$
\text{Dividendo Neto} = \text{Dividendo Bruto} \times (1 - \tau_{withholding})
$$

El impuesto retenido se registra como una transacción `TAX` separada.

---

## 🔗 Relacionados

- 💰 **[Eventos de Dividendo](../asset-events/dividend.md)** — Cómo afectan los dividendos a los precios de los activos
- 💰 **[Tributación](../../fundamentals/taxation.md)** — Tratamiento fiscal de los dividendos
- 📈 **[Acciones](../asset-types/stocks.md)** — La principal clase de activos que pagan dividendos
