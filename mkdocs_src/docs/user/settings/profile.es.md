# 👤 Perfil

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="profile" alt="Perfil">
</div>

La pestaña **Perfil** gestiona tu **identidad** en LibreFolio — quién eres y cómo inicias sesión. Las opciones de visualización (idioma, divisa, tema) están en **[Preferencias](preferences.md)**; las opciones de toda la instancia están en **[Configuración › Administración › Configuración global](../../admin/settings.md)**.

## 🔒 Bloqueo de edición

La pestaña se abre **bloqueada**: los campos son de solo lectura hasta que hagas clic en el ✏️ **botón de lápiz** de la cabecera. Esto evita ediciones accidentales. Si vuelves a bloquear la pestaña mientras hay cambios sin guardar, un diálogo de confirmación te pregunta si quieres descartarlos.

Mientras está desbloqueada, cada campo modificado muestra sus propios botones de **guardar** / **deshacer**, y la cabecera ofrece **guardar todo** y **deshacer todo** para acciones en bloque.

## 🖼️ Avatar

Pasa el ratón por tu avatar (con la pestaña desbloqueada) y haz clic en la superposición de cámara 📷 para abrir el selector de imágenes: elige una imagen existente de la [biblioteca de Archivos](../files/index.md), una compartida o una tuya, o sube una nueva. Las imágenes subidas pasan por la **[herramienta de Recorte de imágenes](../misc/image-crop.md)** con el preajuste *avatar* (recorte cuadrado, vista previa circular).

El avatar se guarda de inmediato y se usa en toda la aplicación allí donde se muestra tu identidad: la barra lateral, el uso compartido de brókers y las listas de colaboradores. Los administradores también lo ven en **[Configuración › Administración › Usuarios](../../admin/users.md#accounts)**, junto a tu nombre de usuario.

Como los demás usuarios ven tu avatar, su imagen es **compartida**: una imagen que subas aquí se almacena como compartida, y una de tus imágenes personales pasa a ser compartida cuando la eliges, con un aviso (véase [Compartida o personal](../files/index.md#visibility)).

!!! note "También se puede configurar desde la página de Bienvenida"

    Las cuentas recién creadas pueden elegir la misma imagen una vez, durante la **[configuración de bienvenida del primer inicio de
    sesión](../getting-started.md#welcome-setup)** — es el
    mismo selector, solo que se llega desde otra pantalla. Si omites ese paso, tus iniciales
    quedan como avatar; siempre puedes añadir o cambiar una imagen más tarde desde aquí.

## ✏️ Nombre de usuario, correo electrónico y cuenta creada

- **Nombre de usuario** y **Correo electrónico** son editables (hace falta desbloquear la pestaña). Los cambios se aplican a tus credenciales de inicio de sesión de inmediato. Cambiar el correo también pide tu contraseña actual: véase [Cambiar tu correo electrónico](#email-change) más abajo.
- **Cuenta creada** es un campo de solo lectura que muestra tu fecha de registro.

### 📧 Cambiar tu correo electrónico {: #email-change }

En cuanto el correo del campo sea una dirección distinta de la actual, aparece un campo **Contraseña actual** justo debajo del campo del correo, con un recordatorio: *Para cambiar tu correo electrónico, introduce tu contraseña actual. Tus otros dispositivos cerrarán sesión.* El botón de guardar del correo, y **guardar todo**, permanecen desactivados hasta que la escribas.

- **Contraseña incorrecta**: la pestaña dice *La contraseña actual es incorrecta*. Tu nuevo correo permanece en su campo y solo se vacía la contraseña: escríbela otra vez y luego guarda.
- **Contraseña incorrecta, una y otra vez**: las contraseñas incorrectas de aquí y los inicios de sesión fallidos con tu nombre de usuario se suman. Tras 10 intentos fallidos en 15 minutos, el cambio se rechaza incluso con la contraseña correcta, y también se rechaza iniciar sesión con tu nombre de usuario, durante un máximo de 15 minutos. La pestaña dice entonces *Demasiadas contraseñas incorrectas: espera unos minutos e inténtalo de nuevo.*, y conserva tanto tu nuevo correo como la contraseña que escribiste: vuelve a guardar cuando termine la espera.
- **Correo rechazado por otro motivo**, por ejemplo porque otra cuenta ya lo usa, como su correo o como su nombre de usuario, aunque esté escrito con otras mayúsculas: la pestaña muestra el motivo y se restablece tu correo actual.
- **Correo guardado**: sigues con la sesión iniciada en este dispositivo. Todos los demás dispositivos con sesión iniciada en tu cuenta cierran sesión y deben iniciarla de nuevo. Cualquier enlace de restablecimiento de contraseña que se te haya enviado antes del cambio deja de funcionar, incluso uno que aún esté esperando en tu buzón antiguo.
- **Un correo a cada dirección**: cuando tu instancia puede enviar correos, LibreFolio escribe a la dirección que tenías antes para informarte del cambio, y a tu nueva dirección para confirmar que ahora es la de tu cuenta. El primero no muestra nada de la nueva dirección e indica qué hacer si no realizaste el cambio; el segundo no muestra nada de la anterior. Si alguno no llega, revisa también la carpeta de spam.
- **Solo cambiaron las mayúsculas**, como `Anna@example.com` por `anna@example.com`: sigue siendo tu dirección, así que la pestaña no pide contraseña, la guardas de inmediato, no se cierra la sesión en ningún dispositivo y sigue verificada. Solo las letras de la A a la Z se consideran iguales aunque cambien de mayúscula a minúscula; las acentuadas no: `Émile@example.com` y `émile@example.com` son dos direcciones diferentes.

Cambiar solo tu nombre de usuario no pide contraseña y no cierra la sesión en ningún dispositivo. El nuevo nombre de usuario no puede contener `@`, porque al iniciar sesión LibreFolio interpreta cualquier cosa con un `@` como una dirección de correo: la pestaña dice *El nombre de usuario no puede contener @: para iniciar sesión, siempre puedes usar tu dirección de correo.*, y se restablece tu nombre de usuario actual. Los espacios, las letras acentuadas y los signos como `.`, `_`, `-` o `+` sí valen.

!!! info "Por qué tu contraseña"

    Tu dirección de correo es la forma en que se puede recuperar tu cuenta: un enlace de restablecimiento de contraseña enviado allí permite a quien lo lea elegir una nueva contraseña. Sin esta comprobación, alguien con un momento dentro de tu sesión abierta (un ordenador desbloqueado, una cookie de sesión robada) podría poner su propia dirección en tu cuenta y quedarse con ella para siempre. Sin tu contraseña, no pueden cambiar la dirección.

## 🔐 Seguridad

### 🔑 Cambiar contraseña

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="password-modal" alt="Cambiar contraseña">
</div>

El botón **Cambiar contraseña** (siempre disponible, no hace falta desbloquear) abre un modal que requiere:

1. Tu **contraseña actual** (para verificación)
2. Una **nueva contraseña** que cumpla todas las reglas de la lista de comprobación bajo el campo: al menos 8 caracteres, una letra mayúscula, una letra minúscula, un número y un carácter especial — y debe ser distinta de la actual
3. **Confirmación** de la nueva contraseña

La lista de comprobación sigue lo que escribes, y el servidor aplica exactamente las mismas reglas. Cuentan las letras y los dígitos de cualquier alfabeto: `É` es una letra mayúscula, `é` una minúscula. Un carácter especial es cualquier cosa que no sea una letra, un número ni un espacio, como `!`, `_` o `€`. Si el servidor aun así rechaza la nueva contraseña, el modal dice *La contraseña no cumple los requisitos de seguridad*, y la lista de comprobación muestra qué reglas faltan.

Las contraseñas actuales incorrectas y los inicios de sesión fallidos con tu nombre de usuario se suman, igual que para [el correo](#email-change): tras 10 intentos fallidos en 15 minutos, el cambio se rechaza incluso con la contraseña actual correcta, y también se rechaza iniciar sesión con tu nombre de usuario, durante un máximo de 15 minutos. El modal dice entonces *Demasiadas contraseñas incorrectas: espera unos minutos e inténtalo de nuevo.*, y conserva lo que escribiste en sus tres campos: inténtalo de nuevo cuando termine la espera.

Tras la confirmación, tu sesión sigue activa: no necesitas iniciar sesión de nuevo. Todos los demás dispositivos con sesión iniciada en tu cuenta cierran sesión. Cualquier enlace de restablecimiento de contraseña que se te haya enviado antes del cambio deja de funcionar.

### 🗑️ Eliminar cuenta

El botón **Eliminar cuenta** elimina permanentemente tu cuenta y su configuración. Su diálogo muestra primero lo que se eliminaría junto con tu cuenta y después te pide que escribas tu **nombre de usuario**. **Eliminar permanentemente** actúa de inmediato: se cierra tu sesión y vuelves a la página de inicio de sesión.

Tus brókers siguen la misma regla que [salir de un bróker compartido](../brokers/sharing.md), y el diálogo los enumera antes de que confirmes:

- **Se eliminan, con todas sus transacciones y archivos**: los brókers de los que eres el **único propietario**, cada uno con su número de transacciones. Sus archivos de informe importados también se eliminan, y desaparecen además para los usuarios con los que los compartiste. Si no hay ninguno, el diálogo dice *No se elimina ningún bróker*;
- **Brókers compartidos que se quedan (solo desaparece tu acceso)**: todos los demás brókers que puedas abrir, con tu rol en ellos. Se quedan para sus otros usuarios: solo se elimina tu acceso;
- un aviso cuando las transacciones en otros brókers son mitades de transferencias con los brókers que se van: se quedan, sin su otra mitad. Una transferencia recibida se convierte en un ajuste por su coste, y una transferencia enviada a uno de esos brókers, en un ajuste que saca los activos del bróker que los envió, sin valor: su coste se contabiliza allí como una pérdida realizada (véase [Editar o eliminar un bróker](../brokers/index.md)).

Si el diálogo no puede cargar esa lista, no te deja eliminar: ciérralo e inténtalo de nuevo. Si la eliminación falla por un motivo técnico, no se elimina nada.

!!! warning "Irreversible"

    Eliminar tu cuenta no se puede deshacer. Si eres el **único administrador activo** de la instancia, la eliminación se rechaza: primero concede a otra cuenta el rol de administrador, desde la pestaña [Usuarios](../../admin/users.md).

---

## 🔗 Relacionado

- 🎛️ **[Preferencias de usuario](preferences.md)** — Idioma, divisa base y tema
- ⚙️ **[Resumen de configuración](index.md)** — Resumen de la configuración general
- ℹ️ **[Acerca de](about.md)** — Información de versión, plugins y registro de cambios
- 🛡️ **[Configuración global](../../admin/settings.md)** — Opciones de toda la instancia (admin)
