# Audit MkDocs EN vs codice — baseline riproducibile

> **Release 2 · Phase 0 · 05_cleanAudit**
>
> Companion di [00_INDEX](00_INDEX.md). Registra lo stato contro cui sono state
> confrontate le pagine, senza modificare il worktree preesistente.

## Identita' snapshot

| Campo | Valore |
|---|---|
| Acquisito | `2026-08-05T10:54:55+02:00` |
| Branch | `dev_release2` |
| HEAD | `09cbb7e28f4e4e4bba9f9d40748b98e1876f5103` |
| SHA-256 manifest originale | `ea01e8f86bd36a9b36f68e83336ee0e174ff35e6d67336922420d8471f235107` |
| Pagine EN non-developer | 182 |
| Pagine developer EN-only sospese | 103 |

Il manifest originale conteneva anche l'elenco ordinato delle 182 pagine. La
partizione completa e' persistita nelle tabelle di copertura dei nove report di
dominio; la loro unione e' stata verificata esattamente uguale all'insieme delle
182 pagine EN non-developer.

## Worktree gia' dirty alla baseline

Questi path erano gia' modificati o non tracciati prima dell'audit. Non sono stati
revertiti, formattati o altrimenti alterati dall'audit.

```text
M  .github/instructions/backend.instructions.md
M  .github/instructions/frontend.instructions.md
M  .github/skills/devpy-tools/devpy/SKILL.md
M  .github/skills/devpy-tools/lint-format-backend/SKILL.md
M  .github/skills/devpy-tools/lint-format-frontend/SKILL.md
M  Pipfile
M  Pipfile.lock
M  TODO_FUTURI.md
M  backend/app/api/v1/assets.py
M  backend/app/api/v1/fx.py
M  backend/app/schemas/assets.py
M  backend/app/schemas/brokers.py
M  backend/app/schemas/fx.py
M  backend/app/schemas/prices.py
M  backend/app/schemas/provider.py
M  backend/app/schemas/settings.py
M  backend/app/schemas/uploads.py
M  backend/app/schemas/users.py
M  backend/app/schemas/utilities.py
M  backend/app/services/asset_source.py
M  backend/app/services/asset_source_providers/mockprov.py
M  backend/app/services/asset_source_providers/yahoo_finance.py
M  backend/app/services/brim_provider.py
M  backend/app/services/brim_providers/broker_generic_csv.py
M  backend/app/services/fx.py
M  backend/app/services/portfolio_engine.py
M  backend/app/services/static_uploads.py
M  backend/app/services/transaction_service.py
M  dev.py
M  frontend/package-lock.json
M  frontend/package.json
M  pyproject.toml
?? LibreFolio_developer_journal/Release_2/Phase_0/05_cleanAudit/
?? frontend/knip.json
```

## Drift controllato alla chiusura

Un confronto `git status --porcelain` per path contro questa baseline non ha rilevato
nuovi path dirty ne' path tornati puliti. Le citazioni restano quindi riferite al
worktree sopra, non a un checkout pulito di `HEAD`.

## Validazioni eseguite

- `./dev.py mkdocs build` completato con successo alla baseline.
- Nav i18n: 182 sorgenti EN non-developer e 182 riferimenti nav normalizzati, con
  differenza vuota in entrambe le direzioni.
- `./dev.py mkdocs check-links`: un solo candidato `${lang` da
  `AboutTab.svelte`; tracciato in [01](01_user-core.md) come falso positivo del parser
  statico su template literal annidato.
