# 🔐 Configuration: Secrets and Plugin Settings

This page covers what must stay private in a LibreFolio install: the options that are **secrets**
(keys, passwords and tokens), which can also be read from files such as Docker secrets, the
**instance key** that protects what LibreFolio stores, and the **settings of the plugins**, API keys
included.

New to the `.env` file? How to create it, the main options and which value wins are in
[Configuration](configuration.md); this page goes deeper into the secrets.

---

## 🔐 Secrets {: #secrets }

These options are secrets: keep them as private as the database. Each one can be written in `.env` or
read from a file.

| Secret | From a file | What it is |
| --- | --- | --- |
| `JWT_SECRET` | `JWT_SECRET_FILE` | The key that signs login sessions, in the [main options](configuration.md). |
| `LIBREFOLIO_INSTANCE_KEY` | `LIBREFOLIO_INSTANCE_KEY_FILE` | The [instance key](#instance-key). Not set: LibreFolio creates one in the data directory. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` | The key of a paid search service, for the `apikey` engine of the [web search](configuration_accounts.md#optional-web-search-for-new-assets). Unlike the first two, a file that cannot give it does not stop the server: it only turns the web search off. |
| `LIBREFOLIO_SMTP_PASSWORD` | `LIBREFOLIO_SMTP_PASSWORD_FILE` | The password of the SMTP server that sends LibreFolio's emails: see [Email](email.md). Like the web-search key, a file that cannot give it does not stop the server: it only turns email off. |
| `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` | `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE` | The token of the hosting panel that backs up the instance: see [Hosting for Others](hosting_panel_backups.md#panel-backups). Like the web-search key, a file that cannot give it does not stop the server: the panel's backup routes answer `503`. |
| `LIBREFOLIO_WAKE_TOKEN` | `LIBREFOLIO_WAKE_TOKEN_FILE` | The token of the [scheduled wake-up](wake_sync.md#wake-sync), in the [main options](configuration.md). A token that cannot be used, or a file that cannot give it, does not stop the server either: the start log has an error (`platform.hosting_panel`), and the scheduled wake-up answers `503` until it is fixed. |
| `LIBREFOLIO_PANEL_STATUS_TOKEN` | `LIBREFOLIO_PANEL_STATUS_TOKEN_FILE` | The token of the hosting panel's status route, in the [main options](configuration.md): see [Hosting Panel API](hosting_panel_api.md#panel-api). Like the wake-up token, a token that cannot be used, or a file that cannot give it, does not stop the server: the start log has an error (`platform.hosting_panel`), and the status route answers `503` until it is fixed. |
| `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` | `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` | The token of the setup link of the [initial administrator](configuration_accounts.md#initial-admin), when a hosting panel delivers that link. A token that cannot be used stops the server at startup, and so does, as for the first two, a file that cannot give it. |

A plugin may have secrets of its own, such as the API key of a paid data source: see
[Plugin Settings](#plugin-settings).

### 📄 Secrets in Files {: #secret-files }

Add `_FILE` to the name of a secret and give the path of a file that holds it. This is how Docker and
Kubernetes hand over their secrets, such as `/run/secrets/jwt_secret`: the secret stays out of `.env`
and out of the container's environment.

- The secret is the text of the file, without the line breaks at its end and without the byte order
  mark that some Windows editors put at its start. Any other space counts, at the start and at the
  end too.
- A relative path starts from the project folder.
- A secret or its `_FILE` variable that is empty or holds only spaces counts as not set: a stray
  space is never used as a key.
- Set one of the two. When both are set, the variable itself wins, the file is ignored and the start
  log has a [warning](configuration_security.md#startup-checks).
- For `JWT_SECRET_FILE`, `LIBREFOLIO_INSTANCE_KEY_FILE` and `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE`,
  a file that is missing, cannot be read, is empty or blank (only spaces and line breaks), is not
  UTF-8 text or is larger than 64 KiB stops the server at startup. The error names the variable and
  the path, never the secret.
- `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` is read only when a search uses the `apikey` engine. A
  file that cannot give the key does not stop the server: the search goes on without the web search,
  with a warning in the log (`web_link_finder: …; disabling`), and the providers' own search keeps
  working.
- `LIBREFOLIO_SMTP_PASSWORD_FILE` is read only when `LIBREFOLIO_SMTP_HOST` is set. Like the web-search
  key file, a file that cannot give the password does not stop the server: email stays off, with an
  error in the log (`Email configuration cannot be used: email stays off`).
- `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE` is read by the [startup checks](configuration_security.md#startup-checks), then each
  time the hosting panel calls its backup routes. Like the web-search key file, a file that cannot give
  the token does not stop the server: the start log has an error
  (`The hosting panel's backup token cannot be read: LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE: <path> does not exist`,
  or another reason), and those routes answer `503`, with an error in the log at each call
  (`The hosting panel's backup token cannot be used: its routes refuse every request`).
- `LIBREFOLIO_WAKE_TOKEN_FILE` and `LIBREFOLIO_PANEL_STATUS_TOKEN_FILE` are read the same way, by the
  startup check `platform.hosting_panel`, then at each call of their route. A file that cannot give
  the token does not stop the server either: the start log has an error
  (`A hosting panel token cannot be used, and its route answers 503 to every call: LIBREFOLIO_WAKE_TOKEN (FILE_UNREADABLE)`),
  and the route answers `503`, with an error at each call that names the file's variable and its
  path.
- LibreFolio reads these variables from its environment: `./dev.py` and Docker Compose
  (`env_file: .env`) put the values of `.env` there, so `.env` works with both.

??? example "🐳 A Docker secret with Docker Compose"

    1. Save a new key in a file next to `docker-compose.yml`:

        ```bash
        python3 -c "import secrets; print(secrets.token_urlsafe(64))" > jwt_secret.txt
        ```

    2. Add the marked lines to `docker-compose.yml`, and keep the rest of the service as it is:

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

    3. If `.env` gives `JWT_SECRET` a value, remove that line: it would win over the file. An empty
       `JWT_SECRET=` line does no harm. Then run `docker compose up -d`.

    Compose mounts the file in the container as it is on the host, with its owner and permissions.
    LibreFolio runs there as the user of the image, `1000:1000` for the official one (see
    [Advanced Docker](docker_advanced.md)), and that user must be able to read the file. With the
    official image, for example: `sudo chown 1000:1000 jwt_secret.txt`, then
    `sudo chmod 600 jwt_secret.txt`. Otherwise the server stops at startup and the error says that the
    file `cannot be read`.

    `LIBREFOLIO_INSTANCE_KEY_FILE`, `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE`,
    `LIBREFOLIO_SMTP_PASSWORD_FILE`, `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE`,
    `LIBREFOLIO_WAKE_TOKEN_FILE`, `LIBREFOLIO_PANEL_STATUS_TOKEN_FILE` and
    `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` are mounted the same way; what each does when its file
    cannot give the secret is in [Secrets in Files](#secret-files).

### 🗝️ The Instance Key {: #instance-key }

The instance key is one secret per installation: LibreFolio derives its encryption keys from it.
There is nothing to set up. LibreFolio uses the first key it finds:

1. `LIBREFOLIO_INSTANCE_KEY`, the key itself;
2. `LIBREFOLIO_INSTANCE_KEY_FILE`, a file that holds it, such as a Docker secret;
3. `secrets/instance.key` in the data directory, which LibreFolio creates the first time it needs the
   key: 43 random characters, in a folder and a file that only the user running LibreFolio can open
   (`0700` and `0600`).

A key of your own must be random and at least 32 characters long, such as the output of
`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`. Never use a passphrase: the keys
LibreFolio derives from it are only as strong as it is.

On a managed or cloud deployment, the key can come from the environment or a Docker secret instead of
the data directory. Give every instance its own key: never share one key between several instances.

!!! warning "🔑 Never change or delete the key once in use"

    Only the same key can read again what was encrypted with it.

    - Back up `secrets/` with the rest of the data directory, and keep the copies as private as the
      database: see [Backup](filesystem.md#backup).
    - Once the key exists, LibreFolio cannot tell a lost `instance.key` from a first use: it creates a
      new key, and what the old one encrypted can no longer be read. When you restore the data, put
      `secrets/` back with it before you start LibreFolio again. Never start LibreFolio on restored
      data without its `secrets/`. If LibreFolio has already created a new key, stop it, put your
      copy of `instance.key` in place of the new one and start it again, before anyone enters a
      [plugin secret](#plugin-secrets) again: a secret entered under the new key would become
      unreadable once the old key is back.
    - If `instance.key` is there but damaged or out of reach, LibreFolio logs an error and never
      replaces it: see what to do in [Startup Checks](configuration_security.md#startup-checks).
    - Setting `LIBREFOLIO_INSTANCE_KEY` where `secrets/instance.key` already exists changes the key. To
      move the key to the environment or to a Docker secret, use the content of `secrets/instance.key`
      as the value.

### 🔏 The Key Check {: #instance-key-check }

LibreFolio keeps, next to the key, a **check value**: a short fingerprint of the key in the file
`secrets/instance.key.check` of the data directory (folder `0700`, file `0600`). It is not the key and the key
cannot be worked out from it. At each start, and each time a hosting panel asks, LibreFolio compares the fingerprint of
the key it has now with the one it stored. They differ when LibreFolio starts with **another key than the one the
data was written with**: a machine that got the wrong key, a key file replaced by a new one.

- **The first start** writes the file. If saved plugin secrets already exist and the current key reads
  none of them, LibreFolio does not write it: it would take the wrong key for the right one. The check
  then says the key does not match until you put the right key back.
- **With a key that does not match**, the log has an error at start, the
  Security tab of Settings › Administration says so (the check is `platform.instance_key_check`), and the [status of the hosting panel](hosting_panel_api.md#panel-status)
  answers `"instance_key": "mismatch"`. Two things stop, and only these: the backups that the panel starts
  (a start answers `409` with the code `backup_instance_key_mismatch`, see
  [Backup Jobs](hosting_panel_backups.md#panel-jobs)) and the [scheduled wake-up](wake_sync.md#wake-sync)
  (status `instance_key_mismatch`, no job runs). **The instance keeps serving**: your data does not depend on this
  key, only the saved plugin secrets do. The backup that an administrator starts from the app is not stopped.
  Why the panel's backups stop: a copy made with the wrong key would push a good one out of the copies you keep.
  They resume by themselves when the key is right again: [When the Instance Key Does Not Match](hosting_panel_backups.md#instance-key-mismatch).
- **The way out is the right key.** Put it back, with `LIBREFOLIO_INSTANCE_KEY`, its `_FILE` or the
  `secrets/instance.key` of the data, and start LibreFolio again: the next answer is `ok`, with nothing else to do.
- **To really change the key**, for example when you decide that the old secrets are lost and the plugin
  secrets are entered again, set `LIBREFOLIO_INSTANCE_KEY_ACCEPT=1` for **one start**. That start replaces the stored
  check value with the one of the key it has, and logs a warning. **Then remove the variable and start again**: while it is
  set, every start accepts whatever key it has, and the protection does nothing (the warning is logged at every start, as a reminder).
  The values are `1` or `0`, `true` or `false`, `yes` or `no`, `on` or `off`; any other value stops the start, naming the variable.

!!! note "📏 What the check cannot see"

    Without a stored check value and without any saved plugin secret, there is nothing to compare, so
    the answer is `ok`: the first start of an instance whose key was already wrong cannot be told. From
    then on, the stored value protects it. If the data comes back without its `secrets/` folder, the value
    is written again at the next start, and the plugin secrets decide while it is missing. A check value that cannot be read
    (a permission, a damaged file) never stops a backup: the answer is `ok` and the log has a warning, once.

---

## 🧩 Plugin Settings {: #plugin-settings }

A plugin can ask for settings of its own: the API key of a paid data source, a region, a
preference. Of the plugins shipped with LibreFolio, two ask for one, a personal search preference
each: justETF and Borsa Italiana. None asks for an instance-wide setting; a plugin you add may. A
setting is one of two kinds:

- **Instance-wide**: one value for the whole instance, which only an administrator can save. Every
  user can read a plain value, and of a secret one, such as an API key, only whether it is set.
- **Personal**: each user's own value, which only that user can save and read. Administrators never
  see it.

Personal and instance-wide settings are changed in **Settings › Plugins**, a tab every user has:
each user changes their personal ones there, and administrators the instance-wide ones too, which
the other users see read-only. In the asset dialog, **Configure**, next to the chosen price
provider, opens the same form for that provider alone. What the tab shows, setting by setting:
[Plugin Settings](../user/settings/plugins.md) in the user manual.

An instance-wide setting can also be given by an environment variable, in `.env` or in the
container's environment like the other options; a personal one cannot. The plugins that have
settings, with the keys of their settings, are listed by `GET /api/v1/settings/plugins` to any
signed-in user.

### 🏷️ The Variables {: #plugin-variables }

LibreFolio builds the name of the variable from the kind of plugin, the plugin's code and the
setting's key:

```text
LIBREFOLIO_PLUGIN_<KIND>_<PLUGIN CODE>_<SETTING KEY>
```

- `<KIND>` is `ASSET` for a price provider and `FX` for an exchange-rate provider.
- The whole name is in uppercase, and every character other than a letter or a digit becomes `_`:
  the `api_key` setting of the price provider `my_provider` is
  `LIBREFOLIO_PLUGIN_ASSET_MY_PROVIDER_API_KEY`.
- For a secret setting, a plugin may also accept the variable it read before it had settings, so
  that an existing install keeps working. When both are set, the name above wins.
- Each variable also has a `_FILE` form, the path of a file that holds the value, such as a Docker
  secret. The file is read as in [Secrets in Files](#secret-files), but one that cannot be read never
  stops the server: see below.

### 🔒 A Variable Locks the Setting {: #plugin-variable-lock }

While its variable is set, a setting takes its value from there, and nobody can change it from
inside LibreFolio: a save is refused (`LOCKED_BY_ENV`), and a value saved earlier is ignored until
you remove the variable and restart. **Settings › Plugins** shows the setting read-only, a secret
only as *Set*: *Set by the server variable* and the variable's name for administrators, *Set by the
server* for the other users.

- A wrong value, one the setting does not accept or a `_FILE` that cannot be read, still locks the
  setting, and the plugin is then not configured: LibreFolio refuses every request to it, even when
  the setting is optional, until you fix the variable. It never falls back to the saved value or to
  the plugin's default. The log says why, with a warning once per server process:
  `Plugin setting variable invalid: the plugin is not configured until it is fixed`, with the
  variable and the reason, never the value. In **Settings › Plugins** the plugin's badge reads
  **To configure**, and the setting says that its variable is invalid. Fix the value, then restart.
- In the [managed profile](hosting_providers.md#managed-profile), a setting locked by a variable is
  not shown at all, not even in **Settings › Plugins**, and a save to it is refused as if it did not
  exist: the hosting provider sets it, and the instance's administrators and users never see it.

### 🔐 Saved Secrets and the Instance Key {: #plugin-secrets }

A setting saved inside LibreFolio is kept in the database. A secret one is first encrypted
(AES-256-GCM) with a key derived from the [instance key](#instance-key), and is never shown again,
not even to whoever saved it: LibreFolio only says whether it is set (in **Settings › Plugins**,
*Set on* and the date it was saved). A value given by a variable, secret or not, is never saved in
the database.

If the instance key changes, the saved secrets can no longer be read. LibreFolio keeps them and
reports them as unreadable, and never uses a wrong value. The tab says so under each
one: *Saved, but this instance's key cannot read it. If an administrator can put the old key back,
that comes first; otherwise enter it again.* If you still have the old
key, put it back before anyone enters them again: a secret entered under the new key would become
unreadable once the old one is back. To bring them into another installation, which keeps its own
key, restore a backup there with the old key: `backup restore` with `--instance-key-file`
re-encrypts them with that installation's key ([The Instance Key of Another
Installation](cli_tools.md)). From the first start after the change, and at every start
until they are entered again or the old key is back, the log has an error that counts the
instance-wide ones, if there are any: see [Startup Checks](configuration_security.md#startup-checks).

If `secrets/instance.key` is damaged or out of reach, LibreFolio starts anyway, with an error from
the [startup checks](configuration_security.md#startup-checks); a key you set yourself that cannot be used stops the start
instead. Until you fix it:

- every saved secret is reported as unreadable, and the plugins run without them: a plugin that needs
  one answers that it is not configured;
- secrets given by variables keep working;
- a new secret cannot be saved: the tab answers *Secrets cannot be saved: this instance's key cannot
  be used (see the configuration checks).*, and nothing of that save is written;
- the log has one more error, the first time each server process needs a saved secret:
  `Plugin secrets unreadable: the instance key cannot be used (see the configuration checks)`.

Fix the file, or restore it from a backup, and the saved secrets come back. A new key does not bring
them back: they would have to be entered again.

!!! warning "🗄️ The database and the key in one folder"

    The database (`sqlite/app.db`) and the instance key that LibreFolio generates
    (`secrets/instance.key`) are in the same [data directory](filesystem.md): whoever gets both, the
    folder itself or a copy of it, can read every saved secret.

    - Keep the data directory, and every copy of it, private.
    - Better, give the instance key from a secret store, with `LIBREFOLIO_INSTANCE_KEY_FILE` (a
      Docker secret) or `LIBREFOLIO_INSTANCE_KEY`: LibreFolio then never writes it to the data
      directory. If LibreFolio has already created `secrets/instance.key`, use its content as the
      value, as [The Instance Key](#instance-key) explains: another key would make the saved secrets
      unreadable.

---

## 🔗 Related

- 📄 **[Configuration](configuration.md)** — Create the `.env` File, Main Options, Parameters Set by the Tools, …
- 📄 **[Configuration: Checks and Protections](configuration_security.md)** — Startup Checks, Browser Protections, Stopping the Server
- 📄 **[Configuration: Accounts and Asset Search](configuration_accounts.md)** — Accounts and Sign-ups, The Order of the Price Providers in the Search, Optional: Web Search for New Assets
