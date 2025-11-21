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


ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "discord_bot.py"]
