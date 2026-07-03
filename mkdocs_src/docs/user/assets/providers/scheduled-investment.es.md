# <img src="../../../../../static/scheduled_investment.png" alt=""> Proveedor de Inversión Programada

El proveedor de Inversión Programada está diseñado para instrumentos de renta fija donde el valor se calcula a partir de un calendario de tasas de interés en lugar de precios de mercado. Los ejemplos incluyen cuentas de ahorro, depósitos fijos y bonos gubernamentales con tasas de cupón conocidas.

## 📊 Capacidades

- ✅ **Precio Actual**: Calculado determinísticamente a partir del valor inicial + calendario de intereses + eventos del activo
- ✅ **Historial**: Curva de valor histórica completa basada en el devengo de intereses
- ✅ **Eventos del Activo**: Genera eventos de INTEREST y PRICE_ADJUSTMENT
- ❌ **Búsqueda**: No aplicable

## 🔧 Configuración

- **Identificador**: Generado automáticamente (no se necesita identificador manual)
- **Tipo de Identificador**: `AUTO_GENERATED`
- **Parámetros**: Configurados a través del **Editor de Calendario de Intereses** (componente de UI personalizado)

### Campos Obligatorios

| Campo | Descripción |
|-------|-------------|
| **Valor Inicial** | El principal / valor nominal de la inversión (ej., 10000) |
| **Moneda** | Código de moneda ISO 4217 (ej., EUR, USD) |

## 📋 Editor de Calendario de Intereses

El editor permite definir múltiples períodos de tasas de interés:

| Campo | Descripción |
|-------|-------------|
| **Período** | Fecha de inicio y fin (ambas inclusive) |
| **Tasa %** | Tasa de interés anual como porcentaje (ej., 5.00 = 5%) |
| **Capitalización** | Interés simple o compuesto |
| **Freq. Cap.** | Frecuencia de capitalización (Anual, Semestral, Trimestral, Mensual, Diaria) |
| **Base de cálculo** | Convención de conteo de días (ACT/365, ACT/360, 30/360, ACT/ACT) |

### ⚡ Interés Moratorio

Puede activar el **Interés Moratorio** para definir una tasa de penalización aplicada después de que finalice el último período programado. El interés moratorio tiene un **período de gracia** configurable (en días) antes de comenzar a devengarse.

## 📋 Eventos del Activo

Los eventos del activo describen sucesos que afectan al activo de forma global (no son transacciones a nivel de cartera):

| Tipo de Evento | Efecto en el Precio | Descripción |
|-----------|----------------|-------------|
| **INTEREST** | El precio baja según el valor del evento | Pago de intereses — el usuario recibió efectivo, por lo que el valor del activo disminuye |
| **PRICE_ADJUSTMENT** | Cambio algebraico | Deterioro (negativo) o ajuste al alza (positivo) del valor del activo |

Los eventos se configuran en el editor y afectan al precio calculado a partir de su fecha en adelante.

## 🧮 Cómo se Calcula el Valor

1. Se comienza con `initial_value` como el principal base
2. Para cada período de interés, se calcula el interés devengado basándose en la tasa, el tipo de capitalización y la convención de conteo de días
3. Se aplican los eventos del activo: los eventos INTEREST reducen el precio, los eventos PRICE_ADJUSTMENT lo modifican algebraicamente
4. El valor actual = `initial_value` + interés devengado - Σ(eventos INTEREST) + Σ(eventos PRICE_ADJUSTMENT)

!!! note "Motor Puramente Determinista"

    El proveedor es completamente determinista: dada la misma configuración, siempre produce los mismos precios. NO accede a la base de datos ni lee transacciones. Todas las entradas provienen de `provider_params`.

## 🎯 Casos de Uso

- **Cuentas de ahorro** con tasas de interés fijas o variables
- **Depósitos a plazo** (CD/Depositi vincolati)
- **Bonos gubernamentales** donde se desee rastrear el interés devengado en lugar del precio de mercado
- **Préstamos de Crowdfunding** (préstamos P2P) con calendarios de intereses conocidos
- **Cualquier instrumento** con un calendario de tasas de interés conocido
