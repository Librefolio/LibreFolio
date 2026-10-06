#!/bin/sh
# Startup script for the Tailscale container that publishes a LAN service through Funnel.
#
# Watchdog: if Tailscale does not reach the Running state in time, or if containerboot (and with
# it tailscaled), socat or the funnel stop later, the script exits with an error. Docker's restart
# policy (restart: unless-stopped) then restarts the container, instead of leaving it "running"
# with nothing behind it.
set -eu
[ "${DEBUG:-0}" = 1 ] && set -x

: "${HOST_IP:?HOST_IP is not set}"
: "${HOST_PORT:?HOST_PORT is not set}"
: "${TAILSCALE_FUNNEL_PORT:?TAILSCALE_FUNNEL_PORT is not set}"
# The socket containerboot gives tailscaled. Exported, so containerboot and every CLI call below
# use the same path instead of relying on the /var/run symlink.
TS_SOCKET="${TS_SOCKET:-/tmp/tailscaled.sock}"
STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-180}"        # seconds allowed to reach Running
export TS_SOCKET

ts() { tailscale --socket="$TS_SOCKET" "$@"; }

CB_PID=""
SOCAT_PID=""
FUNNEL_PID=""
stop() {
    echo "Stop requested: stopping the funnel, socat and containerboot..."
    for pid in "$FUNNEL_PID" "$SOCAT_PID"; do
        if [ -n "$pid" ]; then kill -TERM "$pid" 2>/dev/null || true; fi
    done
    if [ -n "$CB_PID" ]; then kill -TERM "$CB_PID" 2>/dev/null || true; wait "$CB_PID" 2>/dev/null || true; fi
    exit 0
}
trap stop TERM INT

echo "Starting containerboot..."
/usr/local/bin/containerboot &
CB_PID=$!

# A restart keeps the container's filesystem, so socat is installed only when missing:
# a restart while the internet is down does not fail here.
if ! command -v socat >/dev/null 2>&1; then
    echo "Installing socat..."
    apk add --no-cache socat || { echo "Failed to install socat. Exiting so Docker restarts the container."; exit 1; }
fi

echo "Starting socat: 127.0.0.1:${TAILSCALE_FUNNEL_PORT} -> ${HOST_IP}:${HOST_PORT}..."
socat TCP-LISTEN:"${TAILSCALE_FUNNEL_PORT}",fork,reuseaddr TCP:"${HOST_IP}":"${HOST_PORT}" &
SOCAT_PID=$!

echo "Waiting up to ${STARTUP_TIMEOUT}s for Tailscale to reach the 'Running' state..."
start=$(date +%s)
until ts status --json 2>/dev/null | grep -q '"BackendState": "Running"'; do
    if ! kill -0 "$CB_PID" 2>/dev/null; then
        echo "containerboot exited before Tailscale was running. Exiting so Docker restarts the container."
        exit 1
    fi
    if [ $(( $(date +%s) - start )) -ge "$STARTUP_TIMEOUT" ]; then
        echo "Tailscale is not running after ${STARTUP_TIMEOUT}s. Exiting so Docker restarts the container."
        exit 1
    fi
    sleep 2
done
echo "Tailscale is running."

echo "Clean old serve/funnel configurations..."
ts serve reset
ts funnel reset

# The funnel runs in the foreground mode on purpose: its output goes to the container log. It is
# started as a child of this script so the watchdog below can tell when it stops.
echo "Starting the funnel on port ${TAILSCALE_FUNNEL_PORT}..."
ts funnel "${TAILSCALE_FUNNEL_PORT}" &
FUNNEL_PID=$!

# Stay up while all three are alive; when one stops, exit so Docker restarts the container.
while kill -0 "$CB_PID" 2>/dev/null && kill -0 "$SOCAT_PID" 2>/dev/null && kill -0 "$FUNNEL_PID" 2>/dev/null; do
    sleep 10 &
    wait $! || true
done
for name in containerboot socat funnel; do
    case "$name" in
        containerboot) pid=$CB_PID ;;
        socat) pid=$SOCAT_PID ;;
        funnel) pid=$FUNNEL_PID ;;
    esac
    kill -0 "$pid" 2>/dev/null || echo "$name stopped."
done
echo "Exiting so Docker restarts the container."
exit 1
