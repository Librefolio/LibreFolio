# ⚖️ Asignación de Activos

La asignación de activos es el proceso de decidir **cómo distribuir su cartera** entre diferentes clases de activos. Las investigaciones demuestran consistentemente que la asignación de activos explica la mayor parte de la variabilidad del rendimiento de la cartera, más que la selección de valores individuales o el *market timing*.

---

## 📊 Asignación Estratégica vs Táctica

### 🏗️ Asignación Estratégica de Activos (SAA)

Un **objetivo a largo plazo** basado en su tolerancia al riesgo, horizonte temporal y metas:

| Perfil | Acciones | Bonos | Alternativos | Efectivo |
|---------|----------|-------|---------------|----------|
| Agresivo (horizonte largo) | 80-90% | 5-15% | 5-10% | 0-5% |
| Balanceado | 50-60% | 30-40% | 5-10% | 5% |
| Conservador (horizonte corto) | 20-30% | 50-60% | 5-10% | 10-20% |

La SAA se revisa con poca frecuencia (anualmente o ante cambios importantes en la vida).

### 🎯 Asignación Táctica de Activos (TAA)

**Desviaciones a corto plazo** respecto al objetivo estratégico para aprovechar oportunidades percibidas en el mercado:

- Sobreponderar una clase de activos que se espera que tenga un rendimiento superior
- Reducir la exposición a una clase de activos que muestre debilidad
- Ajustar según las condiciones macroeconómicas

!!! warning "La TAA es difícil"

    Intentar predecir el momento exacto del mercado (*timing*) es extremadamente difícil. La mayoría de las investigaciones académicas muestran que los ajustes tácticos perjudican más de lo que ayudan a los inversores promedio.

---

## 📈 Trayectoria de Deslizamiento (Glide Path) y Estrategia de Fecha Objetivo

Una **trayectoria de deslizamiento** (*glide path*) desplaza gradualmente la asignación de agresiva (más acciones) a conservadora (más bonos) a medida que el inversor se acerca a su fecha objetivo (normalmente la jubilación):

$$
w_{stocks}(t) = w_{max} - (w_{max} - w_{min}) \cdot \frac{t}{T}
$$

donde $t$ son los años transcurridos y $T$ es el tiempo hasta la fecha objetivo.

### 📉 La Justificación

- **Inversores jóvenes**: tienen un horizonte temporal largo → pueden tolerar la volatilidad a corto plazo → deben mantener más acciones.
- **Inversores cercanos a la jubilación**: necesitan preservación de capital → deben mantener más bonos.
- La trayectoria de deslizamiento automatiza esta transición.

---

## 🔄 Reequilibrio

Con el tiempo, los movimientos de los precios de los activos provocan que la cartera se **desvíe** de su asignación objetivo. El reequilibrio restaura los pesos originales.

### 📊 Métodos de Reequilibrio

| Método | Activador | Pros | Contras |
|--------|-------------|------|---------|
| **Calendario** | Horario fijo (mensual, trimestral) | Simple, predecible | Puede provocar operaciones innecesarias |
| **Umbral** | Cuando la asignación se desvía en X% | Solo opera cuando es necesario | Requiere monitoreo |
| **Híbrido** | Revisión por calendario, opera si supera el umbral | Lo mejor de ambos | Ligeramente más complejo |

### 📐 Bono de Reequilibrio

En una cartera de activos volátiles y no correlacionados, el reequilibrio sistemático genera un **bono de reequilibrio**: un pequeño rendimiento excedente derivado de la disciplina de "comprar bajo, vender alto" de forma automática:

$$
R_{rebalanced} \approx R_{buy\&hold} + \frac{1}{2} \sum_i w_i \sigma_i^2 (1 - \rho_{avg})
$$

El bono es mayor cuando las volatilidades son altas y las correlaciones son bajas.

---

## 🌍 Diversificación Geográfica

Más allá de la asignación por clase de activo, la diversificación geográfica distribuye el riesgo entre diversas economías:

| Región | Rol | Riesgo Cambiario |
|--------|-----|------------------|
| Doméstica | Posiciones principales, sin riesgo FX | Ninguno |
| Desarrolladas (US, EU, JP) | Crecimiento + estabilidad | Moderado |
| Emergentes (CN, IN, BR) | Mayor potencial de crecimiento | Alto |

!!! info "Cobertura cambiaria"

    Las inversiones extranjeras introducen un [riesgo FX](../../user/fx/index.md). Algunos ETF ofrecen variantes cubiertas (*hedged*) que neutralizan la exposición a la moneda, al costo de la prima de cobertura.

---

## 🔗 Relacionado

- 🔀 **[Diversificación](diversification.md)** — La base matemática de las decisiones de asignación
- 📊 **[Métricas de Riesgo](../technical-analysis/risk-metrics/index.md)** — Medición del riesgo de la cartera
- 📊 **[Tipos de Activos](../instruments/asset-types/index.md)** — Las clases de activos para la asignación
- 💰 **[Tributación](../fundamentals/taxation.md)** — Estrategias de asignación fiscalmente eficientes
