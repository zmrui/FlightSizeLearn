#!/bin/bash
# echo "Starting continuous execution. Press Ctrl+C to stop."

echo 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 > socket_info
sleep 1
echo 0 > ml_flight_size

while true
do
  socket_info=$(cat /sys/kernel/tcp_monitor/socket_info) 
  echo -n "$socket_info" > socket_info
  echo -n "$(cat ml_flight_size)" > /sys/kernel/ml_tcp/flight_size
done


