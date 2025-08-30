#!/usr/bin/env python3
"""Test HTTP server without Docker"""
import subprocess
import time
import sys
import os
import signal

# Test the HTTP server locally without Docker
print("Starting MCP server with HTTP transport (no Docker)...")
print("=" * 50)

# Set environment variables
env = os.environ.copy()
env["MCP_TRANSPORT"] = "http"
env["PORT"] = "8080"
env["API_KEY"] = "T4TevWYV3suiQ8eLFbza"
env["SIMPLER_GRANTS_API_KEY"] = "T4TevWYV3suiQ8eLFbza"
env["PYTHONUNBUFFERED"] = "1"

# Start the server
print("Starting server...")
server_process = subprocess.Popen(
    [sys.executable, "main.py"],
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

try:
    # Wait for server to start
    print("Waiting for server to start...")
    time.sleep(3)
    
    # Monitor output for 10 seconds
    print("\nServer output:")
    print("-" * 40)
    
    start_time = time.time()
    while time.time() - start_time < 10:
        line = server_process.stdout.readline()
        if line:
            print(line.strip())
        
        # Check if process has ended
        if server_process.poll() is not None:
            print(f"\nServer exited with code: {server_process.returncode}")
            break
    
    print("-" * 40)
    print("\nTo test the server, run in another terminal:")
    print("  python3 scripts/test_http_local.py")
    print("\nPress Ctrl+C to stop the server")
    
    # Keep running
    while True:
        line = server_process.stdout.readline()
        if line:
            print(line.strip())
        if server_process.poll() is not None:
            break
        time.sleep(0.1)
    
except KeyboardInterrupt:
    print("\n\nShutting down server...")
    server_process.terminate()
    time.sleep(1)
    if server_process.poll() is None:
        server_process.kill()
    print("Server stopped.")
except Exception as e:
    print(f"Error: {e}")
    server_process.terminate()