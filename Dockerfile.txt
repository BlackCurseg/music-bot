# Use a lightweight version of Python
FROM python:3.10-slim

# Install FFmpeg and git (required for some music libraries)
RUN apt-get update && \
    apt-get install -y ffmpeg git && \
    rm -rf /var/lib/apt/lists/*

# Set up the folder for your bot
WORKDIR /app

# Copy all your files into the container
COPY . .

# Install your Python libraries
RUN pip install --no-cache-dir -r requirements.txt

# Start your bot
CMD ["python", "bot.py"]