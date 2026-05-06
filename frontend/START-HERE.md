# Starting the Phase 8 Frontend

## Quick Start

Since PowerShell execution policy may block npm commands, please follow these steps:

### Option 1: Run Setup Script
cd frontend
node start-frontend.js

### Option 2: Manual Setup
1. Open PowerShell as Administrator
2. Run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
3. Navigate to this folder: `cd frontend`
4. Install dependencies: `npm install`
5. Start development server: `npm run dev`

### Option 3: Use Command Prompt
1. Open Command Prompt (cmd)
2. Navigate to this folder: `cd frontend`
3. Install dependencies: `npm install`
4. Start development server: `npm run dev`

## What You'll See

Once started, the frontend will be available at:
- **URL**: http://localhost:3000
- **API**: Connects to Phase 7 backend at http://localhost:8000

## Features Available

✅ Welcome page with facts-only positioning
✅ Three clickable example questions
✅ Chat interface with thread management
✅ New chat button for creating new threads
✅ Responsive design for mobile and desktop

## Troubleshooting

If you see TypeScript errors, don't worry - they're expected until dependencies are installed.
The frontend requires the Phase 7 API server to be running on port 8000 for full functionality.

## Next Steps

1. Make sure Phase 7 API is running: `python src/scripts/run_phase7_api.py`
2. Start the frontend using one of the options above
3. Open http://localhost:3000 in your browser
4. Test the chat functionality with the example questions
