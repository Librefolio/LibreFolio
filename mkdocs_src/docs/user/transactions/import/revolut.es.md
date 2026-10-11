# <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" alt=""> Revolut

!!! info "Beta"

    Este plugin está en **Beta** — probado con archivos de muestra, pero pueden existir casos excepcionales.

## 📥 Cómo exportar

Para exportar tu historial de transacciones de acciones y criptomonedas desde Revolut:

1. Abre tu **aplicación móvil de Revolut** o inicia sesión a través del cliente web.
2. Navega a la pestaña **Invest** (o Stocks/Crypto).
3. Toca **... (Más)** junto al saldo de tu cartera y luego selecciona **Statements**.
4. Selecciona la cuenta deseada (por ejemplo, la cuenta de Stocks) y toca **Transaction Statement**.
5. Establece el intervalo de tiempo, elige **CSV** como formato y exporta. Transfiere el archivo a tu ordenador.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Revolut App - Invest Statements selection and CSV export] -->
</div>

## ⚠️ Errores Comunes

!!! warning "Cuenta de Trading vs Cuenta Principal"

    Asegúrate de exportar el extracto de la subcuenta de **Invest/Trading**. El extracto de la tarjeta de débito principal de Revolut utiliza un formato de archivo completamente diferente y no puede ser analizado por este plugin.

## 📝 Notas

- Soporta operaciones con acciones, compras de criptomonedas, dividendos pagados, comisiones de custodia y transferencias de fondos.
- Gestiona automáticamente montos en múltiples divisas dentro del mismo archivo.

## 🔗 Referencia para Desarrolladores

→ [Revolut Provider — Detalles de Implementación](../../../developer/backend/brim/providers_list.md)
