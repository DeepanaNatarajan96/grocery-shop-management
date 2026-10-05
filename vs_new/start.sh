#!/bin/sh
# Starts the Grocery Shop Management System backend server.
# Works on macOS and Linux. Double-click may not work depending on your
# file manager's settings — if so, open a terminal in this folder and run:
#   sh start.sh
cd "$(dirname "$0")/backend" || exit 1

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "Python was not found on this system. Please install Python 3.8+ from https://python.org and try again."
  exit 1
fi

echo "Starting server with: $PYTHON server.py"
"$PYTHON" server.py
