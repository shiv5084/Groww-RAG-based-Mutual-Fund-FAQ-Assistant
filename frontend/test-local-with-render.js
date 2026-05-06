const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

console.log('🚀 Setting up local frontend test with Render backend...\n');

// Create .env.local file for testing
const envContent = `# Local testing with Render backend
NEXT_PUBLIC_API_URL=https://groww-rag-based-mutual-fund-faq-assistant.onrender.com/api/v1
NEXT_PUBLIC_BACKEND_PORT=8000
`;

const envPath = path.join(__dirname, '.env.local');
fs.writeFileSync(envPath, envContent);
console.log('✅ Created .env.local with Render backend URL');

// Verify the environment file
console.log('\n📋 Environment configuration:');
console.log('NEXT_PUBLIC_API_URL=https://groww-rag-based-mutual-fund-faq-assistant.onrender.com/api/v1');
console.log('NEXT_PUBLIC_BACKEND_PORT=8000');

console.log('\n🌟 Starting local development server...');
console.log('📍 Frontend will be available at: http://localhost:3000');
console.log('🔗 API calls will go to: https://groww-rag-based-mutual-fund-faq-assistant.onrender.com/api/v1');
console.log('⏹️  Press Ctrl+C to stop the server\n');

// Start the Next.js development server
const devServer = spawn('npm', ['run', 'dev'], {
    stdio: 'inherit',
    shell: true,
    cwd: __dirname
});

devServer.on('close', (code) => {
    console.log(`\n🛑 Development server exited with code ${code}`);
});

// Handle process termination
process.on('SIGINT', () => {
    console.log('\n🛑 Stopping development server...');
    devServer.kill('SIGINT');
    
    // Clean up .env.local
    if (fs.existsSync(envPath)) {
        fs.unlinkSync(envPath);
        console.log('🗑️  Cleaned up .env.local');
    }
    
    process.exit(0);
});
