# Dockerfile - containerize the Space Fractions service layer for demo.
# The desktop UI is packaged separately via PyInstaller (build_game.ps1).
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "-c", "from spacefractions.health import health; import json; print(json.dumps(health()))"]
