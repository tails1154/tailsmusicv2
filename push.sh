#!/bin/bash
#./docs.sh
git init
echo "Enter commit message"
read -p ">" COMMITMSG
./docs.sh
git add .
git commit -m "$COMMITMSG"
echo "Would you like to push now? (Y/n)"
read -p "push>" YESNO
if [ "$YESNO" = "n" ]; then
	exit 0
else
	git push
fi
