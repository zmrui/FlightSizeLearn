export PATH=$PATH:/usr/local/bin
sysctl -w net.ipv4.ip_forward=1
python3 mahimahi.py