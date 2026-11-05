# <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> CSV genérico

El importador **CSV genérico** lee un archivo CSV que prepares tú mismo. Nombra sus columnas como en la
[referencia de columnas](#column-reference) — `date` y `type` como mínimo — y LibreFolio las reconoce
por sus nombres: no hay que asignar nada manualmente.

## 🎯 Cuándo usarlo

- Tu bróker no está en la [lista de brókers compatibles](index.md).
- Tu bróker ha cambiado su exportación y su importador aún no la lee.
- Llevas tu propia hoja de cálculo o un script escribe el CSV por ti.

## ⚙️ Cómo importarlo

1. **Prepara el archivo.** Guárdalo como `.csv` (desde Excel, guarda una copia como CSV). Su primera fila contiene los nombres de las
   columnas, como en la [referencia de columnas](#column-reference); las demás columnas se ignoran.
2. **Súbelo** en el **[Asistente de importación](how-to.md)** y asígnalo a su bróker.
3. **Comprueba el plugin** en **Seleccionar archivos**: si **CSV genérico** no está ya elegido, selecciónalo en
   la columna **Plugin** del archivo.
4. **Analiza y revisa.** Cada fila se convierte en una transacción.

!!! tip "Un archivo por bróker — no un archivo por divisa"

    Cada fila de un archivo se importa al bróker que asignes a ese archivo, así que nunca mezcles dos
    brókers en un mismo CSV. Las filas en distintas divisas pueden compartir el mismo archivo, ya que cada fila lleva
    su propio `currency`; también puedes dividir el historial de un bróker en varios archivos, uno por año
    por ejemplo, e importarlos juntos.

!!! tip "¿Varias columnas de fecha? Usa la fecha de la operación"

    LibreFolio lee **una** columna de fecha por archivo, nunca dos. Si la cabecera contiene varias columnas
    con un nombre de fecha aceptado (por ejemplo, `trade_date` y `settlement_date`, consulta la
    [referencia de columnas](#column-reference)), toma la **primera, leyendo de izquierda a derecha**,
    e ignora las demás. Una columna con otro nombre, como `order date`, no se lee en absoluto.

    En la columna de fecha pon la **fecha de la operación**: el día en que se realizó la operación o la transacción, no
    el día de liquidación o de registro, que puede llegar días después. Esto es especialmente importante cuando escribes
    el CSV a mano o haces que otra IA lo escriba por ti: dile que use la fecha de la operación y que
    deje las demás fechas fuera del archivo.

### 🧯 Si algo sale mal

- **"no se encontró la columna obligatoria 'date'"** (o `type`): la primera fila no tiene esa columna o le da
  otro nombre. Añádela, o cambia el nombre de la columna por uno aceptado, y vuelve a subir el archivo.
- **Falta una fila**: las filas que LibreFolio no puede leer — un tipo desconocido, una fecha en un formato desconocido,
  un `currency` vacío — se omiten y se listan entre las advertencias del paso **Analizar**; las filas con
  un signo incorrecto aparecen como problemas de validación. Corrígelas en el archivo y vuelve a subirlo.
- **El espacio de trabajo masivo pide un coste en una fila `ADJUSTMENT`**: introduce el coste de **una** unidad,
  no el valor total de la posición. Solo lo pide una fila que añade unidades: una que quita
  unidades (una cantidad negativa) no tiene valor.

### 📅 Formato de fecha {: #day-month-order }

Una fecha como `03/04/2025` puede significar el 3 de abril o el 4 de marzo, y un año puede escribirse con dos dígitos
(`03/04/26`). LibreFolio te permite elegir cómo lee el importador CSV genérico las fechas de tus archivos. La
elección es solo tuya: otras personas del mismo LibreFolio conservan la suya.

Abre **Configuración › Plugins**, busca **Importaciones de brókers** y establece **Formato de fecha**. Cada opción muestra la
forma de la fecha y un ejemplo completo:

| Opción | Ejemplo |
|--------|---------|
| `dd/mm/yyyy` (la opción predeterminada) | `03/04/2025` = **3 de abril de 2025** |
| `mm/dd/yyyy` | `03/04/2025` = **4 de marzo de 2025**, tal como se escribe en Estados Unidos |
| `dd/mm/yy` | `03/04/26` = **3 de abril de 2026** |
| `mm/dd/yy` | `03/04/26` = **4 de marzo de 2026** |
| `yy/mm/dd` | `26/04/03` = **3 de abril de 2026** |
| `yyyy-mm-dd` | `2026-04-03` = **3 de abril de 2026** |

`dd/mm/yyyy` es la forma en que LibreFolio siempre ha leído las fechas, así que nada cambia si nunca abres la configuración.
Con `dd/mm/yyyy` y `mm/dd/yyyy`, una fecha que solo se puede leer en un orden siempre se lee bien: `25/12/2025`
es el 25 de diciembre, porque no existe el mes 25. Con las opciones de año de dos dígitos, el orden que elijas es el
único que se usa, y `yy` sigue la regla habitual: `00`–`68` son 2000–2068, `69`–`99` son 1969–1999. Las fechas
escritas como `2025-12-25`, `20251225` o `25 Dec 2025` tienen un único significado y nunca se desplazan.

Una fila cuya fecha no se pueda leer en el formato elegido se deja fuera, y el análisis lo indica para cada fila
(*Fila 4: 25/12/26 no es una fecha válida en el formato mm/dd/yy…*), con indicaciones de dónde corregirla: corrige la fecha
en el archivo, o cambia el **Formato de fecha** en **Configuración › Plugins** y pulsa **Volver a analizar todo**. Después de la
vigésima fila de este tipo, una sola nota contabiliza las restantes.

!!! tip "Vuelve a analizar el archivo después de cambiarlo"

    Un archivo que ya analizaste conserva las fechas con las que se leyó. Después de cambiar la configuración, el archivo
    muestra el aviso de que debe **analizarse de nuevo**: vuelve a analizarlo y luego revisa las filas.

---

## 🔄 Convertir un informe personalizado

Si tus datos provienen de otra herramienta, un script breve puede convertirlos en un CSV genérico. La
**[especificación técnica de CSV genérico](../../../developer/backend/brim/generic_csv.md)** describe
el formato por completo — signos, qué tipo usar en cada caso y ejemplos resueltos. Puedes pegarla en un asistente de IA
(ChatGPT, Claude, Gemini…) junto con algunas filas de ejemplo de tu archivo y pedirle el script.

---

## 📋 Referencia de columnas {: #column-reference }

Estas son las columnas que LibreFolio reconoce en un archivo CSV genérico. Los nombres de columna no distinguen entre mayúsculas y minúsculas y los espacios que los rodean se ignoran.

| Columna | ¿Obligatoria? | Alias aceptados | Descripción |
|--------|-----------|-----------------|-------------|
| **`date`** | ✅ Siempre | `data`, `settlement_date`, `value_date`, `trade_date`, `fecha`, `datum`, `transaction_date`, `exec_date` | Fecha de la transacción |
| **`type`** | ✅ Siempre | `tipo`, `transaction_type`, `operation`, `operazione`, `action`, `azione`, `trans_type`, `op_type` | Tipo de transacción — consulta los valores a continuación |
| **`quantity`** | Obligatoria para BUY/SELL/ADJUSTMENT | `quantità`, `qty`, `shares`, `azioni`, `units`, `unità`, `amount_shares`, `num_shares` | Número de unidades. **Negativo para SELL, positivo para BUY.** |
| **`amount`** | Obligatoria para la mayoría de los tipos | `importo`, `value`, `cash`, `cash_amount`, `total`, `totale`, `net_amount`, `gross_amount`, `price` | Impacto en efectivo. **Negativo cuando sale efectivo, positivo cuando entra efectivo.** Vacío para ADJUSTMENT. |
| **`currency`** | Opcional (por defecto, EUR) | `valuta`, `ccy`, `curr`, `currency_code`, `divisa`, `währung` | Código de divisa ISO 4217. EUR solo se aplica cuando el archivo no tiene columna de divisa: si la tiene, rellénala en cada fila con un `amount`, o esa fila se omite. |
| **`asset`** | Obligatoria para BUY/SELL/DIVIDEND/ADJUSTMENT | `symbol`, `ticker`, `isin`, `asset_id`, `instrument`, `strumento`, `security`, `titolo`, `name`, `nome` | Ticker, ISIN o una cadena de texto con un nombre coherente para activos no cotizados |
| **`description`** | Opcional | `descrizione`, `notes`, `memo`, `note`, `details`, `dettagli`, `comment`, `commento` | Notas de texto libre |

### 🏷️ Valores válidos de `type`

`BUY` · `SELL` · `DIVIDEND` · `INTEREST` · `DEPOSIT` · `WITHDRAWAL` · `FEE` · `TAX` · `ADJUSTMENT`

!!! warning "No admitidos: TRANSFER, FX_CONVERSION, CASH_TRANSFER"

    Estos necesitan dos filas vinculadas, algo que un CSV no puede expresar: esas filas se omiten con una advertencia.
    Introdúcelas manualmente desde la página Transacciones o usa el propio importador de tu bróker.

---

## 🔗 Relacionados

- 🧙 **[Cómo importar](how-to.md)** — el Asistente de importación, paso a paso
- 🏦 **[Brókers compatibles](index.md)** — comprueba primero si tu bróker tiene su propio importador
- 🛠️ **[Especificación técnica de CSV genérico](../../../developer/backend/brim/generic_csv.md)** — el formato completo, para scripts y desarrolladores
