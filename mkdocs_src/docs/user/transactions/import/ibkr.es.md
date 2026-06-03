# 🏦 Interactive Brokers (IBKR)

!!! info "Beta"

    Este plugin está en fase **Beta**: se ha probado con archivos de muestra, pero pueden existir casos excepcionales.

## Cómo exportar

1. Inicie sesión en el [Portal del Cliente de Interactive Brokers](https://www.interactivebrokers.com) o en Trader Workstation (TWS).
2. Vaya a **Reports → Activity → Flex Queries** o **Statements → Activity Statement**.
3. Seleccione el rango de fechas y exporte como **CSV**.

## Notas

- Compatible con los informes de actividad estándar de IBKR (operaciones, dividendos, comisiones, depósitos, retiros).
- Se admiten cuentas multi-moneda.
- Las acciones corporativas (divisiones, fusiones) pueden requerir ajustes manuales.

## 🔗 Referencia para desarrolladores

→ [Proveedor IBKR — Detalles de implementación](../../../developer/backend/brim/providers_list.md)
