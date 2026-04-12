# 💰 Dividendo

Un **dividendo** es una distribución de efectivo pagada por una empresa (o fondo) a sus accionistas, que representa una parte de los beneficios de la compañía.

---

## 📖 Definición

Los dividendos son pagos periódicos realizados a partir de las ganancias de una empresa a sus accionistas. Normalmente se pagan trimestralmente (común en EE. UU.) o semestralmente/anualmente (común en Europa). Los ETF también distribuyen dividendos recaudados de sus posiciones subyacentes.

**Fechas clave** en el ciclo de vida del dividendo:

| Fecha | Significado |
|------|---------|
| **Fecha de declaración** | La junta anuncia el monto del dividendo y las fechas |
| **Fecha ex-dividendo** | Primer día de negociación en el que los compradores NO reciben el dividendo. El precio de la acción normalmente cae en la cantidad del dividendo al abrir el mercado. |
| **Fecha de registro** | La empresa verifica quién posee las acciones (normalmente 1-2 días después de la fecha ex) |
| **Fecha de pago** | El efectivo se deposita en las cuentas de los accionistas |

---

## 📉 Impacto en el Precio de Mercado

En la **fecha ex-dividendo**, el precio de la acción teóricamente cae en el **monto exacto del dividendo**. Esto se debe a que los nuevos compradores en esa fecha no recibirán el próximo pago.

!!! example "Ejemplo"

    **Apple (AAPL)** cotiza a $180.00. Un dividendo trimestral de $0.25 pasa a ex-dividendo.

    - **Cierre antes de la fecha ex**: $180.00
    - **Apertura fecha ex** (teórica): $179.75
    - **Diferencia**: −$0.25 (= monto del dividendo)

    En la práctica, las fuerzas del mercado pueden hacer que el precio de apertura real difiera, pero la bolsa **ajusta el precio de referencia** a la baja exactamente en $0.25.

---

## 📊 Efecto en el Retorno Total

Si bien el precio cae en la cantidad del dividendo, el **retorno total** (cambio de precio + dividendos recibidos) permanece neutral en el momento del pago. Con el tiempo, los dividendos reinvertidos se capitalizan significativamente.

$$
\text{Total Return} = \frac{P_{\text{end}} - P_{\text{start}} + \sum D_i}{P_{\text{start}}}
$$

Donde $D_i$ representa cada pago de dividendo recibido durante el periodo de tenencia.

---

## 🔢 Rentabilidad por Dividendo

La **rentabilidad por dividendo** expresa el dividendo anual como un porcentaje del precio actual de la acción:

$$
\text{Dividend Yield} = \frac{\text{Annual Dividends per Share}}{\text{Current Price per Share}} \times 100\%
$$

!!! tip "Rangos típicos"

    - Acciones de crecimiento: 0–1%
    - Empresas maduras: 2–4%
    - Alto rendimiento / REITs: 4–8%+

---

## 🧮 Cómo maneja LibreFolio los Dividendos

En LibreFolio, se registra un evento `DIVIDEND` con:

- **Fecha**: La fecha ex-dividendo
- **Monto**: El pago en efectivo por acción
- **Moneda**: La moneda del pago (ej. USD, EUR)

Para los **activos con precio de mercado** (Yahoo Finance, justETF), los eventos de dividendos son informativos: explican la brecha de precio de la fecha ex, pero no modifican el precio obtenido. Para los activos de **Scheduled Investment**, son integrales para el modelo de precios.

---

## 🔗 Relacionado

- 📅 **[Descripción general de eventos de activos](index.md)** — Todos los tipos de eventos
- 💸 **[Tipos de transacciones](../transaction-types/index.md)** — Cómo aparecen los dividendos en las transacciones de la cartera
- 📈 **[Retornos y tasas de crecimiento](../../fundamentals/returns.md)** — Retorno total incluyendo dividendos
