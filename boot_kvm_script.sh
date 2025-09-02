#!/bin/bash 
# taskset -c 1 ./virtme/virtme-run -a "nokaslr" --rwdir /home/ubuntu/FlightSize --pwd --kdir ./linux/ --memory 1024M --script-sh "./cmds.sh" 
taskset -c 1 ./virtme/virtme-run -a "nokaslr" --rwdir /home/ubuntu/FlightSize --pwd --kdir ./linux/ --memory 1024M --script-sh "./cmd_in_virtme.sh" 
echo "[Finish]"
