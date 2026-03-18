# CORS Validation Checklist

## Required Backend Configuration (FastAPI)

Before auth stories (FE-1.2, FE-1.3) begin, verify these CORS settings on the backend:

- `Access-Control-Allow-Credentials: true` must be in response headers for `/auth/*` endpoints
- `Access-Control-Allow-Origin` must be explicit (e.g., `http://localhost:3000`) — NOT wildcard `*`
- `Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS`
- `Access-Control-Allow-Headers: Content-Type, Authorization`

## Validation Steps

1. Start backend: `cd TensorBros/Reqruit && .venv/Scripts/python.exe -m uvicorn src.main:app --reload`
2. Start frontend: `cd reqruit-frontend && pnpm dev`
3. Test: `curl -X POST http://localhost:8000/api/v1/auth/login -H "Origin: http://localhost:3000" -v 2>&1 | grep -i "access-control"`
4. Confirm response includes `Access-Control-Allow-Credentials: true` and non-wildcard origin

## Status

⏳ Not yet validated — requires backend to be running locally.
Story FE-1.2 (User Registration) must NOT begin until this is confirmed.
