# 📥 <img src="https://www.credit-agricole.it/favicon.ico" alt=""> Crédit Agricole

Crédit Agricole es a la vez tu **banco y tu bróker**. La importación principal es la **Lista movimenti** de la cuenta: los últimos **dos años** de efectivo real — sueldo o pensión, transferencias, facturas, impuestos, comisiones, cupones y dividendos.

## 💳 Exporta los movimientos de la cuenta

### 📄 Paso 1 — Abre la lista de movimientos

En la banca en línea, abre **Conti** en el menú superior y elige **Lista movimenti**. Si tienes varias cuentas, elige la tuya en **Seleziona rapporto**.

![Crédit Agricole — inicio, sección de movimientos de cuenta corriente](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/01C_CA_HomeContiMovimenti.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

### 🗓️ Paso 2 — Elige el periodo

Haz clic en **Ricerca avanzata**, configura **Data contabile (Dal)** y **Data contabile (Al)** en el intervalo más amplio que permita el banco (dos años), y luego haz clic en **CERCA**.

![Crédit Agricole — lista de movimientos de la cuenta](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/02C_CA_ListaMovimentiConti.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

### 💾 Paso 3 — Descarga el archivo

Debajo de la lista, haz clic en **SCARICA EXCEL** o **SCARICA CSV**, e importa el archivo sin abrirlo ni editarlo.

![Crédit Agricole — exportación de movimientos de cuenta con aviso de periodo](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/03C_CA_ExportMovimentiContiConWarning.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

??? warning "✂️ Exportación por bloques — cuando el banco solo muestra los primeros resultados"

    Cuando la lista dice **Stai visualizzando i primi … risultati**, se ha cortado y faltan los movimientos más antiguos. Exporta el periodo por bloques:

    1. Descarga el bloque tal cual.
    2. Anota la fecha de su movimiento **más antiguo**.
    3. Configura **Data contabile (Al)** en esa fecha, haz clic en **CERCA** y vuelve a descargar.
    4. Repite hasta que un bloque llegue al inicio de tu periodo.

    Importa todos los bloques juntos. El día en que se encuentran dos bloques está en ambos archivos: el paso **Duplicados** del asistente conserva una copia ([cómo funciona](how-to.md#only-when-needed)).

### 💰 Paso 4 — Añade el saldo inicial

La exportación enumera movimientos, no el efectivo que ya tenías, así que el efectivo del bróker empezaría desde cero. Lee **Saldo Iniziale** y **Data dal** en la parte superior de la exportación de Excel, y añade un **Depósito** de ese importe en esa fecha con el [formulario de transacción](../form.md).

![Crédit Agricole — fila "Saldo inicial" y "Fecha desde" en la parte superior de la exportación](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/04C_CA_SaldoInizialeExportMovimenti.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

## 🕰️ Historial de valores de más de dos años

¿Tu cuenta de valores tiene más de dos años? Una segunda exportación, la **Lista movimenti deposito titoli**, recupera sus operaciones anteriores, cupones y vencimientos — solo valores, sin efectivo bancario.

??? note "📦 Añade el historial de valores — cuando tu cuenta de valores tiene más de dos años"

    Expórtala **después** de los movimientos de la cuenta y haz que termine el día **anterior** a su **Data dal**: así los dos archivos nunca se solapan y ninguna operación se cuenta dos veces.

    #### 📂 Paso 1 — Abre los movimientos de valores

    Abre **Portafoglio** en el menú superior y elige **Lista Movimenti**.

    ![Crédit Agricole — inicio, selección de la sección Cuenta de Valores](../../../static/broker-guides/CreditAgricole/MovimentiSoloTitoli/01_CA_HOME_selezionePagina.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

    #### 🗓️ Paso 2 — Elige el periodo

    Configura **Data Operazione (Dal)** lo más atrás que permita el banco, y **Data Operazione (Al)** como el día anterior a la **Data dal** de los movimientos de la cuenta.

    ![Crédit Agricole — lista de movimientos de valores con selector de periodo](../../../static/broker-guides/CreditAgricole/MovimentiSoloTitoli/02_CA_ListaMobimentiPeriodo.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

    #### 💾 Paso 3 — Descarga el archivo

    Haz clic en **CERCA**, luego en **SCARICA EXCEL** o **SCARICA CSV**, e importa el archivo tal cual.

    ![Crédit Agricole — área de exportación de movimientos de valores](../../../static/broker-guides/CreditAgricole/MovimentiSoloTitoli/03_CA_ExportZone.jpeg){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

    #### 🔄 Qué importa este archivo

    | En el archivo (**Causale**) | Se importa como |
    |:--------------------------|:------------|
    | `CEDOLA` | **Interés** (cupón de bono) |
    | `ACQ.CONT.SU MERC.`, `SICAV: SOTTOSCR` | **Compra** |
    | `FONDI: RIMBORSO` | **Venta** (reembolso de fondo) |
    | `TITOLI SCADUTI` | **Venta** a la par (100), más **Interés** por cualquier importe pagado por encima de la par |
    | `GIRO ALTRO DOSSIER`, `VERS.TITOLI` | **Ajuste**: valores transferidos desde otro dossier, como una herencia, a su valor contable y sin efectivo |

    Cualquier otra causale se omite con una advertencia. Cada compra recibe un **Depósito** correspondiente, y cada venta, cupón o prima un **Retiro** correspondiente: este archivo no añade efectivo propio, y el efectivo real procede de los movimientos de la cuenta.

## 🔄 Qué se importa

| En los movimientos de la cuenta | Se importa como |
|:-------------------------|:------------|
| Sueldo o pensión, pagos con tarjeta, facturas, retiros de efectivo, transferencias | **Depósito** o **Retiro**, según el signo del importe |
| Cupones y dividendos | **Interés** o **Dividendo**, vinculados al valor cuando la línea indica su ISIN; una retención indicada (`RITENUTA`) se convierte en un **Impuesto** aparte |
| Intereses de la cuenta y la comisión mensual (`INTERESSI/COMPETENZE`) | **Interés** cuando se abona, **Comisión** cuando se carga |
| Comisiones y cargos | **Comisión**, o **Impuesto** para el impuesto sobre plusvalías, el impuesto de timbre y las retenciones |
| Compras y ventas de valores y fondos | **Compra** o **Venta** cuando los cupones del mismo bono dan la cantidad; de lo contrario, una fila de efectivo para que la completes |
| Bonos vencidos o amortizados | **Venta** a la par (100), más **Interés** por cualquier prima; sin el nominal del bono en el archivo, una **Venta** por el importe total, con una advertencia |
| Un reembolso de fondo pagado por transferencia bancaria | Un **Depósito** para que lo completes: el banco indica el dinero, no las participaciones vendidas |
| Cualquier otra operación | **Depósito** o **Retiro** según el signo, listado en un aviso para que puedas comprobarlo |

## ⚠️ Conviene saber

- **Algunas filas piden tu ayuda** en el paso **Correcciones** del asistente ([cómo funciona](how-to.md#only-when-needed)):
    - operaciones sin cantidad, y reembolsos de fondos: elige el tipo, el valor y la cantidad;
    - operaciones cuyo importe puede incluir intereses devengados y comisiones: añádelos en **¿Separar el precio de los cargos?**, a partir de tu nota de contrato (*nota informativa*);
    - cargos que no indican ningún valor: asígnalos, o mantenlos en la cuenta.
- **Los valores se emparejan por nombre.** La exportación de valores no da ISIN: empareja cada valor en el panel **Resolver activos** de [Revisión](how-to.md#review).
- **Importes tal como están escritos**, en la divisa de cada fila, sin conversión. Las fechas son las fechas de la operación.
- **Mensajes en italiano.** La mayoría de los avisos del importador sobre estos archivos están en italiano, como el informe.

## 🔗 Referencia para desarrolladores

→ [Importador de Crédit Agricole — Detalles de implementación](../../../developer/backend/brim/credit_agricole.md)
