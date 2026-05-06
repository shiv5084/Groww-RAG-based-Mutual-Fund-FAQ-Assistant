# Deployment Plan: Mutual Fund FAQ Assistant

This plan outlines the steps to deploy the Mutual Fund FAQ Assistant with a FastAPI backend on **Render** and a Next.js frontend on **Vercel**.

## 1. Backend Deployment (Render)

### Configuration
- **Service Type**: Web Service
- **Runtime**: Python 3.10+
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn src.phase7_api.main:app --host 0.0.0.0 --port $PORT`
- **Root Directory**: `.` (Root of the repository)

### Environment Variables
| Variable | Value | Description |
| :--- | :--- | :--- |
| `GROQ_API_KEY` | `your_api_key_here` | Required for LLM generation |
| `PYTHON_VERSION` | `3.10.0` | Recommended version |
| `CORS_ORIGINS` | `https://your-frontend-url.vercel.app` | (Optional) For security |

### Necessary Code Changes
- [x] Add `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings` to `requirements.txt`.
- [ ] Ensure `data/sessions` directory exists or is handled by the app (Render disks are ephemeral on free tier, but SQLite is fine for temporary sessions).
- [ ] Fix any relative path issues in `main.py` for deployment.

---

## 2. Frontend Deployment (Vercel)

### Configuration
- **Framework Preset**: Next.js
- **Root Directory**: `frontend`
- **Build Command**: `npm run build`
- **Install Command**: `npm install`

### Environment Variables
| Variable | Value | Description |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | `https://your-backend.onrender.com/api/v1` | URL of the Render backend |

### Necessary Code Changes
- [x] Update `frontend/src/utils/api-client.ts` to use `NEXT_PUBLIC_API_URL` in production.
- [ ] Ensure all assets (logos, icons) are in the `public` directory.

---

## 3. Implementation Steps

### Step 1: Update Requirements
Updated the `requirements.txt` file to include all necessary backend dependencies. (Completed)

### Step 2: Update API Client
Modified `frontend/src/utils/api-client.ts` to correctly handle the production API URL. (Completed)

### Step 3: Push to GitHub
Pushed the configuration changes to the repository. (Completed)

### Step 4: Deploy to Render
1. Connect your GitHub repository to Render.
2. Select "Web Service".
3. Use the configurations mentioned above.
4. Add the `GROQ_API_KEY`.

### Step 5: Deploy to Vercel
1. Connect your GitHub repository to Vercel.
2. Select the `frontend` folder as the root directory.
3. Add `NEXT_PUBLIC_API_URL` pointing to your Render app.

---

## 4. Post-Deployment Verification
- [ ] Check Render logs for successful startup.
- [ ] Verify the `/api/v1/health` endpoint on Render.
- [ ] Check Vercel build logs.
- [ ] Test end-to-end chat functionality.

> [!WARNING]
> **Render Free Tier Note**: The backend will "sleep" after 15 minutes of inactivity. The first request after a sleep period will take ~30 seconds to respond as the service wakes up.
