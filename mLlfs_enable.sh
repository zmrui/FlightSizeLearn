export PATH=$PATH:/usr/local/bin
sysctl -w net.ipv4.ip_forward=1
insmod kmod_sysfs/tcp_monitor/tcp_monitor.ko
/home/ubuntu/FlightSize/sync.sh &
python3 mahimahi.py
