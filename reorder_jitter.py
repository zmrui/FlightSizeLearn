#!/usr/bin/env python3
"""
mininet_reorder_topo.py
======================
A self‑contained Mininet experiment that emulates packet reordering on a
bottleneck link and measures its impact on TCP (CUBIC/BBR) with iperf3.

*Now runs iperf3 **silently** – only the final receiver bitrate is printed.*

Usage (as root):
    sudo python3 mininet_reorder_topo.py --bw 10 --rtt 50 \
         [--enable-reorder] [--reorder-pct 25 --corr-pct 50] [--cca bbr]

Arguments
---------
--bw              Bottleneck bandwidth in **Mbit/s** (default 10)
--rtt             Target RTT across the bottleneck in **ms** (default 50)
--enable-reorder  Add out‑of‑order delivery via *netem*
--reorder-pct     Percentage of packets to reorder when enabled (default 25)
--corr-pct        Reordering correlation (see tc‑netem docs, default 50)
--cca             TCP congestion control algorithm on both hosts
                  (default "cubic"; set to "bbr" if your kernel supports it)

What it does
------------
1. Builds a two‑host, two‑switch topology with a single configurable
   bottleneck link (`bw`, `rtt/2` each direction).
2. Optionally attaches a *netem* qdisc with `delay 0ms reorder …` to both
   directions of the bottleneck, causing out‑of‑order delivery without loss.
3. Starts an iperf3 server on **h2**, runs a 20‑second client on **h1** with JSON
   output captured silently, parses the receiver throughput, and prints the
   average in Mbit/s.

Requirements: Mininet ≥ 2.3.0, iperf3, and root privileges.
"""

import argparse
import json
import sys
import time
from subprocess import PIPE

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.node import OVSController
from mininet.log import setLogLevel, info


class ReorderTopo(Topo):
    """A two‑host topology with a configurable bottleneck link."""

    def build(self, bw_mbps: float, delay_ms: float):
        h1 = self.addHost("h1")
        h2 = self.addHost("h2")
        s1 = self.addSwitch("s1")
        s2 = self.addSwitch("s2")

        # Fat access links
        self.addLink(h1, s1, cls=TCLink, bw=1000)
        self.addLink(h2, s2, cls=TCLink, bw=1000)

        # Bottleneck (bw + one‑way delay = RTT/2)
        self.addLink(
            s1,
            s2,
            cls=TCLink,
            bw=bw_mbps,
            delay=f"{delay_ms}ms",
            max_queue_size=1000,
            use_tbf=True,
        )


def apply_reorder(net, reorder_pct: float, corr_pct: float):
    """Attach a netem qdisc that reorders packets on both directions."""

    s1, s2 = net.get("s1"), net.get("s2")
    link = net.linksBetween(s1, s2)[0]
    for intf in (link.intf1, link.intf2):
        # Chain netem **below** the existing TBF to keep the rate‑limit
        cmd = (
            f"tc qdisc add dev {intf} parent 5:1 handle 10: "
            f"netem delay 0ms reorder {reorder_pct}% {corr_pct}%"
        )
        info(f"*** {cmd}\n")
        intf.node.cmd(cmd)


def set_congestion_control(hosts, cca: str):
    for h in hosts:
        h.cmd(f"sysctl -w net.ipv4.tcp_congestion_control={cca}")
        if cca.lower() == "bbr":
            h.cmd("sysctl -w net.core.default_qdisc=fq")

def apply_jitter(net, rtt_ms: float, jitter_ms: float):
    """Attach a netem qdisc that reorders packets via jitter."""

    s1, s2 = net.get("s1"), net.get("s2")
    link = net.linksBetween(s1, s2)[0]
    base_delay_ms = rtt_ms / 2.0

    for intf in (link.intf1, link.intf2):
        # USE 'tc qdisc change' to MODIFY the existing netem qdisc (5:1)
        # created by TCLink. This is the correct and reliable method.
        # We must re-state the base delay and add the jitter to it.
        # The parent is 5:0 (the TBF) and the handle we are changing is 5:1.
        cmd = (
            f"tc qdisc change dev {intf} parent 5:0 handle 5:1 "
            f"netem delay {base_delay_ms}ms {jitter_ms}ms"
        )
        info(f"*** {cmd}\n")
        print(intf.node.cmd(cmd))

def run_iperf(net, cca: str) -> float:
    """Run a 20‑second iperf3 test **quietly** and return receiver throughput."""

    h1, h2 = net.get("h1"), net.get("h2")
    set_congestion_control((h1, h2), cca)

    # Start silent iperf3 server (‑1 exits after one test)
    h2.popen("iperf3 -s -1 -J > /dev/null 2>&1", shell=True)
    time.sleep(1)  # ensure it is listening

    info("*** Running 20‑second iperf3 test (quiet)\n")
    client = h1.popen(
        ["iperf3", "-c", h2.IP(), "-t", "20", "-J"],
        stdout=PIPE,
        stderr=PIPE,
        text=True,
    )
    out, _ = client.communicate()
    result = json.loads(out)

    recv_bps = result["end"]["sum_received"]["bits_per_second"]
    return recv_bps / 1e6  # → Mbit/s


def main():
    p = argparse.ArgumentParser(description="Mininet packet reordering demo")
    p.add_argument("--bw", type=float, default=10, help="Bottleneck bw (Mbit/s)")
    p.add_argument("--rtt", type=float, default=50, help="RTT across link (ms)")
    p.add_argument("--jitter_ms", type=float, default=0, help="Add jitter (ms) to cause reordering. A value > 0 enables it.")
    p.add_argument("--cca", default="cubic", help="TCP CC algo (cubic | bbr)")
    args = p.parse_args()

    # Mininet
    setLogLevel("info")
    topo = ReorderTopo(bw_mbps=args.bw, delay_ms=args.rtt / 2)
    net = Mininet(topo=topo, link=TCLink, controller=OVSController, autoSetMacs=True,xterms=True)

    try:
        net.start()

        # if args.enable_reorder:
        #     info("*** Enabling packet reordering\n")
        #     apply_reorder(net, args.reorder_pct, args.corr_pct)
        if args.jitter_ms > 0:
            info(f"*** Enabling packet reordering via {args.jitter_ms}ms jitter\n")
            apply_jitter(net, args.rtt, args.jitter_ms)


        input()
        raise RuntimeError
        mbps = run_iperf(net, args.cca)
        info(f"\n*** Receiver average bitrate: {mbps:.2f} Mbit/s\n")

    finally:
        net.stop()


if __name__ == "__main__":
    main()
