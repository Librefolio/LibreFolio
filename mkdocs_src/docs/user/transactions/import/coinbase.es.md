# <img src="https://www.coinbase.com/favicon.ico" alt=""> Coinbase

!!! info "Beta"

    Este complemento está en fase **Beta**: ha sido probado con archivos de muestra, pero pueden existir casos límite.

## 📥 Cómo exportar

Para exportar su historial de transacciones desde Coinbase:

1. Inicie sesión en su [cuenta de Coinbase](https://www.coinbase.com).
2. Haga clic en su foto de perfil en la esquina superior derecha y seleccione **Taxes** o **Statements**.
3. En la sección **Reports**, localice **Transaction History**.
4. Haga clic en **Generate Report**, seleccione **CSV** como tipo de archivo y elija el rango de fechas deseado.
5. Una vez que el informe esté listo, descargue el archivo CSV en su computadora.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Coinbase Taxes/Reports - Generate Transaction History CSV report] -->
</div>

## ⚠️ Errores comunes

!!! warning "Tipo de informe incorrecto"

    Asegúrese de descargar el informe de **Transaction History**. Otros informes (como Tax Statements, Balance Summaries o informes específicos de Asset Ledger) tienen una estructura diferente y no se analizarán correctamente.

!!! warning "Conversiones USD/EUR"

    El analizador de Coinbase procesa intercambios de criptomonedas, compras, ventas y comisiones. Asegúrese de que la moneda de visualización de su cuenta coincida con la moneda principal de su cartera de LibreFolio para evitar discrepancias en el tipo de cambio.

## 📝 Notas

- Admite compras, ventas, conversiones, envíos, recepción de fondos, recompensas de staking y cobro de comisiones.
- Admite las principales monedas fiduciarias base (USD, EUR, GBP).

## 🔗 Referencia para desarrolladores

→ [Proveedor de Coinbase — Detalles de implementación](../../../developer/backend/brim/providers_list.md)
