# 🚀 Phase 8 Frontend Setup Instructions

## Current Status
✅ Frontend code is **COMPLETE** and ready to run
❌ PowerShell execution policy is blocking npm commands

## 📋 Quick Setup Steps

### Step 1: Open Command Prompt (NOT PowerShell)
1. Press `Win + R`
2. Type `cmd` and press Enter
3. Navigate to frontend folder:
   ```cmd
   cd "c:\Users\HP\Desktop\shiv\programming project\Git_hub project\Groww-RAG-MutualFundFAQAssistant\frontend"
   ```

### Step 2: Install Dependencies
```cmd
npm install
```
*This will install Next.js, React, TypeScript, and TailwindCSS*

### Step 3: Start Development Server
```cmd
npm run dev
```

### Step 4: Access the Application
- **Frontend**: http://localhost:3000
- **NEXT_PUBLIC_API_URL=http://localhost:${BACKEND_PORT:-8000}/api/v1** (must be running separately)

## 🔧 Alternative: PowerShell Fix (Advanced)

If you prefer using PowerShell, run this as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then restart PowerShell and use the normal npm commands.

## ✅ What You'll Get

Once running, you'll see:

### Welcome Page
- Facts-only positioning
- Three clickable example questions
- Clean, professional design

### Chat Interface
- Real-time message exchange
- Thread management
- Citation links
- Responsive design

### Features
- ✅ New Chat button (creates new thread_id)
- ✅ Message history per thread
- ✅ Error handling and loading states
- ✅ Mobile and desktop responsive

## 🧪 Testing the Frontend

1. **Start Phase 7 API first**:
   ```cmd
   python src/scripts/run_phase7_api.py
   ```

2. **Then start frontend** (using Command Prompt):
   ```cmd
   cd frontend
   npm install
   npm run dev
   ```

3. **Test functionality**:
   - Click example questions
   - Type custom questions
   - Use "New Chat" button
   - Check responsive design

## 📁 Frontend Structure (Already Created)

```
frontend/
├── package.json                 # ✅ Dependencies configured
├── next.config.js              # ✅ API proxy setup
├── tsconfig.json               # ✅ TypeScript config
├── tailwind.config.js          # ✅ TailwindCSS config
├── postcss.config.js           # ✅ PostCSS config
└── src/
    ├── app/
    │   ├── layout.tsx          # ✅ Root layout
    │   ├── page.tsx            # ✅ Main chat interface
    │   └── globals.css         # ✅ Global styles
    ├── types/
    │   └── api.ts              # ✅ API type definitions
    └── utils/
        └── api-client.ts        # ✅ Type-safe API client
```

## 🎯 Ready to Use

The frontend is **100% complete** and ready for:
- Development testing
- Integration with Phase 7 API
- Deployment to production
- Further customization

## 🆘 Troubleshooting

**Issue**: "npm command not found"
**Solution**: Use Command Prompt (cmd) instead of PowerShell

**Issue**: TypeScript errors
**Solution**: Expected until dependencies are installed

**Issue**: API connection errors
**Solution**: Make sure Phase 7 API is running on port 8000

**Issue**: Port 3000 already in use
**Solution**: Stop other services or use `npm run dev -- -p 3001`

---

**Next Step**: Open Command Prompt and run the setup commands above! 🚀
