# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /add_expense_group

# Copy .env file to the container

# Copy the current directory contents into the container at /app
COPY . /add_expense_group/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5001 available to the world outside this container
EXPOSE 5004



CMD ["gunicorn","app:app", "--bind", "0.0.0.0:5004" ]
