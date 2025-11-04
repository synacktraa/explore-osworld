FROM happysixd/osworld-docker

# Install wget and bsdtar
RUN apt-get update && \
    apt-get install -y wget libarchive-tools ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Download and extract on the fly
RUN wget --progress=dot:giga -O - \
    https://huggingface.co/datasets/xlangai/ubuntu_osworld/resolve/main/Ubuntu.qcow2.zip \
    | bsdtar -xOf - > /System.qcow2 && \
    chmod 644 /System.qcow2

# Verify the VM was installed successfully
RUN test -f /System.qcow2 && \
    echo "VM installed at /System.qcow2" && \
    ls -lh /System.qcow2