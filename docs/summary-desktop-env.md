# Desktop Environment – Research Summary

## Objective
Enable OSWorld’s desktop environment to run on modern sandbox providers (Daytona, E2B) that expect self-contained Docker images while still supporting the 22.7 GB Ubuntu VM disk required by the controller service.

## Key Constraints & Discoveries
- The legacy workflow mounts `System.qcow2` as an external volume at `/System.qcow2`; the base image (`happysixd/osworld-docker`) hardcodes that path.
- Daytona offers managed volumes but disallows mounting them at `/`, while both Daytona & E2B enforces a ~10 GiB layer limit on image layers.
- Daytona’s native volumes can host the VM under an alternate mount point; E2B lacks built-in volumes but can attach storage via FUSE helpers (e.g., S3FS, gfuse). Overall solutions revolve around baking the disk into the image or remapping it through provider-specific volume mechanisms.

## Experiments Completed
1. **Bake VM into Image (synacktra/osworld-ubuntu)**
   - Built a multi-stage Dockerfile that bundles the QCOW2 inside the image.
   - Local Docker run succeeded; E2B template build failed because the image produces ~12 GB uncompressed layers, exceeding the per-layer cap.

2. **Daytona Volume at Root**
   - Attempted to mount Daytona’s managed volume at `/System.qcow2`.
   - Daytona’s sandbox rejected the mount (`destination can't be '/'`), confirming the root-path restriction.

3. **Patch Base Image for `/vm/System.qcow2`**
   - Reverse engineered the closed-source image to replace `/run/install.sh`, redirecting VM lookups from `/System.qcow2` to `/vm/System.qcow2`.
   - New image (`synacktra/osworld-docker`) runs perfectly with a volume mounted at `/vm`, restoring controller functionality in local Docker.

4. **Daytona Snapshot with Conditional Entrypoint**
   - Daytona snapshot validation launches the container without volumes, so the original entrypoint crashed.
   - Added `verify-and-entry.sh` wrapper: if `/vm/System.qcow2` exists run the original entrypoint; otherwise sleep to satisfy validation.
   - Snapshot build/validate now passes, but runtime sandboxes fail to obtain an IP (APIs never come up) despite the same image working when run directly via Docker. Root cause still under investigation.

## Provider Status
- **Local Docker** – Working via patched image and `/vm` mount.
- **Daytona** – Snapshot publishes; runtime launch currently fails (no IP, controller offline).
- **E2B** – Blocked by layer-size limits; evaluating volume-backed alternatives (S3FS/gfuse).
