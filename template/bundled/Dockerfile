# This builds osworld-docker with Ubuntu VM pre-installed

# Stage 1: Download and extract Ubuntu VM
FROM ubuntu:22.04 AS vm-builder

RUN apt-get update && \
    apt-get install -y wget unzip ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /tmp

# Download Ubuntu VM
RUN wget --progress=dot:giga \
    https://huggingface.co/datasets/xlangai/ubuntu_osworld/resolve/main/Ubuntu.qcow2.zip && \
    unzip Ubuntu.qcow2.zip && \
    rm Ubuntu.qcow2.zip

# Verify the VM file exists and is readable
RUN test -f /tmp/Ubuntu.qcow2 && \
    echo "VM file size: $(du -h /tmp/Ubuntu.qcow2)"

# Stage 2: Layer VM on top of osworld-docker
FROM happysixd/osworld-docker

# Copy VM from builder stage to the expected location
COPY --from=vm-builder --chmod=644 /tmp/Ubuntu.qcow2 /System.qcow2

# Verify the VM was copied successfully
RUN test -f /System.qcow2 && \
    echo "VM installed at /System.qcow2" && \
    ls -lh /System.qcow2
