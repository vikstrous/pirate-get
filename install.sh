#!/usr/bin/env sh
if [ "$UID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

TMP=`mktemp python`
if [ `which python2.7` ]
then
    echo "#!/usr/bin/env python2.7" > $TMP
elif [ `which python2` ]
then
    echo "#!/usr/bin/env python2" > $TMP
else
    echo "#!/usr/bin/env python" > $TMP
fi

sed 1d `dirname $0`/pirate-get.py >> $TMP

cp $TMP /usr/bin/pirate-get
chmod +x /usr/bin/pirate-get
chmod 755 /usr/bin/pirate-get
