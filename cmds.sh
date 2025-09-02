export PATH=$PATH:/usr/local/bin
sysctl -w net.ipv4.ip_forward=1
# insmod kmod_sysfs/tcp_monitor/tcp_monitor.ko
# /home/ubuntu/FlightSize/sync.sh &
# python3 mahimahi.py
# /usr/bin/python3 mininetscript.py
# python3 compare_two_methods_reorder.py
cca=$(cat cca_control)
reorder=$(cat reorder_control)
bw=$(cat bw_control)
rtt=$(cat rtt_control)
ML=$(cat ML_control)
if [ "${ML}" = "ON" ]; then
    insmod kmod_sysfs/tcp_monitor/tcp_monitor.ko
    /home/ubuntu/FlightSize/sync.sh &
fi
# python3 reorder7.gemini.py --cca $cca --$reorder --bw $bw --rtt $rtt --res_path "ML${ML}_${cca}_${reorder}_bw${bw}_rtt${rtt}"
python3 reorder8.wget.py --cca $cca --$reorder --bw $bw --rtt $rtt --res_path "wget_ML${ML}_${cca}_${reorder}_bw${bw}_rtt${rtt}"
dmesg > dmesg.txt
