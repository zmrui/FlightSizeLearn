#!/usr/bin/env python3
"""
reordering_iperf_mininet.py

Create a minimal Mininet topology (h1-r-h2) where host 'r' acts as a
bridging relay. The link from r to h2 is configured as a bottleneck
using the netem queue discipline. This script allows for enabling or
disabling packet reorder emulation on that bottleneck link to observe
its effect on different congestion control algorithms (CCAs).
"""

import argparse
import json
import time
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI
import os
import datetime

def run_iperf_pair(h1, h2, duration, cca):
    """Run iperf3 for one CCA. Returns average receiver goodput (bps)."""
    # Launch a one-shot JSON iperf3 server on h2
    info(f"  Starting iperf3 server on {h2.name}...\n")
    h2.cmd(f'iperf3 -s -p 5001 -1 -J > /tmp/iperf_server_{cca}.json &')
    time.sleep(1)  # Allow server to bind

    # Run the iperf3 client on h1
    info(f"  Running iperf3 client on {h1.name} for {duration}s (CCA: {cca})...\n")
    client_out = h1.cmd(f'iperf3 -c {h2.IP()} -p 5001 -t {duration} -C {cca} -J')
    
    try:
        report = json.loads(client_out)
        bps = report["end"]["sum_received"]["bits_per_second"]
    except (KeyError, ValueError) as e:
        info(f"*** Failed to parse iperf3 JSON for {cca}: {e}\n")
        bps = 0
    return bps

def configure_bottleneck(intf, bw_mbit: float, delay_ms: float, reorder: bool):
    """Attach a root netem qdisc adding bandwidth limit, delay & reordering."""
    # Remove any existing qdisc
    intf.cmd(f'tc qdisc del dev {intf.name} root || true')
    
    # Base netem command for rate and delay
    tc_cmd = (
        f'tc qdisc add dev {intf.name} root netem '
        f'rate {bw_mbit}Mbit delay {delay_ms}ms'
    )
    
    # Conditionally add reordering parameters
    if reorder:
        info(f"*** Configuring bottleneck on {intf.name} with reordering\n")
        tc_cmd += ' reorder 25% 50%'
    else:
        info(f"*** Configuring bottleneck on {intf.name} without reordering\n")
        
    intf.cmd(tc_cmd)

def setup_bridge_relay(relay):
    """Turn Mininet host *relay* into an L2 bridge (br0)."""
    relay.cmd('ip link add br0 type bridge')
    relay.cmd('ip link set dev br0 up')
    # Add relay's interfaces to the bridge
    for iface in relay.intfList():
        if 'lo' not in iface.name:
            relay.cmd(f'ip link set dev {iface.name} up')
            relay.cmd(f'ip link set dev {iface.name} master br0')
            # Flush any IP addresses so the host is invisible at L3
            relay.cmd(f'ip addr flush dev {iface.name}')

def main():
    parser = argparse.ArgumentParser(description='Mininet packet-reordering demo')
    # res_path
    parser.add_argument('--res_path', type=str, default="", help='Result path')
    parser.add_argument('--bw', type=float, default=10, help='Bottleneck bandwidth in Mbit/s (default: 10)')
    parser.add_argument('--rtt', type=float, default=100, help='Target path RTT in ms (default: 100)')
    parser.add_argument('--duration', type=int, default=20, help='iperf3 test duration in seconds')
    parser.add_argument('--cca', default='bbr', help='Space-separated list of CCAs to test')
    # Add mutually exclusive flags for controlling reordering
    reorder_group = parser.add_mutually_exclusive_group()
    reorder_group.add_argument('--reorder', dest='reorder', action='store_true', help='Enable packet reordering emulation (default)')
    reorder_group.add_argument('--no-reorder', dest='reorder', action='store_false', help='Disable packet reordering emulation')
    parser.add_argument('--cli', action='store_true', help='Enter Mininet CLI after tests')
    parser.set_defaults(reorder=True)
    args = parser.parse_args()

    if args.res_path:
        print(f"Res path: {args.res_path}")

    one_way_delay = args.rtt / 2.0  # ms

    # It's good practice to set the log level
    # setLogLevel('info')
    setLogLevel('critical')

    info('*** Creating Mininet topology (h1-r-h2)\n')
    net = Mininet(link=TCLink, build=False)  # No controller needed for a bridge
    h1 = net.addHost('h1')
    h2 = net.addHost('h2')
    r = net.addHost('r') # This host will act as a relay/bridge

    # Links are high-speed by default; we apply the bottleneck on a specific interface
    net.addLink(h1, r, cls=TCLink)
    net.addLink(r, h2, cls=TCLink)

    net.build()
    net.start()

    info('*** Setting up relay host as L2 bridge\n')
    setup_bridge_relay(r)
    
    # Configure the bottleneck on the interface from the relay to h2
    bottleneck_intf = r.intf('r-eth1')  # Interface toward h2
    configure_bottleneck(bottleneck_intf, args.bw, one_way_delay, args.reorder)


    info(f'*** Testing CCA={args.cca}\n')
    # Ensure kernel module is loaded
    h1.cmd(f'modprobe tcp_{args.cca} || true')
    goodput = run_iperf_pair(h1, h2, args.duration, args.cca)
    info(f'    {args.cca}: {goodput/1e6:.2f} Mbit/s average receiver rate\n')

    info('\n=== Summary ===\n')
    result_str = f'{args.cca:>8}: {goodput/1e6:.2f} Mbit/s'
    print(f'{args.cca:>8}: {goodput/1e6:.2f} Mbit/s')

    if args.cli:
        CLI(net)

    net.stop()
    if args.res_path:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_path = "/home/ubuntu/FlightSize/Results/overhead/"
        res_path = os.path.join(base_path, args.res_path)
        if not os.path.exists(res_path):
            os.makedirs(res_path)
        save_path = os.path.join(res_path, f"{timestamp}.txt")
        with open(save_path, "w") as f:
            f.write(result_str)
    return result_str

if __name__ == '__main__':
    main()
