import os
import time
import Mininet_testbed.analyze.mn_net_topo
# import Mininet_testbed.analyze.fs_compare
# import Mininet_testbed.analyze.misc
import Mininet_testbed.utils.config
import random
# from matplotlib import pyplot as plt
import pandas as pd
from datetime import datetime



def Reorder(cca,rtt, bw,  reorder_percentage_in_10000,reorder_distance,loss=0,nameprefix="", keep=1):
    MLFS = "MLFSOff"
    reorder_probility=2000/100.0
    reorder_tc_prob = 100.0 - reorder_probility
    # reorder_tc_prob = reorder_probility
    maxqsize=1000
    print("maxqsize=",maxqsize)
    now = datetime.now()
    dt_string = MLFS+now.strftime("%Y-%m-%d-%Hh.%Mm.%Ss")
    resfolder = os.path.join(Mininet_testbed.utils.config.RESULTS_DIR,'reorder',dt_string)
    # realsub_folder = os.path.join(resfolder,f'{cca}_bw{bw}_rtt{rtt}_reorder{reorder_percentage_in_10000/100}%')
    realsub_folder = resfolder
    print(realsub_folder)

    mn_net = Mininet_testbed.analyze.mn_net_topo.mn_network(rtt=rtt,bw=bw,cca=cca,reorder=True,
                                    nameprefix=nameprefix,
                                    probability=reorder_probility,correlation=0,reorder_distance=reorder_distance,
                                    maxqsize=maxqsize,sub_folder=realsub_folder)
    mn_net.make_subfolder()
    mn_net.start_mininet()
    reordercmd = f'tc qdisc change dev h3-eth0 parent 5:1 handle 10:0 netem delay 100ms reorder {reorder_tc_prob}% 50%'
    # reordercmd = f'sudo tc qdisc change dev h3-eth0 parent 5:1 handle 10:0 netem gap 0 reorder {reorder_tc_prob}% delay 3ms'
    
    print(reordercmd)
    print(mn_net.h3.cmd(reordercmd))
    print(mn_net.h3.cmd('tc qdisc show dev h3-eth0'))
    mn_net.disable_tso()
    # input()
    # mn_net.stop_mininet()
    # exit()
    # mn_net.start_tcpdump(result_save_path=mn_net.workingdir)
    # if loss > 0:
    #     mn_net.set_iptables_prob_packet_loss(percentage=loss/10000)

    # mn_net.start_iperf_size(durition_time=20)
    mn_net.start_iperf_time_json(durition_time=10)

    mn_net.wait_until_iperf_end()
    # mn_net.kill_tcpdump()
    # input()
    time.sleep(5)
    mn_net.stop_mininet()
    mn_net.save_log()
    # mn_net.return_top_folder()

    # files = os.listdir(mn_net.workingdir)
    # for item in files:
    #     if cca in item and item.endswith("name.txt"):
    #         filename = item
    # fc=Mininet_testbed.analyze.fs_compare.fs_compare_class(folder = mn_net.workingdir, filename=filename)
    # first_data_send_time = fc.generate()
    # print("first_data_send_time",first_data_send_time)
    # print('Began parse printk',datetime.now())
    # fc.parse_printk(first_data_send_time)
    # # print('Began parse_printk_fs_old_method',datetime.now())
    # # fc.parse_printk_fs_old_method(first_data_send_time)

    # print('Began parse_receiver_tcpdump',datetime.now())
    # fc.parse_receiver_tcpdump()
    # print('Began parse_sender_tcpdump',datetime.now())
    # fc.parse_sender_tcpdump()
    # tp_first_data_send_time = fc.merge_tcpdump_and_get_send_time()
    # print("first_data_send_time",tp_first_data_send_time)
    # fc.change_tcpdump_df_time(tp_first_data_send_time)

    # print('Began cal_FlightSize_new',datetime.now())
    # fc.cal_FlightSize_new()

    # fc.Downgrade_resolution()
    # print('Began fs_Lin_tp_printk',datetime.now())
    # fc.fs_Lin_tp_printk()

    # fc.diff_time(endtime=1.9)

    # fc.check_two_flightsize_results()
    # fc.draw_CWND()

    # average_E_tp, average_E_pk = Mininet_testbed.analyze.misc.calculat_E(os.path.join(fc.folder,'FlightSize_compare.csv'))
    # print(average_E_tp, average_E_pk)
    # return average_E_tp, average_E_pk


if __name__ == "__main__":
    for cca in ['bbr']:
        for rtt in [10]:
            for bw in [10]:
                for rate in [100]:
                    for run in range(1):
                        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                        now = datetime.now()
                        print(now)
                        dt_string = "bbr_"+ now.strftime("%Y-%m-%d-%Hh.%Mm.%Ss")
                        Reorder(cca=cca,rtt=rtt,bw=bw,reorder_percentage_in_10000=rate,reorder_distance=rtt/2)
                        exit()
    # os.system(f'sudo chown {Mininet_testbed.utils.config.USER} -R {Mininet_testbed.utils.config.ROOTDIR}')
