#!/bin/bash
./docs.sh
git init
git add .
echo "Enter commit message"
read -p ">" COMMITMSG
git commit -m "$COMMITMSG"
git push
