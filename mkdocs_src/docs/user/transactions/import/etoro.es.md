# 📥 <img src="https://www.etoro.com/favicon.ico" alt=""> eToro

!!! info "Beta"

    Este plugin está en **Beta** — se ha probado con archivos de muestra, pero pueden existir casos límite.

LibreFolio lee la hoja **Actividad de la cuenta** del extracto de cuenta de eToro que se guarda como CSV.

## 📥 Cómo exportar

1. Inicia sesión en tu [cuenta de eToro](https://www.etoro.com).
2. Abre **Cartera**, luego **Historial** (el icono del reloj).
3. Haz clic en el icono de configuración de la esquina superior derecha y elige **Extracto de cuenta**.
4. Elige las fechas de inicio y fin, y haz clic en **Crear**.
5. Descarga el extracto con el icono **XLS**.
6. Abre el archivo en una hoja de cálculo, ve a la hoja **Actividad de la cuenta** y guárdalo como **CSV**,
   manteniendo los nombres de las columnas en la primera línea. LibreFolio no lee archivos PDF ni Excel.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Marcador de posición de captura de pantalla: Historial de cartera de eToro - Creación y exportación del extracto de cuenta] -->
</div>

## 🔄 Qué se importa

| En Actividad de la cuenta (**Tipo**) | Se importa como |
|:-------------------------------|:------------|
| Posición abierta | **Compra** |
| Posición cerrada | **Venta** |
| Dividendo | **Dividendo** |
| Pago de intereses | **Interés** |
| Depósito | **Depósito** |
| Solicitud de retiro | **Retiro** |
| Comisión de retiro, Comisión de conversión por retiro, Comisión de conversión | **Comisión**, cuando el importe no es cero |

El instrumento proviene de **Detalles** (por ejemplo `NKE/USD`) y la cantidad proviene de **Unidades**.

**No se importan**: **Comisión nocturna** y **Reembolso nocturno** (financiación de CFD) y **SDRT** (impuesto de timbre del Reino Unido) se omiten sin aviso, así que añádelos a mano si los registras. Cualquier otro tipo se omite con un aviso.

## ⚠️ Errores comunes

!!! warning "Comprueba la moneda de los instrumentos no cotizados en USD"

    LibreFolio registra cada fila en la moneda que aparece después de la barra en **Detalles** (`KER/EUR` en euros),
    y todas las demás filas en dólares estadounidenses. eToro expresa sus importes en la moneda de tu cuenta (normalmente
    USD): comprueba las filas de instrumentos cotizados en otra moneda antes de guardarlas.

- **Conserva las fechas de eToro**: día/mes/año, con o sin la hora. Una fila cuya fecha no se pueda leer
  se omite con un aviso.
- **Comisiones de conversión por retiro.** Una comisión distinta de cero se convierte en una **Comisión** aparte, junto a la **Solicitud de retiro** completa. Compara ambas con tu extracto: si la comisión ya se descontó del dinero retirado, desmarca esa comisión en [Revisión](how-to.md#review).
- **Los CFD** se convierten en compras y ventas ordinarias del instrumento, como acciones reales, sin sus comisiones nocturnas: comprueba esas posiciones y sus costes.

## 🔗 Referencia para desarrolladores

→ [Arquitectura de BRIM — notas de eToro](../../../developer/backend/brim/architecture.md#plugin-etoro)
