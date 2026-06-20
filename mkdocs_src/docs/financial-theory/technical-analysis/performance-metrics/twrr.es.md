# ⏱️ TWRR (Time-Weighted Rate of Return)

*[⬅️ Volver a la descripción general de métricas de rendimiento](index.md)*

## 💡 ¿Qué es?
El TWRR mide el rendimiento "puro" de los activos elegidos (el Mercado), ignorando completamente el momento y la magnitud de los depósitos o retiros.

## 🧮 Cómo funciona
Cada vez que se deposita o retira dinero, el TWRR "divide" la línea de tiempo en un subperiodo. Calcula el rendimiento para ese subperiodo específico y luego encadena (multiplica) todos los subperiodos entre sí. 

$$
R_{TWRR} = \prod_{i=1}^{n} (1 + r_i) - 1
$$

## 🎯 Cuándo utilizarlo
- Para juzgar si los **activos elegidos** son realmente buenos.
- Para comparar su cartera con un benchmark externo (como el S&P 500).
- Los fondos de inversión y los ETF siempre informan el TWRR, ya que el gestor del fondo no puede controlar cuándo los clientes depositan o retiran dinero.
