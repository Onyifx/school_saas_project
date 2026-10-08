web: uvicorn main:app --host 0.0.0.0 --port $PORT
worker: python lead_finder.py