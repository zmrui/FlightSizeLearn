#!/usr/bin/env python3

"""
Mininet script to create two hosts connected via a switch with
adjustable link characteristics (bandwidth, delay, loss, reordering)
and run an iperf3 test, saving the client log.
"""

import os
import time
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from datetime import datetime

def run_iperf_test(bw=10, delay='10ms', loss=0, 
                   reorder_percent=0, reorder_corr=0, 
                   duration=10, log_dir='/tmp'):
    """
    Creates a Mininet topology, runs iperf3, and saves the log.

    Args:
        bw (int): Bandwidth in Mbps for the link s1-h2.
        delay (str): Delay for the link s1-h2, e.g., '10ms'.
        loss (int): Packet loss percentage (0-100) for the link s1-h2.
        reorder_percent (int): Packet reorder percentage (0-100) for traffic on h2-eth0.
        reorder_corr (int): Packet reorder correlation (0-100) for traffic on h2-eth0.
        duration (int): iperf3 test duration in seconds.
        log_dir (str): Directory inside h2 to save the iperf3 client log.
    """

    net = Mininet(controller=None, switch=OVSKernelSwitch, link=TCLink, autoSetMacs=True)

    info('*** Adding hosts\n')
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')

    info('*** Adding switch\n')
    s1 = net.addSwitch('s1')

    info('*** Creating links\n')
    # Default link for h1 to s1
    net.addLink(h1, s1) 
    
    # Link with specified bw, delay, loss for h2 to s1
    # These parameters will apply to both h2-eth0 and s1-ethX (connected to h2)
    link_params_h2_s1 = {'bw': bw, 'delay': delay, 'loss': loss}
    net.addLink(h2, s1, **link_params_h2_s1)

    info('*** Starting network\n')
    net.start()

    # --- Apply packet reordering using tc command on h2's interface (h2-eth0) ---
    # TCLink sets up HTB (handle 1:) and then netem (handle 10:) on top of it (parent 1:1).
    # We need to change the existing netem qdisc to add/modify reordering.
    # This will affect traffic leaving h2 towards s1.
    
    h2_intf_name = 'h2-eth0' # h2.intfList()[0].name could also be used if h2 has only one interface

    if reorder_percent > 0:
        info(f'*** Applying packet reordering to {h2_intf_name}: {reorder_percent}% correlation {reorder_corr}%\n')
        # Construct the tc command to change the existing netem qdisc.
        # We must re-specify delay and loss as 'tc qdisc change ... netem ...' replaces all netem options.
        tc_cmd_parts = [
            f'tc qdisc change dev {h2_intf_name}',
            'parent 1:1 handle 10:', # Assumes HTB (1:) and netem (10:) setup by TCLink
            'netem',
            f'delay {delay}',       # Re-specify delay from TCLink
            f'loss {loss}%'         # Re-specify loss from TCLink
        ]
        # Add reorder parameters
        tc_cmd_parts.append(f'reorder {reorder_percent}% {reorder_corr}%')
        
        # Optional: add jitter if needed for reordering or to model it explicitly
        # tc_cmd_parts.append(f'jitter {some_jitter_value_ms}ms') 

        tc_cmd_reorder = ' '.join(tc_cmd_parts)

        info(f"Executing tc command on {h2.name}: {tc_cmd_reorder}\n")
        result = h2.cmd(tc_cmd_reorder)
        
        # Basic check for tc command errors
        if "Error" in result or "failed" in result or "Cannot find" in result:
            info(f"!!! TC command for reordering might have failed on {h2.name}.\nOutput: {result}\n")
            info(f"Current qdiscs on {h2_intf_name}:\n{h2.cmd(f'tc qdisc show dev {h2_intf_name}')}\n")
        else:
            info(f"TC command for reordering successful on {h2.name}.\n")
            # info(f"Updated qdiscs on {h2_intf_name}:\n{h2.cmd(f'tc qdisc show dev {h2_intf_name}')}\n") # Uncomment for verbose qdisc info
    else:
        info("*** No packet reordering specified (reorder_percent is 0).\n")

    # --- Prepare for iperf3 test ---
    # Construct a descriptive log file name
    log_file_name = (f"iperf3_client_h2_to_h1_"
                     f"bw{bw}_delay{delay.replace('ms','')}_loss{loss}_"
                     f"reorder{reorder_percent}corr{reorder_corr}_dur{duration}.json")
    
    full_log_path_on_h2 = os.path.join(log_dir, log_file_name)

    # Ensure log directory exists inside h2's filesystem
    h2.cmd(f'mkdir -p {log_dir}')
    info(f"*** Log directory {log_dir} ensured on {h2.name}.\n")

    info(f'*** Starting iperf3 server on {h1.name} ({h1.IP()})\n')
    h1.cmd('iperf3 -s -D') # -D runs as daemon

    # Wait a moment for the iperf3 server to start
    time.sleep(1)

    info(f'*** Starting iperf3 client on {h2.name} ({h2.IP()}), connecting to {h1.IP()}\n')
    info(f'*** Client log will be saved to {h2.name}:{full_log_path_on_h2}\n')
    
    # iperf3 client command. -J for JSON output. --logfile saves it.
    iperf_client_cmd = f'iperf3 -c {h1.IP()} -t {duration} -J --logfile {full_log_path_on_h2}'
    
    info(f"Executing iperf3 client command on {h2.name}: {iperf_client_cmd}\n")
    client_stdout = h2.cmd(iperf_client_cmd) # This will block until iperf3 client finishes
    
    info(f"*** iperf3 client ({h2.name}) process finished.\n")
    if client_stdout.strip(): # Print stdout if any (usually minimal with --logfile)
        info(f"Client stdout:\n{client_stdout}\n")

    info(f"*** iperf3 test finished. Log should be at {h2.name}:{full_log_path_on_h2}\n")
    info("To view the log after the script, you can use 'cat' in h2's shell if you run CLI,")
    info(f"e.g., 'mininet> h2 cat {full_log_path_on_h2}'\n")

    # --- Optional: Start Mininet CLI for interactive inspection ---
    # CLI(net) 

    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    now = datetime.now()
    dt_string = "bbr_"+ now.strftime("%Y-%m-%d-%Hh.%Mm.%Ss")

    # Clean up previous Mininet instances (important for tc rules)
    info('*** Cleaning up any previous Mininet network configurations...\n')
    # os.system('mn -c -q')
    time.sleep(1) # Give a moment for cleanup to complete

    # --- Customizable parameters for the test ---
    bandwidth_mbps = 20       # Bandwidth in Mbps
    link_delay_ms = '50ms'    # Link delay (e.g., '50ms')
    packet_loss_percent = 0   # Packet loss percentage (e.g., 5 for 5%)
    
    # Reordering parameters (applied if reorder_pkt_percent > 0)
    # Effective reordering often requires some base delay.
    reorder_pkt_percent = 10  # Percentage of packets to reorder (e.g., 10 for 10%)
    reorder_pkt_corr = 25     # Correlation for reordering (e.g., 25 for 25%)

    test_duration_seconds = 5 # Duration of the iperf3 test in seconds
    
    # Directory inside host h2 where the iperf3 client log will be saved
    log_directory_on_h2 = os.path.join('/home/ubuntu/FlightSize/Results',dt_string)

    run_iperf_test(bw=bandwidth_mbps,
                   delay=link_delay_ms,
                   loss=packet_loss_percent,
                   reorder_percent=reorder_pkt_percent,
                   reorder_corr=reorder_pkt_corr,
                   duration=test_duration_seconds,
                   log_dir=log_directory_on_h2)

    info(f"*** Script finished. Check {log_directory_on_h2} on host h2 (e.g., via Mininet CLI) for iperf3 logs.\n")
