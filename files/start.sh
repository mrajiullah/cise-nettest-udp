#!/bin/bash

cd /opt/monroe/

echo "DBG: Nettest+udpbwestimator container is starting ..."

#make

python udpbwestimator.py
wait 15
python nettest.py
