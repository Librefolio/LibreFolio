# ![](../../../static/icons/transactions/fx-conversion.png){: width="32" style="vertical-align: middle;" } Conversión de divisas

Las **conversiones de divisas** intercambian una moneda por otra dentro de la **misma cuenta de bróker**. El saldo de una moneda disminuye mientras que el de otra aumenta; no hay cambios en los activos ni en los brókers.

---

## 🔑 Propiedades Clave

| Propiedad | Desde (origen) | Hacia (destino) |
|----------|---------------|-------------|
| **Código** | `FX_CONVERSION` | `FX_CONVERSION` |
| **Efecto en efectivo** | ⬇️ Moneda de origen | ⬆️ Moneda de destino |
| **Efecto en activos** | — | — |
| **Bróker** | El mismo en ambos lados | El mismo en ambos lados |
| **Moneda** | Diferente en cada lado | Diferente en cada lado |
| **Evento fiscal** | Varía según la jurisdicción | Varía |

---

## 📊 Cómo Funciona

Una conversión de divisas registra **dos entradas** en el mismo bróker con **monedas diferentes**. El tipo de cambio es implícito, basado en los montos:

$$
FX_{rate} = \frac{\text{Amount}_{target}}{\lvert\text{Amount}_{source}\rvert}
$$

Las conversiones de divisas pueden ser:

- **Explícitas**: El usuario convierte deliberadamente las monedas (por ejemplo, EUR → USD antes de comprar acciones estadounidenses).
- **Implícitas**: El bróker convierte automáticamente al comprar un activo denominado en moneda extranjera.

!!! info "FX Implícito y Comisiones"

    Cuando un bróker convierte la moneda automáticamente, el tipo de cambio efectivo a menudo incluye un diferencial (spread). La diferencia entre el tipo de cambio de mercado y el tipo de cambio efectivo es esencialmente una comisión oculta:

    $$
    \text{Implicit Fee} = \lvert\text{Amount}_{source}\rvert \times (\text{Market Rate} - \text{Effective Rate})
    $$

---

## 📈 Tipo de Cambio Implícito y Spread del Bróker

LibreFolio calcula automáticamente el **tipo de cambio implícito** a partir de los dos montos:

$$
\text{Implied Rate} = \frac{\lvert\text{Amount}_{target}\rvert}{\lvert\text{Amount}_{source}\rvert}
$$

Esto se compara con el **tipo de cambio de mercado** del subsistema de FX en la fecha de la transacción. La diferencia es el **spread del bróker**:

$$
\text{Spread} = \text{Implied Rate} - \text{Market Rate}
$$

$$
\text{%Spread} = \frac{\text{Spread}}{\text{Market Rate}} \times 100
$$

!!! warning "Disponibilidad del Tipo de Cambio de Mercado"

    La comparación con el tipo de cambio de mercado requiere que el par de FX correspondiente esté configurado en el sistema de FX de LibreFolio. Si el par no está configurado o no existe un tipo de cambio para la fecha de la transacción, solo se mostrará el tipo de cambio implícito.

---

## 🔀 Relación con Depósitos/Retiros

Internamente, una Conversión de divisas se compone de un Retiro (moneda de origen) y un Depósito (moneda de destino). LibreFolio admite:

| Operación | Resultado |
|-----------|--------|
| **División** (desvincular) | Conversión de divisas → Retiro independiente + Depósito |
| **Promover** (vincular) | Retiro + Depósito → Conversión de divisas |

**Restricciones de promoción**: monedas diferentes, mismo bróker.

---

## 🔗 Relacionado

- 💵 **[Depósito y Retiro](deposit-withdrawal.md)** — Movimientos de efectivo de un solo lado
- 🔄 **[Transferencia de Activos](transfer.md)** — Movimiento de activos entre brókers
- 🏦 **[Transferencia de Efectivo](cash-transfer.md)** — Transferencias bancarias entre brókers

---

*Ver también: [💱 Tasas de FX](../../../user/fx/index.md) — cómo configurar y sincronizar los tipos de cambio en LibreFolio.*
