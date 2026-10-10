# 📥 <img src="https://finecobank.com/favicon.ico" alt=""> Fineco

!!! info "Beta"

    Este plugin está en **Beta** — probado con archivos de ejemplo, pero pueden existir casos límite.

LibreFolio importa el informe **Movimenti Dossier Titoli** de FinecoBank —los movimientos de tu
cartera de valores— guardado como CSV.

## 📥 Cómo exportar

1. Inicia sesión en tu cuenta de **FinecoBank** (web o app).
2. Abre los movimientos de **Dossier Titoli** y elige la cuenta y el periodo que quieras.
3. Exporta la lista: Fineco te da un archivo Excel.
4. Ábrelo y **guárdalo como CSV**. Conserva las líneas anteriores a la tabla (**Dossier:**,
   **Intestatario:**) y los nombres de las columnas: LibreFolio reconoce el informe por ellos.

## 🔄 Qué se importa

| En el informe (**Descrizione**) | Se importa como |
|:--------------------------------|:------------|
| *Compravendita titoli*, con **Segno** `A` o `V` | **Compra** o **Venta** |
| *Dividendo* | **Dividendo** |
| *Stacco Cedole* | **Interés** (cupón de bono) |
| *Rimborso* | **Venta** (amortización o vencimiento) |
| *Aumento capitale* | **Ajuste** de la cantidad, sin efectivo |
| Columnas de comisiones, cuando el informe las tiene | Una **Comisión** separada por fila, en euros |

Cualquier otra operación se omite con una advertencia.

**Bonos amortizados por encima de la par.** Cuando un bono se amortiza por encima de la par (100) —un *premio fedeltà* o una
revalorización por inflación— la venta se registra a la par y el importe por encima de esta como un
**Interés** separado, como un cupón, de modo que tu ganancia refleje solo el precio. LibreFolio reconoce los bonos por
su nombre (BTP, BOT, CCT…). Los bonos amortizados a la par o por debajo de la par, y otros reembolsos, permanecen como una única
**Venta**.

## ⚠️ Para tener en cuenta

- **Las dos disposiciones funcionan**, con o sin las columnas de comisiones: LibreFolio los distingue por
  sí mismo.
- **Importes tal como están escritos.** Cada fila conserva su propia divisa (**Divisa**), sin conversión; la
  columna **Cambio** se ignora.
- **Fechas.** LibreFolio usa la fecha valor (**Data valuta**) o la fecha de negociación cuando falta.

## 🔗 Referencia para desarrolladores

→ [Arquitectura BRIM — notas de Fineco](../../../developer/backend/brim/architecture.md#plugin-fineco)
