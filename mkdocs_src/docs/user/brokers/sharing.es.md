# 🤝 Compartir bróker

Comparte un bróker con las personas que lo necesiten: una pareja, un familiar, un asesor o un contable. Cada persona recibe un **rol**, que decide lo que puede hacer, y cada Propietario una **participación de propiedad**, que decide qué parte de la cuenta le corresponde.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="sharing-modal" alt="Modal de compartir bróker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## ➕ Compartir un bróker

Abre el panel de compartir con el botón de compartir en la tarjeta del bróker, o con **Compartir bróker** en la barra de herramientas del bróker (abre la pestaña **Información**). Solo un Propietario puede cambiarlo; todos los demás lo ven en modo de solo lectura.

1. Haz clic en **+** (**Añadir usuario**) y busca a la persona **por nombre de usuario**.
2. Elige el **Rol** y, para un Propietario, el **% de propiedad**. Luego haz clic en **Añadir usuario**.
3. Haz clic en **Guardar configuración**. Nada cambia antes de que lo hagas: hasta entonces, **↺ Restablecer** devuelve la lista a como estaba.

??? note "✏️ Cambiar o eliminar a alguien — y cuándo se rechaza un guardado"

    Haz clic en el chip de una persona para cambiar su **Rol** o **% de propiedad**, o para **Eliminar acceso**; haz clic en **Confirmar** y luego en **Guardar configuración**.

    Se rechaza un guardado si dejara el bróker **sin un Propietario** —así que el último Propietario no puede eliminarse ni degradarse— o si las participaciones suman **más del 100%** (el panel advierte *La propiedad total supera el 100%*).

    Cambios sin guardar: el diálogo abierto desde la lista de brókers pregunta antes de cerrarse, pero en la pestaña **Información**, cambiar a otra pestaña los descarta.

---

## 🛡️ Qué puede hacer cada rol

| Qué puedes hacer | Lector | Editor | Propietario |
|:--|:--:|:--:|:--:|
| Ver el bróker, sus transacciones, informes y gráficos | ✅ | ✅ | ✅ |
| Añadir, editar e importar transacciones; subir y eliminar archivos de informes | ❌ | ✅ | ✅ |
| Editar la configuración del bróker | ❌ | ✅ | ✅ |
| Gestionar quién tiene acceso | ❌ | ❌ | ✅ |
| Eliminar el bróker | ❌ | ❌ | ✅ |

- 👁️ **Lector** — solo lectura, para un contable o familiares que solo necesitan mirar.
- ✏️ **Editor** — hace el trabajo diario, pero no puede compartir ni eliminar el bróker.
- 👑 **Propietario** — control total; un bróker puede tener varios Propietarios.

---

## 📊 Participación de propiedad

Cada Propietario tiene una **participación** del 0% al 100%: la parte de la cuenta que es suya. Los Lectores y Editores siempre tienen 0%. Las participaciones pueden sumar menos del 100% —por ejemplo, cuando un copropietario no usa LibreFolio—, pero nunca más del 100%; el panel muestra los totales **Asignado** y **Disponible** mientras editas.

La participación decide qué cuenta en tus cifras:

- El **Panel** solo cuenta los brókers que **posees** con una participación superior al 0%, y escala sus importes según tu participación: con el 50%, ves la mitad del valor, los ingresos y el P&L del bróker.
- La pestaña **Riesgo** del panel cubre los mismos brókers: los que posees con una participación superior al 0% (consulta [Pestaña de riesgo](../dashboard/index.md#risk-tab)).
- Los brókers en los que eres Lector o Editor, o que posees con el 0%, no están en tu panel. Su propia página los muestra: los Lectores y Editores ven los importes **completos**, los Propietarios su participación.

---

## 💡 Configuraciones comunes

| Quién | Configuración | Qué ve |
|:--|:--|:--|
| Cónyuge o pareja | Dos Propietarios, 50% cada uno | Cada uno de ustedes ve la mitad de la cuenta en su propio panel |
| Copropietario sin cuenta de LibreFolio | Tú como Propietario, 50% | Tu mitad; el otro 50% queda sin asignar |
| Asesor financiero o contable | Lector | Todo el bróker en su página, nada en su panel |
| Familiar que registra operaciones | Editor | Añade e importa transacciones, pero no puede compartir ni eliminar el bróker |

---

## 🚪 Abandonar un bróker o renunciar

No necesitas permiso de un Propietario para abandonar. En **Tu acceso** del panel de compartir, tras una confirmación:

- **Abandonar bróker** elimina tu acceso de inmediato, y el bróker desaparece de tus listas;
- **Cambiar a lector** (solo Editores) renuncia a la edición; un Propietario puede volver a hacerte Editor.

!!! danger "Último Propietario: abandonar elimina el bróker"

    Si eres el **único Propietario** que queda, el botón pasa a ser **Abandonar y eliminar bróker**: abandonar *elimina permanentemente el bróker junto con todas sus transacciones y archivos de informes importados*. Esto no se puede deshacer. Para conservar el bróker, convierte primero a otro usuario en Propietario y luego abandona.

Eliminar tu cuenta sigue la misma regla — consulta [Perfil](../settings/profile.md).

Para obtener acceso al bróker de otra persona, pídeselo a uno de sus Propietarios. Los brókers que no puedes abrir aparecen en **Otros brókers existentes** en la página [Brókers](index.md), y su botón de compartir muestra quién tiene acceso. Cualquier usuario que haya iniciado sesión en este LibreFolio puede ver quién tiene acceso a cualquier bróker, así que las personas que comparten una instancia pueden encontrarse.
