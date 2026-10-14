# <img src="https://www.schwab.com/favicon.ico" alt=""> Charles Schwab

!!! info "Beta"

    Este complemento se encuentra en fase **Beta**: ha sido probado con archivos de muestra, pero podrían existir casos límite.

## 📥 Cómo exportar

Para exportar tu historial de transacciones desde Charles Schwab:

1. Inicia sesión en tu [Charles Schwab Client Portal](https://www.schwab.com).
2. Ve a la pestaña **Accounts** y selecciona **History**.
3. Selecciona la cuenta que deseas exportar (si tienes varias cuentas).
4. Selecciona el rango de fechas deseado.
5. Haz clic en el enlace **Export** (generalmente ubicado en la esquina superior derecha de la tabla de transacciones) y selecciona **CSV**.
6. Guarda el archivo en tu computadora.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Charles Schwab Portal - History tab and Export link] -->
</div>

## ⚠️ Errores comunes

!!! warning "Do Not Modify Headers"

    Los archivos CSV de Schwab incluyen filas de resumen/metadatos cerca del final. El analizador BRIM ignora las filas que no corresponden a transacciones y puede emitir advertencias por acciones desconocidas o filas no válidas. No edites manualmente la exportación.

## 📝 Notas

- Soporta parámetros de CSV con formato de EE. UU. (estructuras de fecha MM/DD/AAAA y listados de moneda USD).
- Analiza transacciones de compra/venta, pagos de dividendos, reinversiones y cargos por transacción.

## 🔗 Referencia para desarrolladores

→ [Proveedor de Charles Schwab — Detalles de implementación](../../../developer/backend/brim/providers_list.md)
