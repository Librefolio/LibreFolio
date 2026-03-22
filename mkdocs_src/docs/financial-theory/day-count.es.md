# 📅 Convenios de Cómputo de Días

Un **Convenio de Cómputo de Días** determina cómo se devenga el interés a lo largo del tiempo para una variedad de instrumentos financieros, como bonos, préstamos e hipotecas. Define dos cosas:

1. Cómo calcular el número de días entre dos fechas.
2. Cómo calcular el número de días en un año.

## 🔧 Uso en LibreFolio

Los convenios de cómputo de días son utilizados activamente por el proveedor de fuente de activos *Scheduled Investment* (`backend/app/services/asset_source_providers/scheduled_investment.py`) para cálculos de rendimiento sintético. La función `calculate_day_count_fraction()` en `backend/app/utils/financial_math.py` implementa los cuatro convenios y devuelve una fracción de tiempo `Decimal` utilizada en los cálculos de devengo de intereses.

El convenio predeterminado es **ACT/365**.

## 📅 ACT/365 (Actual/365)

- **Días**: El número real de días entre dos fechas.
- **Año**: 365 días (asumido).
- **Fórmula**: $t = \frac{\text{días reales}}{365}$
- **Uso**: Común en los mercados monetarios del Reino Unido y para algunos bonos gubernamentales. **Predeterminado en LibreFolio.**

## 📅 ACT/360 (Actual/360)

- **Días**: El número real de días entre dos fechas.
- **Año**: 360 días (asumido).
- **Fórmula**: $t = \frac{\text{días reales}}{360}$
- **Uso**: Muy común en los mercados monetarios de EE. UU. y para préstamos comerciales.

## 📐 30/360 (Bond Basis)

- **Días**: Se calcula asumiendo que cada mes tiene 30 días.
- **Año**: 360 días (asumido).
- **Fórmula**: $t = \frac{360(Y_2 - Y_1) + 30(M_2 - M_1) + (D_2 - D_1)}{360}$
- **Uso**: Estándar para bonos corporativos de EE. UU. y muchos bonos municipales.

## 📅 ACT/ACT (Actual/Actual)

- **Días**: El número real de días entre dos fechas.
- **Año**: El número real de días en el año (365 o 366 en años bisiestos).
- **Fórmula**: $t = \frac{\text{días reales}}{365 \text{ o } 366}$
- **Uso**: Estándar para bonos del Tesoro de EE. UU. Maneja correctamente los años bisiestos calculando la fracción para cada año por separado.

!!! info "¿Por qué es importante?"
    La diferencia entre convenios puede ser significativa para capitales grandes o plazos largos. Por ejemplo, para un préstamo de 1.000.000 € al 5% con duración de 30 días: ACT/365 produce 4.109,59 € en intereses, mientras que ACT/360 produce 4.166,67 € — una diferencia de 57 €.

:material-link: [Convenio de Cómputo de Días en Wikipedia](https://en.wikipedia.org/wiki/Day_count_convention){ target="_blank" }
