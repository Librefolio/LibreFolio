"""Platform services: what the application needs to run, apart from any financial domain.

The market-data scheduler, the container-registry probe, the resolution of open date ranges, the project-wide
data-quality thresholds, the backup export, the instance key, the configuration checks, the readiness probe, and the
pauses of the price providers after «too many requests». Modules are imported from where they are defined: this
package re-exports nothing.
"""
