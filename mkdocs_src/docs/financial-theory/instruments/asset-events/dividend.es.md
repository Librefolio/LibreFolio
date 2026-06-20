# 💰 Dividendo

Un **dividendo** es una distribución de efectivo pagada por una empresa (o fondo) a sus accionistas, que representa una parte de los beneficios de la empresa.

---

## 📖 Definición

Los dividendos son pagos periódicos realizados a partir de las ganancias de una empresa a sus accionistas. Normalmente se pagan trimestralmente (común en EE. UU.) o semestralmente/anualmente (común en Europa). Los ETF también distribuyen dividendos recaudados de sus activos subyacentes.

**Fechas clave** en el ciclo de vida del dividendo:

| Fecha | Significado |
|------|---------|
| **Fecha de declaración&nbsp;** | La junta anuncia el importe del dividendo y las fechas |
| **Fecha ex-dividendo&nbsp;** | Primer día de cotización en el que los compradores NO reciben el dividendo. El precio de la acción suele bajar el importe del dividendo al abrir el mercado. |
| **Fecha de registro&nbsp;** | La empresa verifica quién posee las acciones (normalmente 1-2 días después de la fecha ex) |
| **Fecha de pago&nbsp;** | El efectivo se deposita en las cuentas de los accionistas |

---

## 📉 Impacto en el Precio de Mercado

En la **fecha ex-dividendo**, el precio de la acción cae teóricamente el **importe exacto del dividendo**. Esto se debe a que los nuevos compradores en esa fecha no recibirán el próximo pago.

!!! example "Example"

    **Apple (AAPL)** cotiza a $180.00. Un dividendo trimestral de $0.25 entra en fecha ex-dividendo.

    - **Antes del cierre de la fecha ex**: $180.00
    - **Apertura de la fecha ex** (teórica): $179.75
    - **Diferencia**: −$0.25 (= importe del dividendo)

    En la práctica, las fuerzas del mercado pueden hacer que el precio de apertura real difiera, pero la bolsa **ajusta el precio de referencia** a la baja exactamente en $0.25.

---

## 📊 Efecto en el Retorno Total

Aunque el precio cae el importe del dividendo, el **retorno total** (cambio de precio + dividendos recibidos) permanece neutral en el momento del pago. Con el tiempo, los dividendos reinvertidos se capitalizan significativamente.

$$
\text{Total Return} = \frac{P_{\text{end}} - P_{\text{start}} + \sum D_i}{P_{\text{start}}}
$$

Donde $D_i$ representa cada pago de dividendo recibido durante el periodo de tenencia.

---

## 🔢 Rentabilidad por Dividendo

La **rentabilidad por dividendo** expresa el dividendo anual como un porcentaje del precio actual de la acción:

$$
\text{Dividend Yield} = \frac{\text{Dividendos anuales por acción}}{\text{Precio actual por acción}} \times 100\%
$$

!!! tip "Typical ranges"

    - Acciones de crecimiento: 0–1%
    - Empresas maduras: 2–4%
    - High-yield / REITs: 4–8%+

---

## 🧮 Cómo gestiona LibreFolio los dividendos

En LibreFolio, un evento `DIVIDEND` (y la transacción de cartera correspondiente) se registra con:

- **Fecha**: La fecha ex-dividendo
- **Importe**: El pago en efectivo por acción
- **Moneda**: La moneda del pago (ej. USD, EUR)

### La diferencia contable: Dividendo frente a Interés
Es fundamental distinguir entre una transacción de **Dividendo** y una de **Interés** a nivel de base de datos:

1. **Dividendo (basado en capital)**: En el seguimiento de cartera de partida doble, un dividendo representa una entrada de efectivo (`cash.amount > 0`) generada por la tenencia de acciones de un activo de capital específico. El número de acciones poseídas en la fecha ex es constante; no se añaden ni eliminan acciones durante este pago en efectivo. Por lo tanto, la transacción de la base de datos requiere `quantity = 0` para evitar el doble conteo o la inflación del saldo de acciones. Cualquier información sobre el número de acciones que generaron el pago se trata como *informativa* y se almacena habitualmente en el campo de descripción.
2. **Interés (basado en deuda/rendimiento)**: Un pago de intereses representa el rendimiento de la deuda o de depósitos en efectivo (ej. cuentas de ahorro o cupones de bonos). A diferencia de los dividendos, los intereses no requieren estrictamente que exista un activo de capital subyacente (el activo es opcional).

Para los **activos con precio de mercado** (Yahoo Finance, justETF), los eventos de dividendos son informativos: explican la brecha de precio en la fecha ex, pero no modifican el precio obtenido. Para los activos de **inversión programada**, son parte integrante del modelo de precios.

---

## 🔗 Relacionado

- 📅 **[Descripción general de eventos de activos](index.md)** — Todos los tipos de eventos
- 💸 **[Tipos de transacciones](../transaction-types/index.md)** — Cómo aparecen los dividendos en las transacciones de la cartera
- 📈 **[Retornos y Tasas de Crecimiento](../../fundamentals/returns.md)** — Retorno total incluyendo dividendos
