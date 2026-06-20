# <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" alt=""> Revolut

!!! info "Beta"

    Este plugin está en **Beta** — probado con archivos de muestra, pero pueden existir casos excepcionales.

## 📥 Cómo exportar

Para exportar su historial de transacciones de acciones y criptomonedas desde Revolut:

1. Abra su **aplicación móvil de Revolut** o inicie sesión a través del cliente web.
2. Navegue a la pestaña **Invest** (o Stocks/Crypto).
3. Toque **... (Más)** junto al saldo de su cartera y luego seleccione **Statements**.
4. Seleccione la cuenta deseada (por ejemplo, la cuenta de Stocks) y toque **Transaction Statement**.
5. Establezca el intervalo de tiempo, elija **CSV** como formato y exporte. Transfiera el archivo a su ordenador.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Revolut App - Invest Statements selection and CSV export] -->
</div>

## ⚠️ Errores Comunes

!!! warning "Cuenta de Trading vs Cuenta Principal"

    Asegúrese de exportar el extracto de la subcuenta de **Invest/Trading**. El extracto de la tarjeta de débito principal de Revolut utiliza un formato de archivo completamente diferente y no puede ser analizado por este plugin.

## 📝 Notas

- Soporta operaciones con acciones, compras de criptomonedas, dividendos pagados, comisiones de custodia y transferencias de efectivo.
- Gestiona automáticamente montos en múltiples divisas dentro del mismo archivo.

## 🔗 Referencia para Desarrolladores

→ [Proveedor de Revolut — Detalles de Implementación](../../../developer/backend/brim/providers_list.md)
