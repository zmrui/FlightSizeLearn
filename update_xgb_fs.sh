#!/bin/bash
# echo "Starting continuous execution. Press Ctrl+C to stop."

while true
do
  socket_info="$(cat /sys/kernel/tcp_monitor/socket_info)" 
  echo $socket_info
  temp=$(/home/ubuntu/FlightSize/C_ml_model/xgb_fs "$socket_info")    
  echo $temp
  echo $temp > /sys/kernel/ml_tcp/flight_size
done
