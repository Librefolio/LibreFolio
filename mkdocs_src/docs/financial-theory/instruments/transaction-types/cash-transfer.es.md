# ![](../../../static/icons/transactions/cash-transfer.png){: width="32" style="vertical-align: middle;" } Transferencia de Efectivo

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="form-modal-cash-transfer" alt="Transaction Form — Cash Transfer">
</div>

**Las transferencias de efectivo** (transferencias bancarias / bonifici) mueven dinero entre cuentas de bróker. El saldo disminuye en el origen y aumenta en el destino; no hay activos involucrados.

---

## 🔑 Propiedades Clave

| Propiedad | Desde (origen) | Hacia (destino) |
|----------|---------------|-------------------|
| **Código** | `CASH_TRANSFER` | `CASH_TRANSFER` |
| **Efecto en fondos** | ⬇️ Disminuye | ⬆️ Aumenta |
| **Efecto en activos** | — | — |
| **Bróker** | Bróker de origen | Bróker de destino |
| **Divisa** | La misma en ambos lados | La misma en ambos lados |
| **Evento fiscal** | No | No |

---

## 📊 Cómo Funciona

Una transferencia de efectivo registra **dos entradas**: un retiro en el bróker de origen y un depósito en el de destino. Ambos comparten la misma divisa con importes reflejados. Los dos lados pueden tener **fechas diferentes**; por ejemplo, una transferencia enviada el lunes puede llegar el miércoles.

Escenarios comunes:

- Transferir fondos de un bróker a otro
- Mover efectivo a una cuenta de ahorros
- Enviar dinero entre cuentas personales

!!! note "Fechas diferentes"

    A diferencia de las transferencias de activos, donde ambos lados suelen liquidarse en la misma fecha, las transferencias bancarias pueden durar varios días. LibreFolio admite fechas separadas para cada lado.

---

## 🔀 Relación con Depósitos/Retiros

Internamente, una Transferencia de Efectivo se compone de un Retiro y un Depósito. LibreFolio admite:

| Operación | Resultado |
|-----------|--------|
| **División** (desvincular) | Transferencia de Efectivo → Retiro + Depósito independientes |
| **Promover** (vincular) | Retiro + Depósito → Transferencia de Efectivo |

**Restricciones de promoción**: misma divisa, brókers diferentes, importes de efectivo opuestos.

---

## 🔗 Relacionados

- 🔄 **[Transferencia de Activos](transfer.md)** — Mover valores (no efectivo)
- 💵 **[Depósito y Retiro](deposit-withdrawal.md)** — Movimientos de efectivo de un solo lado
- 💱 **[Conversión de Divisa](fx-conversion.md)** — Cambio de divisa
