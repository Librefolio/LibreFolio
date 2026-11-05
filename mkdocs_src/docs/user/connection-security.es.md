# 🔐 Seguridad de la conexión

El indicador de seguridad de la conexión en la barra lateral de LibreFolio te dice si lo que escribes —tu contraseña, tus cifras— viaja cifrado entre tu dispositivo y tu servidor. Muestra uno de tres niveles, **segura**, **red local** o **no segura**, según la dirección que abriste y la red en la que estés. Los administradores también ven allí cuándo las comprobaciones de seguridad de la instancia requieren su atención: consulta [Advertencias de seguridad para administradores](#security-warnings).

Para la máxima seguridad, asigna a LibreFolio una dirección HTTPS y úsala en todas partes, incluso en tu red doméstica.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="security" data-name="connection-indicator" alt="El indicador de seguridad de la conexión en la parte inferior de la barra lateral, abierto en Conexión: red local: su motivo, que cualquiera en la misma red puede leer el tráfico, y el enlace Cómo conectarse de forma segura" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🚦 Los tres niveles

### 🟢 Conexión: segura {: #connection-secure }

Lo que escribes está cifrado, o nunca sale del servidor.

<div class="lf-pros-cons" markdown>

| ✅ Ventaja | ⚠️ Desventaja |
|:--|:--|
| Nadie en el camino puede leerlo ni cambiarlo, ni siquiera en una Wi-Fi pública. | Nada, por lo que respecta al riesgo. |

</div>

!!! warning "📱 Tailscale con HTTP sin cifrar y la aplicación"

    A través de Tailscale con una dirección `http://` sin cifrar, como `http://100.110.x.x:6040`, tu
    navegador no [instalará LibreFolio como aplicación](pwa.md). Por eso una dirección HTTPS sigue
    siendo mejor: en cuanto al riesgo, ambas son iguales, ya que Tailscale también cifra el tráfico.

👉 **Qué hacer:** nada, sigue usando esta dirección. Para la aplicación, cambia a una
[dirección HTTPS](#https-address).

??? info "🔍 Cuándo una conexión cuenta como segura"

    Los detalles indican uno de tres motivos:

    - **HTTPS**: cualquier dirección `https://`. Tu navegador decide por sí solo, independientemente
      de lo que vea el servidor.
    - **En el propio servidor**: `localhost`, nombres que terminan en `.localhost` y direcciones
      de loopback como `127.0.0.1` y `::1`. Tu navegador decide por sí solo: el tráfico no sale de
      ese equipo.
    - **VPN (Tailscale)**: una dirección `http://` sin cifrar dentro de los rangos de Tailscale,
      `100.64.0.0/10` y `fd7a:115c:a1e0::/48`, o un nombre que termina en `.ts.net`. Tailscale cifra
      el tráfico entre tu dispositivo y el servidor. Si el servidor, en cambio, ve que la solicitud
      llega desde internet, el nivel es [red local](#connection-local-network), con el motivo
      Incierto.

### 🏠 Conexión: red local {: #connection-local-network }

Abriste LibreFolio mediante `http://` sin cifrar dentro de tu red doméstica o de oficina, por ejemplo
en `http://192.168.1.100:6040`, la dirección que usan otros dispositivos tras una
[instalación](installation.md) estándar.

<div class="lf-pros-cons" markdown>

| 🤷 Te conformas con | ⚠️ Desventaja |
|:--|:--|
| Una conexión que no requiere configuración y cuyo tráfico permanece dentro de tu red. | Nada está cifrado: cualquiera en la misma red, como un invitado en tu Wi-Fi, podría leer el tráfico, incluida la contraseña. |

</div>

👉 **Qué hacer:** usa la [dirección HTTPS](#https-address) también en casa.

El mismo nivel aparece con un motivo que empieza por *Incierto* cuando LibreFolio no puede
determinar dónde estás realmente: el consejo no cambia.

??? info "🔍 Cuándo una conexión cuenta como red local"

    **Una dirección local con `http://` sin cifrar**: una dirección en `10.x`, `172.16.x` a
    `172.31.x`, `192.168.x` o `169.254.x`, una dirección IPv6 link-local o local única, o un
    nombre que termina en `.local`, `.lan`, `.home.arpa` o `.internal`, o que no tiene ningún
    punto, como `http://nas:6040`. Un nombre corto de MagicDNS de Tailscale, como
    `http://my-server:6040`, tampoco tiene punto, así que cuenta aquí: la IP de Tailscale o el
    nombre completo que termina en `.ts.net` cuenta como [segura](#connection-secure).

    **Incierto**: tu navegador juzga la dirección que abriste, y después el servidor informa desde
    dónde ve llegar la solicitud, solo el tipo de dirección y nunca tu dirección IP. El servidor
    puede confirmar el veredicto del navegador o hacerlo incierto, pero nunca hacer que una conexión
    cuente como segura; hasta que responda, prevalece el veredicto del navegador. Cuando ambos no
    coinciden, el nivel es red local y el motivo empieza por *Incierto*:

    - una dirección que parece pública y que el servidor ve llegar desde tu red local, desde
      Tailscale o desde el propio servidor, por ejemplo mediante DNS dividido o un proxy local;
    - una dirección local o de Tailscale que el servidor ve llegar desde internet.

    El tráfico no está cifrado y LibreFolio no puede determinar dónde estás realmente.

### 🔴 Conexión: no segura {: #connection-not-secure }

Llegaste a LibreFolio mediante `http://` sin cifrar desde internet, por ejemplo a través de un puerto
abierto en tu router. En un teléfono, un punto rojo en el botón de menú te avisa incluso mientras
la barra lateral está cerrada.

<div class="lf-pros-cons" markdown>

| ✅ Ventaja | ⚠️ Desventaja |
|:--|:--|
| Ninguna. | Las contraseñas y los datos viajan en texto plano por redes que no controlas: cualquiera en el camino podría leerlos o incluso cambiarlos. |

</div>

👉 **Qué hacer:** evita esta dirección. Si ejecutas el servidor, asigna a LibreFolio una
[dirección HTTPS](#https-address) y deja de exponer HTTP sin cifrar. Después, cambia tu contraseña:
**Configuración** → [**Perfil**](settings/profile.md) → **Cambiar contraseña**. Esto también cierra la sesión en todos los demás dispositivos con la sesión iniciada en tu cuenta.

??? info "🔍 Cuándo una conexión cuenta como no segura"

    **Una dirección pública con `http://` sin cifrar**: una dirección o un nombre que no es local, no
    es de Tailscale y no es el propio servidor, como una IP pública o un nombre de dominio como
    `http://myhome.duckdns.org:6040`. El nivel se mantiene cuando el servidor también ve que la
    solicitud llega desde internet, o no puede determinarlo. Si ve que la solicitud llega desde tu
    red local, desde Tailscale o desde el propio servidor, el nivel es
    [red local](#connection-local-network), con el motivo Incierto.

---

## 🔒 Cómo conectarse de forma segura {: #https-address }

Asigna a LibreFolio una dirección HTTPS y después usa solo esa. Quien ejecute el servidor la
configura de una de estas dos formas:

- **Tailscale**, sin abrir ningún puerto en tu router: Tailscale Serve proporciona una dirección
  HTTPS a los dispositivos de tu tailnet, y Funnel una pública que no necesita Tailscale en tus
  dispositivos. Consulta [Exponer de forma segura](../admin/service_exposure.md).
- **Un proxy inverso** con un certificado TLS, como Caddy, Traefik o Nginx: consulta
  [Docker avanzado](../admin/docker_advanced.md).

Después, sigue algunos buenos hábitos:

- usa la dirección `https://` en todos los dispositivos, también en casa;
- guárdala en marcadores y actualiza los marcadores antiguos y los accesos directos de la pantalla
  de inicio que todavía apunten a `http://`;
- si no ejecutas el servidor, pide la dirección a quien lo ejecute;
- comprueba el indicador: debería mostrar **Conexión: segura**.

Si ejecutas el servidor, [Comprobar la seguridad de la conexión](../admin/connection_checks.md)
muestra cómo verificar el resultado.

---

## 🛡️ Advertencias de seguridad para administradores {: #security-warnings }

Si eres administrador, la misma línea también te indica, en cada página, cuándo las comprobaciones
de seguridad de tu instancia requieren tu atención: los errores y advertencias que **Configuración** →
**Administración** → **Seguridad** enumera y cuenta en su pestaña.

- **Un punto en el icono.** Un pequeño punto aparece en la esquina del escudo de la línea, tanto
  con la barra lateral expandida como contraída: rojo cuando al menos una comprobación da error,
  ámbar cuando solo hay advertencias.
- **Un enlace en los detalles.** Haz clic en la línea: después del motivo, un enlace muestra el
  recuento, como **2 advertencias de seguridad**, errores incluidos. El enlace abre la pestaña
  **Seguridad**, donde cada hallazgo indica qué va mal, y cierra los detalles.
- **El recuento en palabras.** Con la barra lateral contraída, al señalar el escudo se muestra el
  nivel y el recuento, como *Conexión: segura — 2 advertencias de seguridad*. Un lector de pantalla
  lee lo mismo, tanto con la barra lateral expandida como contraída.
- **En un teléfono**, la barra lateral se oculta detrás del botón de menú, así que el botón también
  lleva el punto: rojo cuando hay un error o cuando la conexión figura como [no segura](#connection-not-secure),
  y ámbar cuando solo hay advertencias. Abre el menú para ver la línea.

El punto sigue a la pestaña **Seguridad**: la información nunca se cuenta, así que si solo hay
información, o nada en absoluto, no aparece ningún punto. LibreFolio lee las comprobaciones una vez,
cuando se abre en tu navegador: después de corregir algo en el servidor y reiniciarlo, recarga la
página o haz clic en **Comprobar de nuevo** en la pestaña. Los demás usuarios nunca ven el punto ni
el enlace, y su navegador nunca solicita las comprobaciones. Qué significa cada comprobación y cómo
corregirla: «Seguridad» en [Configuración global](../admin/settings.md#security-tab).

---

## 🧭 Lo que el indicador no hace

El indicador describe la conexión que estás usando ahora mismo y ofrece consejos. Hay tres cosas que
quedan fuera de su alcance.

**No bloquea nada.** Es un consejo, no una comprobación. Y como describe la conexión del
dispositivo en el que estás, el mismo LibreFolio puede mostrar **Conexión: segura** en tu portátil y
**Conexión: no segura** en tu teléfono.

**No comprueba los certificados.** Un certificado autofirmado que aceptaste en el navegador muestra
**Conexión: segura**. El tráfico está cifrado, pero nadie garantiza que el servidor sea realmente
tuyo.

**No siempre puede ver dónde estás.** Cuando LibreFolio se ejecuta en Docker Desktop y se expone
directamente, o está detrás de un proxy que no transmite tu dirección en `X-Forwarded-For`, el
servidor ve a todos los visitantes como locales. El HTTP sin cifrar desde internet muestra entonces
**Conexión: red local**, con el motivo Incierto, en lugar de **Conexión: no segura**. Docker Engine
en Linux conserva tu dirección.

Independientemente de lo que muestre el indicador, el consejo sigue siendo el mismo: usa la
dirección HTTPS.

---

## 🔗 Relacionado

- 🌐 **[Exponer de forma segura](../admin/service_exposure.md)** — Tailscale, de una VPN privada a
  una dirección HTTPS pública
- 🔍 **[Comprobar la seguridad de la conexión](../admin/connection_checks.md)** — Para
  administradores: la dirección HTTPS, la cookie de sesión y el proxy inverso
- 🐳 **[Docker avanzado](../admin/docker_advanced.md)** — Archivo Compose, variables de entorno,
  proxy inverso
- 📝 **[Configuración](../admin/configuration.md)** — Todas las opciones del archivo `.env`
- 📦 **[Instalación con Docker](installation.md)** — Acceso local y remoto después de instalar
- 📱 **[Instalar como aplicación (PWA)](pwa.md)** — Requiere una dirección HTTPS
