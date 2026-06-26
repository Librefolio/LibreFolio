# <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> CSV Genérico

El proveedor de **CSV Genérico** es un fallback flexible para los brókers que no cuentan con soporte directo. Permite el mapeo manual de columnas para que pueda importar desde cualquier exportación basada en CSV.

## Cuándo usarlo

- Su bróker no se encuentra en la lista de brókers compatibles.
- Un bróker compatible cambió su formato de exportación y el plugin aún no ha sido actualizado.
- Tiene una hoja de cálculo personalizada o un CSV generado por script que desea importar.

## Cómo funciona

1. Cargue su archivo CSV.
2. LibreFolio muestra las columnas detectadas sin procesar.
3. Mapee cada columna con el campo correspondiente de LibreFolio (fecha, tipo, activo, cantidad, monto, moneda, descripción).
4. Previsualice las filas analizadas y confirme la importación.

---

## 🔄 Convertir un informe personalizado

Si su fuente de datos no es compatible de forma nativa, puede escribir un script de conversión para transformarla al formato CSV Genérico.

!!! info "Especificaciones técnicas para desarrolladores y LLMs"

    La especificación completa del formato — incluyendo convenciones de signo, cuándo usar cada tipo de transacción, patrones P2P, gestión de cancelaciones y ejemplos prácticos — se encuentra en la documentación técnica:

    **[CSV Genérico — Especificación Técnica](../../../developer/backend/brim/generic_csv.md)**

    Puede pegar esa página directamente en un LLM (ChatGPT, Claude, Gemini…) junto con algunas filas de ejemplo de su archivo fuente y pedirle que escriba un script Python de conversión.

---

## 📋 Referencia de columnas

Estas son las columnas reconocidas por LibreFolio en un archivo CSV Genérico. Los nombres de columnas no distinguen entre mayúsculas y minúsculas.

| Columna | ¿Obligatoria? | Alias aceptados | Descripción |
|---------|--------------|-----------------|-------------|
| **`date`** | ✅ Siempre | `data`, `settlement_date`, `value_date`, `trade_date`, `fecha`, `datum`, `transaction_date`, `exec_date` | Fecha de la transacción |
| **`type`** | ✅ Siempre | `tipo`, `transaction_type`, `operation`, `operazione`, `action`, `azione`, `trans_type`, `op_type` | Tipo de transacción — ver valores abajo |
| **`quantity`** | Requerida para BUY/SELL/TRANSFER/ADJUSTMENT | `quantità`, `qty`, `shares`, `azioni`, `units`, `unità`, `amount_shares`, `num_shares` | Número de unidades. **Negativo para SELL, positivo para BUY.** |
| **`amount`** | Requerida para la mayoría de tipos | `importo`, `value`, `cash`, `cash_amount`, `total`, `totale`, `net_amount`, `gross_amount`, `price` | Impacto en efectivo. **Negativo cuando el dinero sale, positivo cuando entra.** Vacío para TRANSFER y ADJUSTMENT. |
| **`currency`** | Opcional (EUR por defecto) | `valuta`, `ccy`, `curr`, `currency_code`, `divisa`, `währung` | Código de divisa ISO 4217 |
| **`asset`** | Requerida para BUY/SELL/DIVIDEND/TRANSFER/ADJUSTMENT | `symbol`, `ticker`, `isin`, `asset_id`, `instrument`, `strumento`, `security`, `titolo`, `name`, `nome` | Ticker, ISIN, o nombre consistente para activos no cotizados |
| **`description`** | Opcional | `descrizione`, `notes`, `memo`, `note`, `details`, `dettagli`, `comment`, `commento` | Texto libre |

### Valores válidos para `type`

`BUY` · `SELL` · `DIVIDEND` · `INTEREST` · `DEPOSIT` · `WITHDRAWAL` · `FEE` · `TAX` · `TRANSFER` · `ADJUSTMENT` · `FX_CONVERSION` · `CASH_TRANSFER`

---

## 🔗 Ver también

- **[CSV Genérico — Especificación Técnica](../../../developer/backend/brim/generic_csv.md)** — Convenciones de signo, patrones P2P, gestión de cancelaciones, consejo LLM
- **[Arquitectura BRIM](../../../developer/backend/brim/architecture.md)** — Cómo funciona el asistente de importación

