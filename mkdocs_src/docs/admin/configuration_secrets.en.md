# 🔐 Configuration: Secrets and Plugin Settings

What must stay private in a LibreFolio installation: the options that are **secrets** (keys, passwords and tokens), also read from files such as Docker secrets; the **instance key**, which protects what LibreFolio stores; the **plugin settings**, API keys included.

New to the `.env` file? How to create it, the main options and which value wins: [Configuration](configuration.md).

---

## 🔐 Secrets {: #secrets }

**Where**: in LibreFolio's `.env`, or in the container's environment (`environment:` block of `docker-compose.yml`). Each secret can also be read from a file, with its `_FILE` variable ([Secrets in Files](#secret-files)). Treat them as privately as the database.

| Secret | From a file | What it is |
| --- | --- | --- |
| `JWT_SECRET` | `JWT_SECRET_FILE` | The key that signs login sessions, in the [main options](configuration.md). |
| `LIBREFOLIO_INSTANCE_KEY` | `LIBREFOLIO_INSTANCE_KEY_FILE` | The [instance key](#instance-key). Not set: LibreFolio creates one in the data directory. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` | The key of a paid search service, for the `apikey` engine of the [web search](configuration_accounts.md#optional-web-search-for-new-assets). |
| `LIBREFOLIO_SMTP_PASSWORD` | `LIBREFOLIO_SMTP_PASSWORD_FILE` | The password of the SMTP server that sends LibreFolio's emails: [Email](email.md). |

A plugin may have secrets of its own, such as the API key of a paid data source: [Plugin Settings](#plugin-settings).

### 📄 Secrets in Files {: #secret-files }

Add `_FILE` to the name of the secret and give the path of a file that holds it, for example `/run/secrets/jwt_secret`. This is how Docker and Kubernetes hand over their secrets: the secret stays out of `.env` and out of the container's environment.

Rules of the file:

- The secret is the text of the file, without the line breaks at its end and without the byte order mark that some Windows editors put at its start. Any other space counts, at the start and at the end too.
- A relative path starts from the project folder.
- A secret or its `_FILE` variable that is empty or holds only spaces counts as not set: a stray space is never used as a key.
- Set one of the two. Both set: the variable itself wins, the file is ignored and the start log has a [warning](configuration_security.md#startup-checks).
- `.env` works both with `./dev.py` and with Docker Compose (`env_file: .env`): both put its values in the environment, where LibreFolio reads them.

If the file does not give the secret:

| Variable | When it is read | If the file does not give the secret |
| --- | --- | --- |
| `JWT_SECRET_FILE`, `LIBREFOLIO_INSTANCE_KEY_FILE`, `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` | at startup | **The server stops at startup.** The error names the variable and the path, never the secret. This covers a file that is missing, cannot be read, is empty or blank (only spaces and line breaks), is not UTF-8 text or is larger than 64 KiB. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` | only when a search uses the `apikey` engine | The server does not stop: the search goes on without the web search, with a warning in the log (`web_link_finder: …; disabling`); the providers' own search keeps working. |
| `LIBREFOLIO_SMTP_PASSWORD_FILE` | only when `LIBREFOLIO_SMTP_HOST` is set | The server does not stop: email stays off, with an error in the log (`Email configuration cannot be used: email stays off`). |

??? example "🐳 A Docker secret with Docker Compose"

    1. **From a terminal, in the folder of `docker-compose.yml`**, save a new key in a file:

        ```bash
        python3 -c "import secrets; print(secrets.token_urlsafe(64))" > jwt_secret.txt
        ```

        You get `jwt_secret.txt` next to `docker-compose.yml`.

    2. **From a terminal**, make the file readable by the user of the image, `1000:1000` for the official one ([Advanced Docker](docker_advanced.md)):

        ```bash
        sudo chown 1000:1000 jwt_secret.txt
        sudo chmod 600 jwt_secret.txt
        ```

        Compose mounts the file in the container as it is on the host, owner and permissions included: if the user of the image cannot read it, the server stops at startup with `cannot be read` for the file.

    3. **In `docker-compose.yml`**, add the marked lines and leave the rest of the service as it is:

        ```yaml
        services:
          librefolio:
            environment:
              - LIBREFOLIO_DATA_DIR=/app/backend/data/prod-docker
              - HOST=0.0.0.0
              - JWT_SECRET_FILE=/run/secrets/jwt_secret  # added
            secrets:                                     # added
              - jwt_secret                               # added
        secrets:                                         # added
          jwt_secret:                                    # added
            file: ./jwt_secret.txt                       # added
        ```

    4. **In `.env`**, if a line gives `JWT_SECRET` a value, remove it: it would win over the file. An empty `JWT_SECRET=` line does no harm.

    5. Restart LibreFolio. With Docker Compose, run `docker compose up -d`.

    The files of `LIBREFOLIO_INSTANCE_KEY_FILE`, `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` and `LIBREFOLIO_SMTP_PASSWORD_FILE` are mounted the same way; what each variable does when the file does not give the secret: the table in [Secrets in Files](#secret-files).

### 🗝️ The Instance Key {: #instance-key }

One secret per installation: LibreFolio derives its own encryption keys from it. There is nothing to set up. LibreFolio uses the first key it finds:

1. `LIBREFOLIO_INSTANCE_KEY`, the key itself;
2. `LIBREFOLIO_INSTANCE_KEY_FILE`, a file that holds it, such as a Docker secret;
3. `secrets/instance.key` in the data directory, which LibreFolio creates the first time it needs it: 43 random characters, in a folder and a file that only the user running LibreFolio can open (`0700` and `0600`).

**To provide a key of your own**, for example in the cloud, from the environment or from a Docker secret instead of the data directory. Every instance has its own key: never share one key between several instances.

1. **From a terminal**, generate the key:

    ```bash
    python3 -c "import secrets; print(secrets.token_urlsafe(32))"
    ```

    You get a random key of at least 32 characters, the minimum. Never use a passphrase: the keys LibreFolio derives from it are only as strong as the passphrase. If LibreFolio has already created `secrets/instance.key`, generate nothing: use its content as the value, because setting `LIBREFOLIO_INSTANCE_KEY` where `secrets/instance.key` already exists changes the key.

2. **In `.env` or in the container's environment**, set the key, or save it in a file and give the path, as in the [Docker example](#secret-files):

    ```env
    LIBREFOLIO_INSTANCE_KEY=<key>
    # or
    LIBREFOLIO_INSTANCE_KEY_FILE=/run/secrets/instance_key
    ```

3. Restart LibreFolio. With Docker Compose, run `docker compose up -d`.

!!! warning "🔑 Never change or delete the key once in use"

    Only the same key can read again what was encrypted with it.

    - Back up `secrets/` with the rest of the data directory, and keep the copies as private as the database: [Backup](filesystem.md#backup).
    - Once the key exists, LibreFolio cannot tell a lost `instance.key` from a first use: it creates a new key, and what the old one encrypted can no longer be read. When you restore the data, put `secrets/` back with it before you start LibreFolio again. Never start LibreFolio on restored data without its `secrets/`.
    - If LibreFolio has already created a new key: stop it, put your copy of `instance.key` in place of the new one and start it again, before anyone enters a [plugin secret](#plugin-secrets) again: a secret entered under the new key would become unreadable once the old one is back.
    - `instance.key` present but damaged or out of reach: LibreFolio logs an error and never replaces it. What to do: [Startup Checks](configuration_security.md#startup-checks).

### 🔏 The Key Check {: #instance-key-check }

Next to the key, LibreFolio keeps a **check value**: `secrets/instance.key.check` in the data directory (folder `0700`, file `0600`), a short fingerprint of the key from which the key cannot be worked out. At each start it compares the fingerprint of the key it has now with the stored one: they differ when it starts with **a key other than the one the data was written with** (a machine that got the wrong key, a key file replaced by a new one).

- **The first start** writes the file. It does not write it if saved plugin secrets already exist and the current key reads none of them: it would take the wrong key for the right one. The check then says that the key does not match until you put the right one back.
- **With a key that does not match**: an error in the log at start, and the **Security** tab of Settings › Administration says so (the check is `platform.instance_key_check`). **The instance keeps serving**: your data does not depend on this key, only the saved plugin secrets do.

**The fix is the right key.**

1. **In `.env` or in the container's environment** (`LIBREFOLIO_INSTANCE_KEY` or its `_FILE`), or **in the data directory** (`secrets/instance.key`), put back the key the data was written with.
2. Restart LibreFolio. With Docker Compose, run `docker compose up -d`. The next answer is `ok`, with nothing else to do.

**To really change the key**, for example when you decide that the old secrets are lost and the plugin secrets are entered again:

1. **In `.env` or in the container's environment**, add, for **one start only**:

    ```env
    LIBREFOLIO_INSTANCE_KEY_ACCEPT=1
    ```

    Values: `1` or `0`, `true` or `false`, `yes` or `no`, `on` or `off`; any other value stops the start, naming the variable.

2. Restart LibreFolio. With Docker Compose, run `docker compose up -d`. That start replaces the stored check value with the one of the key it has, and logs a warning.

3. **Remove the variable and restart again.** While it is set, every start accepts whatever key it has and the protection does nothing; the warning is logged at every start, as a reminder.

!!! note "📏 What the check cannot see"

    - Without a stored check value and without any saved plugin secret there is nothing to compare: the answer is `ok`. The first start of an instance whose key was already wrong cannot be told; from then on, the stored value protects it.
    - If the data comes back without its `secrets/` folder, the value is written again at the next start; while it is missing, the plugin secrets decide.
    - A check value that cannot be read (a permission, a damaged file) never stops a backup: the answer is `ok` and the log has a warning, once.

---

## 🧩 Plugin Settings {: #plugin-settings }

A plugin can ask for settings of its own: the API key of a paid data source, a region, a preference. Of the plugins shipped with LibreFolio, two ask for one, a personal search preference each: justETF and Borsa Italiana. None asks for an instance-wide setting; a plugin you add may. Two kinds:

| Kind | Who saves it | Who reads it | From an environment variable |
| --- | --- | --- | --- |
| **Instance-wide** | only an administrator | every user reads a plain value; of a secret one, such as an API key, they only know whether it is set | yes: [The Variables](#plugin-variables) |
| **Personal** | only that user | only that user; administrators never see it | no |

**Where to change them**: in **Settings › Plugins**, a tab every user has: the personal ones each their own, the instance-wide ones only administrators (the other users see them read-only). In the asset dialog, **Configure**, next to the chosen price provider, opens the same form for that provider alone. What the tab shows, setting by setting: [Plugin Settings](../user/settings/plugins.md) in the user manual.

The plugins that have settings, with the keys of their settings, are listed by `GET /api/v1/settings/plugins` to any signed-in user.

### 🏷️ The Variables {: #plugin-variables }

**Where**: in `.env` or in the container's environment, like the other options; only for instance-wide settings. The name of the variable:

```text
LIBREFOLIO_PLUGIN_<KIND>_<PLUGIN CODE>_<SETTING KEY>
```

- `<KIND>` is `ASSET` for a price provider and `FX` for an exchange-rate provider.
- All uppercase; every character other than a letter or a digit becomes `_`. The `api_key` setting of the price provider `my_provider`:

    ```env
    LIBREFOLIO_PLUGIN_ASSET_MY_PROVIDER_API_KEY=<value>
    ```

- Each variable also has a `_FILE` form: the path of a file that holds the value, such as a Docker secret, read as in [Secrets in Files](#secret-files). A file that cannot be read never stops the server: see [below](#plugin-variable-lock).
- For a secret setting, a plugin may also accept the variable it read before it had settings, so that an existing installation keeps working. Both set, the name above wins.

Then restart LibreFolio. With Docker Compose, run `docker compose up -d`.

### 🔒 A Variable Locks the Setting {: #plugin-variable-lock }

While its variable is set, a setting takes its value from there and nobody can change it from inside LibreFolio: a save is refused (`LOCKED_BY_ENV`), and a value saved earlier is ignored until you remove the variable and restart. **Settings › Plugins** shows the setting read-only, a secret only as *Set*: *Set by the server variable* and the variable's name for administrators, *Set by the server* for the other users.

**A wrong value**, one the setting does not accept, or a `_FILE` that cannot be read, still locks the setting, and the plugin is then not configured: LibreFolio refuses every request to it, even when the setting is optional, until you fix the variable. It never falls back to the saved value or to the plugin's default.

- In the log, a warning once per server process: `Plugin setting variable invalid: the plugin is not configured until it is fixed`, with the variable and the reason, never the value.
- In **Settings › Plugins**, the plugin's badge reads **To configure** and the setting says that its variable is invalid.

Fix the value **in `.env` or in the container's environment**, then restart LibreFolio. With Docker Compose, run `docker compose up -d`.

### 🔐 Saved Secrets and the Instance Key {: #plugin-secrets }

A setting saved inside LibreFolio is kept in the database. A secret one is first encrypted (AES-256-GCM) with a key derived from the [instance key](#instance-key), and is never shown again, not even to whoever saved it: **Settings › Plugins** only says whether it is set, *Set on* and the date it was saved. A value given by a variable, secret or not, is never saved in the database.

**If the instance key changes**, the saved secrets can no longer be read. LibreFolio keeps them, reports them as unreadable and never uses a wrong value. The tab says so under each one: *Saved, but this instance's key cannot read it. If an administrator can put the old key back, that comes first; otherwise enter it again.* From the first start after the change, and at every start until they are entered again or the old key is back, the log has an error that counts the instance-wide ones, if there are any: [Startup Checks](configuration_security.md#startup-checks).

| Situation | What to do |
| --- | --- |
| You still have the old key | Put it back, before anyone enters the secrets again ([The Instance Key](#instance-key) explains why). |
| You no longer have it | Enter every secret again in **Settings › Plugins**. |
| You want to bring them into another installation, which keeps its own key | **From a terminal, on that installation**, restore a backup with the old key: `backup restore` with `--instance-key-file` re-encrypts them with that installation's key ([The Instance Key of Another Installation](cli_tools.md)). |

**If `secrets/instance.key` is damaged or out of reach**, LibreFolio starts anyway, with an error from the [startup checks](configuration_security.md#startup-checks); a key you set yourself that cannot be used stops the start instead. Until you fix it:

- every saved secret is reported as unreadable, and the plugins run without them: a plugin that needs one answers that it is not configured;
- secrets given by variables keep working;
- a new secret cannot be saved: the tab answers *Secrets cannot be saved: this instance's key cannot be used (see the configuration checks).*, and nothing of that save is written;
- the log has one more error, the first time each server process needs a saved secret: `Plugin secrets unreadable: the instance key cannot be used (see the configuration checks)`.

Fix the file **in the data directory**, or restore it from a backup: the saved secrets come back. A new key does not bring them back: they would have to be entered again.

!!! warning "🗄️ The database and the key in the same folder"

    The database (`sqlite/app.db`) and the instance key that LibreFolio generates (`secrets/instance.key`) are in the same [data directory](filesystem.md): whoever gets both, the folder itself or a copy of it, can read every saved secret.

    - Keep the data directory, and every copy of it, private.
    - Better still, provide the instance key from a secret store, with `LIBREFOLIO_INSTANCE_KEY_FILE` (a Docker secret) or `LIBREFOLIO_INSTANCE_KEY`: LibreFolio then never writes it to the data directory. If `secrets/instance.key` already exists, use its content as the value ([The Instance Key](#instance-key)): another key would make the saved secrets unreadable.

---

## 🔗 Related

- 📄 **[Configuration](configuration.md)** — Create the `.env` File, Main Options, Parameters Set by the Tools, …
- 📄 **[Configuration: Checks and Protections](configuration_security.md)** — Startup Checks, Browser Protections, Stopping the Server
- 📄 **[Configuration: Accounts and Asset Search](configuration_accounts.md)** — Accounts and Sign-ups, The Order of the Price Providers in the Search, Optional: Web Search for New Assets
