# <img src="https://www.justetf.com/android-chrome-144x144.png?v2" alt=""> justETF

justETF proporciona datos detallados para ETFs europeos, incluyendo precios actuales y datos históricos con soporte multidivisa.

## 📊 Capacidades

- ✅ **Precio Actual**: Cotizaciones de gettex en tiempo real (solo EUR)
- ✅ **Historial**: Datos de precios históricos en EUR, USD, CHF o GBP
- ✅ **Eventos**: puede emitir eventos `DIVIDEND` a partir de los datos del gráfico cuando hay series de dividendos presentes
- ✅ **Búsqueda**: Búsqueda de texto completo en más de 3000 ETFs europeos

## 💱 Selección de Divisa

justETF permite obtener precios en **4 divisas**: EUR, USD, CHF, GBP.

Al buscar un ETF, los resultados aparecen con banderas de divisa:

| Bandera | Significado |
|------|---------|
| 🇪🇺 | Precios en Euro |
| 🇺🇸 | Precios en Dólar estadounidense |
| 🇨🇭 | Precios en Franco suizo |
| 🇬🇧 | Precios en Libra esterlina |
| 👑 | Divisa NAV nativa del fondo (se muestra junto a la bandera) |

!!! note "Conversión de divisa"

    JustETF realiza la conversión en el servidor utilizando sus propios tipos de cambio.
    Para divisas que no estén en la lista soportada (JPY, SEK, etc.), utilice el sistema de conversión de divisa integrado de LibreFolio.

## ⚠️ Limitaciones

!!! warning "Alternativas del Precio Actual"

    El valor actual intenta primero la cotización de gettex en tiempo real en **EUR**.

    Si esa cotización en vivo no está disponible, LibreFolio recurre al `latestQuote` diario de la API del gráfico de rendimiento para **EUR, USD, CHF y GBP**.

    Los datos históricos siguen disponibles para todas las divisas soportadas.

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

- Ideal para ETFs domiciliados en Europa listados en justETF
- Utiliza el ISIN como identificador principal
- La 👑 en los resultados de búsqueda indica la denominación NAV nativa del fondo — esta es la divisa que el gestor del fondo utiliza internamente, no necesariamente la divisa en la que se opera
