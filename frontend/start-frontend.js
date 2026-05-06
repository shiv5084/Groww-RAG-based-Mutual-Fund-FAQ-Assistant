const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log('🚀 Starting Phase 8 Frontend Setup...\n');

// Check if node_modules exists
const nodeModulesPath = path.join(__dirname, 'node_modules');
if (!fs.existsSync(nodeModulesPath)) {
    console.log('📦 Installing dependencies...');
    
    // Use npm to install dependencies
    const npmInstall = spawn('npm', ['install'], {
        stdio: 'inherit',
        shell: true,
        cwd: __dirname
    });
    
    npmInstall.on('close', (code) => {
        if (code === 0) {
            console.log('✅ Dependencies installed successfully!\n');
            startDevServer();
        } else {
            console.log('❌ Failed to install dependencies');
            console.log('\nPlease manually run:');
            console.log('1. cd frontend');
            console.log('2. npm install');
            console.log('3. npm run dev');
            process.exit(1);
        }
    });
} else {
    console.log('📦 Dependencies already installed!\n');
    startDevServer();
}

function startDevServer() {
    console.log('🌟 Starting development server...');
    console.log('📍 Frontend will be available at: http://localhost:3000');
    const backendPort = process.env.BACKEND_PORT || 8000;
    console.log(`🔗 API should be running at: http://localhost:${backendPort}`);
    console.log('⏹️  Press Ctrl+C to stop the server\n');
    
    // Start the Next.js development server
    const devServer = spawn('npm', ['run', 'dev'], {
        stdio: 'inherit',
        shell: true,
        cwd: __dirname
    });
    
    devServer.on('close', (code) => {
        console.log(`Development server exited with code ${code}`);
    });
    
    // Handle process termination
    process.on('SIGINT', () => {
        console.log('\n🛑 Stopping development server...');
        devServer.kill('SIGINT');
        process.exit(0);
    });
}
