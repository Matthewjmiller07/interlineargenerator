# Start from a TeX Live base image
FROM texlive/texlive

# Install Python and pip
RUN apt-get update && \
    apt-get install -y python3 python3-pip

# Install xelatex if not included in the texlive/texlive image
RUN apt-get install -y texlive-xetex

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip3 install -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV NAME World

# Run the application
CMD ["python3", "app.py"]