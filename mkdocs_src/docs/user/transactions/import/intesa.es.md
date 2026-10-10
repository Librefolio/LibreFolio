# 📥 <img src="https://www.intesasanpaolo.com/favicon.ico" alt=""> Intesa Sanpaolo

!!! info "Beta"

    Este plugin está en **Beta** — probado con archivos de ejemplo, pero pueden existir casos límite.

LibreFolio lee dos exportaciones de Intesa Sanpaolo, en **CSV** o **Excel (XLSX)**, tal como las descargas:

- la **lista de movimientos** — los cupones, dividendos, comisiones e impuestos de un período;
- la **instantánea de cartera** (*patrimonio*) — tus posiciones a su coste fiscal, y tu saldo de efectivo.

## 🧭 ¿Qué archivos debo importar?

=== "Cuenta completamente nueva"

    Importa la **lista de movimientos**: trae los cupones, dividendos, comisiones e impuestos. LibreFolio
    no extrae compras ni ventas de ella, así que añade tus compras a mano con el
    [formulario de transacción](../form.md), o con un archivo [CSV Genérico](generic-csv.md).

=== "Cuenta con historial (recomendado)"

    Intesa exporta aproximadamente **un año** de movimientos, y LibreFolio no extrae compras ni ventas de
    ellos. En su lugar, empieza por la instantánea de cartera:

    1. Importa la **instantánea de cartera**. Añade un **Depósito** por tu saldo de efectivo y un
       **Ajuste** por cada posición, a su coste fiscal, todos con fecha de la instantánea: la última
       fecha de cotización del informe.
    2. Establece la fecha de **Apertura de Cuenta** del bróker a ese día. Los movimientos anteriores ya están contabilizados
       en la instantánea: el asistente los marca como **Antes de la apertura** y los omite
       ([cómo funciona](how-to.md#opening-date)).
    3. A partir de entonces, importa la **lista de movimientos** para los nuevos cupones, dividendos, comisiones e impuestos.

## 📥 Cómo exportar

### 🔍 Paso 1 — Abre la búsqueda avanzada

En la página de inicio de tu banca online, haz clic en **RICERCA AVANZATA**, junto a **Ultime Operazioni**.

![Intesa Sanpaolo — página de inicio, RICERCA AVANZATA junto a Ultime Operazioni](../../../static/broker-guides/IntesaSanPaolo/01_ISP_RicercaAvanzata.jpg){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

### 🗓️ Paso 2 — Filtra y descarga los movimientos

Establece **Tipologia Operazione** en **Operazioni titoli**, elige el período en **Da** y **A**, haz clic en **APPLICA**, luego en **SCARICA EXCEL**.

![Intesa Sanpaolo — Tipologia Operazione establecida en Operazioni titoli, período, APPLICA y SCARICA EXCEL](../../../static/broker-guides/IntesaSanPaolo/02_ISP_FiltraExport.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

### 📊 Paso 3 — Descarga la instantánea de cartera

Para una cuenta con historial, abre **Patrimonio** desde la página de inicio y descarga las posiciones de
tu *Deposito Amministrato*.

## 🔄 Qué se importa

| En la lista de movimientos (**Operazione**) | Se importa como |
|:---------------------------------------|:------------|
| *Cedole* (cupones) | **Interés**, vinculado al valor mencionado en **Dettagli** |
| *Dividend…* | **Dividendo**, vinculado de la misma forma |
| *Commission…* | **Comisión** |
| *Ritenut…*, *Imposta…*, *Bollo…* | **Impuesto** |

Cualquier otra operación —compras, ventas y movimientos bancarios cotidianos como pagos con tarjeta o transferencias
incluidos— se omite con una advertencia: la importación nunca falla por ello.

De la **instantánea de cartera**: un **Ajuste** por cada posición (su cantidad, a su coste fiscal)
y un **Depósito** por el saldo de efectivo cuando no es cero, todos en la fecha de la instantánea.

## ⚠️ Conviene saber

- **Filtra por Operazioni titoli.** Sin ese filtro, cada pago con tarjeta o transferencia del
  período aparece en las advertencias como una fila omitida.
- **El mismo valor, dos nombres.** La lista de movimientos menciona un valor solo en texto libre, mientras que
  la instantánea proporciona su ISIN. Vincula ambos al mismo activo en el panel **Resolve Assets** de
  [Revisión](how-to.md#review).
- **Importes tal como están escritos.** Los movimientos conservan la divisa de su columna **Valuta**, y la instantánea
  está en euros: nada se convierte.
- **Mensajes en italiano.** Las advertencias de importación están en italiano, al igual que el informe.

## 🔗 Referencia para desarrolladores

→ [Arquitectura BRIM — notas de Intesa Sanpaolo](../../../developer/backend/brim/architecture.md#plugin-intesa)
