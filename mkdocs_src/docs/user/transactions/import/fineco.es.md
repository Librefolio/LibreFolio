# <img src="https://finecobank.com/favicon.ico" alt=""> Fineco

!!! info "Beta"

    Este plugin está en **Beta** — probado con archivos de muestra, pero pueden existir casos excepcionales.

## 📥 Cómo Exportar

LibreFolio importa el informe **"Movimenti Dossier Titoli"** (movimientos del dossier de valores)
exportado desde FinecoBank.

1. Inicie sesión en su cuenta de **FinecoBank** (web o app).
2. Abra la sección **Dossier Titoli** y seleccione la cuenta/periodo que desee.
3. Exporte la lista de movimientos. Fineco ofrece el informe como archivo Excel.
4. Si el archivo es `.xls`/`.xlsx`, ábralo y **guárdelo como CSV** antes de importarlo; el
 plugin lee el formato **CSV**.

## 📝 Notas

- **Las advertencias de importación se muestran en italiano.** La única exportación compatible hoy es el *Movimenti Dossier Titoli* italiano de FinecoBank, por lo que cualquier advertencia generada durante el análisis aparece en italiano para coincidir con el informe. FinecoBank también opera en el Reino Unido; si se añade posteriormente un formato de exportación del Reino Unido (u otro), sus advertencias seguirán el idioma de ese formato.
- Se admiten automáticamente dos formatos de exportación:
 - **sin comisiones** (11 columnas), y
 - **con comisiones** (15 columnas). Las columnas de comisiones se importan como transacciones
 separadas de **comisiones**.
- Operaciones admitidas: compras y ventas (*Compravendita titoli*), dividendos
 (*Dividendo*), cupones de bonos (*Stacco Cedole*), reembolsos/vencimientos (*Rimborso*),
 y aumentos de capital (*Aumento capitale*, importados como un **ajuste** de cantidad
 sin movimiento de efectivo).
- **Bonos reembolsados sobre la par** — cuando una fila de *Rimborso* corresponde a un bono con precio **sobre la par (100)**,
 el monto acreditado sobre la par (un *premio fedeltà* / revaluación por inflación) se contabiliza como una
 parte separada de **interés** y la **venta** se registra a la par 100. Esto refleja cómo se tratan los cupones
 (*reddito di capitale*) y mantiene la plusvalía realizada basada únicamente en precio versus costo.
 Los bonos reembolsados a la par o por debajo de la par, y los reembolsos de acciones, se importan como una venta única.
- **Los montos se importan textualmente** en la moneda informada por Fineco: la columna *Divisa*
 de cada fila determina la moneda de las cifras de esa fila. No se realiza ninguna
 conversión de moneda y se ignora la columna *Cambio* (tipo de cambio); los números
 aparecen en LibreFolio exactamente como aparecen en el informe.
- La *Data valuta* (fecha valor) se utiliza como fecha de liquidación de la transacción.

## 🔗 Referencia para Desarrolladores

→ [BRIM Providers — Detalles de Implementación](../../../developer/backend/brim/providers_list.md)
