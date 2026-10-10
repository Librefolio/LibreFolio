---
title: Asignador PAC
description: Planifica las compras que acercan lo más posible una nueva inversión a su asignación objetivo, en unidades enteras o por importe, sin realizar órdenes.
---

# 🧮 Asignador PAC

El **asignador PAC** responde a una pregunta:

> Con el dinero disponible para este ciclo de aportaciones, ¿qué compras acercan
> mi asignación lo más posible a su objetivo?

Abre **Herramientas** desde la barra lateral y haz clic en la tarjeta del asignador PAC: se abre un planificador guiado. Describes un escenario paso a paso, pulsas **Calcular plan** y obtienes un plan de compra para evaluar. Es una simulación: no se compra nada y no se envía ninguna orden a un bróker.

## 🗺️ Uso del planificador

El planificador te guía por estos pasos, en orden. El paso **Cambio** solo aparece cuando el escenario necesita tipos de cambio.

### 🎬 Escenario

Planificas una nueva inversión, un «PAC puro»: el cálculo parte de una cartera vacía, por lo que no se cuenta lo que ya tienes, y reparte el efectivo que elijas entre los Activos, lo más cerca posible de los pesos objetivo.

Aquí estableces la **Divisa de valoración**, en la que se comparan y resumen los importes. Al principio es la **Moneda predeterminada** de tus preferencias. El dinero permanece en su propia moneda: cada cambio necesario aparece en el plan.

La fecha de referencia es siempre hoy: el planificador la vuelve a establecer antes de cada copia desde LibreFolio y antes de cada cálculo.

### 💰 Liquidez

¿De dónde viene el dinero? Puedes combinar varias fuentes:

- **Desde tus brókers**: efectivo que ya está en tus brókers en LibreFolio. Eliges cuánto de él usar.
- **Nueva aportación**: dinero nuevo que añades, como la cuota del PAC.
- **Cuenta externa**: un saldo en una cuenta no registrada en LibreFolio, por ejemplo en tu banco. Declaras cuánto hay y cuánto usar. Desde una cuenta externa no se compra nada: su dinero se envía a un bróker.

El bróker que recibe una aportación o el dinero de una cuenta externa se elige en el paso **Brókers**. Cada importe permanece en su propia moneda.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-step-liquidity" alt="El paso Liquidez, junto a la lista de pasos: efectivo de un bróker, con el importe a usar de lo disponible; una nueva aportación, con su importe y moneda; y una cuenta externa, con su liquidez declarada y el importe a usar">
</div>

### 🏦 Brókers

Añade los brókers donde el plan puede comprar: **Elegir bróker existente** copia uno de los tuyos, y **Bróker manual** añade uno a mano. En cualquier caso, son datos del escenario: el bróker en sí nunca se modifica. Las comisiones y los modos de orden no se registran en LibreFolio, por eso los estableces aquí.

Para cada moneda en la que compres, establece:

- El modo de orden: **Por número de unidades** o **Por importe**.
- El **Incremento** $\Delta$: cada orden propuesta es un múltiplo entero de él. Con $q$ el tamaño de una orden, en unidades o como importe:

    $$
    q = k\,\Delta, \qquad k = 0, 1, 2, \dots
    $$

    Por número de unidades, $\Delta$ es un número entero: $\Delta = 1$ significa solo unidades enteras. Por importe, $\Delta$ es el importe más pequeño que puedes introducir, como $\Delta = 0.01$, y las unidades que obtienes pueden ser fracciones de una unidad.

- La **Comisión de compra**: una **Parte fija** $f$ más un **Porcentaje** $r$ del importe de la orden $A$, con el margen sobre el precio incluido. El **Mínimo** $f_{\min}$ y el **Máximo** $f_{\max}$ limitan solo la parte porcentual, y un **Máximo** vacío no establece límite superior:

    $$
    \text{comisión} = f + \min\big(\max(r\,A,\ f_{\min}),\ f_{\max}\big)
    $$

    La comisión se cobra en cada orden, y sin orden no hay comisión. Se paga con tu liquidez y no se invierte. Por ejemplo, con $r = 0.19\%$, $f_{\min} = 1.50$, $f_{\max} = 18$ y sin parte fija, una orden de $500$ paga $1.50$, una de $2{,}000$ paga $3.80$, y una de $20{,}000$ paga $18$.

Cada bróker también tiene dos ajustes propios:

- **Liquidez utilizable**: el dinero que el plan puede usar para comprar allí, es decir, el efectivo propio del bróker más las aportaciones y otras cuentas que permitas. Al principio se permiten todas: puedes excluir una fuente, limitar cuánto de ella se usa allí y darle una **Prioridad** ($0$ = preferida).
- **Conversión de divisa**: **Tú conviertes antes de comprar** o **El bróker convierte cuando compras**. Ambos convierten al tipo del paso **Cambio** menos el spread, así que el cálculo es el mismo en ambos casos: solo cambia la forma en que el plan muestra la conversión.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-step-brokers" alt="El editor de bróker, como datos de escenario que dejan el bróker sin cambios: bajo Cómo compras, moneda por moneda, el Tipo de orden Por importe, el Incremento y la Comisión de compra con su mínimo, porcentaje, máximo y parte fija; Conversión de divisa con El bróker convierte cuando compras seleccionado; y Aplicar al borrador">
</div>

Aún no soportado: un régimen fiscal, pérdidas y comisiones de venta para un bróker.

### 💼 Activos

Añade los Activos que el plan puede comprar, en cualquier combinación:

- busca los Activos registrados en LibreFolio;
- añade **Tus Activos**: aquellos con una posición abierta hoy en tus brókers, añadidos solo como filas, sin cantidades;
- añade un **Activo manual**.

Cada precio es uno de estos:

- **Auto**: el último precio almacenado en LibreFolio, leído de nuevo justo antes del cálculo. No se llama a ningún proveedor de datos.
- **Manual**: tu propio precio, usado tal como se introduce y nunca se vuelve a leer.

Un precio faltante permanece en el borrador: el cálculo lo solicita.

La composición por país, sector y tipo, copiada del Activo o introducida a mano, alimenta solo los mapas y barras de exposición del resultado, no el cálculo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-step-assets" alt="El paso Activos: Buscar Activo, Tus Activos y Activo manual, luego un Activo de LibreFolio con precio Auto, otro con precio Manual, y un Activo manual con su insignia Manual, cada uno con su precio y composición">
</div>

### 🔀 Rutas

Para cada bróker, elige qué Activos puede comprar: **Permitir todos**, **Excluir todos**, o haz clic en cada uno.

Luego, solo donde los necesites, establece límites en cada ruta. Se miden como las órdenes de ese bróker, en unidades o como importe. Con $q$ la compra del Activo en ese bróker:

- **Compra mínima** $q_{\min}$: si el plan compra allí, compra al menos esta cantidad, así que $q = 0$ o $q \ge q_{\min}$.
- **Compra obligatoria** $q_{\text{req}}$: se compra pase lo que pase, $q \ge q_{\text{req}}$. Si los recursos no son suficientes, el plan se vuelve imposible.
- **Compra máxima** $q_{\max}$: lo máximo que el plan puede comprar allí, $q \le q_{\max}$.

Dos ajustes más determinan cómo compra allí el plan:

- **Prioridad** ($0$ = preferida): solo rompe empates entre planes igual de cerca del objetivo.
- **Margen sobre el precio** $m$: cada compra se cuenta a $p\,(1 + m)$ en lugar del precio $p$ de una unidad, para cubrir una subida de precio antes de la orden. Un margen del $0.5\%$ sobre un precio de $100$ cuenta $100.50$. La diferencia es una reserva, no se invierte. Por importe, una orden de $A$ compra $A / \big(p\,(1 + m)\big)$ unidades.

Los campos vacíos no restringen nada.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-step-routing" alt="El paso Rutas: para cada bróker, sus ajustes de orden, Permitir todos, Excluir todos y cuántos Activos puede comprar; en el primer bróker, Activos excluidos y uno permitido con su Compra mínima, Compra obligatoria, Compra máxima, Margen sobre el precio y Prioridad">
</div>

### ⚖️ Objetivos

Aquí repartes el dinero que inviertes ahora entre los Activos: un objetivo $w_i$ por Activo, en porcentaje, se permiten decimales. Para calcular, los objetivos deben sumar exactamente $100\%$:

$$
\sum_i w_i = 100\%
$$

Dos acciones te ayudan a conseguirlo:

- **Equilibrar todo** reescala cada objetivo, manteniendo sus proporciones:

    $$
    w_i' = \frac{w_i}{\sum_j w_j} \cdot 100\%
    $$

    Si todos son $0$, cada Activo recibe una parte igual. El redondeo mantiene el total exactamente en $100\%$. Para cambiar solo algunas filas, **Equilibrar a 100%** en una fila da a ese Activo lo que falta, o quita el exceso, y **Equilibrar las filas seleccionadas a 100%** reescala solo las filas que marques.

- **Copiar distribución actual** lee cuánto pesa hoy cada uno de estos Activos en los brókers que marques, contando solo estos Activos y no el efectivo. Con $H_i$ el valor de mercado del Activo $i$ mantenido allí hoy:

    $$
    w_i = \frac{H_i}{\sum_j H_j} \cdot 100\%
    $$

    Los pesos se redondean a $0.01$ puntos porcentuales y siguen sumando exactamente $100\%$, y un Activo que introdujiste a mano recibe $0$. Son solo pesos, una base para editar y no un consejo: los ves antes de usarlos, y un objetivo que hayas cambiado no se sobrescribe sin tu confirmación.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-step-targets" alt="El paso Objetivos del asignador PAC: un porcentaje objetivo por Activo, con su barra de distribución, sumando 100%; Equilibrar todo, deshabilitado porque los objetivos ya están equilibrados; y Copiar distribución actual">
</div>

### 💱 Cambio (solo cuando es necesario)

Este paso aparece solo cuando el escenario necesita tipos de cambio. Contiene un tipo $x$ por cada par de divisas en juego, cada uno **Auto** o **Manual**:

- **Auto**: el último tipo almacenado en LibreFolio, leído cuando se abre el paso y de nuevo justo antes del cálculo. No se llama a ningún proveedor de datos.
- **Manual**: tu propio tipo.

También contiene un **Spread de conversión** $s$: un porcentaje de cada importe convertido, mantenido como margen por un cambio en el tipo oficial o por comisiones del bróker. Convertir un importe $D$ al tipo $x$ (unidades recibidas por cada unidad convertida) da

$$
D \cdot x\,(1 - s)
$$

en lugar de $D \cdot x$. La valoración, que compara y suma importes en la divisa de valoración, usa el tipo oficial $x$ sin spread; las conversiones usan el tipo con el spread, $x\,(1 - s)$.

Los tipos también deben ser coherentes entre sí, de modo que ninguna conversión cree valor: con efectivo en CHF, un Activo en USD y valoración en EUR, por ejemplo, un CHF convertido a USD después del spread no puede valer más en EUR que un CHF,

$$
x_{\text{CHF} \to \text{USD}}\,(1 - s)\,x_{\text{USD} \to \text{EUR}}
\le x_{\text{CHF} \to \text{EUR}}
$$

y lo mismo se cumple para cada conversión que el plan pueda necesitar entre dos divisas distintas de la divisa de valoración. De lo contrario, el cálculo no comienza y el resultado es **Entrada no válida** (consulta [Leer el resultado](#reading-the-result)): la causa puede ser un tipo **Manual** o tipos **Auto** de días o fuentes diferentes, así que alinea los tipos o establece un **Spread de conversión** que cubra la diferencia. Solo se tolera una diferencia lo bastante pequeña como para provenir de almacenar tipos con diez decimales: la conversión entonces usa el tipo a través de la divisa de valoración cuando este es menor,

$$
\min\left(x_{\text{CHF} \to \text{USD}}\,(1 - s),\;
\frac{x_{\text{CHF} \to \text{EUR}}}{x_{\text{USD} \to \text{EUR}}}\right)
$$

así que sigue sin crear valor. Cuando los tipos son coherentes, este tipo es el habitual $x\,(1 - s)$. Tus tipos no se modifican: cada conversión del plan muestra el tipo del que parte como *spot* y el tipo que usa como *aplicado*.

Cada importe que el plan registra se redondea una vez, sobre su valor final exacto, a la unidad mínima de su divisa (el céntimo para EUR o USD), y siempre en contra del plan: los importes que recibe (lo que entrega una conversión) se redondean a la baja, los importes que paga (el coste de una orden y su comisión) se redondean al alza. Así, el redondeo nunca mejora un plan, dividir una conversión en otras más pequeñas no aporta nada, y la parte de redondeo de **No invertido** nunca es negativa. La columna **Redondeo** de **Saldos por bróker y divisa** muestra cuánto de cada fila proviene del redondeo: ≈ marca una cifra mostrada redondeada, como cuando la diferencia exacta no tiene forma decimal finita (por ejemplo, tras convertir USD → EUR a $1/1.085$), y una diferencia por debajo de la unidad mínima conserva los dígitos que necesita, como ≈ −0.0022 en lugar de ≈ −0.00.

Cuando LibreFolio no tiene un tipo para un par, el paso ofrece **Añadir el par** o **Descargar los tipos**: cada uno abre la ventana correspondiente de la página de Cambio, y no se añade ni descarga nada hasta que lo confirmes allí.

Aún no soportado: un tipo de cambio o spread distinto por bróker, un margen de seguridad sobre el tipo, una comisión de conversión además del spread, y conversiones en más de un paso (por ejemplo, EUR → USD → CHF).

### 🧠 Estrategia

La estrategia es **Proporcional**: solo compras, no vende nada.

Entre todos los planes de compra que respetan tus ajustes, elige el mejor con una cascada de criterios, y cada uno decide solo entre los planes que siguen empatados en los anteriores:

1. **Cercanía a los objetivos (distancia L2)**: la menor distancia

    $$
    D = \sum_i \big(V_i - w_i\,R\big)^2
    $$

    donde $V_i$ es el valor del Activo $i$ después del plan, $w_i$ su objetivo, y $R$ la **Base de los objetivos**: el efectivo que elegiste que puede llegar a un bróker donde pueda comprar (en un PAC nada está ya invertido). Así, $w_i\,R$ es el valor ideal del Activo $i$. Los valores están en la divisa de valoración, al precio de cotización, sin comisiones ni margen sobre el precio. Elevar al cuadrado hace que las grandes diferencias pesen más, y $D$ se mide en dinero al cuadrado, por ejemplo EUR².

2. **Dinero no invertido**: el menor dinero que queda fuera de los Activos, $R - \sum_i V_i$.

3. **Prioridad de bróker y fuente**: la menor suma de los números de **Prioridad** de las órdenes y fuentes de efectivo que usa el plan.

4. **Costes explícitos (comisiones, spread, margen)**: el menor total de comisiones, spread de conversión y margen sobre el precio, en la divisa de valoración.

5. **Número de órdenes**: el menor número de órdenes.

Un orden fijo de Activos y brókers resuelve cualquier empate final, por lo que una búsqueda que se completa siempre da el mismo plan para los mismos datos; una búsqueda detenida por un límite de tiempo o de nodos puede dar un plan diferente en una máquina más lenta o más ocupada.

### ✅ Revisión

Una última comprobación antes del cálculo. Enumera la copia completa que se enviará (el backend recibe esta copia, y solo esta), señala los campos que aún faltan por completar y ofrece **Calcular plan**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-step-review" alt="El paso Revisión: el resumen de cada paso, con el paso Objetivos señalado; el campo que aún falta completar antes de calcular, con un enlace a su paso; Datos del cálculo plegados; y Calcular plan, deshabilitado hasta que se complete ese campo">
</div>

### 📋 Valores copiados o introducidos

El planificador funciona sin ningún bróker o Activo registrado: todo se puede introducir a mano. Cuando prefieras partir de tus datos de LibreFolio, los copias con una acción explícita: **Elegir bróker existente**, **Desde tus brókers**, la búsqueda de Activos o **Tus Activos**, y **Copiar distribución actual**. En el paso **Cambio**, un tipo **Auto** se lee de LibreFolio en cuanto se abre el paso.

Cada valor muestra de dónde proviene (**Copiado**, **Manual** o **Modificado**), y una copia también muestra su fecha. Una copia no sigue a su fuente mientras editas, y una copia que hayas modificado se puede restaurar.

Cuando pulsas **Calcular plan**, el planificador primero vuelve a leer de LibreFolio los precios, tipos y saldos que copiaste y no has cambiado. Los valores que introdujiste o cambiaste permanecen como están. Si esa lectura falla, no se calcula nada: puedes **Intentar de nuevo** o **Calcular con los datos copiados** para usar las copias anteriores.

### ⏳ Mientras calcula

Mientras la solicitud está activa, el planificador muestra **Cálculo en curso** y la configuración queda bloqueada. **Dejar de esperar** detiene solo la espera: el servidor puede terminar de todos modos, y esa respuesta se descarta.

Si cambias el borrador después de un resultado, aparece un aviso de **Resultado no actualizado**: los valores anteriores todavía se pueden consultar, pero ya no describen el borrador actual. Desde el aviso, **Volver a Revisión** regresa al último paso, y **Descartar el resultado anterior** elimina el resultado antiguo y también te lleva allí.

## 📊 Leer el resultado {: #reading-the-result }

Un plan calculado se abre con un encabezado: la fecha del escenario, la divisa de valoración y la revisión del borrador, luego una fila de insignias. Cada insignia se explica cuando la señalas, la tocas o la enfocas. Un plan también muestra su **distancia L2** a los objetivos (la $D$ del paso **Estrategia**), cuánto es **No invertido** y cuántas notas dejó el cálculo; las notas se enumeran justo debajo, en **Notas sobre el cálculo**. **Editar configuración** te lleva de vuelta al paso **Revisión**, y **Calcular nuevo plan** ejecuta el cálculo de nuevo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-result" alt="Un plan calculado: el encabezado con sus insignias de resultado, la distancia L2, No invertido y las notas, Editar configuración y Calcular nuevo plan; las Cifras clave, cada una con sus partes, junto a la caja de Cálculo; y la tabla Asignación por Activo, con la parte objetivo de cada Activo junto a su parte después del plan, su valor después del plan y su valor ideal, y los totales">
</div>

Un cálculo termina con uno de estos resultados:

| Resultado | Qué significa |
|---|---|
| **Plan disponible** | Un plan que respeta todas las restricciones. Una segunda insignia dice cuánto vale. **Óptimo demostrado**: el solucionador demostró, dentro de su pequeño margen de cálculo (que crece con los importes), que no existe un plan mejor, objetivo por objetivo en el orden del paso **Estrategia**, y la comprobación exacta del plan coincide con sus números. **Optimalidad no demostrada**: el solucionador alcanzó su límite de tiempo o de nodos, o sus propios números no coinciden con la comprobación exacta del plan; entonces es el mejor plan encontrado, pero no está demostrado que sea el mejor. |
| **Sin operación** | Con el efectivo que elegiste, ninguna compra cumple las restricciones: el plan es no hacer nada. Ninguna orden, ningún cambio de divisas y ninguna financiación. |
| **Infactible con estas restricciones** | Marcado **Infactibilidad demostrada**: ninguna combinación cumple todas las restricciones duras a la vez. Se enumeran las restricciones implicadas (cada **Compra obligatoria**, y la liquidez que puede llegar a los brókers), cada una con un enlace al paso donde puedes cambiarla. El planificador no elige cuál relajar, y ningún plan parcial se muestra como válido. |
| **Ningún plan dentro de los límites** | El solucionador no encontró ningún plan antes de alcanzar su límite. Esto no es una prueba de que no exista. Una búsqueda más ligera ayuda: menos Activos o rutas, una **Compra máxima** más baja o un **Incremento** mayor. |
| **Se necesitan más datos** | Falta algo. Tu borrador está intacto, y ningún Activo se elimina en silencio: añade el dato que falta o elimina el Activo tú mismo. |
| **Entrada no válida** | Algunos de los datos no son válidos. |
| **Escenario no soportado** | No es un error en tus datos: la herramienta aún no maneja este caso. |

Cada plan mostrado se ha comprobado de nuevo en aritmética decimal exacta, independientemente del solucionador: esa es la insignia **Verificado en decimal**. Una última insignia indica cómo terminó la búsqueda: **Completada** (el solucionador terminó su búsqueda por sí mismo), **Límite de tiempo** o **Límite de nodos**. Cuando se encontró un plan pero la búsqueda se detuvo en un límite, un aviso añade que puede existir un plan mejor; el resultado sigue completo y se puede consultar. Si el redondeo a la unidad mínima de una divisa deja a un bróker ligeramente corto, un aviso indica cuánto efectivo más necesita ese bróker para ejecutar el plan.

Los tres últimos resultados significan que el cálculo no pudo comenzar con tus datos: no se calcula nada, y se enumeran los problemas encontrados, con un enlace al paso correspondiente cuando lo haya. **Detalles** añade el código de backend de cada problema.

Los errores de plataforma, como un tiempo de espera agotado, una cola llena o un trabajador caído, no son conclusiones financieras sobre tu escenario: tu borrador permanece intacto, así que inténtalo de nuevo más tarde. Si la herramienta no está disponible, consulta [Configuración → Acerca de → Diagnóstico de plugins](../../settings/about.md).

### 🗂️ Cómo se estructura un plan

Debajo del resultado, un plan se estructura en este orden:

1. **Cifras clave**: el plan en unos pocos números, **Base de los objetivos**, **Invertido después**, **No invertido**, **Efectivo elegido**, **Costes** y **Órdenes**, cada uno con un **?** que lo explica y, bajo el valor, las partes que lo componen. Junto a ellos, la caja **Cálculo** muestra cuánto tiempo trabajó el optimizador, el tiempo que se le permitió para cada objetivo y cuántos objetivos cerró.
2. **Asignación por Activo**: para cada Activo, su parte objetivo junto a su parte después del plan, con su valor ideal $w_i\,R$, su valor después del plan $V_i$, la diferencia respecto al ideal $V_i - w_i\,R$, y el valor comprado.
3. **Plan operativo**: los pasos a seguir, en orden. Primero el efectivo (**Efectivo disponible**, **Transferencia**, **Depósito**), luego los cambios de divisas que haces tú mismo, luego una tabla de órdenes por bróker, con la **Instrucción** que introducir en el bróker, el **Precio**, el **Importe de la orden** y la **Comisión**. Una conversión que el bróker hace por sí mismo cuando compras no tiene número: aparece encima de las órdenes de ese bróker como **Conversión automática**. Esta sección se muestra solo cuando el plan tiene algo que hacer.
4. **Exposiciones – ideal vs real**: mapas y barras por país, tipo y sector, construidos a partir de las composiciones de los Activos. Los gráficos no cambian el plan.
5. **Saldos por bróker y divisa**: cómo se mueve cada saldo de efectivo y qué queda.
6. **Prueba y solucionador**: cómo se estableció el resultado. Las insignias de resultado, prueba y parada, el valor exacto de cada objetivo, las etapas del solucionador y los tiempos del backend.

**Asignación por Activo** y **Plan operativo** se abren al inicio; las demás secciones se abren a petición, y **Expandir todo** / **Contraer todo** las abre o cierra juntas. Sin plan (**Infactible con estas restricciones** o **Ningún plan dentro de los límites**), **Prueba y solucionador** es la única sección, y las cifras clave muestran solo la caja **Cálculo**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-result-plan" alt="El plan operativo: pasos numerados, primero las transferencias y el depósito que llevan el efectivo a un bróker, luego un cambio de divisa con su tipo, cada uno con su importe; después las órdenes de ese bróker, con Instrucción, Precio, Importe de la orden y Comisión; y las órdenes del siguiente bróker">
</div>

Haz clic en una orden, o en su botón **Detalle**, para abrir su detalle: la instrucción, la cantidad económica, los precios usados (precio de origen, precio medio y precio de cargo con el margen sobre el precio), el débito de efectivo y la comisión, las conversiones que la pagan, y la prioridad, el límite y los mínimos de su ruta. **Mostrar procedencia** enumera de dónde proviene cada valor, **Copiado** o **Manual**, con la fecha y hora de la copia o de tu introducción.

**Prueba y tiempos**, en la parte superior del resultado, abre **Prueba y solucionador** y se desplaza hasta él.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="pac-result-proof" alt="La sección Prueba y solucionador: las insignias de Resultado, Prueba y Parada; el valor exacto de cada objetivo, en orden, con el desempate final; la tabla de Etapas del solucionador; los Tiempos del backend; y Dónde se fue el tiempo, una barra de las fases del cálculo">
</div>

Cada cifra proviene de la contabilidad del backend; la interfaz no suma nada. Con el modo privacidad activado (consulta [Preferencias de usuario](../../settings/preferences.md)), el resultado oculta lo que revelaría cuánto posees: cada importe (cifras clave, valores, saldos, importes de órdenes, comisiones y costes, y los valores de objetivo y del solucionador medidos en dinero, incluida la **distancia L2**), cada cantidad y los límites de compra de una ruta (**Compra mínima**, **Compra obligatoria**, **Compra máxima**). Los importes de los problemas enumerados cuando un cálculo no pudo comenzar también se ocultan. Los precios de mercado, tipos de cambio, porcentajes (objetivos, partes, pesos de exposición, spreads y márgenes sobre el precio), incrementos, prioridades, recuentos y fechas permanecen visibles, porque no dicen nada sobre cuánto posees.

## 🧮 Qué hace el motor de cálculo

El motor que hay detrás de esta herramienta planifica **compras**. Dado un conjunto de Activos con sus precios, los brókers y rutas de compra que pueden usarse para alcanzarlos, el efectivo y las aportaciones disponibles, y un peso objetivo por Activo, busca la combinación de compras cuya asignación resultante se acerque lo más posible a esos objetivos.

Merece la pena conocer tres propiedades, porque determinan lo que el planificador puede prometer:

- **Compra en los incrementos de cada bróker.** Unidades enteras o importes, siempre en múltiplos del incremento que establezcas: los incrementos, las comisiones y las divisas implicadas forman parte del problema que resuelve, no de un paso de redondeo aplicado después.
- **Sus números publicados provienen de aritmética exacta.** Cada plan candidato se vuelve a comprobar exactamente antes de mostrar nada. Un plan que no supera esa comprobación nunca se publica.
- **Nunca hace pasar por óptimo un plan no demostrado.** Un plan detenido por un límite de tiempo o de nodos se muestra como el mejor encontrado y se marca **Optimalidad no demostrada**. Lo mismo ocurre con un plan cuya comprobación exacta no coincide con los propios números del solucionador, incluso cuando la búsqueda terminó por sí misma. Cuando no se encuentra ningún plan, lo dice en lugar de adivinar. Con importes de alrededor de diez mil millones de unidades de una divisa o más, los cálculos del solucionador pueden perder precisión: la herramienta puede entonces detenerse con un error, o marcar el plan como **Optimalidad no demostrada**.

Por lo tanto, un cálculo completado informa uno de los pocos resultados honestos enumerados en [Leer el resultado](#reading-the-result).

El motor solo planifica compras. No planifica ventas.

## 🎯 Cómo debe interpretarse su objetivo

El asignador PAC distribuye la liquidez disponible **ahora**: efectivo existente más nuevas aportaciones. Sus objetivos describen cómo debería asignarse ese dinero; no describen la mezcla final de una cartera que ya posees.

El cálculo no toma en absoluto las posiciones que ya posees como entrada, así que cambiarlas no puede cambiar lo que planifica esta herramienta. **Copiar distribución actual** solo las convierte en pesos objetivo para que los edites, y esos pesos no siguen cambios posteriores.

## 🚫 Lo que esta herramienta nunca hace

El planificador y el cálculo que hay detrás se mantienen dentro del contrato de la plataforma de Herramientas:

- no realiza órdenes, no ejecuta operaciones ni contacta con un bróker;
- no escribe en tus Activos, brókers o transacciones;
- no lee tu cartera por sí mismo: el cálculo recibe solo el escenario enviado desde **Revisión**, y el planificador lee tus datos de LibreFolio solo cuando copias algo o abres el paso **Cambio** (para sus tipos **Auto**), y luego de nuevo justo antes de un cálculo para los valores copiados que no hayas cambiado;
- su resultado es un plan para evaluar, no un consejo ni una instrucción.

## 🔒 Tus datos financieros

El cálculo se ejecuta sobre el escenario enviado con la solicitud. No se le entrega una cartera en vivo, una conexión a la base de datos ni tu sesión iniciada, y no produce nada que se almacene.

Tu borrador vive solo en la página abierta: no se guarda ni en el servidor ni en el navegador. Salir del planificador, o recargar o cerrar la pestaña, con un borrador en curso te pide confirmación primero. Cerrar sesión o cambiar de cuenta descarta el borrador sin preguntar.

Como siempre, evita pegar valores reales de cartera, exportaciones de bróker o identificadores de cuenta en ejemplos o mensajes de soporte.

## 🔗 Relacionado

- [Resumen de Herramientas](../index.md)
- [Preferencias de usuario](../../settings/preferences.md), incluido el modo privacidad
