# <img src="https://www.degiro.com/favicon.ico" alt=""> Degiro

!!! info "Beta"

    Este complemento está en **Beta**: se ha probado con archivos de muestra, pero pueden existir casos límite.

## 📥 Cómo Exportar

Para exportar sus transacciones desde Degiro:

1. Inicie sesión en el [Portal del Cliente de Degiro](https://www.degiro.eu).
2. Vaya a **Bandeja de entrada** (o Cuenta) en la barra lateral izquierda, luego haga clic en **Estado de cuenta**.
3. Seleccione la **Fecha de inicio** y la **Fecha de finalización** deseadas para cubrir su historial de transacciones.
4. Haga clic en el botón **Exportar** y seleccione el formato **CSV**.
5. Guarde el archivo en su computadora.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Degiro Portal - Inbox and Account Statement page] -->
</div>

## ⚠️ Problemas Comunes

!!! warning "Informes Separados"

    Degiro tiene diferentes opciones de exportación en el menú. Asegúrese de descargar el **Estado de cuenta** (que registra todos los movimientos de efectivo, compras, ventas y dividendos) en lugar de solo la lista de "Transacciones", que podría omitir eventos de efectivo.

!!! warning "Formatos de Idioma"

    El analizador admite múltiples plantillas locales de Degiro (inglés, holandés, italiano, alemán, etc.). Sin embargo, asegúrese de no modificar manualmente los encabezados de las columnas o los delimitadores CSV después de exportar.

## 📝 Notas

- Admite operaciones de compra/venta, dividendos, comisiones de transacción, depósitos y retiros.
- Las conversiones de divisa realizadas por Degiro se procesan automáticamente.
