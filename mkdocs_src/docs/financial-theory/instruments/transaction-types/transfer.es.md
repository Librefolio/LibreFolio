# <img src="../../../static/icons/transactions/transfer.png" width="32" style="vertical-align: middle;" /> Transferencias y Conversión de FX

Las **Transferencias** mueven activos entre carteras sin venta, mientras que las **Conversiones de FX** intercambian una moneda por otra dentro de una cartera.

---

## 🔑 Propiedades Clave

| Propiedad | Transferencia Entrante | Transferencia Saliente | Conversión de FX |
|----------|------------|-------------|---------------|
| **Código** | `TRANSFER_IN` | `TRANSFER_OUT` | `FX_CONVERSION` |
| **Efecto en el saldo de efectivo** | — | — | ⬆️⬇️ (intercambio) |
| **Efecto en activos** | ⬆️ Aumenta | ⬇️ Disminuye | — |
| **Evento fiscal** | Varía según la jurisdicción | Varía | Varía |

---

## 🔄 Transferencia Entrante / Saliente

Las transferencias modelan el movimiento de activos entre cuentas de bróker o carteras **sin venta**. Escenarios comunes:

- Mover acciones de un bróker a otro
- Heredar activos
- Contribuciones en especie a un tipo de cuenta diferente (ej. ISA, 401k)

!!! info "Preservación de la base de costo"

    Al transferir activos, se debe preservar la **base de costo original**. La transferencia en sí misma no es un evento imponible en la mayoría de las jurisdicciones (aunque las reglas varían).

---

## 💱 Conversión de FX

Intercambios de moneda dentro de una cartera:

$$
\text{Amount}_{target} = \text{Amount}_{source} \times \text{FX Rate} - \text{Fees}
$$

Las conversiones de FX pueden ser:

- **Explícitas**: El usuario convierte monedas deliberadamente (ej. EUR → USD)
- **Implícitas**: El bróker convierte automáticamente al comprar un activo denominado en moneda extranjera

---

## 📊 Ajuste

El tipo de transacción `ADJUSTMENT` es una categoría general para correcciones manuales tanto de los saldos de efectivo como de los de activos. Casos de uso:

- Corregir errores de importación
- Registrar acciones corporativas no cubiertas por los tipos estándar
- Configuración del saldo inicial

---

## 🔗 Relacionado

- 🛒 **[Compra y Venta](buy-sell.md)** — Transacciones de activos estándar
- 💵 **[Depósito y Retirada](deposit-withdrawal.md)** — Movimientos de efectivo
- 💰 **[Tipos de cambio de FX](../../../user/fx/index.md)** — Gestión de tipos de cambio
