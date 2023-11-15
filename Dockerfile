# Use a base image with TeX Live pre-installed
FROM texlive/texlive

# Install Python and pip, and clean up the APT cache to reduce image size
RUN apt-get update && \
    apt-get install -y python3 python3-pip texlive-xetex && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV NAME World

# Run the application as a non-root user for security
RUN useradd -m myuser
USER myuser

CMD ["python3", "app.py"]
