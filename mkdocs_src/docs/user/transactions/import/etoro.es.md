# 📥 <img src="https://www.etoro.com/favicon.ico" alt=""> eToro

!!! info "Beta"

    Este plugin está en **Beta** — probado con archivos de ejemplo, pero pueden existir casos límite.

LibreFolio lee la hoja **Account Activity** del extracto de cuenta de eToro, guardado como CSV.

## 📥 Cómo exportar

1. Inicia sesión en tu [cuenta de eToro](https://www.etoro.com).
2. Abre **Cartera** y luego **History** (el icono del reloj).
3. Haz clic en el icono de configuración en la esquina superior derecha y elige **Account Statement**.
4. Elige las fechas de inicio y fin y haz clic en **Create**.
5. Descarga el extracto con el icono **XLS**.
6. Abre el archivo en una hoja de cálculo, ve a la hoja **Account Activity** y guárdalo como **CSV**,
   manteniendo los nombres de las columnas en la primera línea. LibreFolio no lee archivos PDF ni Excel.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: eToro Portfolio History - Account Statement creation and export] -->
</div>

## 🔄 Qué se importa

| En Account Activity (**Type**) | Se importa como |
|:-------------------------------|:------------|
| Open Position | **Compra** |
| Position closed | **Venta** |
| Dividend | **Dividendo** |
| Interest Payment | **Interés** |
| Deposit | **Depósito** |
| Withdraw Request | **Retiro** |
| Withdraw Fee, Withdrawal Conversion Fee, Conversion Fee | **Comisión**, cuando el importe no es cero |
| Overnight fee (CFD financing) | **Comisión**, cuando el importe no es cero: un coste del dinero, sin activo |
| Overnight refund (CFD financing given back) | **Interés**: dinero devuelto (importe positivo), sin activo y con la descripción *Overnight refund* |
| SDRT (impuesto de timbre del Reino Unido) | **Impuesto**, sobre el instrumento de la fila |

El instrumento proviene de **Details** (por ejemplo, `NKE/USD`) y la cantidad procede de **Units**.

Cualquier otro tipo se omite con una advertencia.

## ⚠️ Errores comunes

!!! warning "Comprueba la moneda de los instrumentos no cotizados en USD"

    LibreFolio registra cada fila en la moneda que aparece después de la barra en **Details** (`KER/EUR` en euros),
    y todas las demás filas en dólares estadounidenses. eToro indica sus importes en la moneda de tu cuenta (normalmente
    USD): revisa las filas de instrumentos cotizados en otra moneda antes de guardarlas.

- **Conserva las fechas de eToro**: día/mes/año, con o sin la hora. Una fila cuya fecha no se pueda leer
  se omite con una advertencia.
- **Comisiones de conversión por retiro.** Una comisión distinta de cero se convierte en una **Comisión** independiente, junto a la
  **solicitud de retiro** completa. Compara ambas con tu extracto: si la comisión ya se descontó del
  dinero retirado, desactívala en [Revisión](how-to.md#review).
- **CFDs**: se convierten en compras y ventas ordinarias del instrumento, como si fueran acciones reales. Sus **comisiones
  overnight** se importan como transacciones independientes de tipo **Comisión**, sin activo: contrasta esas posiciones y
  sus costes con tu extracto.
- **Comisiones y devoluciones overnight.** Las comisiones se importan como **Comisión** y las devoluciones como **Interés**: el
  coste overnight que realmente pagaste, neto de devoluciones, es la diferencia entre las comisiones y las devoluciones. Una devolución aparece
  como ingreso, por lo que un informe de tus ingresos la incluye.

## 🚧 Limitaciones conocidas {: #known-limitations }

- **Importes en la moneda de tu cuenta.** Consulta la advertencia anterior: revisa la moneda de los instrumentos no
  cotizados en USD antes de guardarlos.
- **¿Algo no cuadra?** Por favor, abre una [incidencia](https://github.com/Librefolio/LibreFolio/issues) con
  un archivo de ejemplo anonimizado.

## 🔗 Referencia para desarrolladores

→ [Arquitectura BRIM — notas sobre eToro](../../../developer/backend/brim/architecture.md#plugin-etoro)
