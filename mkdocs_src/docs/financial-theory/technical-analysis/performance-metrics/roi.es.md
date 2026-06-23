# 📉 ROI Simple (Retorno de la Inversión)

*[⬅️ Volver a la descripción general de métricas de rendimiento](index.md)*

## 💡 ¿Qué es?
El ROI Simple mide el porcentaje de retorno absoluto generado por una inversión en relación con su costo, sin considerar el tiempo transcurrido ni los flujos de caja de manera compleja. 

## 🧮 Fórmula

$$
ROI = \frac{\text{Valor Actual}}{\text{Precio de Compra Medio (PCM)}} - 1
$$

## 🎯 Cuándo usarlo
- Para evaluar una **sola posición** (por ejemplo, "¿Cuánto he ganado con mis acciones de Apple?").
- Cuando se desea una instantánea rápida e intuitiva de la ganancia total no ajustada.

## ⚠️ El defecto: Dilución del flujo de caja
El ROI Simple deja de ser preciso cuando se realizan inversiones posteriores en el mismo activo. Si compras una acción y sube un +50%, tu ROI es del +50%. Si luego inviertes 10 veces más capital en la misma acción y el precio no se mueve, tu ganancia absoluta sigue siendo la misma, pero tu nueva y masiva base de capital diluirá instantáneamente tu ROI, bajándolo quizás al +5%. Parecerá que tu rendimiento colapsó, aunque el mercado no se haya movido. Para corregir este efecto de dilución y evaluar los rendimientos monetarios absolutos ajustados a estos movimientos de capital, consulte la métrica [P&L del Periodo](period-pnl.md).
