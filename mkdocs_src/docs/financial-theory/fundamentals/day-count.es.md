# 📅 Convenciones de Conteo de Días

Una **Convención de Conteo de Días** determina cómo se devengan los intereses a lo largo del tiempo para diversos instrumentos financieros, como bonos, préstamos e hipotecas. Define dos cosas:

1. Cómo calcular el número de días entre dos fechas.
2. Cómo calcular el número de días de un año.

## 🔧 Uso en LibreFolio

Las convenciones de conteo de días son utilizadas activamente por el proveedor de fuentes de activos de **Inversión Programada** (`backend/app/services/asset_source_providers/scheduled_investment.py`) para cálculos de rendimiento sintético. La función `calculate_day_count_fraction()` en `backend/app/utils/financial_math.py` implementa las cuatro convenciones y devuelve una fracción de tiempo `Decimal` utilizada en los cálculos de devengo de intereses.

La convención por defecto es **ACT/365**.

## 📅 ACT/365 (Actual/365)

- **Días**: El número real de días entre dos fechas.
- **Año**: Se asume que tiene 365 días.
- **Fórmula**: $t = \frac{\text{días reales}}{365}$
- **Uso**: Común en los mercados monetarios del Reino Unido y para algunos bonos gubernamentales. **Predeterminado en LibreFolio.**

## 📅 ACT/360 (Actual/360)

- **Días**: El número real de días entre dos fechas.
- **Año**: Se asume que tiene 360 días.
- **Fórmula**: $t = \frac{\text{días reales}}{360}$
- **Uso**: Muy común en los mercados monetarios de EE. UU. y para préstamos comerciales.

## 📐 30/360 (Base de bono)

- **Días**: Calculados asumiendo que cada mes tiene 30 días.
- **Año**: Se asume que tiene 360 días.
- **Fórmula**: $t = \frac{360(Y_2 - Y_1) + 30(M_2 - M_1) + (D_2 - D_1)}{360}$
- **Uso**: Estándar para bonos corporativos de EE. UU. y muchos bonos municipales.

## 📅 ACT/ACT (Actual/Actual)

- **Días**: El número real de días entre dos fechas.
- **Año**: El número real de días del año (365 o 366 para años bisiestos).
- **Fórmula**: $t = \frac{\text{días reales}}{365 \text{ o } 366}$
- **Uso**: Estándar para los bonos del Tesoro de EE. UU. Gestiona correctamente los años bisiestos calculando la fracción para cada año por separado.

!!! info "¿Por qué es esto importante?"

    La diferencia entre convenciones puede ser significativa para importes de capital elevados o duraciones largas. Por ejemplo, 30 días en un préstamo de 1 M€ al 5%: ACT/365 genera 4.109,59 € en intereses, mientras que ACT/360 genera 4.166,67 €, una diferencia de 57 € para el mismo periodo de 30 días.

:material-link: [Convención de Conteo de Días en Wikipedia](https://en.wikipedia.org/wiki/Day_count_convention){ target="_blank" }
