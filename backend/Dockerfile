# Backend image. Build from the REPO ROOT (the API needs ml/dkt_model.py and
# the trained checkpoint too):
#   docker build -f backend/Dockerfile -t algebra-tutor-api .
FROM python:3.11-slim

WORKDIR /app

# CPU-only PyTorch: the server only runs inference, and the default wheel
# bundles CUDA libraries (~1.5 GB) that would never be used.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir torch==2.4.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r backend/requirements.txt

# Only what inference needs: model class, trained weights, skill id mapping.
COPY ml/__init__.py ml/dkt_model.py ml/
COPY ml/checkpoints/dkt.pt ml/checkpoints/dkt_config.json ml/checkpoints/
COPY data/processed/skill_map.csv data/processed/
COPY backend/app backend/app

# SQLite file location. On Render's free plan the disk is wiped on every
# restart/redeploy, so attempts are lost then (fine for a demo).
ENV TUTOR_DB=/tmp/tutor.db

# Render sets $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
