# 🔐 Seguridad de la conexión

El indicador de seguridad de la conexión, en la barra lateral de LibreFolio, te dice si lo que
escribes — tu contraseña, tus importes — viaja cifrado entre tu dispositivo y tu servidor. Muestra
uno de tres niveles, **segura**, **red local** o **no segura**, según la dirección que abriste y la
red en la que estás.

Para la máxima seguridad, asigna a LibreFolio una dirección HTTPS y úsala en todas partes, también en
tu red doméstica.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="security" data-name="connection-indicator" alt="El indicador de seguridad de la conexión en la parte inferior de la barra lateral, abierto en Conexión: red local: su motivo, que cualquiera en la misma red puede leer el tráfico, y el enlace Cómo conectarse de forma segura" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🚦 Los tres niveles

### 🟢 Conexión: segura {: #connection-secure }

Lo que escribes está cifrado, o nunca sale del servidor.

- ✅ **A favor:** nadie en el camino puede leerlo ni modificarlo, ni siquiera en un Wi-Fi público.
- ⚠️ **En contra:** a través de Tailscale con una dirección `http://` sin cifrar, como
  `http://100.110.x.x:6040`, tu navegador no [instalará LibreFolio como aplicación](pwa.md).
- 👉 **Qué hacer:** nada, sigue usando esta dirección. Para la aplicación, pasa a una
  [dirección HTTPS](#https-address).

??? info "🔍 Cuándo una conexión es segura"

    Los detalles dan uno de tres motivos:

    - **HTTPS**: cualquier dirección `https://`. Tu navegador decide solo, vea lo que vea el
      servidor.
    - **En el propio servidor**: `localhost`, los nombres que terminan en `.localhost` y las
      direcciones de loopback como `127.0.0.1` y `::1`. Tu navegador decide solo: el tráfico no
      sale de ese ordenador.
    - **VPN (Tailscale)**: una dirección `http://` sin cifrar en los rangos de Tailscale,
      `100.64.0.0/10` y `fd7a:115c:a1e0::/48`, o un nombre que termina en `.ts.net`. Tailscale
      cifra el tráfico entre tu dispositivo y el servidor. Si el servidor ve en cambio que la
      solicitud llega desde internet, el nivel es [red local](#connection-local-network), como
      incierto.

### 🏠 Conexión: red local {: #connection-local-network }

Abriste LibreFolio por `http://` sin cifrar dentro de tu red doméstica o de oficina, por ejemplo en
`http://192.168.1.100:6040`, la dirección que usan los demás dispositivos tras una
[instalación](installation.md) estándar.

- ✅ **A favor:** funciona sin configurar nada, y el tráfico se queda dentro de tu red.
- ⚠️ **En contra:** nada está cifrado: cualquiera en la misma red, como un invitado en tu Wi-Fi,
  podría leer el tráfico, contraseña incluida.
- 👉 **Qué hacer:** usa la [dirección HTTPS](#https-address) también en casa.

El mismo nivel aparece con un motivo que empieza por *Incierta* cuando LibreFolio no puede saber
dónde estás realmente: el consejo no cambia.

??? info "🔍 Cuándo una conexión es de red local"

    **Una dirección local por `http://` sin cifrar**: una dirección en `10.x`, de `172.16.x` a
    `172.31.x`, en `192.168.x` o en `169.254.x`, una dirección IPv6 de enlace local o local única,
    o un nombre que termina en `.local`, `.lan`, `.home.arpa` o `.internal`, o sin ningún punto,
    como `http://nas:6040`. Un nombre MagicDNS corto de Tailscale, como `http://my-server:6040`,
    tampoco tiene punto, así que cuenta aquí: la IP de Tailscale o el nombre completo que termina
    en `.ts.net` cuenta como [segura](#connection-secure).

    **Incierta**: tu navegador juzga la dirección que abriste, y luego el servidor informa de dónde
    ve llegar la solicitud, solo el tipo de dirección y nunca tu dirección IP. El servidor puede
    confirmar el veredicto del navegador o hacerlo incierto, pero nunca hacer que una conexión
    cuente como segura; hasta que responde, vale el veredicto del navegador. Cuando los dos no
    coinciden, el nivel es red local y el motivo empieza por *Incierta*:

    - una dirección que parece pública, que el servidor ve llegar desde tu red local, desde
      Tailscale o desde el propio servidor, por ejemplo mediante un split DNS o un proxy local;
    - una dirección local o de Tailscale que el servidor ve llegar desde internet.

    El tráfico no está cifrado, y LibreFolio no puede saber dónde estás realmente.

### 🔴 Conexión: no segura {: #connection-not-secure }

Llegaste a LibreFolio por `http://` sin cifrar desde internet, por ejemplo a través de un puerto
abierto en tu router. En un teléfono, un punto rojo en el botón del menú te avisa incluso con la
barra lateral cerrada.

- ✅ **A favor:** funciona desde cualquier lugar, sin nada que instalar.
- ⚠️ **En contra:** las contraseñas y los datos viajan en texto claro por redes que no controlas:
  cualquiera en el camino podría leerlos, o incluso modificarlos.
- 👉 **Qué hacer:** evita esta dirección. Si gestionas el servidor, asigna a LibreFolio una
  [dirección HTTPS](#https-address) y deja de exponer HTTP sin cifrar. Después cambia tu contraseña:
  **Configuración** → [**Perfil**](settings/profile.md) → **Cambiar contraseña**.

??? info "🔍 Cuándo una conexión no es segura"

    **Una dirección pública por `http://` sin cifrar**: una dirección o un nombre que no es local,
    ni de Tailscale, ni el propio servidor, como una IP pública o un nombre de dominio como
    `http://myhome.duckdns.org:6040`. El nivel se mantiene cuando el servidor también ve llegar la
    solicitud desde internet, o no puede saberlo. Si la ve llegar desde tu red local, desde
    Tailscale o desde el propio servidor, el nivel es [red local](#connection-local-network), como
    incierto.

---

## 🔒 Cómo conectarse de forma segura {: #https-address }

Asigna a LibreFolio una dirección HTTPS, y después usa solo esa. Configurarla le corresponde a quien
gestiona el servidor: si no eres tú, pídele la dirección.

- **Tailscale**, sin abrir puertos en tu router: Tailscale Serve da una dirección HTTPS a los
  dispositivos de tu tailnet, y Funnel una dirección pública que no necesita Tailscale en tus
  dispositivos. Consulta [Exponer de forma segura](../admin/service_exposure.md).
- **Un proxy inverso** con un certificado TLS, como Caddy, Traefik o Nginx: consulta
  [Docker avanzado](../admin/docker_advanced.md).

Usa la dirección `https://` en todos los dispositivos, también en casa: guárdala en marcadores, y
actualiza los marcadores antiguos y los accesos directos de la pantalla de inicio que todavía apuntan
a `http://`. El indicador muestra entonces **Conexión: segura**.

Si gestionas el servidor, [Comprobar la seguridad de la conexión](../admin/connection_checks.md)
explica cómo verificar el resultado.

---

## 🧭 Lo que el indicador no hace

El indicador es un consejo, no un control: no bloquea nada. Describe la conexión que estás usando
ahora mismo, así que el mismo LibreFolio puede mostrar **Conexión: segura** en tu portátil y
**Conexión: no segura** en tu teléfono.

Tampoco comprueba los certificados. Un certificado autofirmado que aceptaste en el navegador muestra
**Conexión: segura**: el tráfico está cifrado, pero nadie garantiza que el servidor sea realmente el
tuyo.

Y no siempre ve dónde estás. Cuando LibreFolio se ejecuta en Docker Desktop y se expone
directamente, o está detrás de un proxy que no pasa tu dirección en `X-Forwarded-For`, el servidor
ve a todos los visitantes como locales: HTTP sin cifrar desde internet muestra entonces
**Conexión: red local**, como incierta, en lugar de **Conexión: no segura**. Docker Engine en Linux
conserva tu dirección. En cualquier caso, el consejo es el mismo: usa la dirección HTTPS.

---

## 🔗 Relacionado

- 🌐 **[Exponer de forma segura](../admin/service_exposure.md)** — Tailscale, desde una VPN privada hasta una
  dirección HTTPS pública
- 🔍 **[Comprobar la seguridad de la conexión](../admin/connection_checks.md)** — Para los
  administradores: la dirección HTTPS, la cookie de sesión y el proxy inverso
- 🐳 **[Docker avanzado](../admin/docker_advanced.md)** — Archivo Compose, variables de entorno,
  proxy inverso
- 📝 **[Configuración](../admin/configuration.md)** — Todas las opciones del archivo `.env`
- 📦 **[Instalación con Docker](installation.md)** — Acceso local y remoto después de instalar
- 📱 **[Instalar como aplicación (PWA)](pwa.md)** — Requiere una dirección HTTPS
