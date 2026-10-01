#!/bin/bash
# Run this locally after 'npm login' to publish the initial empty packages 
# so you can configure OIDC on npmjs.com.

set -e

# Change to the directory where this script is located
cd "$(dirname "$0")"

echo "Publishing initial ktui-linux-x64..."
cd npm/ktui-linux-x64
mkdir -p bin && touch bin/ktui && chmod +x bin/ktui
npm publish --access public
cd ../..

echo "Publishing main ktui package..."
npm publish --access public

echo "Done! You can now configure OIDC on npmjs.com."
