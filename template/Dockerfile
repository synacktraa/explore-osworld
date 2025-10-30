FROM happysixd/osworld-docker

# Replace the install script inside the image
COPY --chmod=644 override-install.sh /run/install.sh

# Copy a conditional entry script to verify VM presence
COPY --chmod=755 verify-and-entry.sh /run/verify-and-entry.sh

# Override the default entrypoint to use the new script
ENTRYPOINT ["/run/verify-and-entry.sh"]
