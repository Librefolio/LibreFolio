# <img src="https://www.ecb.europa.eu/favicon-32.png" alt=""> Banco Central Europeo (BCE)

El **Banco Central Europeo (BCE)** es el principal proveedor de tipos de referencia para las carteras europeas. Publica diariamente los tipos de cambio del euro frente a aproximadamente 45 monedas principales y emergentes.

## 📊 Capacidades

- ✅ **Precio Actual**: Tipo de referencia actualizado una vez al día
- ✅ **Historial**: Tipos históricos disponibles desde 1999
- ❌ **Búsqueda**: Sin búsqueda de activos (solo tipos de cambio)

## 🔧 Especificaciones

- **Moneda Base**: EUR 🇪🇺
- **Frecuencia de Actualización**: De lunes a viernes (exceptuando los festivos del BCE), alrededor de las 16:00 CET
- **API Key**: No es necesaria (endpoint público)

## 💰 Monedas Soportadas

El BCE admite una amplia gama de monedas, incluyendo:

- **Principales**: USD 🇺🇸, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, CAD 🇨🇦, AUD 🇦🇺, NZD 🇳🇿
- **Europeas/Regionales**: SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, PLN 🇵🇱, CZK 🇨🇿, HUF 🇭🇺, RON 🇷🇴, BGN 🇧🇬, TRY 🇹🇷
- **Globales / Emergentes**: CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦

## 📝 Notas Importantes

- **Formato de cotización**: Los tipos se expresan como la cantidad de moneda extranjera por 1 EUR (por ejemplo, 1 EUR = 1.08 USD). LibreFolio normaliza automáticamente este tipo dependiendo de la moneda base de su cartera.
- **Sin datos de fin de semana**: El BCE no publica tipos los sábados, domingos ni los festivos oficiales del BCE (por ejemplo, Viernes Santo, Lunes de Pascua, Navidad). LibreFolio conservará el tipo del último día hábil disponible para las valoraciones de fin de semana.
