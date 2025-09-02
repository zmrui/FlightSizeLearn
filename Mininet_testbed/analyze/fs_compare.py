# Real flightsize calculate by sending and receiving
from matplotlib import pyplot as plt
from decimal import *
import csv
import Mininet_testbed.analyze.mn_net_topo
import os
import json
import pandas as pd
from itertools import islice
from collections import Counter

def find_duplicates(lst):
    counts = Counter(lst)
    return [item for item, count in counts.items() if count > 1]

def comp_time(time1:str,time2:str):
    '20:19:03.971179'
    '20:19:08.984640'
    t1_list=time1.split(":")
    t1h=Decimal(t1_list[0])
    t1m=Decimal(t1_list[1])+t1h*60
    t1s=Decimal(t1_list[2])+t1m*60
    try:
        t2_list=time2.split(":")
        t2h=Decimal(int(t2_list[0]))
        t2m=Decimal(int(t2_list[1]))+t2h*60
        t2s=Decimal(t2_list[2])+t2m*60
    except:
        print("exception processing time")
        print(time2)
        print(t2_list)
        return None
    return (t2s - t1s)

def get_kernel_time(string):
    try:
        kerneltime = Decimal(string.split('] [')[0][1:])
    except:
        print(string)
        # exit()
    return kerneltime
#example input:[319647.788661] [sendertpinfo] reordering:3 reord_seen:0 segs_out:29 app_limited:0 lost:0 
def senderinfo(string):
    string = string.split("o] ")[1]
    segs = string.split(" ")
    reordering = int(segs[0][11:])
    data_lereord_seenn = int(segs[1][11:])
    segs_out = int(segs[2][9:])
    app_limited = int(segs[3][12:])
    lost = int(segs[4][5:])
    return reordering, data_lereord_seenn,segs_out,app_limited,lost

def sender(string):
    # example input: [ 1758.520750] [sender_send_pkt] seq:2621048322 data_len:0

    string = string.split("p] ")[1]
    segs = string.split(" ")
    seq = int(segs[0])
    data_len = int(segs[1])
    return seq, data_len

def fwp(string):
    # example input: [  377.414821] [rrp] 3004163115 0 1480

    string = string.split("p] ")[1]
    segs = string.split(" ")
    seq = int(segs[0])
    data_len = int(segs[1])
    len = int(segs[2])
    return seq, data_len,len

def receiver(string):
    # example input: [  377.414821] [rrp] 3004163115 0 1480

    string = string.split("p] ")[1]
    segs = string.split(" ")
    seq = int(segs[0])
    data_len = int(segs[1])
    len = int(segs[2])
    return seq, data_len,len

def get_cwnd(string):
    #example input: [78588.013651] [sender_CWND] snd_cwnd:1 snd_ssthresh:7
    string = string.split("D] ")[1]
    segs = string.split(" ")

    cwnd = int(segs[0])
    ssthresh = int(segs[1])
    # print(cwnd,ssthresh)
    return cwnd,ssthresh

def ca_state(string):
    # example input: [ 1759.538884] [tcp_ca_state] 4
    segs = string.split(' ')
    ca = int(segs[-1])
    return ca

def get_flightsize(string):
    #exmaple input: [ 1758.520760] [sender_flightsize] packets_out:1 retrans_out:0 sacked_out:0 lost_out:0
    
    string = string.split("sf] ")[1]
    segs = string.split(" ")

    packets_out = int(segs[0])
    retrans_out = int(segs[1])
    sacked_out = int(segs[2])
    lost_out = int(segs[3])

    flightsize = packets_out + retrans_out - sacked_out - lost_out
    return flightsize,packets_out,retrans_out,sacked_out,lost_out

class fs_compare_class:
    def __init__(self,filename,folder,focus_begin=0,focus_end=0) -> None:
        self.top_folder = os.getcwd()
        os.chdir(folder)
        self.filename=filename
        self.folder = folder
        self.title = self.filename.split('_name.')[0]
        self.filename=self.filename.replace("_name.txt",'')
        self.dmesgfile = self.filename + "_dmesg.txt"

        self.senderiperflogpath = os.path.join(self.title+"_iperflog")
        self.receiveriperflogpath = os.path.join(self.title+"_iperflog_receiver")

        self.draw_begin = focus_begin
        self.draw_end = 0
        self.focus_end = focus_end
        self.focus_begin = focus_begin

        self.rtt = 10
        self.sender_df_list = []
        self.average_rtt_list = []

    def parse_sender_tcpdump(self):
        with open(os.path.join(self.folder,'tcpdump_sender.txt'), "r") as fid:
            lines = fid.readlines()
        dfdata = []
        for line in lines:
            if 'seq' in line:
                segs = line.split(', ')
                tcpdumptime = segs[0].split(' ')[0]
                sequence = segs[1].split(':')[0].replace('seq ','')
                for seg in segs:
                    if 'options' in seg:
                        option = seg
                options = option.split(',')
                for op in options:
                    if 'TS' in op:
                        ts = op
                tsval = int(ts.split('ecr')[0].replace('TS val',''))
                tsecr = int(ts.split('ecr')[1].replace(']',''))
                length = int(segs[-1].replace('length',''))
                item = []
                item.append(tcpdumptime)
                item.append('SEND')
                item.append(sequence)
                item.append(tsval)
                item.append(tsecr)
                item.append(length)
                dfdata.append(item)
        df = pd.DataFrame(dfdata,columns=['Time', 'Operation', 'Sequence', 'TSval', 'TSecr','Length'])
        df['Sequence'] = df['Sequence'].astype(int)
        df['TSval'] = df['TSval'].astype(int)
        df['TSecr'] = df['TSecr'].astype(int)
        df['Length'] = df['Length'].astype(int)
        self.sender_tcpdump_df = df.copy()
        df.to_csv(os.path.join(self.folder,'csvs','tcpdump_sender.csv'), index=False)
        return df
    def Downgrade_resolution2(self):
        self.LinFlightsizedf_bk = self.LinFlightsizedf.copy()
        self.FlightSize_df_method2_bk = self.FlightSize_df_method2.copy()

        for idx, row in self.LinFlightsizedf.iterrows():
            dgtime = row['Time']
            dgtime = round(dgtime,4)
            self.LinFlightsizedf.at[idx,'Time'] = dgtime
        self.LinFlightsizedf.to_csv(os.path.join(self.folder,'csvs','Final_LinFS.csv'), index=False)

        for idx, row in self.FlightSize_df_method2.iterrows():
            dgtime = row['Time']
            dgtime = round(dgtime,4)
            self.FlightSize_df_method2.at[idx,'Time'] = dgtime
        self.FlightSize_df_method2.to_csv(os.path.join(self.folder,'csvs','Final_TcpdumpsFS.csv'), index=False)
    def Downgrade_resolution(self):
        self.LinFlightsizedf_bk = self.LinFlightsizedf.copy()
        self.OldFlightsize_timefrom0_df_bk = self.OldFlightsize_timefrom0_df.copy()
        self.FlightSize_df_method2_bk = self.FlightSize_df_method2.copy()

        # for idx, row in self.LinFlightsizedf.iterrows():
        #     dgtime = row['Time']
        #     dgtime = round(dgtime,4)
        #     self.LinFlightsizedf.at[idx,'Time'] = dgtime
        # self.LinFlightsizedf.to_csv(os.path.join(self.folder,'csvs','Final_LinFS.csv'), index=False)

        # for idx, row in self.OldFlightsize_timefrom0_df.iterrows():
        #     dgtime = row['Time']
        #     dgtime = round(dgtime,4)
        #     self.OldFlightsize_timefrom0_df.at[idx,'Time'] = dgtime
        # self.OldFlightsize_timefrom0_df.to_csv(os.path.join(self.folder,'csvs','Final_PrintKFS.csv'), index=False)
        # for idx, row in self.FlightSize_df_method2.iterrows():
        #     dgtime = row['Time']
        #     dgtime = round(dgtime,4)
        #     self.FlightSize_df_method2.at[idx,'Time'] = dgtime
        # self.FlightSize_df_method2.to_csv(os.path.join(self.folder,'csvs','Final_TcpdumpsFS.csv'), index=False)

    def fs_Lin_tp_printk(self):
        df_lin = self.LinFlightsizedf_bk.copy()
        df_lin = df_lin[df_lin['Time'] >= 0]
        df_printk = self.OldFlightsize_timefrom0_df_bk.copy()
        df_printk = df_printk[df_printk['Time'] >= 0]
        df_tcpdump = self.FlightSize_df_method2_bk.copy()
        df_tcpdump = df_tcpdump[df_tcpdump['Time'] >= 0]
        plt.clf()
        plt.plot(df_lin['Time'].tolist(),df_lin['LinuxFlightSize'].tolist(),label="Linux FS")
        plt.plot(df_printk['Time'].tolist(),df_printk['AccurateFlightSize1'].tolist(),label="AccurateFlightSize1") 
        plt.plot(df_tcpdump['Time'].tolist(),df_tcpdump['FlightSizeMethod2'].tolist(),label="FlightSizeMethod2")
        plt.xlabel('time')
        plt.ylabel('flightsize')
        plt.grid()
        plt.legend()
        plt.savefig(os.path.join(self.folder,'fs_lin_tp.jpg'))

        plt.clf()
        plt.plot(df_lin['Time'].tolist(),df_lin['LinuxFlightSize'].tolist(),label="Linux FS")
        plt.xlabel('time')
        plt.ylabel('flightsize')
        plt.grid()
        plt.legend()
        plt.savefig(os.path.join(self.folder,'fs_lin.jpg'))

        plt.clf()
        plt.plot(df_printk['Time'].tolist(),df_printk['AccurateFlightSize1'].tolist(),label="AccurateFlightSize1") 
        plt.xlabel('time')
        plt.ylabel('flightsize')
        plt.grid()
        plt.legend()
        plt.savefig(os.path.join(self.folder,'fs_printk.jpg'))

        plt.clf()
        plt.plot(df_tcpdump['Time'].tolist(),df_tcpdump['FlightSizeMethod2'].tolist(),label="FlightSizeMethod2")
        plt.xlabel('time')
        plt.ylabel('flightsize')
        plt.grid()
        plt.legend()
        plt.savefig(os.path.join(self.folder,'fs_tp.jpg'))
        # print("In Fs Compare")
        dfdata = []
        # for it in range(len(self.LinFlightsizedf)):
        index2 = 0
        index3 = 0
        lindflength = len(self.LinFlightsizedf)
        
        dfit2 = list(self.FlightSize_df_method2.iterrows())
        dfit3 = list(self.OldFlightsize_timefrom0_df.iterrows())
        # last_time = 0
        for idx, row in self.LinFlightsizedf.iterrows():
            
            if idx % 1000 == 0:
                print(f"{idx}/{lindflength}")

            t1 = row["Time"]

            if float(t1)<0:
                continue
            # if last_time + 0.032 > float(t1):
            #     continue
            # last_time = float(t1)
            # if float(t1)>18:
            #     break

            
            for idx2, row2 in islice(dfit2, index2, None):
                t2 = row2["Time"]
                if t2 > t1:
                    break
                index2 = max(0,idx2-5)
                tpfs = row2['FlightSizeMethod2']

            for idx3, row3 in islice(dfit3, index3, None):
                t3 = row3["Time"]
                if t3 > t1:
                    break
                index3 = max(idx3-5,0)
                printkfs = row3['AccurateFlightSize1']

            item = []
            timepoint = t1

            lfs = row['LinuxFlightSize']
            item.append(timepoint)
            item.append(printkfs)
            item.append(tpfs)
            item.append(lfs)
            # print(item)
            dfdata.append(item)
        df = pd.DataFrame(dfdata,columns=['Time', 'FlightSizePrintK','FlightSizeTP', 'LinuxFlightSize'])
        df['Time'] = df['Time']
        df['FlightSizeTP'] = df['FlightSizeTP'].astype(int)
        df['LinuxFlightSize'] = df['LinuxFlightSize'].astype(int)
        df.to_csv(os.path.join(self.folder,'FlightSize_compare.csv'), index=False)
        self.LinTPFlightsizedf = df.copy()
        # print("end Fs Compare")
        return df
    def draw_CWND(self):

        plt.clf()   

        # plt.plot(self.resultdf['time'].to_list(),self.resultdf['cwnd'].to_list(),label="CWND")
        plt.scatter(self.x_CWND_time_list,self.y_CWND_value_list,label="CWND",c='b',s=1)

        plt.xlabel("time second(s)")
        plt.ylabel("CWND value")
        plt.title(self.filename)
        plt.grid()
        plt.legend()
        plt.savefig(self.filename+"_cwnd.jpg")
        print("@ save graph to => ",self.filename+"_cwnd.jpg")
    def fs_Lin_tp(self,stoptime):
        plt.clf()
        plt.plot(self.LinFlightsizedf_bk['Time'].tolist(),self.LinFlightsizedf_bk['LinuxFlightSize'].tolist(),label="Linux FS")
        plt.plot(self.FlightSize_df_method2_bk['Time'].tolist(),self.FlightSize_df_method2_bk['FlightSizeMethod2'].tolist(),label="FlightSizeMethod2")
        plt.xlabel('time')
        plt.ylabel('flightsize')
        plt.grid()
        plt.legend()
        plt.savefig(os.path.join(self.folder,'fs_lin_tp.jpg'))

        plt.clf()
        plt.plot(self.LinFlightsizedf_bk['Time'].tolist(),self.LinFlightsizedf_bk['LinuxFlightSize'].tolist(),label="Linux FS")
        plt.xlabel('time')
        plt.ylabel('flightsize')
        plt.grid()
        plt.legend()
        plt.savefig(os.path.join(self.folder,'fs_lin.jpg'))


        plt.clf()
        plt.plot(self.FlightSize_df_method2_bk['Time'].tolist(),self.FlightSize_df_method2_bk['FlightSizeMethod2'].tolist(),label="FlightSizeMethod2")
        plt.xlabel('time')
        plt.ylabel('flightsize')
        plt.grid()
        plt.legend()
        plt.savefig(os.path.join(self.folder,'fs_tp.jpg'))
        # print("In Fs Compare")
        dfdata = []
        # for it in range(len(self.LinFlightsizedf)):
        index2 = 0

        lindflength = len(self.LinFlightsizedf)
        
        dfit2 = list(self.FlightSize_df_method2.iterrows())

        for idx, row in self.LinFlightsizedf.iterrows():
            
            if idx % 1000 == 0:
                print(f"{idx}/{lindflength}")
            # t1=self.x_Linux_FLIGHTSIZE_time_list[it]
            t1 = row["Time"]
            # print("In {}".format(t1))
            if float(t1)<0:
                continue
            if float(t1)>stoptime:
                break
            # for it2 in range(len(self.x_My_FLIGHTSIZE_time_list)):
            
            for idx2, row2 in islice(dfit2, index2, None):
            # for idx2, row2 in islice(self.FlightSize_df_method2.iterrows(), index2, None):
            # for idx2, row2 in self.FlightSize_df_method2.iterrows():
                t2 = row2["Time"]
                # print("have t2 {}".format(t2))
                if t2 > t1:
                    break
                index2 = max(0,idx2-5)
                tpfs = row2['FlightSizeMethod2']
                
            # tempdf = self.FlightSize_df_method2.query('Time <= {}'.format(float(t1)))
            # print(tempdf)
            # row2 = tempdf.iloc[-1]

            # tempdf2 = self.OldFlightsize_timefrom0_df.query('Time <= {}'.format(float(t1)))
            # row3 = tempdf2.iloc[-1]
            # print(t1,row['LinuxFlightSize'],row2)
            # exit()
            item = []
            timepoint = t1

            lfs = row['LinuxFlightSize']
            item.append(timepoint)
            item.append(tpfs)
            item.append(lfs)
            # print(item)
            dfdata.append(item)
        df = pd.DataFrame(dfdata,columns=['Time','FlightSizeTP', 'LinuxFlightSize'])
        df.to_csv(os.path.join(self.folder,'FlightSize_compare.csv'), index=False)
        self.LinTPFlightsizedf = df.copy()
        # print("end Fs Compare")
        return df

    def merge_tcpdump_and_get_send_time(self):
        self.tcpdump_df = pd.concat([self.receiver_tcpdump_df,self.sender_tcpdump_df])
        self.tcpdump_df.reset_index(drop=True,inplace=True)
        self.tcpdump_df.sort_values(by=['Time'],inplace=True,kind='stable')

        first_send_time = None
        for idx1, row1 in self.tcpdump_df.iterrows():
            operation = row1['Operation']
            sendtime = row1['Time']
            sendseq = row1['Sequence']
            TSval = row1['TSval']
            Length = row1['Length']
            if first_send_time is None:
                if Length> 200:
                    first_send_time = sendtime
                    return first_send_time
    def parse_receiver_tcpdump(self):
        with open(os.path.join(self.folder,'tcpdump_receiver.txt'), "r") as fid:
            lines = fid.readlines()
        dfdata = []
        for line in lines:
            if 'seq' in line:
                segs = line.split(', ')
                tcpdumptime = segs[0].split(' ')[0]
                sequence = segs[1].split(':')[0].replace('seq ','')
                for seg in segs:
                    if 'options' in seg:
                        option = seg
                options = option.split(',')
                for op in options:
                    if 'TS' in op:
                        ts = op
                tsval = int(ts.split('ecr')[0].replace('TS val',''))
                tsecr = int(ts.split('ecr')[1].replace(']',''))
                length = int(segs[-1].replace('length',''))
                item = []
                item.append(tcpdumptime)
                item.append('RECV')
                item.append(sequence)
                item.append(tsval)
                item.append(tsecr)
                item.append(length)
                dfdata.append(item)
        df = pd.DataFrame(dfdata,columns=['Time', 'Operation', 'Sequence', 'TSval', 'TSecr','Length'])
        df['Sequence'] = df['Sequence'].astype(int)
        df['TSval'] = df['TSval'].astype(int)
        df['TSecr'] = df['TSecr'].astype(int)
        df['Length'] = df['Length'].astype(int)
        df.to_csv(os.path.join(self.folder,'csvs','tcpdump_receiver.csv'), index=False)
        self.receiver_tcpdump_df = df.copy()
        return df

    def change_tcpdump_df_time(self,start_time):
        for idx, row in self.tcpdump_df.iterrows():
            timefield = row['Time']
            if start_time is None:
                start_time = timefield
            timefrom0 = comp_time(start_time, timefield)
            self.tcpdump_df.at[idx,'Time'] = timefrom0
        self.tcpdump_df['Time'] = self.tcpdump_df['Time']
        self.tcpdump_df.reset_index(drop=True,inplace=True)
        self.tcpdump_df.to_csv(os.path.join(self.folder,'csvs','tcpdump_all.csv'), index=False)
        self.tcpdump_df['seqkey'] = self.tcpdump_df['Sequence']
        self.tcpdump_df['tsvkey'] = self.tcpdump_df['TSval']
        self.tcpdump_df.set_index(['seqkey', 'tsvkey'],drop=True,inplace=True)
        # self.tcpdump_df.sort_index(inplace=True)
        self.tcpdump_df.to_csv(os.path.join(self.folder,'csvs','tcpdump_all_query.csv'), index=False)
    def cal_FlightSize_new(self):
        dfdata = []
        df2data = []
        flightsize = 0
        for idx1, row1 in self.tcpdump_df.iterrows():
            operation = row1['Operation']
            sendtime = row1['Time']
            sendseq = row1['Sequence']
            TSval = row1['TSval']
            Length = row1['Length']
            item = []
            item.append(sendtime)
            if Length>=480:
            # if True:
                if operation == "SEND":
                    tempdf = self.tcpdump_df.loc[(sendseq, TSval)]
                    rev_result = tempdf.query('Sequence == {} and TSval == {} and Length == {} and Operation == "{}"'.format(sendseq,TSval,Length,'RECV'))
                    snd_result = tempdf.query('Sequence == {} and TSval == {} and Length == {} and Operation == "{}"'.format(sendseq,TSval,Length,'SEND'))
                    num_send = len(snd_result)
                    num_recv = len(rev_result)
                    if num_recv == 0:
                        opitem = []
                        opitem.append(sendtime)
                        opitem.append(sendseq)
                        opitem.append('SEND-Loss')
                        opitem.append("--")
                        opitem.append(flightsize)
                        df2data.append(opitem)
                        
                        # print("Sequence {}, Tsval {}, Length {} was not received".format(sendseq,TSval,Length))
                    elif num_recv == 1:
                        flightsize += 1
                        opitem = []
                        opitem.append(sendtime)
                        opitem.append(sendseq)
                        opitem.append('SEND')
                        opitem.append("+1")
                        opitem.append(flightsize)
                        df2data.append(opitem)        
                    else:
                        print("Sequence {}, Tsval {}, Length {} multple".format(sendseq,TSval,Length))
                        print('[exception in flightsize calculation1]')
                        raise RuntimeError("Sequence {}, Tsval {}, Length {} was not received".format(sendseq,TSval,Length))
                elif operation == "RECV":
                    tempdf = self.tcpdump_df.loc[(sendseq, TSval)]
                    result = tempdf.query('Sequence == {} and TSval == {} and Length == {} and Operation == "{}"'.format(sendseq,TSval,Length,'SEND'))
                    if len(result) >= 1:
                        flightsize -= 1
                        opitem = []
                        opitem.append(sendtime)
                        opitem.append(sendseq)
                        opitem.append('RECV')
                        opitem.append("-1")
                        opitem.append(flightsize)
                        df2data.append(opitem)
                    else:
                        print("Sequence {}, Tsval {}, Length {} have {} results".format(sendseq,TSval,Length,len(result)))
                        print('[exception in flightsize calculation2]')
                        raise RuntimeError("Sequence {}, Tsval {}, Length {} have {} results".format(sendseq,TSval,Length,len(result)))
                else:
                    print("[ERROR in FLightSize calcluation]")
                    raise RuntimeError("[ERROR in FLightSize calcluation]")
            
            item.append(flightsize)
            dfdata.append(item)
        df = pd.DataFrame(dfdata,columns=['Time', 'FlightSizeMethod2'])
        df.to_csv(os.path.join(self.folder,'csvs','FlightSize_from_tcpdump.csv'), index=False)
        df2 = pd.DataFrame(df2data,columns=['Time', 'Sequence', 'oprtation','number', 'FlightSize'])
        df2.to_csv(os.path.join(self.folder,'csvs','FlightSize_from_tcpdump_operation.csv'), index=False)
        self.FlightSize_df_method2 = df.copy()
        self.FlightSize_method2_operation = df2.copy()
        return df
    def parse_sender_iperf_json(self,offset=0):
        with open(self.senderiperflogpath, 'r') as fin:
            iperfOutput = json.load(fin)
        
        snd_mss = iperfOutput['start']['tcp_mss_default']

        time = []
        transferred = []
        bandwidth = []
        retr = []
        cwnd = []
        rtt = []

        for interval in iperfOutput['intervals']:
            interval_data = interval['streams'][0]
            time_slot = float(interval_data['end']) - float(interval_data['start'])
            if time_slot > 2 or time_slot < 0.5:
                continue
            time.append(interval_data['end'] + offset)
            transferred.append(interval_data['bytes'] / (2**20))
            bandwidth.append(interval_data['bits_per_second'] / (2**20))
            if 'retransmits' in list(interval_data.keys()):
                retr.append(interval_data['retransmits'])
            if 'snd_cwnd' in list(interval_data.keys()):
                cwnd.append(interval_data['snd_cwnd'] / snd_mss)
            if 'rtt' in list(interval_data.keys()):
                rtt.append(interval_data['rtt'] / 1000)

        data_dict = {'time': time, 'transferred': transferred, 'bandwidth': bandwidth}
        if len(retr) > 0:
            data_dict['retr'] = retr
        if len(cwnd) > 0:
            data_dict['cwnd'] = cwnd
        if len(rtt) > 0:
            data_dict['rtt'] = rtt

        df = pd.DataFrame(data_dict)
        self.sender_resultdf = df
    
    def generate(self,offset=0.0,o2=0.0):
        dfdata = []
        dropped_deduction_dict = None
        dropped_seq_list = None
        dropped_seq_list = self.find_dropped_at_h3()
        first_send_time = None

        self.x_Linux_FLIGHTSIZE_time_list = []
        self.y_Linux_FLIGHTSIZE_value_list = []

        self.y_sack_out_value_list = []
        self.y_retrans_out_value_list = []
        self.y_lost_out_value_list = []
        self.y_packets_out_value_list = []
        self.y_Linux_packets_out_plus_retrans_out_value_list = []
        Linux_FLIGHTSIZE = 0
        ############################
        self.x_Linux_lost_time_list = []
        self.y_Linux_lost_value_list = [] 

        self.x_My_L_time_list = []
        self.y_My_L_value_list = [] 
        total_lost = 0
        ############################
        self.x_My_FLIGHTSIZE_time_list = [0]
        self.y_My_FLIGHTSIZE_value_list = [0]
        self.y_My_FLIGHTSIZE_receiving_list = [0]
        self.y_My_FLIGHTSIZE_cumulative_receiving = 0
        self.y_My_FLIGHTSIZE_sending_list = [0]
        self.y_My_FLIGHTSIZE_cumulative_sending = 0
        
        self.y_My_FLIGHTSIZE_cumulative_sending_minus_receiving_list=[0]
        self.y_My_FLIGHTSIZE_lost_sequence_number_list = [0]

        ############################
        My_FLIGHTSIZE = 0
        linux_fs_df_data = []
        self.y_ca_state_changeto_value_list = []
        self.x_ca_state_changeto_time_list = []
        last_ca_state = None

        self.x_CWND_time_list = []
        self.y_CWND_value_list = []
        self.x_sstresh_time_list = []
        self.y_sstresh_value_list = []

        self.x_packet_drop_time_list = []

        start_time = None
        with open(self.dmesgfile, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if line == "\n":
                    continue
                try:
                    original_kerneltime = Decimal(line.split('] [')[0][1:])
                except:
                    # print("Unknow",line)
                    continue
                if start_time is None:
                    start_time=original_kerneltime
                    # self.draw_begin = self.draw_begin - start_time #- Decimal(self.mn_net_obj.rtt/1000)
                kerneltime=original_kerneltime-start_time
                # if kerneltime > 10:
                #     break
                # if "sender_send_pkt" in line:
                if "ssp" in line:
                    continue
                    seq, data_len = sender(line)
                    if first_send_time is None:
                        if data_len >= 1000:
                            first_send_time = original_kerneltime
                    
                    # continue
                    # if data_len < 100:
                    #     continue
                    if dropped_seq_list:
                        if seq == dropped_seq_list[0]:
                            deduction = 1
                            dropped_seq_list.remove(seq)
                            item = []
                            item.append(original_kerneltime)
                            item.append(seq)
                            item.append('SEND/LOSS')
                            item.append('{}'.format(sending_packets))
                            item.append('{:d}'.format(My_FLIGHTSIZE))
                            dfdata.append(item)
                            # My_FLIGHTSIZE -= deduction
                            # self.x_packet_drop_time_list.append(kerneltime)
                            # self.x_My_FLIGHTSIZE_time_list.append(kerneltime)
                            # self.y_My_FLIGHTSIZE_value_list.append(My_FLIGHTSIZE)
                            continue
                        
                    if data_len % 1448 == 0:
                        sending_packets = int(data_len / 1448)

                        My_FLIGHTSIZE += sending_packets
                        self.x_My_FLIGHTSIZE_time_list.append(original_kerneltime)
                        self.y_My_FLIGHTSIZE_value_list.append(My_FLIGHTSIZE)
                        item = []
                        item.append(original_kerneltime)
                        item.append(seq)
                        item.append('SEND')
                        item.append('+{}'.format(sending_packets))
                        item.append('{:d}'.format(My_FLIGHTSIZE))
                        dfdata.append(item)
                        self.y_My_FLIGHTSIZE_cumulative_sending += sending_packets
                        self.y_My_FLIGHTSIZE_sending_list.append(self.y_My_FLIGHTSIZE_cumulative_sending)
                        self.y_My_FLIGHTSIZE_cumulative_sending_minus_receiving_list.append(self.y_My_FLIGHTSIZE_cumulative_sending-self.y_My_FLIGHTSIZE_cumulative_receiving)
                    elif data_len < 200:
                        continue
                    else:
                        sending_packets = int(data_len // 1448) +  1

                        My_FLIGHTSIZE += sending_packets
                        self.x_My_FLIGHTSIZE_time_list.append(original_kerneltime)
                        self.y_My_FLIGHTSIZE_value_list.append(My_FLIGHTSIZE)
                        item = []
                        item.append(original_kerneltime)
                        item.append(seq)
                        item.append('SEND')
                        item.append('+{}'.format(sending_packets))
                        item.append('{:d}'.format(My_FLIGHTSIZE))
                        dfdata.append(item)
                        self.y_My_FLIGHTSIZE_cumulative_sending += sending_packets
                        self.y_My_FLIGHTSIZE_sending_list.append(self.y_My_FLIGHTSIZE_cumulative_sending)
                        self.y_My_FLIGHTSIZE_cumulative_sending_minus_receiving_list.append(self.y_My_FLIGHTSIZE_cumulative_sending-self.y_My_FLIGHTSIZE_cumulative_receiving)

                if "1fwp" in line:
                    
                    #as sender
                    seq, data_len,pklen = fwp(line)
                    if first_send_time is None:
                        if pklen >= 1480:
                            first_send_time = original_kerneltime

                    deduction = 0
                    if pklen >= 500:
                        if dropped_seq_list:
                            if seq in dropped_seq_list:
                                # print("Loss seq:",seq)
                                deduction = 1
                                dropped_seq_list.remove(seq)
                                item = []
                                item.append(original_kerneltime)
                                item.append(seq)
                                item.append('SEND-Loss')
                                item.append('--')
                                item.append('{:d}'.format(My_FLIGHTSIZE))
                                # print(item)
                                dfdata.append(item)
                                # print(dfdata)
                                self.x_My_L_time_list.append(kerneltime)
                                total_lost += deduction
                                self.y_My_L_value_list.append(total_lost)
                                continue
                                My_FLIGHTSIZE -= deduction
                                self.x_packet_drop_time_list.append(kerneltime)
                                self.x_My_FLIGHTSIZE_time_list.append(kerneltime)
                                self.y_My_FLIGHTSIZE_value_list.append(My_FLIGHTSIZE)
                    
                            
                        sending_packets = 1

                        My_FLIGHTSIZE += sending_packets
                        self.x_My_FLIGHTSIZE_time_list.append(original_kerneltime)
                        self.y_My_FLIGHTSIZE_value_list.append(My_FLIGHTSIZE)
                        item = []
                        item.append(original_kerneltime)
                        item.append(seq)
                        item.append('SEND')
                        item.append('+{}'.format(sending_packets))
                        item.append('{:d}'.format(My_FLIGHTSIZE))
                        dfdata.append(item)
                    else:
                        sending_packets = 0
                        pass
                        # sending_packets = 0
                        # self.x_My_FLIGHTSIZE_time_list.append(original_kerneltime)
                        # self.y_My_FLIGHTSIZE_value_list.append(My_FLIGHTSIZE)
                        # item = []
                        # item.append(original_kerneltime)
                        # item.append(seq)
                        # item.append('SEND')
                        # item.append('--'.format(sending_packets))
                        # item.append('{:d}'.format(My_FLIGHTSIZE))
                        # dfdata.append(item)
                    self.y_My_FLIGHTSIZE_cumulative_sending += sending_packets
                    self.y_My_FLIGHTSIZE_sending_list.append(self.y_My_FLIGHTSIZE_cumulative_sending)
                    self.y_My_FLIGHTSIZE_cumulative_sending_minus_receiving_list.append(self.y_My_FLIGHTSIZE_cumulative_sending-self.y_My_FLIGHTSIZE_cumulative_receiving) 

                            
                    
                    
                    

                    
                # elif "receiver_rcv_pkt" in line:
                elif "rrp" in line:
                    seq, __data_len,pklen = receiver(line)
                
                    # if pklen <200:
                    #     continue
                    if pklen >= 500:
                        receiving_packets = 1
                        My_FLIGHTSIZE -= receiving_packets
                        self.x_My_FLIGHTSIZE_time_list.append(original_kerneltime)
                        self.y_My_FLIGHTSIZE_value_list.append(My_FLIGHTSIZE)
                        item = []
                        item.append(original_kerneltime)
                        item.append(seq)
                        item.append('RECV')
                        item.append('-{}'.format(receiving_packets))
                        item.append('{:d}'.format(My_FLIGHTSIZE))
                        dfdata.append(item)
                    else:
                        receiving_packets = 0
                        pass
                        # self.x_My_FLIGHTSIZE_time_list.append(original_kerneltime)
                        # self.y_My_FLIGHTSIZE_value_list.append(My_FLIGHTSIZE)
                        # item = []
                        # item.append(original_kerneltime)
                        # item.append(seq)
                        # item.append('RECV')
                        # item.append('--'.format(receiving_packets))
                        # item.append('{:d}'.format(My_FLIGHTSIZE))
                        # dfdata.append(item)
                    self.y_My_FLIGHTSIZE_cumulative_receiving += receiving_packets
                    self.y_My_FLIGHTSIZE_receiving_list.append(self.y_My_FLIGHTSIZE_cumulative_receiving)
                    self.y_My_FLIGHTSIZE_cumulative_sending_minus_receiving_list.append(self.y_My_FLIGHTSIZE_cumulative_sending-self.y_My_FLIGHTSIZE_cumulative_receiving)
                

                # elif "tcp_ca_state" in line:
                elif "scas" in line:  
                    
                    current_ca_state = ca_state(line)
                    self.y_ca_state_changeto_value_list.append(current_ca_state)
                    self.x_ca_state_changeto_time_list.append(original_kerneltime)

                    # if last_ca_state is None:
                    #     last_ca_state = current_ca_state
                    # if current_ca_state != last_ca_state:
                    # if current_ca_state < 4 and last_ca_state == 4:
                    #     self.draw_end = kerneltime + Decimal(self.rtt/1000)
                    # if current_ca_state ==4 or current_ca_state ==3 or last_ca_state ==4 or last_ca_state ==3:
                    #     self.y_ca_state_changeto_value_list.append(current_ca_state)
                    #     self.x_ca_state_changeto_time_list.append(kerneltime)
                    #     last_ca_state = current_ca_state

                # elif "sender_CWND" in line:
                elif "CWND" in line:
                    # print('cwnd')
                    cwnd,ssthresh = get_cwnd(line)
                    # print(cwnd,ssthresh)
                    if cwnd < 10000:
                        self.y_CWND_value_list.append(cwnd)
                        self.x_CWND_time_list.append(original_kerneltime)
                        if ssthresh < 214748:
                            self.y_sstresh_value_list.append(ssthresh)
                            self.x_sstresh_time_list.append(original_kerneltime)

                # elif "sender_flightsize" in line:
                elif "sf" in line:
                    flightsize,packets_out,retrans_out,sacked_out,lost_out=get_flightsize(line)
                    if flightsize < 10000:
                        self.x_Linux_FLIGHTSIZE_time_list.append(original_kerneltime)
                        self.y_Linux_FLIGHTSIZE_value_list.append(flightsize)
                        item = []
                        item.append(original_kerneltime)
                        item.append(flightsize)
                        linux_fs_df_data.append(item)
                        self.y_lost_out_value_list.append(lost_out)
                        self.y_packets_out_value_list.append(packets_out)
                        self.y_sack_out_value_list.append(sacked_out)
                        self.y_retrans_out_value_list.append(retrans_out)
                        self.y_Linux_packets_out_plus_retrans_out_value_list.append(packets_out+retrans_out)
                elif "sendertpinfo" in line:
                    reordering, data_lereord_seenn,segs_out,app_limited,lost=senderinfo(line)
                    self.x_Linux_lost_time_list.append(kerneltime)
                    self.y_Linux_lost_value_list.append(lost)
                else:
                    pass
                    # print("Unknow line",line)
        print("Total deduced from generation:",total_lost)
        df = pd.DataFrame(dfdata,columns=['Time', 'Sequence','oprtation', 'number','AccurateFlightSize1'])
        df['AccurateFlightSize1'] = df['AccurateFlightSize1'].astype(int)
        df['Sequence'] = df['Sequence'].astype(int)
        df.to_csv(os.path.join(self.folder,'csvs','FlightSize_old_method_operation.csv'), index=False)
        self.OldFlightsize_original_time_df = df.copy()

        for idx, row in df.iterrows():
            timefield = row['Time']
            timefrom0 = Decimal(timefield)-Decimal(first_send_time) 
            # print(Decimal(timefield), Decimal(first_send_time))
            df.at[idx,'Time'] = timefrom0
        df = df[df['Time'] >= 0]
        # df = df[df['number'] != '--']
        self.OldFlightsize_timefrom0_df = df.copy()
        df.to_csv(os.path.join(self.folder,'csvs','FlightSize_old_method_operation_time0.csv'), index=False)

        linfsdf = pd.DataFrame(linux_fs_df_data,columns=['Time', 'FlightSize'])
        linfsdf['FlightSize'] = linfsdf['FlightSize'].astype(int)
        linfsdf.to_csv(os.path.join(self.folder,'csvs','Linux_FlightSize_direct.csv'), index=False)
        self.LinFlightsize_original_time_df = linfsdf.copy()

        return first_send_time
 

    def parse_printk(self,first_send_time):
        dfdata = []
        last_update_time = 0
        for idx, row in self.LinFlightsize_original_time_df.iterrows():
            time = row["Time"]
            # if Decimal(time) - Decimal(last_update_time) < 0.032:
            #     continue
            last_update_time = time
            lfs = row['FlightSize']
            timepoint = Decimal(time)- Decimal(first_send_time)
        
            item = []
            item.append(timepoint)
            item.append(lfs)
            dfdata.append(item)
        df = pd.DataFrame(dfdata,columns=['Time', 'LinuxFlightSize'])
        df['LinuxFlightSize'] = df['LinuxFlightSize'].astype(int)
        df.to_csv(os.path.join(self.folder,'csvs','FlightSize_Lin.csv'), index=False)
        self.LinFlightsizedf = df.copy()
        return df

    def find_dropped_at_h3(self):
        arrived_but_not_forwarded_list = []
        self.total_send = 0
        with open(self.dmesgfile) as f:
            file_lines = f.readlines()
            
            for line in file_lines:
                # kernel_time=get_kernel_time(line)
                if '1fwp' in line:
                    seq1, data_len,len1=fwp(line)
                    arrived_but_not_forwarded_list.append(seq1)
                    self.total_send += 1
                elif '2fwp' in line:
                    seq2,data_len,len2=fwp(line)
                    try:
                        arrived_but_not_forwarded_list.remove(seq2)
                    except:
                        print("try to remove ",seq2)
                        # print(arrived_but_not_forwarded_list)

        print("Total Dropped at h3 forwarding:",len(arrived_but_not_forwarded_list))
        # print(arrived_but_not_forwarded_list)
        self.arrived_but_not_forwarded_list = arrived_but_not_forwarded_list

        # diff_list= []
        # for i in range(len(arrived_but_not_forwarded_list)-1):
        #     diff_list.append((arrived_but_not_forwarded_list[i+1]-arrived_but_not_forwarded_list[i])//1448)
        # print(diff_list)
        self.actual_dropped_percentage = len(self.arrived_but_not_forwarded_list)/self.total_send
        print("actual_dropped_percentage",self.actual_dropped_percentage)
        return arrived_but_not_forwarded_list
    def check_two_flightsize_results(self):
        df1 = self.OldFlightsize_timefrom0_df.copy()
        df2 = self.FlightSize_method2_operation.copy()
        df1 = df1.drop('Time', axis=1)
        df2 = df2.drop('Time', axis=1)
        df1.to_csv(os.path.join(self.folder,'csvs','fscompare1.csv'), index=False)
        df2.to_csv(os.path.join(self.folder,'csvs','fscompare2.csv'), index=False)


        # seqs = find_duplicates(self.sender_tcpdump_df['Sequence'].to_list())
        # print(seqs)

    def diff_time(self,endtime=17.5):
        df1 = self.OldFlightsize_timefrom0_df.copy()
        df2 = self.FlightSize_method2_operation.copy()
        dflin = self.LinFlightsizedf.copy()

        df1 = df1[df1['Time'] <= endtime]
        df2 = df2[df2['Time'] <= endtime]
        dflin = dflin[dflin['Time'] <= endtime]


        fs1_impact = Decimal(0)
        df1it = list(df1.iterrows())
        index1 = 0
        for idx1, row1 in islice(df1it, index1, len(df1it)-1):
            fs = row1['AccurateFlightSize1']
            duration_start = row1['Time']
            # print(df1it[idx1+1])
            duration_end = df1.iloc[idx1+1]['Time']
            duration = duration_end - duration_start
            fs_impact = fs * duration
            fs1_impact += fs_impact

        fs2_impact = Decimal(0)
        df2it = list(df2.iterrows())
        index2 = 0
        for idx2, row2 in islice(df2it, index2, len(df2it)-1):
            fs = row2['FlightSize']
            duration_start = row2['Time']
            duration_end = df2.iloc[idx2+1]['Time']
            duration = duration_end - duration_start
            fs_impact = fs * duration
            fs2_impact += fs_impact

        fslin_impact = Decimal(0)
        dflinit = list(dflin.iterrows())
        indexlin = 0
        for idx3, row3 in islice(dflinit, indexlin, len(dflinit)-1):
            fs = row3['LinuxFlightSize']
            duration_start = row3['Time']
            duration_end = dflin.iloc[idx3+1]['Time']
            duration = duration_end - duration_start
            fs_impact = fs * duration
            fslin_impact += fs_impact

        print(f'FS Lin:{fslin_impact} FS Online:{fs1_impact} FS Offiline:{fs2_impact}')
        return fslin_impact, fs1_impact, fs2_impact