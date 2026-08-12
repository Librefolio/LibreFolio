# 📥 <img src="https://www.credit-agricole.it/favicon.ico" alt=""> Crédit Agricole

Crédit Agricole funciona como **banco y bróker** al mismo tiempo: en la misma cuenta mantienes tanto tu **liquidez** (salario o pensión, transferencias, facturas, impuestos) como tus **valores**. Por esta razón, la importación principal a realizar es la **Lista de Movimientos de Cuenta**: es el extracto bancario completo y aporta a LibreFolio la **liquidez real** — transferencias, facturas, pensión, **impuestos**, **comisiones** y los **cupones y dividendos** efectivamente abonados. Descarga el archivo, impórtalo tal cual y el plugin reconocerá el formato automáticamente.

El extracto bancario cubre los **últimos 2 años**. Si tu cuenta de valores es **más antigua** y deseas recuperar su **historial**, despliega la sección de abajo **antes** de continuar.

??? note "📦 ¿Cuenta de valores de más de 2 años? Recupera el historial (opcional)"

    El extracto bancario se detiene a los **2 años**. Si el expediente de valores es más antiguo, añade una segunda exportación — la **Lista de Movimientos del Depósito de Valores** — que se remonta mucho más atrás y recupera al menos el **historial de valores** (cantidades, precios, cupones, vencimientos) **anterior** a ese periodo. Es **solo de valores**: **no** contiene los flujos de caja de la cuenta corriente (transferencias, facturas, impuestos…), que permanecen en la Lista de Movimientos de Cuenta. El efectivo de esta exportación se **auto-equilibra** para no distorsionar los saldos.

    **Cómo combinarlos sin duplicados.** Exporta primero la **Lista de Movimientos de Cuenta** y anota su fecha de inicio (**"Desde fecha"**). Luego exporta la **Lista de Movimientos del Depósito de Valores** **truncada** de modo que finalice el día **anterior** al inicio de los movimientos de cuenta: los dos archivos **no se solapan** y la misma operación no se contabiliza dos veces.

    #### 📂 Paso 1 — Abre el expediente de valores

    Desde la banca en línea, accede a la sección de **Depósito de Valores** y ve a la lista de movimientos.

    ![Crédit Agricole — inicio, selección de la sección Depósito de Valores](../../../static/broker-guides/CreditAgricole/MovimentiSoloTitoli/01_CA_HOME_selezionePagina.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

    #### 🗓️ Paso 2 — Selecciona el periodo

    Ve tan atrás como sea posible, luego trunca al inicio de los movimientos de cuenta (consulta el consejo anterior).

    ![Crédit Agricole — lista de movimientos de valores con selector de periodo](../../../static/broker-guides/CreditAgricole/MovimentiSoloTitoli/02_CA_ListaMobimentiPeriodo.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

    #### 💾 Paso 3 — Exporta

    Exporta e importa el archivo en LibreFolio sin abrirlo ni modificarlo.

    ![Crédit Agricole — área de exportación de movimientos de valores](../../../static/broker-guides/CreditAgricole/MovimentiSoloTitoli/03_CA_ExportZone.jpeg){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

    #### 💰 Paso 4 — Saldo inicial (depósito manual)

    Es necesario para obtener los **totales de liquidez correctos**: ninguna de las dos exportaciones registra el saldo inicial como movimiento, por lo que sin este paso la caja absoluta comienza en cero al inicio del periodo exportado y permanece desajustada.

    **Cómo obtenerlo.** El **Saldo Inicial** se lee en dos lugares equivalentes (es el mismo valor): en la parte superior del **archivo Excel** de la *Lista de Movimientos de Cuenta* y también **al inicio de la exportación en la página web** — la misma página desde la que exportas los movimientos de cuenta. Es el valor (ej. `2984,99 EUR`) a la fecha **"Desde fecha"** (ej. `01/07/2024`).

    El plugin **no** lo crea automáticamente: en el momento de la importación **crea manualmente una transacción de depósito de efectivo** igual a ese **Saldo Inicial**, con una **fecha** igual a la **"Desde fecha"**. Esto mantiene la caja absoluta exacta incluso si la exportación cubre solo una ventana de tiempo.

    ![Crédit Agricole — fila "Saldo Inicial" y "Desde fecha" en la parte superior de la exportación](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/04C_CA_SaldoInizialeExportMovimenti.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

    **Cómo se mapean las operaciones de valores.** El informe solo incluye el **nombre** del valor (`Nome`), no el ISIN: los activos se vinculan por nombre — confirma el activo en el **Paso 4** del asistente si no es reconocido.

    | Tipo de transacción | Importado como |
    |:--------------------|:---------------|
    | `CEDOLA` | **Cupón** de bono → interés (el valor nominal en la columna de cantidad se ignora) |
    | `ACQ.CONT.SU MERC.`, `SICAV: SOTTOSCR` | **Compra** con un **depósito** automático de igual importe |
    | `FONDI: RIMBORSO` | **Venta** (reembolso de fondo) con un **retiro** automático de igual importe |
    | `TITOLI SCADUTI` | **Vencimiento** de bono: **venta a la par (100)** + una pata de **interés** por cualquier importe por encima de la par |
    | `GIRO ALTRO DOSSIER`, `VERS.TITOLI` | **Transferencia entrante** por herencia → **ajuste** sin efectivo usando el precio de coste por unidad |

    Los importes se importan **literalmente** en la divisa del informe: sin conversión, la columna *Tipo de Cambio* se ignora. La fecha utilizada es la *Fecha de operación*.

    **Modelo de caja (valores).** Al ser una exportación solo de valores, LibreFolio mantiene un saldo de caja **neutral** mediante contrapartidas automáticas (etiqueta `auto_cash`): cada **compra** recibe un **depósito** de igual importe, cada **venta**/**cupón**/**interés de vencimiento** recibe un **retiro** de igual importe. De este modo, la exportación de valores **no acumula efectivo fantasma** — la caja real proviene de la Lista de Movimientos de Cuenta.

## 💳 Cómo importar — Lista de Movimientos de Cuenta

Esta es la importación **principal**: el extracto con la **liquidez real** (transferencias, facturas, pensión, impuestos, comisiones, cupones y dividendos abonados). Cubre los **últimos 2 años**.

### 📄 Paso 1 — Abre los movimientos de cuenta

Desde la banca en línea, accede a la sección de **cuenta corriente** y ve a la lista de movimientos.

![Crédit Agricole — inicio, sección de movimientos de la cuenta corriente](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/01C_CA_HomeContiMovimenti.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

### 🗓️ Paso 2 — Selecciona el periodo

Haz clic en **Búsqueda avanzada** para abrir los filtros de fecha, luego establece la ventana más amplia permitida (la exportación de cuenta está limitada a **2 años**).

![Crédit Agricole — lista de movimientos de cuenta](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/02C_CA_ListaMovimentiConti.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

### 💾 Paso 3 — Exporta

Descarga la lista e impórtala en LibreFolio sin modificarla.

![Crédit Agricole — exportación de movimientos de cuenta con aviso sobre el periodo](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/03C_CA_ExportMovimentiContiConWarning.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

!!! warning "Si aparece el aviso sobre el periodo máximo"

    Crédit Agricole limita cuántas filas/meses puedes exportar a la vez. Si aparece el aviso, **divide la exportación en varios sub-bloques** hasta cubrir todos los meses faltantes:

    1. Exporta el bloque tal como se muestra.
    2. Consulta la **última (más antigua)** transacción del bloque descargado y anota su fecha.
    3. Vuelve al selector de periodo y establece como **fecha final ("hasta")** la fecha de esa última transacción.
    4. Exporta el nuevo bloque y **repite** desde el paso 2 hasta alcanzar el periodo deseado.
    5. Importa **todos** los archivos exportados en LibreFolio.

### 📝 Cómo se mapean las transacciones de cuenta

Los **conceptos de operación** de la cuenta se clasifican del siguiente modo:

| Tipo de concepto | Importado como |
|:-----------------|:---------------|
| Cupones / dividendos abonados | **Interés** (cupón) o **Dividendo** si la descripción identifica un valor con **ISIN**; de lo contrario **interés** |
| Intereses / abonos a favor | **Interés** (importe positivo) |
| Comisión de cuenta, comisiones, gastos de gestión, gastos de cobro de cupón | **Comisión** (salida de caja) |
| Impuesto sobre ganancias de capital, impuesto de timbre, retención, D.Lgs 461 | **Impuesto** (salida de caja) |
| Compraventa de valores/fondos | **Compra/Venta** cuando el concepto y el signo coinciden y la cantidad es recuperable; en caso contrario **depósito/retiro** con un **aviso bloqueante** que completas en el paso de corrección |
| Valores vencidos o sorteados | **Venta a la par** que cierra la posición |
| Transferencia recibida que reembolsa un fondo | **Depósito** + **aviso bloqueante**: el fondo indica el contravalor, no las participaciones, así que eliges el fondo e introduces la cantidad |
| Pensión/salarios, TPV, facturas, retiradas, otras transferencias | **Depósito** (importe > 0) / **Retiro** (importe < 0) por signo |

## 🔗 Referencia para desarrolladores

→ [Proveedores BRIM — Detalles de implementación](../../../developer/backend/brim/providers_list.md)
