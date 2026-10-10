# 📥 <img src="https://www.degiro.com/favicon.ico" alt=""> Degiro

LibreFolio importa el **Extracto de cuenta** de DEGIRO: el CSV que registra cada movimiento de tu cuenta — operaciones, comisiones, dividendos, intereses, depósitos, retiros y conversiones de divisa — en cualquier idioma que ofrezca DEGIRO.

## 📥 Cómo exportar

1. Inicia sesión en el [Portal del cliente de Degiro](https://www.degiro.eu).
2. Abre **Bandeja de entrada** en la barra lateral izquierda y, después, **Extracto de cuenta**.
3. Elige la **Fecha de inicio** y la **Fecha de fin**: desde tu primer depósito hasta hoy para obtener el historial completo.
4. Haz clic en **Exportar**, elige **CSV** y guarda el archivo (normalmente `Account.csv`).

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: Degiro Portal - Inbox and Account Statement page] -->
</div>

## ⚠️ Errores comunes

!!! warning "Extracto de cuenta, no Transacciones"

    La exportación de **Transacciones** de DEGIRO solo enumera tus órdenes: no incluye dividendos, depósitos, retiros ni conversiones de divisa. Si la subes, LibreFolio la reconoce, no importa nada y te pide el Extracto de cuenta.

- **Mantén el archivo tal como se exportó.** Cualquier idioma funciona, siempre que no añadas, elimines o reordenes columnas, ni cambies las fechas día-mes-año de DEGIRO.
- **Avisos en el idioma del archivo.** Los avisos de importación están en el idioma del extracto, sea cual sea el idioma que use LibreFolio: inglés, neerlandés, alemán, francés o español, y en inglés para cualquier otro.

## 🔄 Qué se importa

| En el extracto | Se importa como |
|:-----------------|:------------|
| Compras y ventas, como `Buy 5 APPLE INC@180,25 USD`, en cualquier idioma | **Compra** o **Venta**: el signo del importe da la dirección, la descripción da la cantidad |
| Comisiones de órdenes (`DEGIRO Transaction and/or third party fees`) y comisiones de conexión con el mercado | **Comisión** |
| Impuesto de timbre e impuestos sobre transacciones financieras de una orden | **Impuesto** |
| Dividendos y su impuesto de retención (`Dividend`, `Dividend Tax`) | **Dividendo** e **Impuesto**, cada uno en su propia moneda |
| Depósitos y retiros | **Depósito** y **Retiro** |
| Interés (`Flatex Interest Income`) | **Interés**; el interés que se te cobra se convierte en una **Comisión** |
| Créditos promocionales y de cortesía (`DEGIRO courtesy`) | **Interés**, conservando la descripción de DEGIRO |
| Conversiones de divisa (`FX Debit` y `FX Credit`) | Un par vinculado de **conversiones FX** (ver más abajo) |

Los importes se importan tal como los reporta DEGIRO, cada uno en la moneda de su propia fila.

### 💱 Conversiones de divisa

DEGIRO registra una conversión como dos filas: el dinero que sale de una divisa y el dinero que llega a la otra. LibreFolio las importa como un único par vinculado: en la [Revisión](how-to.md#review) del asistente es una sola fila que muestra **Desde**, **Hasta** y el tipo de cambio que implican los dos importes, seleccionada e importada en su totalidad. Cuenta como dos transacciones en **Importar N transacciones**. El coste de AutoFX de DEGIRO ya está incluido en el importe debitado, por lo que no se añade ninguna comisión adicional.

## 🚫 Qué no se importa

Cada tipo que se indica a continuación aparece en un aviso durante la importación, con sus filas originales, para que puedas comprobarlas:

- **Operaciones corporativas** (cambios de producto o ISIN, desdoblamientos, fusiones, dividendos en acciones y sus liquidaciones en efectivo), filas de **fondos del mercado monetario** y **devoluciones de capital**: LibreFolio no las importa automáticamente; comprueba las posiciones a las que afectan.
- **Filas de retiro de flatex** (`flatex Withdrawal`): LibreFolio no puede saber si el dinero salió realmente de tu cuenta. Si lo hizo, añade el retiro a mano.
- **Filas de conversión de divisa sin contraparte**: la otra pata falta en el archivo o no se puede identificar.
- **Filas con un signo inesperado** para su tipo, como un dividendo negativo.
- **Operaciones cuya cantidad no se puede leer** en la descripción.
- **Filas no reconocidas**: cualquier otra cosa que LibreFolio no haya podido clasificar.

Se omiten sin aviso: las líneas informativas sin importe, los registros internos de DEGIRO (barridos de efectivo, transferencias desde o hacia flatexDEGIRO Bank, reservas) y las líneas con importe cero que no nombran ningún producto, como un interés de importe cero.

## 🔗 Referencia para desarrolladores

→ [Arquitectura BRIM — notas de DEGIRO](../../../developer/backend/brim/architecture.md#plugin-degiro)
