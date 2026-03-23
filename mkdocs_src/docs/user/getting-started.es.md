# 🚀 Primeros Pasos

¡Bienvenido a LibreFolio! Esta guía te explica cómo registrar una cuenta, iniciar sesión y crear tu primer broker: todo lo que necesitas para comenzar a hacer seguimiento de tu cartera.

---

## 📝 1. Registra tu Cuenta

Accede a la URL de LibreFolio (por ejemplo, `http://localhost:8000`) y verás la página de inicio de sesión. Haz clic en **Registrarte** para crear una nueva cuenta.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Formulario de Registro" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Completa tus datos:

- 👤 **Nombre de usuario**: Tu nombre visible (único en el sistema)
- 📧 **Correo electrónico**: Una dirección de email válida
- 🔑 **Contraseña**: Una contraseña segura (el indicador de seguridad te ayuda)

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registro con Indicador de Seguridad de Contraseña" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "Primer Usuario = Administrador"

    El primer usuario que se registra se convierte automáticamente en el **administrador del sistema** (superusuario). Este usuario puede gestionar la configuración global, promover a otros usuarios y acceder a todas las funciones de administración.

---

## 🔐 2. Inicia Sesión

Después de registrarte, serás redirigido a la página de inicio de sesión. Ingresa tus credenciales para acceder a tu panel de control.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="01-login" alt="Página de Inicio de Sesión" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🏦 3. Crea tu Primer Broker

Un **Broker** en LibreFolio representa una cuenta de corretaje: el lugar donde se gestionan tus inversiones (por ejemplo, Interactive Brokers, Degiro, una cuenta bancaria, etc.).

!!! note "¿Por qué necesito un Broker?"

    Todas las transacciones en LibreFolio están vinculadas a un broker. Es la cuenta que agrupa tus operaciones, importaciones e informes. Necesitas al menos un broker antes de poder comenzar a hacer seguimiento de cualquier cosa.

### 📋 Pasos

1. Accede a la página **Brokers** desde el menú de la barra lateral
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="list" alt="Lista de Brokers" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>
2. Haz clic en el botón **"Nuevo Broker"**
3. Completa los detalles del broker:
 - 🏷️ **Nombre**: Un nombre descriptivo (por ejemplo, "Mi Cuenta en Degiro")
 - 💰 **Moneda base**: La moneda de la cuenta (por ejemplo, EUR, USD)
 - 🖼️ **Icono** *(opcional)*: Sube un logotipo o avatar del broker
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Lista de Brokers" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>
4. Una vez creado, puedes hacer clic en un broker para ver sus detalles, importar informes y gestionar transacciones.
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="detail" alt="Detalle del Broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

---

## 🔮 4. ¿Qué Sigue?

Ahora que tienes una cuenta y un broker, puedes:

- 📤 **[Subir informes del broker](files/index.md)** — Importar archivos CSV/Excel de tu broker para el análisis automático de transacciones
- 🤝 **[Compartir tu broker](brokers/sharing.md)** — Dar acceso a familiares, asesores o contadores
- 💱 **[Configurar tasas de cambio (FX)](fx/index.md)** — Ajustar la conversión de divisas para carteras multimoneda
- ⚙️ **[Personalizar configuración](../admin/settings.md)** — Modificar idioma, tema y preferencias del sistema

!!! tip "Cálculos de Cartera"

    Los Brokers también se utilizan para los **cálculos de agregación** de cartera. Cuando compartes un broker con otro usuario y estableces un **porcentaje de participación**, el sistema puede calcular la porción de cada usuario en el valor total de la cartera. Esta función está en desarrollo activo.
