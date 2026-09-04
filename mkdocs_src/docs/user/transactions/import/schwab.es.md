# <img src="https://www.schwab.com/favicon.ico" alt=""> Charles Schwab

!!! info "Beta"

    Este complemento se encuentra en fase **Beta**: ha sido probado con archivos de muestra, pero podrían existir casos límite.

## 📥 Cómo exportar

Para exportar su historial de transacciones desde Charles Schwab:

1. Inicie sesión en su [Charles Schwab Client Portal](https://www.schwab.com).
2. Vaya a la pestaña **Accounts** y seleccione **History**.
3. Seleccione la cuenta que desea exportar (si tiene varias cuentas).
4. Seleccione el rango de fechas deseado.
5. Haga clic en el enlace **Export** (generalmente ubicado en la esquina superior derecha de la tabla de transacciones) y seleccione **CSV**.
6. Guarde el archivo en su computadora.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Charles Schwab Portal - History tab and Export link] -->
</div>

## ⚠️ Errores comunes

!!! warning "Do Not Modify Headers"

    Los archivos CSV de Schwab incluyen filas de resumen/metadatos cerca del final. El analizador BRIM ignora las filas que no corresponden a transacciones y puede emitir advertencias por acciones desconocidas o filas no válidas. No edite manualmente la exportación.

## 📝 Notas

- Soporta parámetros de CSV con formato de EE. UU. (estructuras de fecha MM/DD/AAAA y listados de moneda USD).
- Analiza transacciones de compra/venta, pagos de dividendos, reinversiones y cargos por transacción.

## 🔗 Referencia para desarrolladores

→ [Proveedor de Charles Schwab — Detalles de implementación](../../../developer/backend/brim/providers_list.md)
