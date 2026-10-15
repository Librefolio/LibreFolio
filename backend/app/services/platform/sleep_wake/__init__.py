"""Sleep and wake (workstream Z, release 1.3): the user's activity, the idle suspension, the scheduled wake-up.

``activity`` records the user's presence and the work in progress, for every HTTP request (``ActivityMiddleware``, the
outermost middleware). Every feature here serves a self-hosted instance as well, and stays off until it is enabled.
Modules are imported from where they are defined: this package re-exports nothing.
"""
