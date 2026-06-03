# 📊 Proveedor justETF

justETF proporciona datos detallados para ETF europeos, incluyendo precios actuales y datos históricos con soporte multidivisa.

## 📊 Capacidades

- ✅ **Precio Actual**: Cotizaciones de gettex en tiempo real (solo EUR)
- ✅ **Historial**: Datos de precios históricos en EUR, USD, CHF o GBP
- ✅ **Búsqueda**: Búsqueda de texto completo en más de 3000 ETF europeos

## 💱 Selección de Divisa

justETF permite obtener precios en **4 divisas**: EUR, USD, CHF, GBP.

Cuando buscas un ETF, los resultados aparecen con banderas de divisa:

| Bandera | Significado |
|------|---------|
| 🇪🇺 | Precios en Euros |
| 🇺🇸 | Precios en Dólares estadounidenses |
| 🇨🇭 | Precios en Francos suizos |
| 🇬🇧 | Precios en Libras esterlinas |
| 👑 | Divisa NAV nativa del fondo (mostrada junto a la bandera) |

!!! note "Conversión de divisa"

    JustETF realiza la conversión en el servidor utilizando sus propios tipos de cambio.
    Para divisas que no estén en la lista compatible (JPY, SEK, etc.), utiliza el sistema de conversión de divisa integrado de LibreFolio.

## ⚠️ Limitaciones

!!! warning "Precio Actual: Solo EUR"

    Los precios en tiempo real (valor actual) solo están disponibles en **EUR** porque provienen del WebSocket del exchange **gettex**, que es un exchange europeo que cotiza en EUR.

    Para divisas que no sean EUR (USD, CHF, GBP):

    - ✅ Los datos históricos están disponibles (convertidos por JustETF)
    - ❌ El precio en tiempo real **no** está disponible — la sincronización del activo mostrará "current value unavailable"

    **Recomendación**: Si necesitas precios en tiempo real, utiliza EUR. Para el seguimiento de cartera donde los precios de cierre diarios sean suficientes, cualquier divisa funciona.

## 🔧 Configuración

- **Identifier**: Código ISIN (ej. `IE00BK5BQT80`)
- **Identifier Type**: `ISIN`
- **Parameters**:
 - `currency`: Divisa del precio — EUR (por defecto), USD, CHF o GBP

## 💡 Ejemplos

| Activo | ISIN | Divisa Sugerida |
|-------|------|--------------------|
| Vanguard FTSE All-World | `IE00BK5BQT80` | EUR o USD 👑 |
| iShares Core MSCI World | `IE00B4L5Y983` | EUR o USD 👑 |
| Xtrackers MSCI Emerging Markets | `IE00BTJRMP35` | EUR o USD 👑 |

## 📝 Notas

- Ideal para ETF domiciliados en Europa listados en justETF
- Utiliza el ISIN como identificador principal
- La 👑 en los resultados de búsqueda indica la denominación NAV nativa del fondo — esta es la divisa que el gestor del fondo utiliza internamente, no necesariamente la divisa en la que operas
