# 🔧 Utility Module Tests (`utils`)

These tests verify the helper functions and utility modules used throughout the application.

## 🎯 Purpose

To ensure that low-level utilities are robust and handle edge cases correctly.

## 🔑 Key Tests

- **Financial Math**: Tests interest calculations, day count conventions, and compounding formulas.
- **Datetime Utils**: Tests timezone handling and date parsing.
- **Decimal Utils**: Tests precision handling for financial amounts.

## 🧩 Gate and Runner Units

The units below test the project's own tooling rather than application helpers. All are
PURE: no database, no server, no network.

| Sub-command | What It Tests |
|-------------|---------------|
| `gate-i18n-usage` | The three-verdict i18n key classifier in `scripts/i18n_usage.py`, which `./dev.py i18n audit` uses to report unused keys: *used* (proven), *dead* (proven absent), or *not verified* (the key's family exists but its last segment is produced at runtime). It checks typed-union expansion, constant namespaces, both branches of a ternary or of a conditional prefix, backend literals as the vocabulary of dynamic segments, and that test sources never count as evidence. Each case asserts what must be condemned **and** what must survive (`backend/test_scripts/test_utilities/test_i18n_usage_gate.py`). |
| `gate-i18n-catalog` | The translation catalogue that `scripts/i18n_catalog.py` builds from its sources — `frontend/src/lib/i18n/base/`, one folder per subsystem with its `prefixes.txt`, each plugin's `i18n/` fragment — with every rule proven both ways on synthetic trees: a key belongs to the plugin that holds it, else to the subsystem with the longest declared prefix, else to `base`; a key in two sources, a string in one source against a branch in another, or a key outside the folder its prefix names is an error; a missing translation is filled from English with a warning when building and is an error under the strict `check`; the build writes only what changed, read-only, with a sha256 stamp, and refuses a hand-edited file; `add` routing, `move`, `split`, `check --against` and the three-way `absorb`. On the repository: the sources merge strictly in the four languages, and git ignores the generated files and none of the sources ([Internationalization](../frontend/i18n.md); `backend/test_scripts/test_utilities/test_i18n_catalog_gate.py`). |
| `gate-plugin-layout` | Every first-party plugin of the six families (`brim_providers`, `asset_source_providers`, `fx_providers`, `risk_plugins`, `signal_plugins`, `tool_plugins`) is a folder `<family>/<name>/` holding `plugin.py` and an `__init__.py` that is its docstring and nothing else, and no family keeps a plugin as a single module. Over `backend/app`, `backend/test_scripts`, `scripts` and `dev.py`, no import or string (a `patch()` target, a logger name, a `__module__`) reaches a plugin's package instead of its `plugin` module or a `_*` helper beside it. The sources are parsed with `ast`, never imported ([Plugin Folder Layout](../architecture/patterns/registry_pattern.md#plugin-layout); `backend/test_scripts/test_utilities/test_plugin_layout_gate.py`). |
| `gate-plugin-i18n-ownership` | Each plugin's translations live in its own `i18n/` fragment, judged by the metadata its registry publishes. A plugin's space is `brimPlugins.<code>` (the code being its folder's name); `assets.providerParams.<provider_code>` and `pluginSettings.asset.<provider_code>` for an asset plugin; `pluginSettings.fx.<code>` for an FX plugin, the code as the registry has it (`pluginSettings.fx.ECB`); the parent of a signal's `display_name_key` or of a risk analytic's `name_i18n_key`; or exactly a Tool's `name_i18n_key` and `description_i18n_key`. R1: every fragment key lies in its plugin's space. R2: every key a plugin declares in its exclusive space lives in its fragment, the keys of an asset or FX plugin's `settings_fields` included (each field's `label_key` and `description_key`, each option's `label_key`). R3: no fragment key lies in another plugin's space or is declared by another plugin. R4: every catalogue key under an exclusive space lives in that plugin's fragment, Tools aside. Each rule is proven both ways on synthetic trees, and a sentinel fails on a published key field the gate does not read, in the plugins' settings and in the attributes of `PluginSettingField` and `SettingOption` too ([The Ownership Gate](../architecture/patterns/registry_pattern.md#plugin-i18n-gate); `backend/test_scripts/test_utilities/test_plugin_i18n_ownership_gate.py`). |
| `gate-event-loop-io` | No `async def` under `backend/app/api/v1/` directly calls a synchronous function of the BRIM file store, `backend/app/services/brim/brim_provider.py` (its top-level `def`s and their module-level aliases, such as `broker_metadata_lock = _broker_metadata_lock`): that I/O would run on the event loop, so it goes through `await asyncio.to_thread(fn, ...)`. Every way an API file binds the module or imports one of its functions by name is followed (`from`-import, `import … as`, plain, relative, lazy). A reference handed to `to_thread`, the body of a nested `def` or `lambda`, an awaited coroutine of the module and a synchronous handler are not flagged. Control cases prove on in-memory sources that the detector sees a direct call and leaves the allowed shapes alone, and the scan must reach an API file that imports the store: an empty scan would pass without checking anything. The sources are parsed with `ast`, never imported ([Event Loop Blocking Rule](../architecture/patterns/async.md); `backend/test_scripts/test_utilities/test_event_loop_brim_io_gate.py`). |
| `runtime-isolation` | The [runtime lane](index.md#isolated-runtime-lanes) contract: test-port and data-directory resolution with its production guards, propagation of the lane to child processes and nested Pipenv runs, the lane-identity readiness probe, and ownership of the shared test server, which never reuses or signals a process it did not start (`backend/test_scripts/test_utilities/test_runtime_isolation.py`). |

List every unit of the category, each with its description, with `./dev.py test utils --help`.
`./dev.py test utils <unit> --list` lists the tests of one unit without running them, and
`./dev.py test utils all --list` those of the whole category (see [Running Tests](index.md#running-tests)).

## 🚀 Running

```bash
./dev.py test utils
```
