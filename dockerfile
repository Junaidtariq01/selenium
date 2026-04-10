# Use Python 3.9 as base
FROM python:3.9-slim

# Install Chrome and dependencies for Selenium
RUN apt-get update && apt-get install -y \
    wget gnupg unzip curl \
    google-chrome-stable \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libnspr4 \
    libnss3 \
    lsb-release \
    xdg-utils \
    && apt-get clean

# Set display port to avoid crashes
ENV DISPLAY=:99

# Set up working directory
WORKDIR /app
COPY . /app

# Install Python requirements
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the app using Gunicorn (production grade)
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]