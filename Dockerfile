FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (if you need build tools for some packages, add them here)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files (note: `.env` is excluded via .dockerignore)
COPY . .

# Expose keep-alive HTTP port so hosting platforms can detect an open port
EXPOSE 8080

# Start keep_alive server (binds port) and then the Discord bot.
# Use a shell form so both processes can be started; keep the bot in foreground.
CMD ["sh", "-c", "python keep_alive.py & python discord_bot.py"]
