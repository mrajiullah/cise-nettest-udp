#!/bin/bash


cd /opt/monroe/

echo "Experiment starts ..."

make


python udpbwestimator.py
wait 15
python nettest.py
