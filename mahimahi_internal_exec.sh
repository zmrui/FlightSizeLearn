#!/bin/bash

# sudo sh -c "tcpdump -tt -i any tcp dst port 5001 -w $1/internalsult.pcap &"
# tcpdump -tt -i any tcp dst port 5001 -w $1/internalsult.pcap &

iperf3 -c $MAHIMAHI_BASE -p 5001 -t 10 -C bbr