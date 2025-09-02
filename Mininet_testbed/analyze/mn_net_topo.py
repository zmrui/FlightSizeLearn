from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel, info
from mininet.cli import CLI
import os
import time
from decimal import *
import subprocess

# import Mininet_testbed.analyze.fs_compare
import Mininet_testbed.utils.config


TCPDUMP_PROC_1 = None
TCPDUMP_PROC_2 = None
TCPDUMP_PROC_1_CMD = "tcpdump -i h1-eth0 -S tcp dst port 5001 > %s/tcpdump_sender.txt &"
TCPDUMP_PROC_2_CMD = "tcpdump -i h2-eth0 -S tcp dst port 5001 > %s/tcpdump_receiver.txt &"
TCPDUMP_FFM_1_CMD = "tcpdump -i h1-eth0 -S tcp src port 5001 > %s/tcpdump_sender.txt &"
TCPDUMP_FFM_2_CMD = "tcpdump -i h2-eth0 -S tcp src port 5001 > %s/tcpdump_receiver.txt &"
# TCPDUMP_PROC_1_CMD = "tcpdump -S tcp dst port 5001 -G 30 "
# TCPDUMP_PROC_2_CMD = "tcpdump -S tcp dst port 5001 -G 30 "

def mkdirp( path ):
    try:
        os.makedirs( path,0o777 )
    except OSError:
        if not os.path.isdir( path ):
            raise
#My_Topo
#Finished
#Topo for mininet, 
# h1--major transmission, no action to packets, half RTT--h3, 
# h2--for packet drop and reorder---h3
class MyTopo( Topo ):
    def build( self, rtt, bw, maxq,loss=0 ):

        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')

        self.addLink(h1,h3,
                   bw=1000, loss=0,max_queue_size=10000, use_tbf = True)
        self.addLink(h2,h3,
                   bw=bw, delay='%dms'%(rtt//2), loss=loss,max_queue_size=maxq, use_tbf = True)
class MyLossTopo( Topo ):
    def build( self, rtt, bw, maxq, lossprob ):

        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')

        self.addLink(h1,h3,
                   bw=1000, delay='%fms'%(0.01), loss=lossprob,max_queue_size=10000)
        self.addLink(h2,h3,
                   bw=bw, delay='%dms'%(rtt//2), loss=0,max_queue_size=maxq)
# class MyReorderTopo( Topo ):
#     def build( self, rtt, bw, probability, correlation,reorder_distance,maxq):

#         h1 = self.addHost('h1')
#         h2 = self.addHost('h2')
#         h3 = self.addHost('h3')

#         reorder_string="reorder %f%%%%"%(probability)
#         print(reorder_string)
#         self.addLink(h1,h3,
#                    bw=1000, delay='%fms'%(reorder_distance), jitter=reorder_string, loss=0,max_queue_size=10000)
#         self.addLink(h2,h3,
#                    bw=bw, delay='1ms',loss=0,max_queue_size=maxq)
class MyReorderTopo( Topo ):
    def build( self, rtt, bw, probability, correlation,reorder_distance,maxq):

        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')

        self.addLink(h1,h3,
                   bw=1000, delay='1ms',loss=0,max_queue_size=10000)
        self.addLink(h2,h3,
                   bw=bw, delay='%dms'%(rtt//2), max_queue_size=maxq)
#start_mininet
#Finished
#set rtt, bandwidth, congestion control algorithm
class mn_network:
    def __init__(self,rtt=int,bw=int,cca=str,maxqsize=int,sub_folder=None,reorder=False,probability=None,loss_probility=None,correlation=None,reorder_distance=None,nameprefix="") -> None:
        
        self.rtt=rtt
        self.bw=bw
        self.cca=cca
        self.reorder=reorder

        self.probability=probability
        # 25 == 25% delay
        
        if self.probability:
            # self.reorder_tc_prob = self.probability
            self.reorder_tc_prob = 100.0 - self.probability
        # 25 == 25% send immedtly and 75% delay

        self.correlation=correlation
        self.reorder_distance=reorder_distance
        self.packet_drop_position_list=None
        self.packet_reorder_position_list=None
        self.maxqsize=maxqsize
        self.loss_probility = loss_probility
        self.name=str(rtt)+"ms_"+str(bw)+"Mbps_"+nameprefix+cca
        self.top_folder=os.getcwd()
        self.sub_folder=sub_folder
        # if sub_folder:
        #     self.sub_folder= os.path.join(self.top_folder,sub_folder) 
        # if sub_folder:
        #     if not os.path.exists(self.sub_folder):
        #         os.mkdir(self.sub_folder)
        #     os.chdir(self.sub_folder)

        if reorder:
            self.name=self.name+"_reorder_"+str(probability)+"%_"+str(reorder_distance)+"msdelay"

        self.iperf_start_time = None
        self.iperf_expected_end_time = None

        self.CWND_start = 90
        self.tso_enabled = True

        FILE_PATH = "/proc/kmsg"
        self.kmsg_file = open(FILE_PATH,"r")
        print("@","rtt="+str(rtt)+"ms","bw="+str(bw)+"Mbps","cca="+cca)
        self.startTime = time.time()

        self.focus_begin = 0
        self.focus_end = 0
    def get_name(self):
        return self.name

    def make_subfolder(self):
        if self.sub_folder:
            if not os.path.exists(self.sub_folder):
                os.makedirs(self.sub_folder)
        
        # self.workingdir = os.path.join(os.getcwd(),self.sub_folder)
        self.workingdir = self.sub_folder
        print("Working Dir:",self.workingdir)
        csv_path = self.sub_folder + "/csvs"
        mkdirp(csv_path)
    # def start_tcpdump(self,result_save_path:str):
    #     sendCmd
    #     global TCPDUMP_PROC_1
    #     global TCPDUMP_PROC_2
    #     tcpdump_cmd1 = TCPDUMP_PROC_1_CMD%(result_save_path)
    #     tcpdump_cmd2 = TCPDUMP_PROC_2_CMD%(result_save_path)
    #     print('[TCPDUMP_cmd1] ',tcpdump_cmd1)
    #     print(self.h1.cmd(tcpdump_cmd1))
    #     print('[TCPDUMP_cmd2] ',tcpdump_cmd2)
    #     print(self.h2.cmd(tcpdump_cmd2))
    def start_tcpdump(self,result_save_path:str):
        if os.path.isfile(os.path.join(result_save_path,'tcpdump_sender.txt')):
            os.remove(os.path.join(result_save_path,'tcpdump_sender.txt'))
        if os.path.isfile(os.path.join(result_save_path,'tcpdump_receiver.txt')):
            os.remove(os.path.join(result_save_path,'tcpdump_receiver.txt'))
        tcpdump_cmd1 = TCPDUMP_PROC_1_CMD%(result_save_path) # tcpdump -S tcp dst port 5001 > %s/tcpdump_sender.txt &s
        tcpdump_cmd2 = TCPDUMP_PROC_2_CMD%(result_save_path) # tcpdump -S tcp dst port 5001 > %s/tcpdump_receiver.txt &
        c1node = self.net.get('h1')
        print("Sending command '%s' to host %s" % (tcpdump_cmd1, 'h1(sender)'))
        c1node.cmd(tcpdump_cmd1)

        x1node = self.net.get('h2')
        print("Sending command '%s' to host %s" % (tcpdump_cmd2, 'h2(receiver)'))
        x1node.cmd(tcpdump_cmd2)

    def start_tcpdump_src(self,result_save_path:str):
        if os.path.isfile(os.path.join(result_save_path,'tcpdump_sender.txt')):
            os.remove(os.path.join(result_save_path,'tcpdump_sender.txt'))
        if os.path.isfile(os.path.join(result_save_path,'tcpdump_receiver.txt')):
            os.remove(os.path.join(result_save_path,'tcpdump_receiver.txt'))
        tcpdump_cmd1 = TCPDUMP_FFM_1_CMD%(result_save_path) # tcpdump -S tcp dst port 5001 > %s/tcpdump_sender.txt &s
        tcpdump_cmd2 = TCPDUMP_FFM_2_CMD%(result_save_path) # tcpdump -S tcp dst port 5001 > %s/tcpdump_receiver.txt &
        c1node = self.net.get('h1')
        print("Sending command '%s' to host %s" % (tcpdump_cmd1, 'h1(sender)'))
        c1node.cmd(tcpdump_cmd1)

        x1node = self.net.get('h2')
        print("Sending command '%s' to host %s" % (tcpdump_cmd2, 'h2(receiver)'))
        x1node.cmd(tcpdump_cmd2)

    def start_mininet(self):
        # if False:
        if self.reorder==True:
            topo = MyReorderTopo(rtt=self.rtt,bw=self.bw,probability=self.reorder_tc_prob,correlation=self.correlation,reorder_distance=self.reorder_distance,maxq=self.maxqsize)
        # elif self.loss_probility is not None:
        #     topo = MyLossTopo(rtt=self.rtt,bw=self.bw,maxq=self.maxqsize, lossprob=self.loss_probility)
        else:
            topo = MyTopo(rtt=self.rtt,bw=self.bw,maxq=self.maxqsize,loss=self.loss_probility)

        net = Mininet( topo=topo, link=TCLink)
                    # host=CPULimitedHost, link=TCLink, xterms=True,
                    # autoStaticArp=True)    

        net.start()
        h1, h2, h3 = net.getNodeByName('h1', 'h2', 'h3')

        h1eth0 = h1.intf("h1-eth0")
        h1eth0.setIP("192.168.0.1/24")
        h1.cmd("route add -net 10.0.0.0/24 dev h1-eth0 gw 192.168.0.3")

        h2eth0 = h2.intf("h2-eth0")
        h2eth0.setIP("10.0.0.2/24")
        h2.cmd("route add -net 192.168.0.0/24 dev h2-eth0 gw 10.0.0.3")


        h3eth0 = h3.intf("h3-eth0")
        h3eth0.setIP("192.168.0.3/24")
        h3eth1 = h3.intf("h3-eth1")
        h3eth1.setIP("10.0.0.3/24")

        h1.cmd("sysctl net.ipv4.tcp_congestion_control=%s"%(self.cca))
        h1.cmd("sysctl -p")
        h3.cmd("sysctl -p")
        
        print("@ start mininet: %s"%(time.time()-self.startTime))
        self.net=net
        self.h1=h1
        self.h2=h2
        self.h3=h3
        return net,h1,h2,h3

    def stop_mininet(self):
        print("@ stop mininet")
        with open(os.path.join(self.workingdir,self.name+'_name.txt'),'w') as f:
            f.write(self.name)
        self.net.stop()
    def start_iperf_time(self,durition_time:int):
        self.durition_time = durition_time + 1
        time.sleep(2)
        os.system("dmesg -c > /dev/null")
        self.h2.cmd("iperf -s &")
        self.h1.cmd("iperf -c 10.0.0.2 -t %d -i 1 >%siperflog.txt &"%(durition_time,self.name+"_"))
        self.iperflogname = self.name+"_iperflog.txt"
        self.iperf_start_time = time.time()
        self.iperf_expected_end_time = self.iperf_start_time + self.durition_time
        print("@ iperf started for %d seconds :%s"%(durition_time,time.time()-self.startTime))
    def start_iperf_size(self,durition_time:int):
        self.durition_time = durition_time
        time.sleep(2)
        os.system("dmesg -c > /dev/null")
        self.h2.cmd("iperf -s &")
        self.h1.cmd("iperf -c 10.0.0.2 -n 100M -i 1 >%siperflog &"%(self.name+"_"))
        self.iperflogname = self.name+"_iperflog"
        self.iperf_start_time = time.time()
        self.iperf_expected_end_time = self.iperf_start_time + durition_time
        print("@ iperf started for %d seconds :%s"%(durition_time,time.time()-self.startTime))

    def start_iperf_time_json_back(self,durition_time:int, port=6000,cnt=None):
        self.durition_time = durition_time + 1
        time.sleep(2)

        self.h2.cmd("iperf3 -s -p %d  -1 &"%(port))
        h1cmd="iperf3 -c 10.0.0.2 -p %d --congestion %s -t %d  &"%(port,'cubic',durition_time)
        self.h1.cmd(h1cmd)
        print('[h1]:',h1cmd)

    def dynamich3(self,simulation,condition):
        h3cmd = f'{Mininet_testbed.utils.config.ROOTDIR}/h3eth1_cellular_emulation.sh {simulation} {condition} > h3eth1log &'
        self.h3.cmd(h3cmd)
    def dynamich2(self,simulation,condition):
        h2cmd = f'{Mininet_testbed.utils.config.ROOTDIR}/h2eth0_cellular_emulation.sh {simulation} {condition} > h2eth0log &'
        self.h2.cmd(h2cmd)

        
    def start_iperf_time_json(self,durition_time:int, port=5001,cnt=None):
        self.durition_time = durition_time + 1
        time.sleep(2)
        os.system("dmesg -c > /dev/null")
        self.iperflogpath = os.path.join(self.workingdir,self.name+"_iperflog")
        self.receiver_iperflogpath = os.path.join(self.workingdir,self.name+"_iperflog_receiver")
        if os.path.isfile(self.iperflogpath):
            os.remove(self.iperflogpath)
        if os.path.isfile(self.receiver_iperflogpath):
            os.remove(self.receiver_iperflogpath)
        self.h2.cmd("iperf3 -s -p %d -i 1 --json --logfile %s -1 &"%(port,self.receiver_iperflogpath))
        if cnt:
            h1cmd="iperf3 -c 10.0.0.2 -p %d --congestion %s -k %d -f m -i 1 --json --logfile %s &"%(port,self.cca,cnt,self.iperflogpath)
        else:
            h1cmd="iperf3 -c 10.0.0.2 -p %d --congestion %s -t %d -f m -i 1 --json --logfile %s &"%(port,self.cca,durition_time,self.iperflogpath)
        self.h1.cmd(h1cmd)
        print('[h1]:',h1cmd)
        self.iperf_start_time = time.time()
        self.iperf_expected_end_time = self.iperf_start_time + self.durition_time
        print("@ iperf started for %d seconds :%s"%(durition_time,time.time()-self.startTime))
        return "10.0.0.2:5201"

    def save_log(self,altname=None):
        self.name = self.name+"_dmesg.txt"
        if altname is None:
            os.system("dmesg > %s"%(os.path.join(self.workingdir,self.name)))
            print("@ save log to => ",os.path.join(self.workingdir,self.name))
        else:
            os.system("dmesg > %s"%(os.path.join(self.workingdir,altname)))
        
        # os.system("chmod 664 dmesg*")
    # def return_top_folder(self):
    #     if self.sub_folder:
    #         os.chdir(self.top_folder)
    def disable_tso(self):
        self.tso_enabled = False
        self.h1.cmd("ethtool -K h1-eth0 tx off sg off tso off gso off")
        self.h2.cmd("ethtool -K h2-eth0 tx off sg off tso off gso off")
        self.h3.cmd("ethtool -K h3-eth0 tx off sg off tso off gso off")
        self.h3.cmd("ethtool -K h3-eth1 tx off sg off tso off gso off")
        # print(self.h3.cmd("wireshark &"))
        
    def wait_until_iperf_end(self):
        print("@ wait until iperf ends...")
        while(True):
            if time.time() < self.iperf_expected_end_time:
                time.sleep(5)
            else:
                # print("@ iperf end...:%s"%(time.time()-self.startTime))
                # self.h1.cmd("mv %s %s"%(self.iperflogname, self.name+"_iperflog"))
                # self.iperflogname=self.name+"_iperflog"
                return
        
    def set_reorder(self):
        return
        result=self.h3.cmd("tc qdisc change dev h3-eth1 parent 5:1 handle 10: netem delay 100ms reorder 25%%%% 50%%%% ")
        print("result:",result)

    def wait_until_enough_cwnd(self,CWND_start=90):
        print("@ wait until cwnd greater than ",str(CWND_start),"...")
        if self.reorder == True:
            self.CWND_start = CWND_start
        while True:
            string = self.kmsg_file.readline().replace("<4>","")
            if "CWND" in string:
                cwnd,ssthresh = analyze.fs_compare.get_cwnd(string)
                if cwnd >= self.CWND_start:
                    break
        print("@ cwnd greater than ",str(self.CWND_start))
    def set_tc_packet_loss(self,percentage):
        print("@set tc packets dropping rules")
        tcline='tc qdisc change dev h3-eth0  parent 5:1 handle 10: netem delay 0.1ms loss %.2f limit 10000'%(percentage)
        print(tcline)
        print("review:",self.h3.cmd('tc qdisc show dev h3-eth0'))
        print("result:",self.h3.cmd(tcline))
        print("review:",self.h3.cmd('tc qdisc show dev h3-eth0'))

    def set_iptables_prob_packet_loss(self,percentage):
        self.packet_drop_position_list = [0]
        print("Droppping probility is",percentage)
        iptline='''iptables -A FORWARD -p tcp --dport 5001 -m statistic --mode random --probability %.4f -j DROP'''%(percentage)
        print(iptline,"\nresult:",self.h3.cmd(iptline))


    def set_packet_loss(self):
        print("@set packets dropping rules")
        self.name = self.name+"_packetloss1"
        first_drop_seq = None
        while True:
            string = self.kmsg_file.readline().replace("<4>","")
            if "sender_send_pkt" in string:
                seq, data_len = analyze.fs_compare.sender(string)
                first_drop_seq = seq
                break
        hex_seq = hex(first_drop_seq)

        iptables_drop_string ='''iptables -A FORWARD -p tcp --dport 5001 -m u32 --u32 \"24=%s\" -m statistic --mode nth --every 9999999 --packet %d -j DROP'''%(str(hex_seq),0)
        print(iptables_drop_string,"\nresult:",self.h3.cmd(iptables_drop_string))
        print("set packets dropping rules")
        
    def set_packet_loss_type2(self):
        self.name = self.name+"_packetloss2"
        iptables_drop_string ='''iptables -A FORWARD -p tcp --dport 5001 -m statistic --mode nth --every 9999999 --packet 0 -j DROP'''
        print(iptables_drop_string,"\nresult:",self.h3.cmd(iptables_drop_string))
    def set_multiple_packet_loss(self,packet_drop_position_list):
        self.packet_drop_position_list=packet_drop_position_list
        FILE_PATH = "/proc/kmsg"
        temp_kmsg_file = open(FILE_PATH,"r")
        positions_str = ""
        for item in packet_drop_position_list:
            positions_str=positions_str+str(item)+"_"
        print("@@ set_multiple_packet_loss for ",str(len(packet_drop_position_list)))
        self.name = self.name+"_for"+str(len(packet_drop_position_list))
        last_line = None
        
        iptables_list = []
        self.undo_iptables_list = []
        for i in packet_drop_position_list:
            iptables_string = '''iptables -A FORWARD --dst 10.0.0.2 -p tcp --dport 5001 -m statistic --mode nth --every 99999 --packet %d -j DROP'''%(i)
            iptables_list.append(iptables_string)
            self.undo_iptables_list.append(iptables_string.replace('-A','-D'))
        for line in iptables_list:    
            if last_line is None:
                last_line =temp_kmsg_file.readline()
            print(line,"\nresult:",self.h3.cmd(line))
            
        print("last line ",last_line)
    def set_multiple_packet_loss_925new(self,packet_drop_position_list):
        self.packet_drop_position_list=packet_drop_position_list
        FILE_PATH = "/proc/kmsg"
        # temp_kmsg_file = open(FILE_PATH,"r")
        positions_str = ""
        # for item in packet_drop_position_list:
        #     positions_str=positions_str+str(item)+"_"
        print("@@ set_multiple_packet_loss for ",str(len(packet_drop_position_list)))
        self.name = self.name+"_for"+str(len(packet_drop_position_list))
        # last_line = None
        first_drop_seq = None
        while True:
            string = self.kmsg_file.readline().replace("<4>","")
            if "ssp" in string:
                seq, data_len = analyze.fs_compare.sender(string)
                first_drop_seq = seq
                break

        drop_hex_seq_list = []
        for i in self.packet_drop_position_list:
            drop_seq = first_drop_seq+int(1448*i)
            drop_hex_seq = hex(drop_seq)
            drop_hex_seq_list.append(drop_hex_seq)
            
        # self.undo_iptables_list=[]
        # for drop_hex_seq in drop_hex_seq_list:
        #     iptables_drop_string ='''iptables -A INPUT -p tcp --dport 5001 -m u32 --u32 \"24=%s\" -j DROP'''%(str(hex_seq))
        #     print(iptables_drop_string,"\nresult:",self.h2.cmd(iptables_drop_string))
        #     self.undo_iptables_list.append(iptables_drop_string.replace("-A",'-D'))
        # # iptables_drop_string ='''iptables -A FORWARD -p tcp --dport 5001 -m u32 --u32 \"24=%s\" -j DROP'''%(str(hex_seq))
        # # print(iptables_drop_string,"\nresult:",self.h3.cmd(iptables_drop_string))

        "-m statistic --mode nth --every 99999999 --packet 0 "
        iptables_list = []
        self.undo_iptables_list = []
        for drop_hex_seq in drop_hex_seq_list:
            iptables_drop_string ='''iptables -A INPUT -p tcp --dport 5001 -m u32 --u32 \"24=%s\" -m statistic --mode nth --every 999 --packet 0 -j DROP'''%(str(drop_hex_seq))
            print(iptables_drop_string,"\nresult:",self.h2.cmd(iptables_drop_string))
            # iptables_list.append(iptables_drop_string)
            # self.undo_iptables_list.append(iptables_drop_string.replace('-A','-D'))
        # for line in iptables_list:    
        #     # if last_line is None:
        #     #     last_line =temp_kmsg_file.readline()
        #     print(line,"\nresult:",self.h2.cmd(line))
            
        # print("last line ",last_line)
    def unset_multiple_packet_loss(self):
        for iptableline in self.undo_iptables_list:
            print(iptableline,"\nresult:",self.h3.cmd(iptableline))
    def drop_every_x_packets(self,x:int):
        self.name = self.name+"_drop_every_"+str(x)+"_packets"
        iptables_drop_string ='''iptables -A FORWARD -p tcp --dport 5001 -m statistic --mode nth --every %d --packet 0 -j DROP'''%(x)
        print(iptables_drop_string,"\nresult:",self.h3.cmd(iptables_drop_string))
        print("@@ set packet loss every %d packets"%(x))
    def add_reorder_htb(self,packet_reorder_position_list):
        self.packet_reorder_position_list=packet_reorder_position_list
        print("@ sub HTBs rules:")
        #5:2
        h3_add_htb_class="tc class add dev h3-eth1 parent 5:0 classid 5:2 htb rate %dMbit burst 15k"%(self.bw)
        h3_add_netem="tc qdisc add dev h3-eth1 parent 5:2 handle 52: netem delay %sms"%str(int(self.reorder_distance))
        h3_add_filter_to52_at_parent5_0="tc filter add dev h3-eth1 parent 5:0 protocol ip prio 1 handle 52 fw flowid 5:2"
        print(h3_add_htb_class,self.h3.cmd(h3_add_htb_class))
        print(h3_add_netem,self.h3.cmd(h3_add_netem))
        print(h3_add_filter_to52_at_parent5_0,self.h3.cmd(h3_add_filter_to52_at_parent5_0))

        print("@ sub HTBs added: %s"%(time.time()-self.startTime))
    def set_new_reorder(self):
        self.name=self.name+"_new_reorder"
        print("@ ruels:")
        iptables_forward_set_mark="iptables -t mangle -I FORWARD -d 10.0.0.2  -j MARK --set-mark %d"%(52)
        # iptables_forward_set_mark="iptables -t mangle -I FORWARD -d 10.0.0.2 -j DROP"
        print(iptables_forward_set_mark,"\n result:",self.h3.cmd(iptables_forward_set_mark))
        # for i in self.packet_reorder_position_list:
        #     iptables_forward_set_mark="iptables -t mangle -I FORWARD -d 10.0.0.2 -m statistic --mode nth --every 99999999 --packet %d -j MARK --set-mark %d"%(i,52)
        #     print(iptables_forward_set_mark,"\n result:",self.h3.cmd(iptables_forward_set_mark))


        print("@ ACK delay ruels added")
        self.focus_begin = time.time()-self.startTime

    def add_ack_delay(self):
        print("@ sub HTBs rules:")
        #5:2
        h3_add_htb_class="tc class add dev h3-eth0 parent 5:0 classid 5:2 htb rate %dMbit burst 15k"%(self.bw)
        if self.rtt>100:
            h3_add_netem="tc qdisc add dev h3-eth0 parent 5:2 handle 52: netem delay %s"%str(int(self.rtt*4))+"ms"
        else:
            h3_add_netem="tc qdisc add dev h3-eth0 parent 5:2 handle 52: netem delay %s"%str(3000)+"ms"
        h3_add_filter_to52_at_parent5_0="tc filter add dev h3-eth0 parent 5:0 protocol ip prio 1 handle 52 fw flowid 5:2"
        print(h3_add_htb_class,self.h3.cmd(h3_add_htb_class))
        print(h3_add_netem,self.h3.cmd(h3_add_netem))
        print(h3_add_filter_to52_at_parent5_0,self.h3.cmd(h3_add_filter_to52_at_parent5_0))

        #5:3
        h3_add_htb_class="tc class add dev h3-eth0 parent 5:0 classid 5:3 htb rate %dMbit burst 15k"%(self.bw)
        if self.rtt>100:
            h3_add_netem="tc qdisc add dev h3-eth0 parent 5:3 handle 53: netem delay %s"%str(int(self.rtt*8))+"ms"
        else:
            h3_add_netem="tc qdisc add dev h3-eth0 parent 5:3 handle 53: netem delay %s"%str(6000)+"ms"
        h3_add_filter_to52_at_parent5_0="tc filter add dev h3-eth0 parent 5:0 protocol ip prio 1 handle 53 fw flowid 5:3"
        print(h3_add_htb_class,self.h3.cmd(h3_add_htb_class))
        print(h3_add_netem,self.h3.cmd(h3_add_netem))
        print(h3_add_filter_to52_at_parent5_0,self.h3.cmd(h3_add_filter_to52_at_parent5_0))

        print("@ sub HTBs added: %s"%(time.time()-self.startTime))
    def set_ack_delay(self):
        self.name=self.name+"_ackdelay"
        print("@ ACK delay ruels:")
        self.iptables_undo=[]
        iptables_forward_set_mark="iptables -t mangle -I FORWARD -s 10.0.0.2 -m statistic --mode nth --every 99999999 --packet 0 -j MARK --set-mark %d"%(52)
        print(iptables_forward_set_mark,"\n result:",self.h3.cmd(iptables_forward_set_mark))
        self.iptables_undo.append(iptables_forward_set_mark.replace("-I","-D"))
        iptables_forward_set_mark="iptables -t mangle -I FORWARD -s 10.0.0.2 -j MARK --set-mark %d"%(53)
        print(iptables_forward_set_mark,"\n result:",self.h3.cmd(iptables_forward_set_mark))
        self.iptables_undo.append(iptables_forward_set_mark.replace("-I","-D"))
        print("@ ACK delay ruels added")
        self.focus_begin = time.time()-self.startTime
    def unset_ack_delay(self):
        for rule in self.iptables_undo:
            print(rule,"\n \t result:",self.h3.cmd(rule))
        print("@ unset all ACK delaying rules")
    def wait_until_enter_loss(self,check_time_out=False):
        print("@ wait until TCP sender enter loss state...")
        string = ""
        while True:
            current_time= time.time()
            if check_time_out:
                if current_time > self.iperf_expected_end_time:
                    print("@ timeout, exit")
                    if(input("save log? y/n")=="y"):
                        self.save_log()
                    exit()
            string = self.kmsg_file.readline().replace("<4>","")
            if "scas] 4" in string:
                self.focus_begin = Decimal(string.split('] [')[0][1:])
                break
        print("@ TCP sender entered loss state")
    def set_packet_drop(self,times=5):
        self.packet_drop_position_list = "timeout"
        print("@set packets dropping rules")
        self.name = self.name+"_packetdrop_for_one_sequence"
        first_drop_seq = 72400
        while True:
            string = self.kmsg_file.readline().replace("<4>","")
            if "ssp" in string:
                seq, data_len = analyze.fs_compare.sender(string)
                first_drop_seq = first_drop_seq + seq
                break
        hex_seq = hex(first_drop_seq)
        print(first_drop_seq,hex_seq)
        self.undo_iptables=[]
        # for i in range(times):
        #     iptables_drop_string ='''iptables -A FORWARD -p tcp --dport 5001 -m u32 --u32 \"24=%s\" -m statistic --mode nth --every 9999999 --packet %d -j DROP'''%(str(hex_seq),i)
        #     print(iptables_drop_string,"\nresult:",self.h3.cmd(iptables_drop_string))
        #     self.undo_iptables.append(iptables_drop_string.replace("-A",'-D'))
        iptables_drop_string ='''iptables -A FORWARD -p tcp --dport 5001 -m u32 --u32 \"24=%s\" -j DROP'''%(str(hex_seq))
        print(iptables_drop_string,"\nresult:",self.h3.cmd(iptables_drop_string))
        self.undo_iptables.append(iptables_drop_string.replace("-A",'-D'))
        print("set packets dropping rules",iptables_drop_string)

    def unset_packet_drop(self):
        for item in self.undo_iptables:
            print(item,"\nresult:",self.h3.cmd(item))
    def set_packet_drop_continuous(self):
        print("@set packets dropping rules")
        self.name = self.name+"_packetdrop_for_timeout"
        iptables_drop_string ='''iptables -A FORWARD -p tcp --dport 5001 -j DROP'''
        print(iptables_drop_string,"\nresult:",self.h3.cmd(iptables_drop_string))
        self.undo_iptables=[]
        self.undo_iptables.append(iptables_drop_string.replace("-A",'-D'))
        print("set packets dropping rules")
