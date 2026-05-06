# Mutual Fund FAQ Assistant - Frontend

Phase 8 - Frontend Web UI for the Mutual Fund FAQ Assistant.

## Features

- **Welcome copy** with facts-only positioning
- **Three clickable example questions** for quick start
- **Chat transcript area** per active thread
- **"New chat" control** for creating new thread_id
- **Responsive design** for mobile and desktop
- **Type-safe API client** for backend communication

## Technology Stack

- **Next.js 14** with App Router and TypeScript
- **TailwindCSS** for styling
- **Type-safe API client** for Phase 7 backend integration
- **Responsive design** with mobile-first approach

## Setup Instructions

### Prerequisites

- Node.js 18+ installed
- Phase 7 API server running on `http://localhost:${BACKEND_PORT:-8000}`

### Installation

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

### Development

1. Start the development server:
   ```bash
   npm run dev
   ```

2. Open [http://localhost:3000](http://localhost:3000) in your browser

### Production Build

1. Build the application:
   ```bash
   npm run build
   ```

2. Start the production server:
   ```bash
   npm start
   ```

## API Integration

The frontend integrates with the Phase 7 backend API:

- **Thread Management**: Create, retrieve, and delete chat threads
- **Message Exchange**: Send user messages and receive AI responses
- **Real-time Updates**: Live chat interface with message history
- **Error Handling**: Graceful error handling and user feedback

## Key Components

- **`src/app/page.tsx`**: Main chat interface
- **`src/utils/api-client.ts`**: Type-safe API client
- **`src/types/api.ts`**: TypeScript type definitions
- **`src/app/globals.css`**: Global styles with TailwindCSS

## Features Implemented

✅ **Welcome Page**: Facts-only positioning with clear messaging
✅ **Example Questions**: Three clickable starter questions
✅ **Chat Interface**: Real-time message exchange with backend
✅ **Thread Management**: New chat functionality with thread isolation
✅ **Responsive Design**: Mobile and desktop optimized
✅ **Type Safety**: Full TypeScript integration
✅ **Error Handling**: Comprehensive error management

## Environment Variables

Create a `.env.local` file in the frontend directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## Deployment

The frontend is ready for deployment on platforms like:
- Vercel (recommended for Next.js)
- Netlify
- AWS Amplify
- Docker containers

## Architecture

The frontend follows a clean architecture:
- **Components**: Reusable UI components
- **API Layer**: Type-safe client for backend communication
- **State Management**: React hooks for local state
- **Styling**: TailwindCSS with custom components
- **Routing**: Next.js App Router

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Follow the existing code style
2. Use TypeScript for all new code
3. Ensure responsive design
4. Test with the Phase 7 backend
5. Update documentation as needed
