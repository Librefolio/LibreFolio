# 🌍 Exponer de forma segura: acceso público con Funnel

Esta página pone LibreFolio en internet con Tailscale Funnel, en una dirección HTTPS pública, sin abrir ningún puerto en tu router: la configuración única de Funnel y las ACL, y luego el Nivel 3 (una dirección para LibreFolio) o el Nivel 4 (una dirección por servicio, cada uno en su propio contenedor Docker).

Asume que Tailscale ya está instalado en tu servidor. El porqué de Tailscale, el **Paso 0** (la instalación) y los Niveles 1 y 2 privados están en [Exponer de forma segura](service_exposure.md). Aquí, `6040` es el puerto predeterminado de LibreFolio: si estableces un `PORT` diferente en tu `.env`, usa ese número en su lugar.

---

## 🔑 Habilitar Funnel y las ACL en la consola {: #enabling-funnel-and-acls-on-the-console }

**Configuración única, necesaria para los Niveles 3 y 4.** Permite Funnel en las reglas de control de acceso (ACL) de todo tu tailnet.

!!! warning "🔐 Antes de hacerlo público"

    Con Funnel, cualquiera en internet puede abrir la página de inicio de sesión de LibreFolio. Crea tu propia cuenta primero: hasta que exista una cuenta, cualquiera puede registrarse, y la primera cuenta registrada pasa a ser administradora. Después de eso, una instancia nueva solo deja entrar a personas con un enlace de invitación (**Registro** está en **Por invitación** de forma predeterminada): envía uno a cada persona a la que quieras dejar entrar. Una instancia actualizada desde una versión anterior conserva su modo: si **Registro** en la **Configuración global** está en **Abierto**, cámbialo a **Por invitación**, o a **Cerrado** si nadie más debe unirse (consulta [Quién puede registrarse](settings.md)).

1. Visita la página [Controles de acceso](https://login.tailscale.com/admin/acls) en la consola de administración de Tailscale.
2. Haz clic en el botón **Añadir atributo de nodo**.
3. Rellena el formulario:
    * **Destinos**: los nodos a los que se permite usar Funnel. **Sugerimos `tag:external_access`** (darás esta etiqueta a los contenedores Docker del Nivel 4) o `autogroup:member` (todos los dispositivos registrados en tu cuenta personal).
    * **Atributos**: introduce `funnel`.
    * **Nota**: unas palabras sobre por qué existe la regla.
    * **Grupos de IP, App, Capacidad, etc.**: no hacen falta aquí; déjalos vacíos o con sus valores predeterminados.

![Añadir atributo de nodo](../static/tailscale-guide/TailscaleNodeAttribute.png)

Esta regla no es una clave de autenticación: las claves de autenticación (Nivel 4) solo registran un nuevo dispositivo o contenedor en tu tailnet.

??? example "📄 Ver la configuración JSON completa de las ACL para habilitar Funnel"

    Si prefieres editar el archivo de políticas directamente, este ejemplo funcional habilita Funnel para tus propios dispositivos y para los contenedores etiquetados `tag:external_access`:

    ```json
    {
      // Declaration of authorized tags
      "tagOwners": {
        "tag:external_access": ["autogroup:admin"]
      },

      // Standard access rules
      "acls": [
        // Allows all nodes in your private network to communicate
        {"action": "accept", "src": ["*"], "dst": ["*:*"]}
      ],

      "ssh": [
        {
          "action": "check",
          "src":    ["autogroup:member"],
          "dst":    ["autogroup:self"],
          "users":  ["autogroup:nonroot", "root"]
        }
      ],

      // Enabling Funnel on specific nodes or tags
      "nodeAttrs": [
        {
          "target": ["autogroup:member"],
          "attr":   ["funnel"]
        },
        {
          "target": ["tag:external_access"],
          "attr":   ["funnel"]
        }
      ]
    }
    ```

---

## 🥈 Nivel 3: dirección HTTPS pública con Tailscale Funnel {: #level-3-public-https-address-with-tailscale-funnel }

**Ideal para una dirección pública, sin VPN en el cliente.** Funnel publica LibreFolio en una dirección segura `https://<server-name>.your-tailnet.ts.net` que cualquiera puede abrir **sin instalar Tailscale**. HTTPS también es lo que te permite [instalar LibreFolio como aplicación (PWA)](../user/pwa.md) en tu teléfono.

**Antes de empezar:** completa la [configuración única de Funnel y las ACL en la consola](#enabling-funnel-and-acls-on-the-console).

```mermaid
graph LR
    User["👤 Usuario (sin VPN)"] -->|Solicitud HTTPS| Funnel["☁️ Entrada de Tailscale Funnel<br>(servidor público de Tailscale)"]
    Funnel -->|Tunelización WireGuard| Server["🖥️ Servidor local (tailscaled)<br>(100.a.b.c)"]
    subgraph LAN ["Red LAN local"]
        Server -->|Reenvío local| LibreFolio["📊 LibreFolio (puerto 6040)"]
        Server -.->|"<font color='red'><b>No se puede exponer</b></font>"| Other["🔌 Otros servicios locales (puertos diferentes)"]
    end
    style LibreFolio fill:#d4edda,color:#1b1b1b,stroke:#28a745,stroke-width:2px;
    style Other fill:#f8d7da,color:#1b1b1b,stroke:#dc3545,stroke-width:2px;
    linkStyle 3 stroke:#dc3545,stroke-width:2px;
```

### ▶️ Paso 1: Iniciar Funnel en el servidor

En el servidor, publica el puerto local de LibreFolio:

```bash
tailscale funnel --bg 6040
```

Funnel lo sirve en `https://<server-name>.your-tailnet.ts.net` en el puerto 443; `--bg` lo mantiene en ejecución después de que cierres la terminal, y `tailscale funnel reset` lo detiene. Aquí no se necesita ninguna clave de autenticación: el servidor ya se unió a tu tailnet en el [Paso 0](service_exposure.md).
Tampoco hay nada que configurar en LibreFolio: Funnel envía `X-Forwarded-Proto: https`, así que, con el valor predeterminado `SESSION_COOKIE_SECURE=auto`, LibreFolio marca su [cookie de sesión](configuration.md) como `Secure`. `never` solo es para un proxy que declara HTTPS a un navegador que usa HTTP sin cifrar.

### ✅ Paso 2: Aprobar y esperar la propagación {: #step-2-approve-and-wait-for-propagation }

La primera vez, la terminal advierte de que Funnel aún no está permitido para este nodo y muestra un enlace como este:

```text
Funnel is enabled, but the list of allowed nodes in the tailnet policy file does not include the one you are using.
To give access to this node you can edit the tailnet policy file, or visit:

         https://login.tailscale.com/f/funnel?node=xxxxxx
```

1. Abre el enlace en tu navegador, inicia sesión en Tailscale y aprueba Funnel para este nodo.
2. La terminal muestra entonces tu URL pública.
3. Espera unos minutos a que se propaguen los registros de MagicDNS antes de abrirlo desde una red externa.

Para comprobar el resultado, consulta [Comprobación de la seguridad de la conexión](connection_checks.md#checklist).

⚠️ **Límites:** una máquina tiene un solo nombre público, que deben compartir todos los servicios que publiques desde ella. El Nivel 4 da a cada servicio el suyo.

---

## 🥇 Nivel 4: Multi-Funnel con sidecars de Docker {: #level-4-multi-funnel-with-docker-sidecars }

**Ideal para usuarios de Docker que quieren una dirección pública por servicio.** Cada servicio recibe un pequeño contenedor de Tailscale (un *sidecar*) que se une a tu tailnet como su propio nodo, con su propia dirección `https://<name>.your-tailnet.ts.net`. Un script de inicio instala **socat** en el sidecar, y socat reenvía el tráfico de Funnel a la IP estática de la LAN del servicio.

**Antes de empezar:** completa la [configuración única de Funnel y las ACL en la consola](#enabling-funnel-and-acls-on-the-console).

??? info "🧰 ¿Qué es socat?"

    **socat** (SOcket CAT) es una pequeña herramienta de línea de comandos que retransmite datos entre dos conexiones. Aquí funciona como un **mini reenviador**: escucha en un puerto dentro del contenedor de Tailscale y pasa todo lo que recibe al puerto real del servicio en tu LAN.

Añade un sidecar por cada servicio que quieras publicar, en uno o varios hosts; el único límite es el número de dispositivos etiquetados que permita tu [plan de Tailscale](https://tailscale.com/pricing). En este ejemplo, dos hosts ejecutan dos sidecars cada uno:

```mermaid
graph LR
    User["👤 Usuario externo"] -->|HTTPS| Funnel1["☁️ Funnel 1<br>(librefolio.yourtailnet.ts.net)"]
    User -->|HTTPS| Funnel2["☁️ Funnel 2<br>(service1.yourtailnet.ts.net)"]
    User -->|HTTPS| Funnel3["☁️ Funnel 3<br>(service3.yourtailnet.ts.net)"]
    User -->|HTTPS| Funnel4["☁️ Funnel 4<br>(service4.yourtailnet.ts.net)"]
    
    Funnel1 -->|WireGuard| TSC1["🐳 Contenedor Tailscale 1<br>(100.101.x.x)"]
    Funnel2 -->|WireGuard| TSC2["🐳 Contenedor Tailscale 2<br>(100.102.x.x)"]
    Funnel3 -->|WireGuard| TSC3["🐳 Contenedor Tailscale 3<br>(100.103.x.x)"]
    Funnel4 -->|WireGuard| TSC4["🐳 Contenedor Tailscale 4<br>(100.104.x.x)"]
    
    subgraph LAN ["Red LAN local (192.168.1.0/24)"]
        subgraph Host2 ["Servidor 2 (p. ej. mini PC - 192.168.1.10)"]
            TSC3 -->|socat: TCP/8080| Service3["🔌 Servicio 3<br>(192.168.1.10:8080)"]
            TSC4 -->|socat: TCP/9000| Service4["🔌 Servicio 4<br>(192.168.1.10:9000)"]
        end
        subgraph Host1 ["Servidor 1 (p. ej. NAS - 192.168.1.20)"]
            TSC1 -->|socat: TCP/6040| LibreFolio["📊 LibreFolio<br>(192.168.1.20:6040)"]
            TSC2 -->|socat: TCP/80| Service1["🔌 Servicio 1<br>(192.168.1.20:80)"]
        end
    end
    style LibreFolio fill:#d4edda,color:#1b1b1b,stroke:#28a745,stroke-width:2px;
```

### 📁 Paso 1: Preparar la carpeta y el script

Crea una carpeta en el servidor, por ejemplo donde guardas tus volúmenes persistentes de Docker:

```bash
# Create a folder for the Tailscale nodes and enter it
mkdir -p <path_chosen>/tailscale-nodes
cd <path_chosen>/tailscale-nodes
```

Luego descarga en ella el script de inicio <a href="https://raw.githubusercontent.com/Librefolio/LibreFolio/main/mkdocs_src/docs/static/tailscale-guide/custom_startup.sh" target="_blank" rel="noopener noreferrer">custom_startup.sh</a>:

```bash
# Download the script from the official repository
wget https://raw.githubusercontent.com/Librefolio/LibreFolio/main/mkdocs_src/docs/static/tailscale-guide/custom_startup.sh
# Make the script executable
chmod +x custom_startup.sh
```

??? info "🔄 ¿Ya configuraste el sidecar antes? Actualiza tu copia del script"

    El script actual también funciona como **watchdog** y viene con una comprobación de estado de Docker (consulta el Paso 2). Si tu sidecar ejecuta una copia anterior, actualízala:

    1. **Descarga el script de nuevo** en la misma carpeta. La opción `-O custom_startup.sh` sobrescribe el archivo antiguo (sin ella, `wget` guarda la descarga como `custom_startup.sh.1`). Luego asegúrate de que el script se pueda ejecutar:

        ```bash
        cd <path_chosen>/tailscale-nodes
        wget -O custom_startup.sh https://raw.githubusercontent.com/Librefolio/LibreFolio/main/mkdocs_src/docs/static/tailscale-guide/custom_startup.sh
        chmod +x custom_startup.sh
        ```

    2. **Actualiza tu archivo compose**: añade `TS_ENABLE_HEALTH_CHECK`, `TS_LOCAL_ADDR_PORT` y, opcionalmente, `STARTUP_TIMEOUT` al servicio de Tailscale, junto con el bloque `healthcheck`, exactamente como en el Paso 2.

    3. **Vuelve a crear el contenedor**: un reinicio no aplica los cambios de compose. Ejecuta `docker compose up -d` en la carpeta de tu `docker-compose.yml` (vuelve a crear los servicios cuya configuración cambió), o usa la acción *Recrear* / volver a desplegar de Portainer o CasaOS.

    4. **Comprueba el log** con `docker logs -f tailscale-librefolio`: deberías ver `Tailscale is running.`, luego `Starting the funnel on port 6040...` y `Available on the internet:` con tu URL pública. Dentro del `start_period` de 2 minutos de la comprobación de estado, Docker muestra el contenedor como **healthy** (`docker ps`, Portainer, CasaOS). Si, por el contrario, se reinicia continuamente, consulta el panel de solución de problemas del [Paso 3](#3-startup-and-approval).

### 🐳 Paso 2: Configurar Docker Compose

Añade el servicio de Tailscale al **mismo `docker-compose.yml` que el servicio** que expone (por ejemplo, LibreFolio), para que ambos permanezcan juntos:

```yaml
services:
  tailscale-librefolio:
    image: tailscale/tailscale:latest
    container_name: tailscale-librefolio
    hostname: tailscale-librefolio
    restart: unless-stopped
    privileged: false
    network_mode: bridge
    cap_add:
      - NET_ADMIN
      - NET_RAW
    devices:
      - /dev/net/tun:/dev/net/tun
    command:
      - /custom_startup.sh
    environment:
      - HOST_IP=192.168.1.20                # Local IP of the service to expose (e.g. Server 1)
      - HOST_PORT=6040                      # Real port of the service to expose
      - TAILSCALE_FUNNEL_PORT=6040          # Internal Funnel port
      - TS_HOSTNAME=librefolio              # Custom public hostname (e.g. librefolio)
      - TS_AUTHKEY=tskey-auth-...           # Authentication key generated by Tailscale
      - TS_ACCEPT_DNS=true
      - TS_STATE_DIR=/var/lib/tailscale
      - TS_USERSPACE=false
      - TS_ENABLE_HEALTH_CHECK=true         # Expose /healthz for the healthcheck below (Tailscale ≥ 1.78)
      - TS_LOCAL_ADDR_PORT=127.0.0.1:9002   # Where /healthz listens: inside the container only
      - STARTUP_TIMEOUT=180                 # Optional: seconds to reach the Running state (default 180)
    volumes:
      - <path_chosen>/tailscale-nodes/tailscale-librefolio/state:/var/lib/tailscale
      - <path_chosen>/tailscale-nodes/custom_startup.sh:/custom_startup.sh
      - /etc/localtime:/etc/localtime:ro
      - /etc/timezone:/etc/timezone:ro
    # Shows healthy/unhealthy in Docker, Portainer or CasaOS; the restart itself comes from custom_startup.sh exiting
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:9002/healthz"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 120s
```

Luego establece estos valores para tu red:

| Valor | Qué poner |
|---|---|
| `<path_chosen>` | La ruta absoluta elegida en el Paso 1, donde viven el script y los datos de estado (p. ej. `/home/user/docker`). |
| `HOST_IP` | La IP estática de la LAN de la máquina que ejecuta el servicio. |
| `HOST_PORT` | El puerto real del servicio en esa máquina: para LibreFolio, el `PORT` de tu `.env` (`6040` de forma predeterminada). |
| `TAILSCALE_FUNNEL_PORT` | El puerto en el que escucha el contenedor y que publica a través de Funnel. Establécelo en el mismo valor que `HOST_PORT`. |
| `TS_HOSTNAME` | El nombre del nodo: la dirección pública pasa a ser `https://TS_HOSTNAME.your-tailnet.ts.net`. |
| `TS_AUTHKEY` | La clave de autenticación que registra el contenedor en tu tailnet (ver más abajo). |

Para obtener la clave de autenticación para `TS_AUTHKEY`:

1. Ve a [Claves de administración de Tailscale](https://login.tailscale.com/admin/settings/keys).
2. En la sección **Claves de autenticación** (*no* en la sección de tokens de acceso a la API), haz clic en el botón **Generar clave de autenticación...**.
3. Activa el interruptor **Etiquetas** y selecciona tu etiqueta (p. ej. `tag:external_access`). Añade una descripción que reconozcas, como `docker-librefolio-funnel`.
4. Haz clic en **Generar** y copia la clave (`tskey-auth-...`).

Una vez que el contenedor se ha iniciado, la clave de un solo uso se consume: desaparece de la lista **Claves** y el nuevo dispositivo aparece en **Máquinas**.

??? info "🩺 Watchdog y comprobación de estado: qué hace la configuración adicional"

    El script de inicio también funciona como **watchdog**, mientras que el bloque `healthcheck` hace visible el estado del contenedor:

    * **Watchdog (reinicio automático)**: si Tailscale no puede iniciarse (por ejemplo, si no hay conexión a internet al arrancar o hay un flag incorrecto), no alcanza el estado *Running* dentro de `STARTUP_TIMEOUT` segundos, o si Tailscale, socat o Funnel se detienen más adelante, el script termina con un error y Docker reinicia el contenedor (`restart: unless-stopped`). El contenedor nunca se queda "en ejecución" sin nada detrás, y un `docker stop` sigue apagando todo de forma limpia.
    * **Comprobación de estado (solo estado)**: `TS_ENABLE_HEALTH_CHECK=true` activa el endpoint `/healthz` de Tailscale (Tailscale 1.78 o posterior), que responde `200` mientras el nodo tiene una dirección IP de Tailscale y `503` en caso contrario. Docker lo consulta con regularidad y marca el contenedor como *healthy* o *unhealthy*; Portainer y CasaOS muestran el mismo estado.

    Docker estándar (fuera del modo Swarm) **no** reinicia un contenedor marcado como *unhealthy*: el reinicio proviene de que el script termina, así que no necesitas un contenedor "autoheal" adicional (esos ayudantes también necesitan el socket de Docker, lo que implica control total del host).

    | Configuración opcional | Qué hace |
    |---|---|
    | `TS_LOCAL_ADDR_PORT` | Donde escucha `/healthz`. El endpoint no necesita autenticación, y el valor predeterminado de Tailscale, `[::]:9002`, escucha en todas las interfaces: `127.0.0.1:9002` lo mantiene dentro del contenedor. Si lo cambias, actualiza también la URL de la prueba `healthcheck`. |
    | `STARTUP_TIMEOUT` | Segundos que el script espera al estado *Running* (predeterminado `180`) antes de terminar y de que Docker reinicie el contenedor. Auméntalo solo en un servidor muy lento. |
    | `DEBUG` | No está en el ejemplo anterior. `DEBUG=1` imprime cada comando que ejecuta el script en el log del contenedor, para solucionar problemas. Desactivado de forma predeterminada para mantener legible el log. |

??? tip "📈 Supervisar LibreFolio con un monitor (Uptime Kuma)"

    El servicio `librefolio` tiene su propia comprobación de estado, en `GET /api/v1/system/health` (consulta el archivo compose de abajo): le indica a Docker que el servidor responde. Para supervisar LibreFolio desde otro dispositivo, por ejemplo con **Uptime Kuma**, apunta el monitor a `/api/v1/system/ready` en la dirección con la que abres LibreFolio, como `https://librefolio.your-tailnet.ts.net/api/v1/system/ready`. No necesita inicio de sesión y responde:

    * **`200`** cuando LibreFolio está listo para atender solicitudes;
    * **`503`** cuando no lo está, con la comprobación que falla indicada en la respuesta: `database` (`unreachable`) o `migrations` (`behind`, `ahead`, `unknown`).

    La [Guía avanzada de Docker](docker_advanced.md), sección «Servicio: `librefolio`», explica los códigos.

??? example "📄 Ver el archivo Docker Compose de producción completo (LibreFolio + Tailscale)"

    Un `docker-compose.yml` completo: el servicio `librefolio` del `docker-compose.prod.yml` oficial, con el sidecar de Tailscale al lado:

    ```yaml
    # =============================================================================
    # LibreFolio — Production Docker Compose
    # =============================================================================
    # Optimized for end-users running the official pre-built image from GHCR.
    # =============================================================================

    services:
      librefolio:
        image: ${LIBREFOLIO_IMAGE:-ghcr.io/librefolio/librefolio:latest}
        container_name: librefolio
        restart: unless-stopped
        ports:
          - "${PORT:-6040}:6040"
        volumes:
          - ./LibreFolio-data:/app/backend/data/prod-docker
        env_file: .env
        environment:
          - LIBREFOLIO_DATA_DIR=/app/backend/data/prod-docker
          - HOST=0.0.0.0
          - PORT=6040
        healthcheck:
          test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:6040/api/v1/system/health')"]
          interval: 30s
          timeout: 10s
          start_period: 15s
          retries: 3

      tailscale-librefolio:
        image: tailscale/tailscale:latest
        container_name: tailscale-librefolio
        hostname: tailscale-librefolio
        restart: unless-stopped
        privileged: false
        network_mode: bridge
        cap_add:
          - NET_ADMIN
          - NET_RAW
        devices:
          - /dev/net/tun:/dev/net/tun
        command:
          - /custom_startup.sh
        environment:
          - HOST_IP=192.168.1.20                # Local IP of the service to expose (e.g. Server 1)
          - HOST_PORT=6040                      # Real port of the service to expose
          - TAILSCALE_FUNNEL_PORT=6040          # Internal Funnel port
          - TS_HOSTNAME=librefolio              # Custom public hostname (e.g. librefolio)
          - TS_AUTHKEY=tskey-auth-...           # Replace with your generated key
          - TS_ACCEPT_DNS=true
          - TS_STATE_DIR=/var/lib/tailscale
          - TS_USERSPACE=false
          - TS_ENABLE_HEALTH_CHECK=true         # Expose /healthz for the healthcheck below (Tailscale ≥ 1.78)
          - TS_LOCAL_ADDR_PORT=127.0.0.1:9002   # Where /healthz listens: inside the container only
          - STARTUP_TIMEOUT=180                 # Optional: seconds to reach the Running state (default 180)
        volumes:
          - /DATA/AppData/tailscale-nodes/tailscale-librefolio/state:/var/lib/tailscale
          - /DATA/AppData/tailscale-nodes/custom_startup.sh:/custom_startup.sh
          - /etc/localtime:/etc/localtime:ro
          - /etc/timezone:/etc/timezone:ro
        # Shows healthy/unhealthy in Docker, Portainer or CasaOS; the restart itself comes from custom_startup.sh exiting
        healthcheck:
          test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:9002/healthz"]
          interval: 30s
          timeout: 5s
          retries: 3
          start_period: 120s
    ```

### 🚀 Paso 3: Iniciar y aprobar Funnel {: #3-startup-and-approval }

Inicia el stack, el servicio y su sidecar de Tailscale juntos:

```bash
docker compose up -d
```

Luego sigue el log del contenedor de Tailscale:

```bash
docker logs -f tailscale-librefolio
```

En el primer inicio, el log muestra el enlace de aprobación para el nuevo nodo:

```text
Funnel is enabled, but the list of allowed nodes in the tailnet policy file does not include the one you are using.
To give access to this node you can edit the tailnet policy file, or visit:

         https://login.tailscale.com/f/funnel?node=nsKGo6k9ZF11CNTRL
```

* Abre el enlace en tu navegador, inicia sesión en Tailscale y aprueba la activación de Funnel.
* Justo después de la aprobación, el log confirma la URL pública y el proxy local:

```text
Available on the internet:

https://librefolio.yourtailnet.ts.net/
|-- proxy http://127.0.0.1:6040

Press Ctrl+C to exit.
```

El servicio ya está en línea: espera unos minutos a que se propaguen los registros de MagicDNS y luego abre la URL.
No hay nada que configurar en LibreFolio: Funnel envía `X-Forwarded-Proto: https` y socat lo transmite, así que, con el valor predeterminado `SESSION_COOKIE_SECURE=auto`, LibreFolio marca su [cookie de sesión](configuration.md) como `Secure`. `never` solo es para un proxy que declara HTTPS a un navegador que usa HTTP sin cifrar.

Para comprobar el resultado, consulta [Comprobación de la seguridad de la conexión](connection_checks.md#checklist).

??? question "🛠️ El contenedor se reinicia en bucle o está marcado como unhealthy"

    Un problema persistente se manifiesta como un contenedor que se reinicia continuamente (Docker, Portainer o CasaOS también pueden marcarlo como *unhealthy*), no como uno que parece "en ejecución" pero no funciona. Lee el log con `docker logs tailscale-librefolio`: antes de cada reinicio, el script imprime qué ha fallado, normalmente seguido de `Exiting so Docker restarts the container.` Las causas más habituales son:

    * **Un flag en `TS_EXTRA_ARGS` no tiene valor.** Esta variable opcional (no está en el compose anterior) pasa flags adicionales a `tailscale up`, separados por espacios. Un flag sin su valor hace que `tailscale up` falle: el motivo está en la línea justo después de `Running 'tailscale up'`, encima del texto de ayuda que empieza por `USAGE` (por ejemplo, `flag needs an argument: -advertise-tags`), seguido de `failed to auth tailscale: … tailscale up failed: exit status 2` y `containerboot exited before Tailscale was running.` Escribe cada valor como `--flag=value` o `--flag value`: `--advertise-tags=tag:container` y `--advertise-tags tag:container` funcionan ambos.
    * **Un panel de administración cortó el valor.** El editor de variables de entorno de CasaOS (y de paneles similares) trunca un valor en su segundo `=`: `TS_EXTRA_ARGS=--advertise-tags=tag:container` pasa a ser `--advertise-tags`, que falla como se describe arriba. En estos paneles, escribe los valores de los flags con un espacio: `--advertise-tags tag:container`.
    * **Falta una variable obligatoria**: el script se detiene de inmediato con `HOST_IP is not set` (o el mismo mensaje para `HOST_PORT` o `TAILSCALE_FUNNEL_PORT`).
    * **No hay conexión a internet al arrancar**: el contenedor se sigue reiniciando hasta que Tailscale puede iniciarse, y luego funciona con normalidad. Esto es lo esperado.
    * **Inicio muy lento**: el log muestra `Tailscale is not running after 180s.`; aumenta `STARTUP_TIMEOUT`.
    * **Unhealthy, pero sin reiniciarse**: la comprobación de estado no obtiene una respuesta correcta de `/healthz`. Si acabas de añadirla, asegúrate de que `TS_ENABLE_HEALTH_CHECK=true` esté establecido y de que la URL de la prueba `healthcheck` coincida con `TS_LOCAL_ADDR_PORT`; de lo contrario, el nodo no tiene una dirección IP de Tailscale en ese momento.

    Para rastrear cada comando del script, añade `DEBUG=1` a la sección `environment`, vuelve a crear el contenedor y lee el log de nuevo.

Como su clave de autenticación lleva una etiqueta, Tailscale desactiva la caducidad de la clave para el contenedor de forma predeterminada. Con una clave sin etiqueta, desactívala como para el servidor (consejo al final del [Paso 0](service_exposure.md)).

⚠️ **Límites:** requiere una terminal y editar un poco los archivos Docker Compose.

---

## 🔗 Relacionado

- 📄 **[Exponer de forma segura](service_exposure.md)** — ¿Por qué no un simple reenvío de puertos?, Paso 0: Instalar Tailscale en tus dispositivos, Nivel 1: VPN privada punto a punto, …
- 🔗 **[Enlaces útiles](service_exposure.md)** — La consola de Tailscale, las ACL y las guías oficiales de Funnel y Docker
