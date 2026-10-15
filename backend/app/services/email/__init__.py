"""Optional email (F04, release 1.3, workstream E).

LibreFolio sends a few transactional emails — a password-reset link, an invitation, an address to confirm, the
activation of the first administrator, a test — through the SMTP server named by the ``LIBREFOLIO_SMTP_*`` variables
(``backend/app/config/email.py``). The configuration is read only from variables or secret files: never stored, never
shown in the interface, never in a backup. Without a server nothing is sent and everything works as before: links are
copied by hand.

- ``smtp``: the transport, ``smtplib`` in a worker thread, errors as codes;
- ``delivery``: whether the instance can send, the hourly budget of the instance, ``send_email``;
- ``messages``: the texts in the four languages of the interface and the message with its headers;
- ``checks``: the configuration checks shown to administrators.
"""
