# <img src="https://www.trading212.com/favicon-32x32.png" alt=""> Trading212

!!! info "Beta"

    Este plugin está en **Beta** — probado con archivos de muestra, pero pueden existir casos límite.

## 📥 Cómo exportar

Para exportar tu extracto de transacciones desde Trading212:

1. Inicia sesión en el [Portal del Cliente de Trading212](https://www.trading212.com) (o abre la aplicación en tu dispositivo móvil).
2. Ve a la sección de menú/perfil y haz clic en **History**.
3. Haz clic en el botón **Export** (generalmente representado por un icono de exportación o documento en la parte superior de la pestaña de historial).
4. Selecciona las columnas deseadas (asegúrate de que todos los campos como ticker, fecha, cantidad, precio y moneda estén seleccionados).
5. Elige **CSV** como formato y haz clic en **Export**. Guarda el archivo en tu computadora.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Trading212 Portal - History and CSV Export modal] -->
</div>

## ⚠️ Errores comunes

!!! warning "Transacciones de Pies"

    Trading212 admite "Pies" (cestas de activos gestionados automáticamente). Si operas dentro de un Pie, en la exportación, estas operaciones se registran como transacciones de activos subyacentes independientes. El analizador de BRIM procesa estas operaciones individuales automáticamente, pero asegúrate de que los saldos de tus Pies estén completamente sincronizados en la cuadrícula de preparación antes de confirmar.

## 📝 Notas

- Admite compras y ventas de acciones/ETF, dividendos, interés sobre efectivo, depósitos, retiros y tarifas de conversión de divisa.
- Se admiten cuentas multidivisa.

## 🔗 Referencia para desarrolladores

→ [Proveedor de Trading212 — Detalles de Implementación](../../../developer/backend/brim/providers_list.md)
