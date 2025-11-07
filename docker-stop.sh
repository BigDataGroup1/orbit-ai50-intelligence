#!/bin/bash

# Docker stop script for Project ORBIT
set -e

echo "========================================="
echo "  🛑 Stopping ORBIT PE Dashboard"
echo "========================================="
echo ""

docker-compose down

echo ""
echo "✅ Services stopped successfully!"
echo ""
