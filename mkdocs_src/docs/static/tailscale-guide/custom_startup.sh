#!/bin/sh
set -e
set -x # Keep this for debugging purposes

echo "Starting containerboot..."
/usr/local/bin/containerboot &

# --- Install socat ---
echo "Installing socat..."
apk add socat || { echo "Failed to install socat. Exiting."; exit 1; }

# --- Create internal proxy with socat ---
# Socat will listen on TAILSCALE_FUNNEL_PORT on the container's localhost
# and forward the traffic to the destination host IP and port.
echo "Starting socat to proxy 127.0.0.1:${TAILSCALE_FUNNEL_PORT} to ${HOST_IP}:${HOST_PORT}..."
socat TCP-LISTEN:"${TAILSCALE_FUNNEL_PORT}",fork,reuseaddr TCP:"${HOST_IP}":"${HOST_PORT}" & # Run in background

# --- Wait for Tailscale to start ---
echo "Waiting for Tailscale daemon to be in 'Running' state..."
until tailscale status --json | grep -q '"BackendState": "Running"'; do
    echo "Tailscale daemon not yet running, waiting..."
    sleep 2
done
echo "Tailscale daemon is in 'Running' state."


# --- Configure Tailscale Funnel ---
echo "Clean old serve/funnel configurations..."
tailscale serve reset
tailscale funnel reset

tailscale funnel "${TAILSCALE_FUNNEL_PORT}" || { echo "Failed to start tailscale funnel. Exiting."; exit 1; }
