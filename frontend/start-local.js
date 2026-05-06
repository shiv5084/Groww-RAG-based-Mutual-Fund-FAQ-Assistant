const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

console.log('🚀 Starting local frontend with LOCAL backend...\n');

// Detect backend port
const backendPort = process.env.BACKEND_PORT || 8000;
const apiUrl = `http://localhost:${backendPort}/api/v1`;

// Create .env.local file pointing to local backend
const envContent = `# Local testing with local backend
NEXT_PUBLIC_API_URL=${apiUrl}
NEXT_PUBLIC_BACKEND_PORT=${backendPort}
`;

const envPath = path.join(__dirname, '.env.local');

// Check if .env.local already exists and back it up
let backupContent = null;
if (fs.existsSync(envPath)) {
    backupContent = fs.readFileSync(envPath, 'utf8');
    console.log('📦 Backed up existing .env.local');
}

fs.writeFileSync(envPath, envContent);
console.log(`✅ Created .env.local with local backend: ${apiUrl}`);

console.log('\n📋 Environment configuration:');
console.log(`NEXT_PUBLIC_API_URL=${apiUrl}`);
console.log(`NEXT_PUBLIC_BACKEND_PORT=${backendPort}`);

console.log('\n🌟 Starting local development server...');
console.log('📍 Frontend will be available at: http://localhost:3000');
console.log(`🔗 API calls will go to: ${apiUrl}`);
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

    // Restore or clean up .env.local
    if (backupContent) {
        fs.writeFileSync(envPath, backupContent);
        console.log('🗑️  Restored original .env.local');
    } else if (fs.existsSync(envPath)) {
        fs.unlinkSync(envPath);
        console.log('🗑️  Cleaned up .env.local');
    }

    process.exit(0);
});
