# <img src="https://www.interactivebrokers.com/favicon.ico" alt=""> Interactive Brokers (IBKR)

!!! info "Beta"

    Este plugin está en **Beta** — probado con archivos de ejemplo, pero pueden existir casos límite.

## 📥 Cómo exportar

LibreFolio lee las operaciones de una **Activity Flex Query** exportada como CSV. El
**Activity Statement** estándar no es compatible.

1. Inicia sesión en el [Interactive Brokers Client Portal](https://www.interactivebrokers.com) y abre
   **Flex Queries**, en el menú de informes.
2. Crea una **Activity Flex Query** con solo la sección **Trades**, y selecciona los campos que
   generan estas columnas: `Buy/Sell`, `TradeDate`, `ISIN`, `Quantity`, `TradeMoney`,
   `CurrencyPrimary`, `IBCommission`, `IBCommissionCurrency`.
3. Elige **CSV** como formato y `yyyyMMdd` como formato de fecha (por ejemplo `20240315`), y luego
   guarda la consulta.
4. Ejecútala para el periodo que quieras y descarga el archivo.

## ⚠️ Errores comunes

- **La primera línea debe contener los nombres de las columnas.** LibreFolio reconoce el archivo por las
  cabeceras entrecomilladas `Buy/Sell`, `TradeDate`, `ISIN` e `IBCommission` en su primera línea: mantén
  las cabeceras de columna activadas, y desactiva los registros de cabecera y pie y los códigos de sección.
- **Solo CSV**: las exportaciones en PDF y XML no se leen.

## 📝 Qué se importa

- **Compras y ventas** de instrumentos con un ISIN, en la divisa de la operación (`CurrencyPrimary`;
  USD cuando la columna está vacía).
- **Comisiones**, cada una como una **comisión** independiente sobre el mismo activo y fecha, en
  `IBCommissionCurrency` (o la divisa de la operación cuando esa columna está vacía).
- **No se importan**: dividendos, intereses, impuestos, depósitos y retiros, conversiones de divisa
  (las filas sin un ISIN se omiten con una advertencia) y acciones corporativas. Añádelos a mano, o
  con un archivo [Generic CSV](generic-csv.md).
