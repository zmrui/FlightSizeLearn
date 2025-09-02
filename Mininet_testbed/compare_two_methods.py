import os
import time
import Mininet_testbed.analyze.mn_net_topo
import Mininet_testbed.analyze.fs_compare
import random
from matplotlib import pyplot as plt
import pandas as pd

def Compare_two_methods(cca='bbr',keep=1,rtt=1,bw=1,nameprefix="",sub_folder=None):
    # exp_table6_1
    maxqsize=100
    print("maxqsize=",maxqsize)

    mn_net = Mininet_testbed.analyze.mn_net_topo.mn_network(rtt=rtt,bw=bw,cca=cca,reorder=False,
                                    nameprefix=nameprefix,
                                    maxqsize=maxqsize,sub_folder=sub_folder)
    mn_net.make_subfolder()
    mn_net.start_mininet()
    mn_net.disable_tso()
    # input()
    mn_net.start_tcpdump(result_save_path=mn_net.workingdir)
    mn_net.set_iptables_prob_packet_loss(percentage=20/10000)

    # mn_net.start_iperf_size(durition_time=20)
    mn_net.start_iperf_time_json(durition_time=3)

    mn_net.wait_until_iperf_end()
    mn_net.kill_tcpdump()
    # input()
    mn_net.stop_mininet()
    mn_net.save_log()
    # mn_net.return_top_folder()

    files = os.listdir(mn_net.workingdir)
    for item in files:
        if cca in item and item.endswith("name.txt"):
            filename = item
    fc=Mininet_testbed.analyze.fs_compare.fs_compare_class(folder = mn_net.workingdir, filename=filename)
    fc.generate()
    fc.parse_printk()
    # print(fc.Flightsizedf)
    fc.parse_receiver_tcpdump()
    fc.parse_sender_tcpdump()
    fc.change_tcpdump_df_time()
    # print(fc.tcpdump_df)
    fc.cal_FlightSize_new()
    old_csv = pd.read_csv(os.path.join(fc.folder,'FlightSize_old_method_operation.csv'))
    
    plt.clf()
    # plt.figure(figsize=(20,4))
    plt.subplot(1, 2, 1)
    plt.plot(old_csv['Time'].tolist(),old_csv['FlightSize'].tolist(),label="old method")
    plt.xlabel('time')
    plt.ylabel('flightsize')
    plt.title("Old FlightSizeMethod1")
    plt.grid()
    plt.legend()
    plt.subplot(1, 2, 2)
    plt.plot(fc.FlightSize_df_method2['Time'].tolist(),fc.FlightSize_df_method2['FlightSizeMethod2'].tolist(),label="FlightSizeMethod2")
    plt.xlabel('time')
    plt.ylabel('flightsize')
    plt.title("New FlightSizeMethod2")
    plt.grid()
    plt.legend()
    plt.savefig(os.path.join(fc.folder,'fscompare.jpg'))
    # averagedifference,averagediffnostart,averagediffnoequal,averagediffonlyunder,averagediffonlyover = fc.sla(start=5)
    # fc.draw_throughput()
    # fc.draw_CWND()
    # fc.return_top_folder()
    
    # return averagediffnostart
