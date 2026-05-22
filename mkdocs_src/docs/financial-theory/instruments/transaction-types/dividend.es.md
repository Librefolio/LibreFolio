# ![](../../../static/icons/transactions/dividend.png){: width="32" style="vertical-align: middle;" } Dividendo (Transacción)

Una **transacción de dividendo** registra el pago en efectivo recibido por poseer un activo que paga dividendos (acción o ETF de distribución). Representa el impacto a nivel de cartera de un [evento de dividendo](../asset-events/dividend.md).

---

## 🔑 Propiedades Clave

| Propiedad | Detalle |
|----------|--------|
| **Código** | `DIVIDEND` |
| **Efecto en efectivo** | ⬆️ Aumenta el saldo |
| **Efecto en el activo** | — (cantidad sin cambios) |
| **Evento fiscal** | Sí (ingreso imponible en la mayoría de las jurisdicciones) |

---

## 📊 Evento vs Transacción

| Concepto | Evento de Dividendo | Transacción de Dividendo |
|---------|---------------|---------------------|
| **Alcance** | Global — afecta el precio del activo | Personal — afecta a la cartera |
| **Ejemplo** | "Apple declaró $0.25/acción" | "Recibí $12.50 de mis 50 acciones" |
| **Registrado por** | Proveedor o manual (editor de datos) | Informe del bróker (importación BRIM) |
| **Impacto en gráfico** | Marcador de diamante (◆) en el gráfico de precios | No visible en el gráfico |

---

## 📐 Monto del Dividendo

El monto recibido depende del número de acciones poseídas en la **fecha de registro** (la fecha en que la empresa verifica quién posee las acciones):

$$
\text{Dividendo Recibido} = \text{Acciones Poseídas} \times \text{Dividendo por Acción}
$$

Donde:

- **Acciones Poseídas** = número de acciones que posee en la fecha de registro (fecha ex-dividendo − 1 día hábil)
- **Dividendo por Acción** = monto declarado por la empresa (ej. $0.25/acción)

### 💰 Retención Fiscal

Muchas jurisdicciones aplican una **retención fiscal** sobre los dividendos, especialmente en acciones extranjeras. El impuesto se deduce en la fuente (por el bróker o el país emisor) antes de que usted reciba el pago:

$$
\text{Dividendo Neto} = \text{Dividendo Bruto} \times (1 - \tau_{retención})
$$

Donde:

- **Dividendo Bruto** = monto total declarado (antes de impuestos)
- $\tau_{retención}$ = tasa de retención fiscal (ej. 15% para acciones de EE. UU. poseídas por residentes de la UE bajo la mayoría de los tratados fiscales)
- **Dividendo Neto** = lo que realmente llega a su cuenta del bróker

El monto retenido se registra normalmente como una transacción `TAX` separada en LibreFolio, manteniendo el dividendo bruto y la deducción fiscal distintos para fines de reporte fiscal.

---

## 🔗 Relacionado

- 💰 **[Eventos de Dividendo](../asset-events/dividend.md)** — Cómo afectan los dividendos a los precios de los activos
- 💰 **[Tributación](../../fundamentals/taxation.md)** — Tratamiento fiscal de los dividendos
- 📈 **[Acciones](../asset-types/stocks.md)** — La clase de activo principal que paga dividendos
