import os
from subprocess import Popen, PIPE, call
import subprocess
import time
import pandas as pd
from decimal import Decimal
from itertools import islice

def run_shell(shell_cmd):
    try:
        result = subprocess.run(
            [shell_cmd],  # Path to your script
            stdout=subprocess.PIPE,  # Capture standard output
            stderr=subprocess.PIPE,  # Capture standard error
            text=True               # Return strings instead of bytes
        )
        # Print the output
        # print("Standard Output:", result.stdout)
        # print("Standard Error:", result.stderr)
        # print("Return Code:", result.returncode)
        return result.stdout, result.stderr, result.returncode
    except FileNotFoundError as e:
        print("Error: Shell script not found")
        return None
    except Exception as e:
        print(f"Error running shell script: {e}")
        return None
    
def start_tcpdump(interface, result_save_path='/home/ubuntu/FlightSize/extresult.pcap'):
    # tcpdump_cmd1 = f'sudo tcpdump -tt -i {interface} tcp dst port 5001 -w {result_save_path}'
    tcpdump_cmd1 = f'tcpdump -tt -i {interface} tcp dst port 5001 -w {result_save_path}'
    print(tcpdump_cmd1)
    p = Popen(tcpdump_cmd1, stdin=PIPE,shell=True)
def finalexec(savingpath):
    print("In final executation:")
    # os.system('sudo killall mm-link mm-delay iperf3 tcpdump')
    # os.system("sudo chown -R ubuntu /home/ubuntu/FlightSize")
    os.system('killall mm-link mm-delay iperf3 tcpdump')
    os.system("chown -R ubuntu /home/ubuntu/FlightSize")
    print(f'./pcap2csv.sh {savingpath}/internalsult.pcap')
    os.system(f'./pcap2csv.sh {savingpath}/internalsult.pcap')
    print(f'./pcap2csv.sh {savingpath}/extresult.pcap')
    os.system(f'./pcap2csv.sh {savingpath}/extresult.pcap')

def execption_exec():
    # os.system('sudo killall mm-link mm-delay iperf3 tcpdump')
    # os.system("sudo chown -R ubuntu /home/ubuntu/FlightSize")
    os.system('killall mm-link mm-delay iperf3 tcpdump')
    os.system("chown -R ubuntu /home/ubuntu/FlightSize")

def clean_kmesg():
    # os.system("sudo dmesg -c > /dev/null")
    os.system("dmesg -c > /dev/null")

def save_kmesg(filepath):
    os.system(f"dmesg > {filepath}")

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

def parse_tcpdump_sender(savingpath='/home/ubuntu/FlightSize/Results/2024-12-16-18h.38m.48s'):
    raw_csv_df = pd.read_csv(os.path.join(savingpath,'internalsult.pcap-tcp.csv'))
    raw_csv_df['tcp.len'] = raw_csv_df['tcp.len'].astype(int)
    raw_csv_df = raw_csv_df[raw_csv_df['tcp.len'] > 0]
    selected_columns = raw_csv_df[['_ws.col.Time', 'tcp.seq', 'tcp.options.timestamp.tsval', 'tcp.options.timestamp.tsecr', 'tcp.len']]
    renamed_columns = selected_columns.rename(columns={'_ws.col.Time': 'Time', 
                                                       'tcp.seq': 'Sequence', 
                                                       'tcp.options.timestamp.tsval': 'TSval', 
                                                       'tcp.options.timestamp.tsecr': 'TSecr', 
                                                       'tcp.len': 'Length'})
    df = renamed_columns.copy()
    df['Operation'] = "SEND"
    # df = pd.DataFrame(dfdata,columns=['Time', 'Operation', 'Sequence', 'TSval', 'TSecr','Length'])
    df['Sequence'] = df['Sequence'].astype(int)
    df['TSval'] = df['TSval'].astype(int)
    df['TSecr'] = df['TSecr'].astype(int)
    df['Length'] = df['Length'].astype(int)
    df.to_csv(os.path.join(savingpath,'tcpdump_sender.csv'), index=False)
    # print(df)
    return df

def parse_tcpdump_receiver(savingpath):
    raw_csv_df = pd.read_csv(os.path.join(savingpath,'extresult.pcap-tcp.csv'))
    raw_csv_df['tcp.len'] = raw_csv_df['tcp.len'].astype(int)
    raw_csv_df = raw_csv_df[raw_csv_df['tcp.len'] > 0]
    selected_columns = raw_csv_df[['_ws.col.Time', 'tcp.seq', 'tcp.options.timestamp.tsval', 'tcp.options.timestamp.tsecr', 'tcp.len']]
    renamed_columns = selected_columns.rename(columns={'_ws.col.Time': 'Time', 
                                                       'tcp.seq': 'Sequence', 
                                                       'tcp.options.timestamp.tsval': 'TSval', 
                                                       'tcp.options.timestamp.tsecr': 'TSecr', 
                                                       'tcp.len': 'Length'})
    df = renamed_columns.copy()
    df['Operation'] = "RECV"
    df.to_csv(os.path.join(savingpath,'tcpdump_receiver.csv'), index=False)
    # df = pd.DataFrame(dfdata,columns=['Time', 'Operation', 'Sequence', 'TSval', 'TSecr','Length'])
    df['Sequence'] = df['Sequence'].astype(int)
    df['TSval'] = df['TSval'].astype(int)
    df['TSecr'] = df['TSecr'].astype(int)
    df['Length'] = df['Length'].astype(int)
    df.to_csv(os.path.join(savingpath,'tcpdump_receiver.csv'), index=False)
    # print(df)
    return df

def merge_tcpdump_and_get_send_time(sender_tcpdump_df, receiver_tcpdump_df, savingpath):
    tcpdump_df = pd.concat([receiver_tcpdump_df,sender_tcpdump_df])
    tcpdump_df.reset_index(drop=True,inplace=True)
    tcpdump_df.sort_values(by=['Time'],inplace=True,kind='stable')
    tcpdump_df.to_csv(os.path.join(savingpath,'tcpdump_merged.csv'), index=False)

    first_send_time = None
    for idx1, row1 in tcpdump_df.iterrows():
        operation = row1['Operation']
        sendtime = row1['Time']
        sendseq = row1['Sequence']
        TSval = row1['TSval']
        Length = row1['Length']
        if first_send_time is None:
            if Length> 200:
                first_send_time = sendtime
                break
    return tcpdump_df, first_send_time

def change_tcpdump_df_time(df_input, start_time, savingpath='/home/ubuntu/FlightSize/Results/2024-12-16-18h.38m.48s'):
    tcpdump_df = df_input

    for idx, row in tcpdump_df.iterrows():
        timefield = row['Time']
        if start_time is None:
            start_time = timefield
        timefrom0 = comp_time(start_time, timefield)
        tcpdump_df.at[idx,'Time'] = timefrom0

    tcpdump_df['Time'] = tcpdump_df['Time']
    tcpdump_df.reset_index(drop=True,inplace=True)
    tcpdump_df.to_csv(os.path.join(savingpath,'tcpdump_all.csv'), index=False)
    return tcpdump_df

def cal_FlightSize(df_input, savingpath):
        tcpdump_df = pd.read_csv(os.path.join(savingpath,"tcpdump_all.csv"))
        tcpdump_df = df_input
        
        tcpdump_df['seqkey'] = tcpdump_df['Sequence']
        tcpdump_df['tsvkey'] = tcpdump_df['TSval']
        tcpdump_df.set_index(['seqkey', 'tsvkey'],drop=True,inplace=True)
        dfdata = []
        df2data = []
        flightsize = 0
        for idx1, row1 in tcpdump_df.iterrows():
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
                    tempdf = tcpdump_df.loc[(sendseq, TSval)]
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
                    tempdf = tcpdump_df.loc[(sendseq, TSval)]
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
        df = pd.DataFrame(dfdata,columns=['Time', 'FlightSizeTcpdump'])
        df.to_csv(os.path.join(savingpath,'FlightSize_from_tcpdump.csv'), index=False)

        df2 = pd.DataFrame(df2data,columns=['Time', 'Sequence', 'oprtation','number', 'FlightSize'])
        df2.to_csv(os.path.join(savingpath,'FlightSize_from_tcpdump_operation.csv'), index=False)

        return df
def get_Linux_FlightSize(savingpath):
    dmesgfile = os.path.join(savingpath,'kmesg.txt')
    first_send_time = None
    linux_fs_df_data = []
    linux_info_df_data = []

    with open(dmesgfile, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if line == "\n":
                    continue
                try:
                    original_kerneltime = Decimal(line.split('] [')[0][1:])
                except:
                    # print("Unknow",line)
                    continue
                # ntohl(tcph->seq), skb->data_len, 	//0,1
                # icsk->icsk_ca_state,				//2
                # tp->snd_cwnd, tp->snd_ssthresh,		//3,4
                # tp->packets_out, tp->retrans_out, tp->sacked_out, tp->lost_out,	//5,6,7,8
                # tp->prr_out,tp->prr_delivered,		//9,10
                # tp->rcv_tstamp, tp->tsoffset,		//11,12
                # tp->rttvar_us, tp->rtt_seq, tp->srtt_us,	//13,14,15
                # tp->delivered, tp->lost, tp->total_retrans, tp->reordering,		//16,17,18,19
                # tp->rcv_wnd,						//20
                # tp->reord_seen, tp->segs_out		//21,22
                if "ssp" in line or "rev_ack" in line:
                    send_segs = line.split('[ssp] ')[1].split(' ')
                    seq = int(send_segs[0])
                    pklen = int(send_segs[1])
                    icsk_ca_status = int(send_segs[2])
                    tp_snd_cwnd = int(send_segs[3])
                    tp_snd_ssthresh = int(send_segs[4])
                    packets_out = int(send_segs[5])
                    retrans_out = int(send_segs[6])
                    sacked_out = int(send_segs[7])
                    lost_out = int(send_segs[8])
                    tp_prr_out = int(send_segs[9])
                    tp_prr_delivered = int(send_segs[10])
                    tp_rcv_tstamp = int(send_segs[11])
                    tp_tsoffset = int(send_segs[12])
                    tp_rttvar_us = int(send_segs[13])
                    tp_rtt_seq = int(send_segs[14])
                    tp_srtt_us = int(send_segs[15])
                    tp_delivered = int(send_segs[16])
                    tp_lost = int(send_segs[17])
                    tp_total_retrans = int(send_segs[18])
                    tp_reordering = int(send_segs[19])
                    tp_rcv_wnd = int(send_segs[20])
                    tp_reord_seen = int(send_segs[21])
                    tp_segs_out = int(send_segs[22])
                    flightsize = packets_out + retrans_out - sacked_out - lost_out
                    item = [original_kerneltime,flightsize]
                    linux_fs_df_data.append(item)
                    item = [original_kerneltime,0,packets_out+retrans_out-sacked_out-lost_out,
                            seq, pklen,                         # 0,1
                            icsk_ca_status,                     # 2
                            tp_snd_cwnd, tp_snd_ssthresh,       # 3,4
                            packets_out, retrans_out, sacked_out, lost_out, # 5,6,7,8
                            tp_prr_out, tp_prr_delivered,       # 9,10
                            tp_rcv_tstamp, tp_tsoffset,         # 11,12
                            tp_rttvar_us, tp_rtt_seq, tp_srtt_us,           # 13,14,15
                            tp_delivered, tp_lost, tp_total_retrans, tp_reordering, # 16,17,18,19
                            tp_rcv_wnd, tp_reord_seen, tp_segs_out]         # 20,21,22
                    linux_info_df_data.append(item)

                    if first_send_time is None:
                        if pklen >= 1480:
                            first_send_time = original_kerneltime


                elif "sra" in line:
                    ack_segs = line.split('[sra] ')[1].split(' ')

    linfsdf = pd.DataFrame(linux_fs_df_data,columns=['Time', 'LinuxFlightSize'])
    linfsdf['LinuxFlightSize'] = linfsdf['LinuxFlightSize'].astype(int)
    linfsdf.to_csv(os.path.join(savingpath,'FlightSize_Linux_direct.csv'), index=False)

    dfdata = []
    for idx, row in linfsdf.iterrows():
            time = row["Time"]
            lfs = row['LinuxFlightSize']
            timepoint = Decimal(time)- Decimal(first_send_time)
        
            item = []
            item.append(timepoint)
            item.append(lfs)
            dfdata.append(item)
    df = pd.DataFrame(dfdata,columns=['Time', 'LinuxFlightSize'])
    df['LinuxFlightSize'] = df['LinuxFlightSize'].astype(int)
    df.to_csv(os.path.join(savingpath,'FlightSize_Linux.csv'), index=False)

    lininfodf = pd.DataFrame(linux_info_df_data,columns=['Time','FlightSizeRef','FlightSizeLin',
                                                         'Sequence', 'skb.data_len',
                                                         'icsk_ca_status',
                                                         'tp_snd_cwnd','tp_snd_ssthresh',
                                                         'tp_packets_out', 'tp_retrans_out', 'tp_sacked_out', 'tp_lost_out',
                                                         'tp_prr_out','tp_prr_delivered',
                                                         'tp_rcv_tstamp', 'tp_tsoffset',
                                                         'tp_rttvar_us', 'tp_rtt_seq', 'tp_srtt_us',
                                                         'tp_delivered', 'tp_lost', 'tp_total_retrans', 'tp_reordering',
                                                         'tp_rcv_wnd', 'tp_reord_seen', 'tp_segs_out'
                                                         ])
    
    lininfodf.to_csv(os.path.join(savingpath,'Linux_Info_direct.csv'), index=False)

# set time from 0
    for idx, row in lininfodf.iterrows():
            time = row["Time"]
            timepoint = Decimal(time)- Decimal(first_send_time)
        
            lininfodf.at[idx,'Time'] = timepoint

# Add FlightSize value reference
    FlightSizeref_df = pd.read_csv(os.path.join(savingpath,"FlightSize_from_tcpdump.csv"))
    index2 = 0
    lindflength = len(lininfodf)
    
    dfit2 = list(FlightSizeref_df.iterrows())
    # last_time = 0
    for idx, row in lininfodf.iterrows():
        
        if idx % 1000 == 0:
            print(f"{idx}/{lindflength}")

        t1 = row["Time"]

        if float(t1)<0:
            continue
       
        for idx2, row2 in islice(dfit2, index2, None):
            t2 = row2["Time"]
            if t2 > t1:
                break
            index2 = max(0,idx2-5)
            tpfs = row2['FlightSizeTcpdump']

        lininfodf.at[idx,'FlightSizeRef'] = tpfs


    lininfodf.to_csv(os.path.join(savingpath,'Linux_Info.csv'), index=False)

    return first_send_time
def remove_slowstart(savingpath):
    lininfodf = pd.read_csv(os.path.join(savingpath,'Linux_Info.csv'))

    lininfodf = lininfodf[lininfodf['Time'] > 1]

    lininfodf = lininfodf[lininfodf['Time'] < 30]


    lininfodf.to_csv(os.path.join(savingpath, os.path.join(savingpath,f'final_{savingpath.replace("/home/ubuntu/FlightSize/Results/","").replace("/","")}.csv')), index=False)

if __name__ == "__main__":
    # senderdf = parse_tcpdump_sender()
    # receiverdf = parse_tcpdump_receiver()
    # merged_tcpdump_df, tcpdump_first_send_time = merge_tcpdump_and_get_send_time(sender_tcpdump_df=senderdf, receiver_tcpdump_df=receiverdf)
    # change_tcpdump_df_time(merged_tcpdump_df, start_time=tcpdump_first_send_time)
    # cal_FlightSize()
    # get_Linux_FlightSize()
    pass