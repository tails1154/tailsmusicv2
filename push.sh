#!/bin/bash
#./docs.sh
git init
#if [ "$1" = "--commitmsg" ]; then
#	COMMITMSG = $2
#	SKIPCMSG = "1"
#	if [ "$3" = "--push" ]; then
#	./docs.sh
#	git add .
#	git commit -m "$COMMITMSG"
#	exit 0
#	fi
if [ "$1" = "--push" ]; then
	SKIPCONF="1"
fi
if [ "$SKIPCMSG" = "1" ]; then
	echo ""
else
	echo "Enter commit message"
	read -p ">" COMMITMSG
fi
./docs.sh
git add .
git commit -m "$COMMITMSG"
if [ "$SKIPCONF" = "1" ]; then
	git push
	exit 0
fi
echo "Would you like to push now? (Y/n)"
read -p "push>" YESNO
if [ "$YESNO" = "n" ]; then
	exit 0
else
	git push
fi
