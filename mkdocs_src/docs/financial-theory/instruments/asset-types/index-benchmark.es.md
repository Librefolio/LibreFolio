# <img src="../../../static/icons/asset-types/other.png" width="32" style="vertical-align: middle;" /> Índice y Benchmark

Un **índice** es una medida estadística de una sección del mercado financiero. Rastrea el rendimiento de un grupo de activos y sirve como un **benchmark** contra el cual los inversores miden el rendimiento de su propia cartera.

---

## 🔑 Características Clave

| Propiedad | Detalle |
|----------|--------|
| **¿Negociable?** | No directamente — pero los ETF y los futuros rastrean índices |
| **Ejemplos** | S&P 500, MSCI World, FTSE 100, DAX, Nikkei 225 |
| **Uso en LibreFolio** | Referencia para la señal de [Comparación de Activos](../../../user/assets/detail/signals.md) |
| **Precio** | Calculada a partir de las ponderaciones de sus componentes, no se negocia en bolsa |

---

## 📊 Cómo se Construyen los Índices

### 📈 Métodos de Ponderación

| Método | Fórmula | Ejemplo |
|--------|---------|---------|
| **Ponderado por capitalización de mercado** | Peso ∝ cap. de mercado de la empresa | S&P 500, MSCI World |
| **Ponderado por precio** | Peso ∝ precio de la acción | Dow Jones, Nikkei 225 |
| **Ponderado equitativamente** | Todos los componentes tienen el mismo peso | S&P 500 Equal Weight |

### 🔄 Reequilibrio

Los índices se reequilibran periódicamente: se añaden, eliminan o reponderan sus componentes. Esto ocurre normalmente de forma trimestral. Los ETF que rastrean el índice deben ajustar sus posiciones en consecuencia.

---

## 📐 Uso de Benchmarks en LibreFolio

LibreFolio ofrece dos tipos de benchmarks:

### 📊 Benchmarks Reales (Comparación de Activos)

Compare el gráfico de su activo frente a otro activo real (por ejemplo, compare su acción frente al ETF del S&P 500). Esto utiliza la superposición de señales de **Comparación de Activos**.

### 🎯 Benchmarks Sintéticos

Curvas de referencia matemáticas que responden a "¿qué pasaría si mi activo hubiera crecido a un X% anual?":

- **[Crecimiento Lineal](../../technical-analysis/synthetic-benchmarks/linear.md)** — Modelo de interés simple
- **[Crecimiento Compuesto](../../technical-analysis/synthetic-benchmarks/compound.md)** — Modelo de interés compuesto
- **[Onda Senoidal](../../technical-analysis/synthetic-benchmarks/sine-wave.md)** — Referencia cíclica para estacionalidad

---

## 🔗 Relacionado

- 📊 **[ETFs](etfs.md)** — Instrumentos que rastrean índices
- 🎯 **[Benchmarks Sintéticos](../../technical-analysis/synthetic-benchmarks/index.md)** — Curvas de referencia matemáticas
- 📈 **[Retornos y Tasas de Crecimiento](../../fundamentals/returns.md)** — Medición del rendimiento frente al benchmark
