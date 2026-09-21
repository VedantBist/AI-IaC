FROM python:3.11-slim

WORKDIR /app

COPY backend/main.py ./backend/main.py
COPY ml/model.pkl ./ml/model.pkl

RUN pip install --no-cache-dir fastapi uvicorn joblib numpy scikit-learn

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]