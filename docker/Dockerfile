# Use an official Python runtime as a parent image, based on Alpine
FROM python:3.12-alpine

# Install dependencies required for compiling certain Python packages
# gcc and musl-dev are required for compiling C extensions
# libffi-dev is required for the cffi package
# make is often required for building packages
RUN apk add --no-cache gcc musl-dev libffi-dev make

# Set the working directory in the container to /app
WORKDIR /app

# Install any needed packages specified in requirements.txt
# Note: The requirements.txt should contain pan-os-upgrade==0.3.0
RUN pip install --no-cache-dir pan-os-upgrade==0.3.0

# Set the locale to avoid issues with emoji rendering
ENV LANG C.UTF-8

# Run the application
CMD ["pan-os-upgrade"]
