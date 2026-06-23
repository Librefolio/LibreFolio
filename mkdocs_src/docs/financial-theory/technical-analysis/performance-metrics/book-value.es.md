# 📖 Valor Contable

*[⬅️ Volver a la descripción general de métricas de rendimiento](index.md)*

## 💡 ¿Qué es el Valor Contable?

En LibreFolio, el **Valor Contable** (Book Value) representa el coste contable histórico (coste de adquisición o cost basis) de su cartera. Refleja el importe neto del capital que realmente ha comprometido en sus posiciones abiertas actuales, más el efectivo.

Responde a la pregunta: _"¿Cuánto costó construir mi cartera actual?"_

A diferencia del Valor Liquidativo Neto (NAV), que fluctúa con los precios diarios del mercado, el Valor Contable solo cambia cuando compra o vende activos, o cuando deposita/retira efectivo. No representa el valor de mercado liquidado actual.

---

## 🧮 Fórmula

El Valor Contable se calcula utilizando la siguiente fórmula:

$$
\text{Valor Contable} = \text{Coste de Posiciones Abiertas} + \text{Efectivo} + \text{Coste en Tránsito}
$$

Donde:

- **$\text{Coste de Posiciones Abiertas}$**: El coste base total de sus posiciones abiertas, calculado multiplicando la cantidad de cada activo por su [Coste Medio Ponderado (CMP)](weighted-average-cost.md).
- **$\text{Efectivo}$**: El saldo de efectivo real depositado en las cuentas de los brokers incluidos en el alcance.
- **$\text{Coste en Tránsito}$**: El coste contable del efectivo o de los activos actualmente en tránsito entre las cuentas incluidas en el alcance. Este concepto se introduce para gestionar las transferencias (por ejemplo, transferencias bancarias o traspasos de valores) que contablemente salen el día 1 de la cuenta de origen y llegan el día 5 a la cuenta de destino debido a los plazos técnicos de ejecución.

---

## 📝 Ejemplo Práctico

Considere una cartera con los siguientes datos:

- **Coste de Posiciones Abiertas (Coste de Adquisición)**: €27,000
- **Efectivo**: €600
- **Activos en Tránsito (Coste Contable)**: €0

El Valor Contable se calcula como:

$$
\text{Valor Contable} = 27,000 + 600 + 0 = \text{€}27,600
$$

### 📊 Comparación con el NAV (Rendimiento Latente)

Si el valor de mercado actual ([NAV](nav.md)) de esta cartera es **€33,000**, podemos calcular la **Ganancia/Pérdida Latente** (unrealized gain/loss) comparándola con el Valor Contable:

$$
\text{Rendimiento Latente} = \text{NAV} - \text{Valor Contable}
$$

$$
\text{Rendimiento Latente} = 33,000 - 27,600 = +\text{€}5,400
$$

Esto indica que el valor de mercado de su cartera ha aumentado en €5,400 por encima del coste de adquisición total pagado por ella.

---

## ⚙️ Nota sobre los Métodos de Coste Medio

Para determinar el coste contable de las posiciones abiertas, LibreFolio utiliza el método del [Coste Medio Ponderado (CMP)](weighted-average-cost.md) como algoritmo predeterminado para el seguimiento de inventarios:

- Cada vez que compra un activo, se actualiza el coste unitario medio de adquisición.
- Cada vez que vende un activo, la base del coste se reduce de forma proporcional en función del CMP en el momento de la venta, dejando inalterado el coste unitario de las participaciones restantes.
