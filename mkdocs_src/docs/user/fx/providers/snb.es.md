# <img src="https://data.snb.ch/favicon.ico" alt=""> Banco Nacional Suizo (SNB)

El proveedor **Banco Nacional Suizo (SNB)** publica diariamente los tipos de cambio para el franco suizo (CHF). Es sumamente estable y preciso, lo que lo convierte en una fuente valiosa para activos basados en CHF.

## 📊 Capacidades

- ✅ **Precio Actual**: Tipo de referencia actualizado diariamente
- ✅ **Historial**: Tipos diarios históricos
- ❌ **Búsqueda**: Sin búsqueda de activos (solo tipos de cambio)

## 🔧 Especificaciones

- **Moneda Base**: CHF 🇨🇭
- **Frecuencia de Actualización**: Diariamente en días laborables suizos
- **API Key**: No es necesaria (API pública del SNB Data Portal)

## 💰 Monedas compatibles

El SNB proporciona tipos de cambio para una lista selecta de monedas principales:

- **Monedas compatibles**: USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CAD 🇨🇦, AUD 🇦🇺, SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, CNY 🇨🇳

## 📝 Notas Importantes

- **Cotización de divisas en múltiples unidades**: El SNB cotiza algunas monedas por cada **100 unidades** (por ejemplo, el yen japonés, la corona sueca, la corona noruega, la corona danesa) en lugar de 1 unidad. Por ejemplo, el tipo se muestra como `100 JPY = 0.58 CHF`. **LibreFolio detecta y normaliza automáticamente estos tipos** a valores por unidad para garantizar que sus transacciones se calculen correctamente.
- **Festivos**: Los tipos no se publican en los días festivos bancarios suizos ni los fines de semana.
