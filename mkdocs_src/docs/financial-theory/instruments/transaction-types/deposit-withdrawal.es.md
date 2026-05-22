# ![](../../../static/icons/transactions/deposit.png){: width="32" style="vertical-align: middle;" } Depósitos y Retiros

Los **depósitos** y **retiros** rastrean el movimiento de efectivo entrante y saliente de una cuenta de bróker. No involucran ningún activo; solo cambia el saldo de efectivo.

---

## 🔑 Propiedades Clave

| Propiedad | Depósito | Retiro |
|----------|---------|------------|
| **Código** | `DEPOSIT` | `WITHDRAWAL` |
| **Efecto en efectivo** | ⬆️ Aumenta el saldo | ⬇️ Disminuye el saldo |
| **Efecto en activos** | — | — |
| **Evento fiscal** | No | No |

---

## 💡 Por qué son Importantes

Los depósitos y retiros no cambian el valor de mercado de la cartera, pero son fundamentales para la **medición del rendimiento**:

- **Rentabilidad Ponderada por Dinero (MWR)**: tiene en cuenta el momento y el tamaño de los flujos de efectivo — se ve directamente afectada por los depósitos/retiros
- **Rentabilidad Ponderada por el Tiempo (TWR)**: elimina el efecto de los flujos de efectivo para medir el rendimiento "puro" de la cartera

Sin un seguimiento preciso de los depósitos/retiros, es imposible distinguir entre la rentabilidad *generada* por la cartera y la rentabilidad *causada* por añadir o retirar efectivo.

!!! tip "Más información"

    Consulte **[📈 Rendimientos y Tasas de Crecimiento](../../fundamentals/returns.md)** para conocer las fórmulas y la metodología.

---

## 🔗 Relacionado

- 📈 **[Rendimientos y Tasas de Crecimiento](../../fundamentals/returns.md)** — Cálculo de TWR vs MWR
- 🛒 **[Compra y Venta](buy-sell.md)** — Transacciones que utilizan el efectivo depositado
