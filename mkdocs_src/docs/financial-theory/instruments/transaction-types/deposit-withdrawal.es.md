# 💶 ![](../../../static/icons/transactions/deposit.png){: width="32" style="vertical-align: middle;" } Depósitos y Retiros ![](../../../static/icons/transactions/withdrawal.png){: width="32" style="vertical-align: middle;" }

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="form-modal-deposit" alt="Transaction Form — DEPOSIT">
</div>

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

Matiz para la importación desde el bróker: una exportación de solo valores puede omitir las patas de efectivo de la cuenta bancaria que financiaron las operaciones o recibieron los ingresos. En ese caso, un plugin puede generar automáticamente contrapartidas de efectivo para mantener neutro el efectivo del bróker importado: `DEPOSIT + BUY` para una compra al contado, o `SELL + WITHDRAWAL` para una venta/reembolso. Crédit Agricole usa este modelo solo para su **Lista de Movimientos del Depósito de Valores**: los cupones y las primas de vencimiento siguen siendo ingresos, pero reciben asientos `WITHDRAWAL` de compensación. Su **Lista de Movimientos de Cuenta** transporta efectivo bancario real y no crea esos asientos de compensación.

!!! tip "Más información"

    Consulte **[📈 Rendimientos y Tasas de Crecimiento](../../fundamentals/returns.md)** para conocer las fórmulas y la metodología.

---

## 🔗 Relacionado

- 📈 **[Rendimientos y Tasas de Crecimiento](../../fundamentals/returns.md)** — Cálculo de TWR vs MWR
- 🛒 **[Compra y Venta](buy-sell.md)** — Transacciones que utilizan el efectivo depositado
