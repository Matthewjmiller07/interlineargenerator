# Use the official image as a parent image
FROM texlive/texlive

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Make port available to the world outside this container
EXPOSE 80

# Define environment variable
ENV NAME World

# Run the application
CMD ["python", "app.py"]
