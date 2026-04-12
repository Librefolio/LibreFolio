# 📈 Proveedor de Yahoo Finance

Yahoo Finance es el proveedor predeterminado para acciones, ETF y fondos mutuos. Ofrece la cobertura más amplia y admite la búsqueda de activos.

## 📊 Funcionalidades

- ✅ **Precio Actual**: Cotizaciones en tiempo real o diferidas
- ✅ **Historial**: Datos completos de precios históricos
- ✅ **Búsqueda**: Buscar activos por nombre o ticker

## 🔧 Configuración

- **Identificador**: Símbolo de ticker de Yahoo Finance (ej., `AAPL`, `VWCE.DE`, `BTC-USD`)
- **Tipo de Identificador**: `TICKER`
- **Parámetros**: Ninguno

## 💡 Ejemplos

| Activo | Ticker |
|-------|--------|
| Apple Inc. | `AAPL` |
| Vanguard FTSE All-World (Xetra) | `VWCE.DE` |
| Bitcoin | `BTC-USD` |
| iShares Core S&P 500 (Milán) | `CSSPX.MI` |

## 📝 Notas

- Para los ETF cotizados en Europa, añada el sufijo de la bolsa (ej., `.DE` para Xetra, `.MI` para Milán, `.AS` para Ámsterdam)
- Los datos de Yahoo Finance pueden tener un retraso de 15 minutos en algunas bolsas
