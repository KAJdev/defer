FROM python:3.10

# Install dependencies
RUN pip install -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app

# Set the working directory to /app
WORKDIR /app

# Run app.py when the container launches
CMD ["python", "app.py"]