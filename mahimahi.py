import os
import shutil
from subprocess import Popen, PIPE, call
import subprocess
import time
from utils import *
from datetime import datetime

traces = [
    # "traces/ATT-LTE-driving-2016",
    "traces/ATT-LTE-driving",
    "traces/TMobile-LTE-driving",
    "traces/TMobile-LTE-short",
    # "traces/Verizon-LTE-driving",
    # "traces/Verizon-LTE-short",
]

mmdelaylist = [
    20,
    50,
    100,
]

mmloss_ist = [
    0,
    # 0.001,
    0.01,
    0.1,
]

def mahimahi(savingpath, dt_string,traceup , tracedown, mmdelay,loss_uplink, loss_downlink):
   
    # savingpath = 

    os.makedirs(savingpath)

    # Topology graph
    #
    #           Internal    ------data direction------>     External
    #  ______________________________
    # |Mahimahi                      |
    # |   iPerf3 client as sender ---|---> iPerf3 server as receiver
    # |______________________________|
    # 

    # Start Mahimahi
    # traceup = "../mahimahi/traces/Verizon-LTE-short.up"
    # tracedown = "../mahimahi/traces/Verizon-LTE-short.down"
    cmd = f"mm-link {traceup} {tracedown} mm-delay {mmdelay} mm-loss uplink {loss_uplink} mm-loss downlink {loss_downlink}"
    # cmd = "mm-delay 20"
    p = Popen(cmd, stdin=PIPE,shell=True,text=True)

    mahimahi_internel_inetface = 'ingress'

    # Mahimahi External information collection
    mahimahi_external_ip = run_shell("/home/ubuntu/FlightSize/mahimahi_ext_ip.sh")
    mahimahi_external_ip = mahimahi_external_ip[0].replace('\n','')
    
    mahimahi_external_inetface = run_shell("/home/ubuntu/FlightSize/mahimahi_ext_inetface.sh")
    mahimahi_external_inetface = mahimahi_external_inetface[0].replace('\n','')
    print("Here:",mahimahi_external_ip,mahimahi_external_inetface)


    
    # Mahimahi External execuation
    # start_tcpdump(mahimahi_external_inetface,os.path.join(savingpath,"extresult.pcap")) # tcpdump at external enviroment

    cmd = f"iperf3 -s -1 -p 5001 --json --logfile {savingpath}/iperf_receiver.txt "  # start iPerf3 server, only serve once
    print(cmd)
    Popen(cmd, stdin=PIPE,shell=True,text=True) # start iPerf3 server at external enviroment
    clean_kmesg()
    cmd = f"dmesg --follow > {savingpath}/kmesg.txt &"
    p_dmesg = Popen(cmd, stdin=PIPE,shell=True,text=True)
    # tmp= "mm-link ./"+str(args.trace)+" ./"+str(args.trace)+ " --meter-all --uplink-log "+str(args.dir)+"/output_verus/"+str(args.name)+"/"+args.name+"_uplink.csv --downlink-log "+str(args.dir)+"/output_verus/"+str(args.name)+"/"+args.name+"_downlink.csv --uplink-queue=droptail --uplink-queue-args=bytes={}".format(args.queue)
    p.communicate(f"bash /home/ubuntu/FlightSize/mahimahi_internal_exec.sh {savingpath}")
    # save_kmesg(f"{savingpath}/kmesg.txt")
    time.sleep(3)
    p_dmesg.kill()
    return savingpath


def main():
    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d-%Hh.%Mm.%Ss")
    for trace in traces:
        for loss in mmloss_ist:
            for delay in mmdelaylist:
                print(f"[TRACE]:{trace}")
                traceup = trace + ".up"
                tracedown = trace + ".down"
                run = 0

                try:
                    # execption_exec()
                    # Preparing
                    lossdown = 0
                    lossup = loss
                    rootpwd = os.getcwd()
                    resultdir  = os.path.join(rootpwd,'Results')
                    networkenv = f"delay{delay}_lossdown{lossdown}_lossup{lossup}"
                    savingpath = os.path.join(resultdir, "MLOn"+trace.replace('traces/','')+networkenv, dt_string)
                    if os.path.exists(savingpath):
                        shutil.rmtree(savingpath)
                    mahimahi(savingpath=savingpath, dt_string=dt_string,traceup=traceup,mmdelay=delay,tracedown=tracedown,loss_uplink=lossup, loss_downlink=lossdown)
                    run  += 1
                except KeyboardInterrupt:
                    print("Got KeyboardInterrupt CTRL-C, exiting")
                    exit()
                except Exception as e:
                    print("[Exception]:\n",repr(e))
                    # execption_exec()
                finally:
                    print("++++++++++++++++++++++++++\nEND Mahimahi and parse\n++++++++++++++++++++++++++\n")
                        
        
        print("Finish")

if __name__ == "__main__":
    main()