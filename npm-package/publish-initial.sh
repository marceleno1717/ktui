#!/bin/bash
# Run this locally after 'npm login' to publish the initial empty packages 
# so you can configure OIDC on npmjs.com.

set -e

cd "$(dirname "$0")"

echo "Publishing initial ktui-linux-x64-bin..."
cd npm/ktui-linux-x64-bin
npm version 0.1.1 --no-git-tag-version --allow-same-version
mkdir -p bin && touch bin/ktui && chmod +x bin/ktui
npm publish
cd ../..

echo "Publishing initial ktui-darwin-arm64-bin..."
cd npm/ktui-darwin-arm64-bin
npm version 0.1.1 --no-git-tag-version --allow-same-version
mkdir -p bin && touch bin/ktui && chmod +x bin/ktui
npm publish
cd ../..

echo "Publishing initial ktui-win32-x64-bin..."
cd npm/ktui-win32-x64-bin
npm version 0.1.1 --no-git-tag-version --allow-same-version
mkdir -p bin && touch bin/ktui.exe
npm publish
cd ../..

echo "Done! You can now configure OIDC on npmjs.com for the new -bin packages."
