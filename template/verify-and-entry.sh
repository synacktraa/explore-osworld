#!/usr/bin/env bash
set -Eeuo pipefail

VM_PATH="/vm/System.qcow2"

if [ -f "$VM_PATH" ]; then
  echo "✅ VM image found at $VM_PATH — launching original entrypoint..."
  exec /usr/bin/tini -s /run/entry.sh "$@"
else
  echo "⚠️  VM image not found at $VM_PATH. Skipping startup."
  echo "Place the VM at $VM_PATH and restart the container."
  sleep infinity
fi
