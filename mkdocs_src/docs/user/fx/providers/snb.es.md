# <img src="https://data.snb.ch/favicon.ico" alt=""> Banco Nacional Suizo (SNB)

El proveedor **Banco Nacional Suizo (SNB)** publica **promedios mensuales** de tipos de cambio para el franco suizo (CHF), obtenidos del SNB Data Portal, de acceso público. Es una fuente estable y autorizada para activos basados en CHF.

!!! warning "Solo datos mensuales — no hay tipos de cambio diarios"

    El SNB **no** ofrece un conjunto de datos de tipos de cambio diarios: cada valor es el **promedio de un mes calendario**, con fecha del **día 1 de ese mes**. En las cadenas de conversión, un tipo de cambio solo se calcula en fechas en las que **todos** los proveedores involucrados tienen datos, por lo que encadenar a través del SNB produce un punto por mes. Si necesitas tipos de cambio de CHF día a día, usa otro proveedor (p. ej. ECB o FED) para el par.

## 📊 Capacidades

- ✅ **Precio actual**: Último promedio mensual disponible
- ✅ **Historial**: Promedios mensuales históricos
- ❌ **Búsqueda**: Sin búsqueda de activos (solo tipos FX)

## 🔧 Especificaciones

- **Moneda base**: CHF 🇨🇭
- **Frecuencia de actualización**: Mensual — los nuevos promedios se publican alrededor del segundo día hábil del mes siguiente
- **Clave API**: No requerida (API pública del SNB Data Portal)

## 💰 Monedas admitidas

El SNB cubre alrededor de **25 monedas** frente al CHF; LibreFolio carga dinámicamente la lista exacta desde el SNB Data Portal. Incluye:

- **Principales**: USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CNY 🇨🇳
- **Globales**: CAD 🇨🇦, AUD 🇦🇺 y otras monedas del mundo

## 📝 Notas importantes

- **Cotización de monedas por unidades múltiples**: El SNB cotiza algunas monedas por **100 unidades** en lugar de 1 unidad (p. ej. `100 JPY = x CHF`). **LibreFolio detecta y normaliza automáticamente estos tipos de cambio** a valores por unidad para garantizar que tus transacciones se calculen correctamente.
- **Un punto por mes**: los tipos de cambio tienen fecha del día 1 de cada mes. Las conversiones en fechas entre dos puntos mensuales utilizan el tipo de cambio más reciente disponible (backward-fill).
