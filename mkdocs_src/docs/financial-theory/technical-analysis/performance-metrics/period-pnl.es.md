# 📊 P&L del Periodo (Profit and Loss)

*[⬅️ Volver a la descripción general de métricas de rendimiento](index.md)*

## 💡 ¿Qué es el P&L del Periodo?

El **P&L del Periodo** (Profit and Loss / Ganancias y Pérdidas) representa el resultado monetario absoluto generado por su cartera dentro de la ventana de tiempo seleccionada, ajustado por los flujos de efectivo externos.

Responde a la pregunta directa: _"¿Cuánto dinero he ganado o perdido realmente durante este periodo?"_

A diferencia de las métricas basadas en porcentajes (como el [ROI Simple](roi.md) o el [TWRR](twrr.md)), el P&L del Periodo se expresa como una cantidad monetaria absoluta (ej. EUR, USD). Crucialmente, está **ajustado por flujo de caja**, lo que significa que aísla el rendimiento real de la inversión de sus depósitos y retiros.

---

## 🧮 Fórmula

LibreFolio calcula el P&L del Periodo mediante la siguiente ecuación:

$$
\text{P}\&\text{L del Periodo} = \text{NAV}_{\text{fin}} - \text{NAV}_{\text{inicio}} - \text{Flujos Externos Netos}
$$

Donde:

- **$\text{NAV}_{\text{inicio}}$**: El [Valor Liquidativo Neto (NAV / Net Worth)](nav.md) al inicio de la ventana de tiempo seleccionada.
- **$\text{NAV}_{\text{fin}}$**: El Valor Liquidativo Neto al final de la ventana de tiempo seleccionada.
- **$\text{Flujos Externos Netos}$**: El capital neto inyectado o retirado por el inversor durante el periodo, definido como:

$$
\text{Flujos Externos Netos} = \text{Depósitos} - \text{Retiros}
$$

Solo los flujos que entran o salen del alcance de la cartera seleccionada cuentan como externos. Las transferencias internas entre brokers o cuentas dentro del alcance no afectan a este cálculo.

---

## 📝 Ejemplo Práctico

Supongamos que su cartera tiene las siguientes métricas para un año determinado:

- **NAV al inicio**: €27,000
- **Depósitos Totales**: €1,000
- **Retiros Totales**: €0
- **NAV al final**: €33,000

Primero, calculamos los Flujos Externos Netos:

$$
\text{Flujos Externos Netos} = 1,000 - 0 = \text{€}1,000
$$

Luego, calculamos el P&L del Periodo:

$$
\text{P}\&\text{L del Periodo} = 33,000 - 27,000 - 1,000 = \text{€}5,000
$$

### 🔍 Explicación del Resultado

Aunque la valoración total de su cartera aumentó en **€6,000** (de €27,000 a €33,000), **€1,000** de ese incremento corresponde a su propio dinero aportado. Por lo tanto, sus inversiones generaron una ganancia neta real de **€5,000**.

Si la fórmula no se ajustara por flujos externos, mostraría erróneamente un beneficio de €6,000, confundiéndole al pensar que sus activos tuvieron un rendimiento mejor del que realmente tuvieron.

---

## ⚖️ Diferencias Clave

- **vs. ROI / TWRR / MWRR**: Estas son métricas basadas en porcentajes que muestran la tasa de retorno. El P&L del Periodo muestra la cantidad monetaria absoluta de la ganancia/pérdida.
- **vs. Ganancia/Pérdida Latente**: La ganancia/pérdida latente es una instantánea de las posiciones abiertas actuales en comparación con su coste de adquisición original. El P&L del Periodo mide el rendimiento tanto de las posiciones abiertas como de las cerradas (ganancias realizadas, dividendos, intereses) específicamente dentro de los límites de la ventana de tiempo elegida.
