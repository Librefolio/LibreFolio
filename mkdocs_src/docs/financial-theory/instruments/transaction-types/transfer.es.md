# 🔄 ![](../../../static/icons/transactions/transfer.png){: width="32" style="vertical-align: middle;" } Transferencia de Activos

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="form-modal-transfer" alt="Formulario de transacción — TRANSFER">
</div>

Las **transferencias de activos** mueven valores entre cuentas de brókeres **sin realizar una venta**. La posición sale de un bróker y llega a otro; no hay intercambio de efectivo y, en la mayoría de las jurisdicciones, esto no es un evento fiscal.

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

    Consulta **[📊 Precio Medio de Compra (PMC)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** para saber cómo se calcula el coste base automático.

---

## 🔀 Relación con Ajustes

Una Transferencia se guarda como dos filas `TRANSFER`, una por bróker, cada una vinculada a la otra mediante `related_transaction_id`. Separar el par convierte las dos filas en `ADJUSTMENT` independientes, y promover dos Ajustes las vuelve a convertir en una Transferencia:

| Operación | Resultado |
|-----------|--------|
| **Separar par** (desvincular) | Transferencia → dos Ajustes independientes |
| **Promover** (vincular) | Dos Ajustes → Transferencia |

**Restricciones de promoción**: mismo activo, diferentes brókeres, cantidades opuestas, y ninguna de las dos filas vinculada a un evento del activo (un desdoblamiento, por ejemplo), ya que una transferencia no puede llevar ese vínculo.

---

## 👵 Sucesión y Brókeres de Origen no Rastreados

Un verdadero `TRANSFER` necesita dos brókeres en LibreFolio: origen y destino. Si el dossier de origen está fuera de LibreFolio, la pierna entrante se modela mejor como un `ADJUSTMENT` positivo sin efectivo con un `cost_basis_override` por unidad, no como una transferencia emparejada. Las filas de sucesión de Crédit Agricole (`GIRO ALTRO DOSSIER`, `VERS.TITOLI`) utilizan este patrón: los valores heredados entran como capital en especie, no se crea ningún `DEPOSIT` de efectivo y la causa de origen permanece en la descripción para fines de auditabilidad.

---

## 🔗 Relacionados

- 📊 **[Costo Promedio Ponderado](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — Cómo se calcula el costo base en las transferencias
- 🏦 **[Transferencia de fondos](cash-transfer.md)** — Transferencias bancarias (efectivo, no activos)
- 💱 **[Conversión de divisa](fx-conversion.md)** — Cambio de divisas
- 📊 **[Ajuste](adjustment.md)** — Correcciones manuales
