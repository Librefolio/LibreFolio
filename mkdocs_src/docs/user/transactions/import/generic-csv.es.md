# <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> Generic CSV

El importador **Generic CSV** lee un archivo CSV que usted mismo prepara. Nombre sus columnas como en la
[referencia de columnas](#column-reference) — `date` y `type` al menos — y LibreFolio las reconoce
por sus nombres: no hay nada que asignar manualmente.

## 🎯 Cuándo usarlo

- Su bróker no está en la [lista de compatibles](index.md).
- Su bróker cambió su exportación y su importador aún no la lee.
- Usted mantiene su propia hoja de cálculo, o un script escribe el CSV por usted.

## ⚙️ Cómo importarlo

1. **Prepare el archivo.** Guárdelo como `.csv` (desde Excel, guarde una copia como CSV). Su primera fila nombra las
   columnas, como en la [referencia de columnas](#column-reference); las demás columnas se ignoran.
2. **Súbalo** en el **[Asistente de importación](how-to.md)** y asígnelo a su bróker.
3. **Compruebe el plugin** en **Seleccionar archivos**: si **Generic CSV** no está ya elegido, selecciónelo en
   la columna **Plugin** del archivo.
4. **Analice y revise.** Cada fila se convierte en una transacción.

!!! tip "Un archivo por bróker — no un archivo por divisa"

    Cada fila de un archivo se importa al bróker que asigne a ese archivo, así que nunca mezcle dos
    brókers en un mismo CSV. Las filas en distintas divisas pueden compartir el mismo archivo, ya que cada fila lleva
    su propia `currency`; también puede dividir el historial de un bróker en varios archivos, uno por año
    por ejemplo, e importarlos juntos.

### 🧯 Si algo sale mal

- **"required column 'date' not found"** (o `type`): la primera fila carece de esa columna, o la nombra
  de forma diferente. Agréguela, o cambie el nombre de la columna a un nombre aceptado, y vuelva a subir el archivo.
- **Falta una fila**: las filas que LibreFolio no puede leer — un tipo desconocido, una fecha en un formato
  desconocido, una `currency` vacía — se omiten y se listan entre las advertencias del paso **Análisis**; las filas con
  un signo incorrecto aparecen como problemas de validación. Corríjalas en el archivo y vuelva a subirlo.
- **El espacio de trabajo masivo pide un coste en una fila `ADJUSTMENT`**: introduzca el coste de **una** unidad,
  no el valor total de la posición.

---

## 🔄 Convertir un informe personalizado

Si sus datos provienen de otra herramienta, un script corto puede convertirlos en un CSV genérico. La
**[especificación técnica de CSV genérico](../../../developer/backend/brim/generic_csv.md)** describe
el formato completo — signos, qué tipo usar en cada caso, ejemplos resueltos. Puede pegarla en un asistente de IA
(ChatGPT, Claude, Gemini…) con algunas filas de muestra de su archivo y pedirle el script.

---

## 📋 Referencia de columnas {: #column-reference }

Estas son las columnas que LibreFolio reconoce en un archivo CSV genérico. Los nombres de las columnas no distinguen entre mayúsculas y minúsculas, y los espacios que los rodean se ignoran.

| Columna | ¿Obligatoria? | Alias aceptados | Descripción |
|--------|-----------|-----------------|-------------|
| **`date`** | ✅ Siempre | `data`, `settlement_date`, `value_date`, `trade_date`, `fecha`, `datum`, `transaction_date`, `exec_date` | Fecha de la transacción |
| **`type`** | ✅ Siempre | `tipo`, `transaction_type`, `operation`, `operazione`, `action`, `azione`, `trans_type`, `op_type` | Tipo de transacción — véanse los valores a continuación |
| **`quantity`** | Obligatoria para BUY/SELL/ADJUSTMENT | `quantità`, `qty`, `shares`, `azioni`, `units`, `unità`, `amount_shares`, `num_shares` | Número de unidades. **Negativo para SELL, positivo para BUY.** |
| **`amount`** | Obligatoria para la mayoría de los tipos | `importo`, `value`, `cash`, `cash_amount`, `total`, `totale`, `net_amount`, `gross_amount`, `price` | Impacto en efectivo. **Negativo cuando el efectivo sale, positivo cuando el efectivo entra.** Vacía para ADJUSTMENT. |
| **`currency`** | Opcional (por defecto EUR) | `valuta`, `ccy`, `curr`, `currency_code`, `divisa`, `währung` | Código de divisa ISO 4217. EUR se aplica solo cuando el archivo no tiene columna de divisa: si la tiene, rellénela en cada fila con un `amount`, o esa fila se omitirá. |
| **`asset`** | Obligatoria para BUY/SELL/DIVIDEND/ADJUSTMENT | `symbol`, `ticker`, `isin`, `asset_id`, `instrument`, `strumento`, `security`, `titolo`, `name`, `nome` | Ticker, ISIN, o un nombre coherente y constante para activos no cotizados |
| **`description`** | Opcional | `descrizione`, `notes`, `memo`, `note`, `details`, `dettagli`, `comment`, `commento` | Notas de texto libre |

### 🏷️ Valores válidos de `type`

`BUY` · `SELL` · `DIVIDEND` · `INTEREST` · `DEPOSIT` · `WITHDRAWAL` · `FEE` · `TAX` · `ADJUSTMENT`

!!! warning "No soportado: TRANSFER, FX_CONVERSION, CASH_TRANSFER"

    Estos tipos necesitan dos filas vinculadas, lo que un CSV no puede expresar: esas filas se omiten con una advertencia.
    Introdúzcalas a mano desde la página de Transacciones, o utilice el importador propio de su bróker.

---

## 🔗 Relacionado

- 🧙 **[Cómo importar](how-to.md)** — el Asistente de importación, paso a paso
- 🏦 **[Brókers compatibles](index.md)** — compruebe primero si su bróker tiene su propio importador
- 🛠️ **[Especificación técnica de CSV genérico](../../../developer/backend/brim/generic_csv.md)** — el formato completo, para scripts y desarrolladores
