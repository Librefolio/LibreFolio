# <img src="../../../static/icons/transactions/deposit.png" width="32" style="vertical-align: middle;" /> Depósitos y Retiros

Los **depósitos** y **retiros** registran las entradas y salidas de efectivo de una cuenta de bróker. No involucran ningún activo; solo cambia el saldo de efectivo.

---

## 🔑 Propiedades Clave

| Propiedad | Depósito | Retiro |
|----------|---------|------------|
| **Código** | `DEPOSIT` | `WITHDRAWAL` |
| **Efecto en efectivo** | ⬆️ Aumenta el saldo | ⬇️ Disminuye el saldo |
| **Efecto en activos** | — | — |
| **Evento fiscal** | No | No |

---

## 📊 Por Qué Son Importantes

### 📐 Rentabilidad Ponderada por Dinero

Los depósitos y retiros son críticos para calcular la **rentabilidad ponderada por dinero** (MWR / IRR). Sin el seguimiento de los flujos de efectivo, es imposible distinguir entre la rentabilidad generada por la cartera y la rentabilidad causada por la adición o eliminación de efectivo.

$$
0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{t_i}}
$$

donde $CF_i$ es cada flujo de efectivo (depósitos positivos, retiros negativos, valor final positivo).

### 📊 Rentabilidad Ponderada por Tiempo

La **rentabilidad ponderada por tiempo** (TWR) elimina el efecto de los flujos de efectivo calculando la rentabilidad entre cada evento de flujo de efectivo y encadenándolos:

$$
R_{TWR} = \prod_{i=1}^{n} (1 + r_i) - 1
$$

Esto proporciona una medida "pura" de la rentabilidad de la cartera, independiente del momento de los depósitos o retiros.

---

## 🔗 Relacionados

- 📈 **[Rentabilidades y Tasas de Crecimiento](../../fundamentals/returns.md)** — Cálculo de TWR vs MWR
- 🛒 **[Compra y Venta](buy-sell.md)** — Transacciones que utilizan el efectivo depositado
