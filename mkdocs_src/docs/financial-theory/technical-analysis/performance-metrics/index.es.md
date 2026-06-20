# 📈 Métricas de Rendimiento

Al evaluar el éxito de una cartera de inversión, no basta con mirar únicamente el saldo total o el beneficio absoluto. Para comprender realmente el rendimiento, se necesitan métricas estandarizadas que respondan a diferentes preguntas: "¿Cómo se han comportado mis activos?", "¿Qué tan acertado fue el momento de mis operaciones?" y "¿Cuál es el retorno de esta operación específica?".

---

## 🎭 Los dos actores en su cartera

Para entender por qué existen múltiples métricas, imagine que hay dos "actores" diferentes gestionando su patrimonio:

1. **El Mercado (Los Activos):** Hace que los precios de las cosas que posee suban o bajen.
2. **Usted (El Inversor):** Decide *cuándo* depositar o retirar efectivo de la cartera.

Estos dos actores pueden tener rendimientos muy diferentes. Usted podría elegir una acción excelente (El Mercado se comporta bien), pero podría comprarla en el punto más alto justo antes de una caída (Usted se comporta mal). LibreFolio utiliza diferentes métricas para aislar estos dos comportamientos.

---

## 📚 Temas de este capítulo

| Métrica / Concepto | Descripción |
|------------------|-------------|
| **[ROI Simple](roi.md)** | Retorno porcentual absoluto generado por una inversión en relación con su coste. Ideal para evaluar posiciones. |
| **[TWRR](twrr.md)** | Tasa de Retorno Ponderada en el Tiempo (Time-Weighted Rate of Return). Mide el rendimiento puro de los activos subyacentes, ignorando la temporalidad de los flujos de caja. |
| **[MWRR (XIRR)](mwrr.md)** | Tasa de Retorno Ponderada por el Dinero (Money-Weighted Rate of Return). Mide su rendimiento personal como inversor, teniendo en cuenta la temporalidad de los flujos de caja. |
| **[Coste Medio Ponderado](weighted-average-cost.md)** | El coste unitario medio de un activo en una cartera, ponderado por las cantidades adquiridas. |

---

## 💡 El ejemplo práctico (TWRR vs MWRR)

Veamos un ejemplo extremo para ver cómo el [TWRR](twrr.md) y el [MWRR](mwrr.md) cuentan dos historias completamente diferentes, pero matemáticamente correctas.

* **Mes 1:** Usted tiene una gran intuición. Compra **1.000 €** de una acción. Al mes siguiente, la acción se duplica (+100%). Ahora tiene **2.000 €**.
* **Mes 2:** Contagiado por la emoción, vacía su cuenta de ahorros y deposita otros **100.000 €** en la misma acción. Ahora tiene 102.000 € invertidos.
* **Mes 3:** Desafortunadamente, la acción cae un **-10%**. Su capital total cae de 102.000 € a **91.800 €**.

Si mira LibreFolio ahora, ¿qué verá?

### 📈 Su TWRR será: +80%
*¿Por qué?* Los activos que eligió subieron un +100% y luego bajaron un -10%. Matemáticamente: 

$$
(2.0 \times 0.9) - 1 = +0.8
$$

Los activos que eligió se comportaron increíblemente bien. Si hubiera invertido todo su dinero el día 1, sería rico. Su *selección de activos* fue excelente.

### 📉 Su MWRR será: FUERTEMENTE NEGATIVO (aprox. -9%)
*¿Por qué?* Usted depositó un total de 101.000 € de su propio bolsillo, pero actualmente posee 91.800 €. ¡Ha sufrido una pérdida real y absoluta de 9.200 €! 
Su mala elección del momento —depositar 100.000 € justo en el pico antes de una caída— destruyó sus retornos. Su *timing* fue terrible.

---

## ⚖️ Por qué LibreFolio muestra ambos lado a lado

Al colocar el TWRR y el MWRR uno junto al otro en su panel de control, LibreFolio le proporciona un diagnóstico conductual inmediato:

- **TWRR > MWRR:** *"Está eligiendo buenas inversiones, pero su timing es malo. Es probable que esté comprando en el punto más alto (FOMO) y arrastrando sus retornos personales a la baja".*
- **MWRR > TWRR:** *"¡Tiene un timing excelente! Está comprando activos con descuento cuando el mercado cae, impulsando sus retornos personales por encima del promedio del mercado".*
