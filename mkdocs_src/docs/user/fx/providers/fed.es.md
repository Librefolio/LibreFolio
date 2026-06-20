# <img src="https://fred.stlouisfed.org/favicon.ico" alt=""> Reserva Federal (FED)

El proveedor **Federal Reserve (FRED)** recupera datos de tipos de cambio de la base de datos Federal Reserve Economic Data (FRED). Es la fuente primaria o fallback ideal para carteras centradas en el Dólar estadounidense.

## 📊 Capacidades

- ✅ **Precio Actual**: Tipo de referencia actualizado diariamente
- ✅ **Historial**: Tipos históricos profundos (depende de la serie de la moneda)
- ❌ **Búsqueda**: Sin búsqueda de activos (solo tipos de cambio FX)

## 🔧 Especificaciones

- **Moneda Base**: USD 🇺🇸
- **Frecuencia de Actualización**: Diaria en días laborables de EE. UU.
- **API Key**: No es necesaria (recuperada a través de descarga pública de CSV)

## 💰 Monedas Soportadas

FRED proporciona tipos de cambio para aproximadamente 20 monedas principales, incluyendo:

- **Monedas G10**: EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CAD 🇨🇦, CHF 🇨🇭, AUD 🇦🇺, NZD 🇳🇿, SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰
- **Emergentes y Regionales**: CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦, TWD 🇹🇼, THB 🇹🇭

## 📝 Notas Importantes

- **Formato de cotizaciones**: FRED cotiza algunas monedas como "USD por unidad de moneda extranjera" (ej. EUR, GBP) y otras como "moneda extranjera por USD" (ej. JPY, CAD). LibreFolio invierte y normaliza automáticamente estos tipos para garantizar la consistencia en su base de datos.
- **Festivos**: No se publican tipos de cambio en los días festivos federales de EE. UU. (como Acción de Gracias, Día de la Independencia, etc.) ni los fines de semana.
