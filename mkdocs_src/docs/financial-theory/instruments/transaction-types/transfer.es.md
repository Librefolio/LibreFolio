# ![](../../../static/icons/transactions/transfer.png){: width="32" style="vertical-align: middle;" } Transferencia de Activos

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="form-modal-transfer" alt="Transaction Form — TRANSFER">
</div>

Las **transferencias de activos** mueven valores entre cuentas de brókers **sin realizar una venta**. La posición sale de un bróker y llega a otro; no hay intercambio de efectivo y, en la mayoría de las jurisdicciones, esto no es un evento fiscal.

---

## 🔑 Propiedades Clave

| Propiedad | Desde (origen) | Hacia (destino) |
|----------|---------------|-------------------|
| **Código** | `TRANSFER` | `TRANSFER` |
| **Efecto en efectivo** | — | — |
| **Efecto en activos** | ⬇️ Disminuye | ⬆️ Aumenta |
| **Bróker** | Bróker de origen | Bróker de destino |
| **Evento fiscal** | Varía según la jurisdicción | Varía |

---

## 📊 Cómo Funciona

Una transferencia de activos registra **dos entradas**: un débito en el bróker de origen y un crédito en el bróker de destino. Ambas hacen referencia al **mismo activo** con cantidades espejo.

Escenarios comunes:

- Mover acciones de un bróker a otro
- Heredar activos
- Contribuciones en especie a un tipo de cuenta diferente (por ejemplo, ISA, 401k)

!!! info "Preservación del Costo Base"

    Al transferir activos, se debe preservar el **costo base original**. La transferencia en sí misma no es un evento fiscal en la mayoría de las jurisdicciones (aunque las reglas varían). LibreFolio permite una **anulación del costo base** opcional en el lado receptor.

    Consulte **[📊 Precio Medio Ponderado (PMP)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** para saber cómo se calcula el costo base automático.

---

## 🔀 Relación con Ajustes

Internamente, una Transferencia se compone de dos entradas de Ajuste. LibreFolio admite:

| Operación | Resultado |
|-----------|--------|
| **División** (desvincular) | Transferencia → dos Ajustes independientes |
| **Promote** (vincular) | Dos Ajustes → Transferencia |

**Restricciones de Promote**: mismo activo, diferentes brókers, cantidades opuestas.

---

## 🔗 Relacionados

- 📊 **[Costo Promedio Ponderado](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — Cómo se calcula el costo base en las transferencias
- 🏦 **[Transferencia de Efectivo](cash-transfer.md)** — Transferencias bancarias (efectivo, no activos)
- 💱 **[Conversión de divisa](fx-conversion.md)** — Cambio de divisas
- 📊 **[Ajuste](adjustment.md)** — Correcciones manuales
