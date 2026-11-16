# <img src="https://fred.stlouisfed.org/favicon.ico" alt=""> Reserva Federal (FED)

El proveedor **Federal Reserve (FRED)** recupera datos de tipos de cambio de la base de datos Federal Reserve Economic Data (FRED). Es la fuente primaria o fallback ideal para carteras centradas en el Dólar estadounidense.

## 📊 Capacidades

- ✅ **Precio Actual**: Tipo de referencia actualizado diariamente
- ✅ **Historial**: Tipos históricos profundos (depende de la serie de la moneda)
- ❌ **Búsqueda**: Sin búsqueda de activos (solo tipos de cambio FX)

## 🔧 Especificaciones

- **Moneda Base**: USD 🇺🇸
- **Frecuencia de Actualización**: un tipo por día hábil de EE. UU., publicado una vez por semana (ver abajo)
- **API Key**: No es necesaria (recuperada a través de descarga pública de CSV)

## 💰 Monedas Soportadas

FRED proporciona tipos de cambio para 23 monedas:

- **Monedas G10**: EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CAD 🇨🇦, CHF 🇨🇭, AUD 🇦🇺, NZD 🇳🇿, SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰
- **Emergentes y Regionales**: CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦, TWD 🇹🇼, THB 🇹🇭, MYR 🇲🇾, LKR 🇱🇰, VES 🇻🇪

## 📝 Notas Importantes

- **Formato de cotizaciones**: FRED cotiza algunas monedas como "USD por unidad de moneda extranjera" (ej. EUR, GBP) y otras como "moneda extranjera por USD" (ej. JPY, CAD). LibreFolio lee cada serie en su propio sentido y la normaliza para garantizar la consistencia en tu base de datos.
- **Publicación semanal**: los tipos FED son diarios, un valor por cada día hábil de EE. UU., pero la Reserva Federal los publica una vez por semana, los lunes, con los días de la semana anterior. El último tipo FED puede tener por tanto hasta unos 10 días, y una cadena de conversión con un tramo FED no tiene tipo para los días más recientes hasta la publicación siguiente. Las rutas que usan FED lo indican con una nota ℹ️.
- **VES (bolívar venezolano)**: disponible desde el 4 de octubre de 2021, día de la última redenominación. Los valores FRED anteriores están en unidades de bolívar más antiguas y no se usan.
- **Festivos**: No se publican tipos de cambio en los días festivos federales de EE. UU. (como Acción de Gracias, Día de la Independencia, etc.) ni los fines de semana.
