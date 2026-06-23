# 💼 Valor Liquidativo Neto (NAV) / Valor Neto (Net Worth)

*[⬅️ Volver a la Descripción General de las Métricas de Rendimiento](index.md)*

## 💡 ¿Qué es el NAV / Net Worth?

En el panel de control de LibreFolio, el **Net Asset Value (NAV)** (también conocido como **Net Worth** o **Valor Neto**) representa el valor total de mercado de su cartera al final de la ventana de tiempo seleccionada (`date_to`).

Responde a la pregunta fundamental: _"¿Cuánto vale la cartera dentro del alcance seleccionado en este momento preciso?"_

A diferencia de las métricas de rendimiento basadas en periodos (como el ROI o el P&L), el NAV es una **instantánea (snapshot) en un momento dado**. Aunque su tendencia histórica se puede graficar a lo largo del tiempo, el valor final del NAV que se muestra en el panel de control depende únicamente de la fecha de finalización (`date_to`) y es completamente independiente de la fecha de inicio (`date_from`).

---

## 🧮 Fórmula

LibreFolio calcula el Valor Liquidativo Neto utilizando la siguiente fórmula:

$$
\text{NAV} = \text{Valor de Mercado} + \text{Efectivo} + \text{Valor en Tránsito}
$$

Donde:

- **$\text{Valor de Mercado}$**: La valoración de mercado actual de todos los activos mantenidos (ETF, acciones, bonos, criptomonedas, etc.), calculada utilizando el último precio disponible y convertida a la moneda de destino del portafolio.
- **$\text{Efectivo}$**: El saldo de efectivo real depositado en las cuentas de los brokers incluidos en el alcance seleccionado.
- **$\text{Valor en Tránsito}$**: La valoración de mercado de los fondos o activos actualmente en tránsito interno entre cuentas del mismo alcance (ej. transferencias internas iniciadas pero no completadas aún). Al igual que con el [Valor Contable (Book Value)](book-value.md), este concepto gestiona las transaciones (ej. transferencias bancarias o traspasos de valores) que salen de una cuenta el día 1 y llegan a su destino el día 5 debido a los plazos técnicos de ejecución.

---

## 📝 Ejemplo Práctico

Considere una cartera con los siguientes saldos al final del periodo seleccionado:

- **Valor de Mercado de los Activos**: €32,759
- **Efectivo**: €631
- **Activos en Tránsito**: €0

El Valor Liquidativo Neto se calcula como:

$$
\text{NAV} = 32,759 + 631 + 0 = \text{€}33,390
$$


---

## ⚖️ Diferencias Clave

Para evitar confusiones, es importante distinguir el NAV de otras métricas del panel de control:

- **Frente al Book Value (Valor Contable)**: El NAV representa el **valor de mercado actual** de sus activos. El [Book Value](book-value.md) representa el **coste de adquisición histórico** (lo que pagó originalmente por ellos). La diferencia entre ambos constituye la plusvalía o minusvalía latente (unrealized gain/loss).
- **Frente al Period P&L (P&L del Periodo)**: El NAV indica el valor absoluto de su patrimonio. El [Period P&L](period-pnl.md) mide la *variación* de este patrimonio en un periodo determinado, corregida por los depósitos y retiros externos de capital.

---

## ⚠️ Calidad de los Datos y Valoración

Dado que el NAV se basa en los precios de mercado y los tipos de cambio (FX) para convertir todos los activos a su moneda de referencia:

- Si faltan datos de precios o tipos de cambio para cualquier activo en la fecha final (`date_to`), la valoración puede ser incompleta.
- En tales casos, LibreFolio muestra el **Data Quality Banner** (Banner de Calidad de Datos) en la parte superior del panel de control para alertarle de que algunas valoraciones se basan en precios obsoletos o ausentes.
