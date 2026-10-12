"""Leaf helpers for LibreFolio.

A module here is a leaf: it never imports services. Anything that needs FX rates, assets or
other services belongs to a service layer; financial calculations live in
``backend.app.services.financial_math`` (developer decision D-P7, 2026-10-12). Packages
re-export nothing: import a name from the module that defines it.

Layout:

* ``datetime_utils`` — UTC datetime helpers.
* ``json_utils`` — JSON-safety checks for payloads.
* ``decimal_utils`` — decimal parsing, and the truncation to the database precision.
* ``asset/`` — sectors, geographic areas, identifiers, and the locale of their display names.
* ``fx/`` — currencies: ISO codes, display names, symbols and flags.
* ``runtime/`` — the instance's version, the client's network address, and in-memory TTL caches.
"""
