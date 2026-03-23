# 🤝 Compartir Bróker

LibreFolio Le permite compartir el acceso a sus cuentas de bróker con otros usuarios. Esto es útil para familias, asesores financieros o contadores que necesitan visibilidad sobre su cartera.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="sharing-modal" alt="Ventana Modal de Uso Compartido de Bróker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📋 Cómo Compartir

1. Diríjase a la página de detalles de un bróker
2. Haga clic en el botón **Compartir** (:material-share-variant:) en el encabezado
3. Se abrirá la **Ventana Modal de Uso Compartido**
4. Busque por nombre de usuario
5. Seleccione un **rol** (Visualizador, Editor o Propietario)
6. Establezca el **porcentaje de participación** (arrastre el deslizador o escriba el valor)
7. Haga clic en **Guardar** para aplicar los cambios

!!! warning "Solo los Propietarios pueden gestionar el acceso"

    Debe ser **Propietario** del bróker para agregar, eliminar o modificar el acceso de otros usuarios.

---

## 🛡️ Roles de Acceso

Al compartir un bróker, asigna un **rol** que determina lo que el otro usuario puede hacer:

| Permiso | Visualizador | Editor | Propietario |
|:-------------------------------------|:------------:|:------:|:-----------:|
| **Ver Detalles del Bróker** | ✅ | ✅ | ✅ |
| **Ver Transacciones** | ✅ | ✅ | ✅ |
| **Ver Informes y Gráficos** | ✅ | ✅ | ✅ |
| **Agregar/Editar Transacciones** | ❌ | ✅ | ✅ |
| **Importar Archivos (BRIM)** | ❌ | ✅ | ✅ |
| **Editar Configuración del Bróker** | ❌ | ✅ | ✅ |
| **Gestionar Acceso (Agregar/Eliminar Usuarios)** | ❌ | ❌ | ✅ |
| **Eliminar Bróker** | ❌ | ❌ | ✅ |

- 👁️ **Visualizador**: Acceso de solo lectura. Ideal para contadores o miembros de la familia que solo necesitan ver los datos.
- ✏️ **Editor**: Puede gestionar las actividades diarias (transacciones e importaciones) pero no puede eliminar el bróker ni cambiar el acceso.
- 👑 **Propietario**: Control total. Puede hacerlo todo, incluyendo agregar/eliminar otros usuarios.

---

## 📊 Porcentaje de Participación

Cada usuario con acceso a un bróker tiene un **porcentaje de participación** (de 0% a 100%). Esto representa qué parte del valor de la cartera del bróker pertenece a ese usuario.

!!! example "Cuenta Conjunta"

    Usted y su cónyuge comparten una cuenta de bróker al 50/50:

    - Usted (Propietario): **50%**
    - Cónyuge (Editor): **50%**

    Al calcular el valor total de la cartera, el sistema contará el 50% del valor de este bróker para cada uno.

!!! example "Asesor Financiero"

    Su asesor financiero necesita ver su cartera pero no es dueño de ninguna parte:

    - Usted (Propietario): **100%**
    - Asesor (Visualizador): **0%**

La suma de todos los porcentajes de participación para un bróker **no debe superar el 100%**, pero puede ser menor (por ejemplo, una cuenta copropiedad donde el copropietario no está en el sistema).

---

## 💡 Escenarios Comunes

| Escenario | Configuración Sugerida |
|----------|----------------------|
| **Cónyuge / Pareja** | Editor o copropietario, con un 50% de participación cada uno |
| **Asesor Financiero** | Visualizador, con 0% de participación |
| **Contador** | Visualizador, con 0% de participación |
| **Miembro de la familia** | Visualizador o Editor, con un porcentaje de participación personalizado |

!!! note "Agregación de Cartera"

    El porcentaje de participación está diseñado para futuras funciones de agregación de cartera. Cuando se implementen, el panel de control de cada usuario mostrará su participación proporcional en todos los brókeres a los que tenga acceso.
