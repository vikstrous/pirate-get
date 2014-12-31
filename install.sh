#!/usr/bin/env sh
set -e

TMP=$(mktemp pirate-get-XXXXXX)

{
	if [ $(which python2.7) ]
	then
		echo "#!/usr/bin/env python2.7" > "$TMP"
	elif [ `which python2` ]
	then
		echo "#!/usr/bin/env python2" > "$TMP"
	else
		echo "#!/usr/bin/env python" > "$TMP"
	fi

	sed 1d $(dirname $0)/pirate-get.py >> "$TMP"

	cp "$TMP" /usr/bin/pirate-get &&
	chmod +x /usr/bin/pirate-get &&
	chmod 755 /usr/bin/pirate-get &&

	pip install -r requirements.txt &&

	rm $TMP
} || rm $TMP
