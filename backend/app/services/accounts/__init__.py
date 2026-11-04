"""Accounts: the people who use the instance, and what is theirs.

- ``auth_service``: password hashing and verification, session tokens.
- ``user_service``: users, the last-active-administrator guards, account deletion.
- ``settings_service``: per-user settings and the global settings store.
- ``global_settings_service``: typed readers of the global settings.
- ``onboarding_service``: versioned onboarding progress per user and flow.
- ``donation_popup_service``: whether a sign-in shows the support prompt.

Import every name from the module that defines it: this package re-exports nothing, so a test patches the object the
code actually reads.
"""
