#!/usr/bin/env sh
if [ "$UID" -ne 0 ] 
  then echo "Please run as root" 
  exit 
fi

rm /usr/bin/pirate-get
