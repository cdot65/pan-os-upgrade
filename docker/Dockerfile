# Use an official Python runtime as a parent image, based on Alpine
FROM python:3.12-alpine

# Install dependencies required for compiling certain Python packages
# gcc and musl-dev are required for compiling C extensions
# libffi-dev is required for the cffi package
# make is often required for building packages
RUN apk add --no-cache gcc musl-dev libffi-dev make

# Set the working directory in the container to /app
WORKDIR /app

# Add settings.yaml to the container at /app
ADD settings.yaml /app

# Install any needed packages specified in requirements.txt
# Note: The requirements.txt should contain pan-os-upgrade==1.0.0
RUN pip install --no-cache-dir pan-os-upgrade==1.0.0

# Set the locale to avoid issues with emoji rendering
ENV LANG C.UTF-8

# Define the entry point for the application
ENTRYPOINT ["pan-os-upgrade"]

# By default, show the help message if no arguments are provided
CMD ["--help"]
