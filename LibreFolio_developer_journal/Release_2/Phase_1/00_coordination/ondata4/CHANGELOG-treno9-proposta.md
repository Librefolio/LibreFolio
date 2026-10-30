# CHANGELOG del treno 9 — proposta (da approvare, non ancora nel file)

Righe in inglese da aggiungere al capitolo `## [Unreleased]` di `CHANGELOG.md`, nelle sezioni che ci sono già. Sono
scritte dai messaggi di commit e dalle proposte dei lotti. Le righe interne (W-BS senza effetti visibili, J-62, J-71,
J-8, i test di Z, il diario di MF) restano fuori: la regola dice «entries are user-facing».

## ✨ Added

- **Compare an asset with an exchange rate, and back.** A comparison chosen in a card's or a chart's signals now draws
  on the Assets and FX list cards and on both detail pages, also when the page is opened fresh. (Y-41, Y + X)
- **Yahoo Finance fund details.** For an ETF or a mutual fund, the sector distribution, the fund description when the
  summary is missing, and «TER: x%» with the issuer at the end of the description. (#50, X)
- **Start Value and End Value explained.** The positions table's two headers have a tooltip, and the positions guide's
  sentence on them is now in Italian, French and Spanish too. (#49, Y)
- Administrators choose who can sign up (Open, By invitation, Closed) from the **Users** tab too, and every row of the
  **Security** checks has a **Guide** button opening its documentation page. (N69c, N69d, A)
- **Japanese, Chinese and Korean statements preview under the strict content policy.** The CJK fonts are served by
  LibreFolio, downloaded once from a pinned version and checked against fixed hashes; the browser never loads them from
  outside. (H-55)

## 🔄 Changed

- Detail pages: going back to a period already seen shows the comparison series at once, without asking the server
  again; Refresh and Sync still reload them. (N64b, X)
- **Linking two Adjustments as a pair is refused**, with a message in your language pointing to an Asset Transfer. Saved
  data is not changed. (W)
- The Fineco importer reports the rows it skips (unreadable, or an operation it does not know), like the other plugins
  out of beta. (W)
- Notifications are announced by screen readers (errors at once, the others politely), and their close button is named
  in your language. (H-18)
- Python dependencies updated (FastAPI 0.159, SQLAlchemy 2.1, Pydantic 2.14 and others); no change to data, numbers or
  the API. (D)

## 🐛 Fixed

- The lot history shows a transfer that leaves and arrives on the same day as two rows, the departure then the arrival,
  each naming both brokers, as for transfers over several days. (J-68, J)
- The quantities in the Performance table no longer count a transaction dated after the end of the report. (B12, J)

## ⚠️ Breaking changes

- **The interactive API docs are off by default.** `/api/v1/docs`, `/api/v1/redoc` and `/api/v1/openapi.json` answer 404 on
  every instance, Docker included, unless `LIBREFOLIO_API_DOCS` is set (`./dev.py server --debug` sets it). When on,
  they load pinned Swagger UI and ReDoc with integrity checks. (H-55 R5)

## Domande per te

1. Va bene la riga sull'aggiornamento delle dipendenze (D), o la togliamo perché non cambia nulla di visibile?
2. Le API docs spente le metto fra i **⚠️ Breaking changes** (chi usava `/docs` le perde) o fra i **🔄 Changed**?
