# trunk-ignore-all(terrascan/AC_DOCKER_0047)
# Use an official Python runtime as a parent image, based on Alpine
FROM python:3.12-alpine

# Install dependencies required for compiling certain Python packages
# gcc and musl-dev are required for compiling C extensions
# libffi-dev is required for the cffi package
# make is often required for building packages
RUN apk add --no-cache gcc=13.2.1_git20231014-r0 musl-dev=1.2.4_git20230717-r4 libffi-dev=3.4.4-r3 make=4.4.1-r2

# Set the working directory in the container to /app
WORKDIR /app

# Add settings.yaml to the container at /app
COPY settings.yaml /app

# Install any needed packages specified in requirements.txt
# Note: The requirements.txt should contain pan-os-upgrade==1.3.10
RUN pip install --no-cache-dir pan-os-upgrade==1.3.10

# Set the locale to avoid issues with emoji rendering
ENV LANG C.UTF-8

# Create a non-root user
RUN adduser -D panadmin
USER panadmin

# Define the entry point for the application
ENTRYPOINT ["pan-os-upgrade"]

# By default, show the help message if no arguments are provided
CMD ["--help"]

# Add a healthcheck
HEALTHCHECK --interval=30s --timeout=5s \
    CMD pgrep -f "pan-os-upgrade" > /dev/null || exit 1
