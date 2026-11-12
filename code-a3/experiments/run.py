#!/usr/bin/env python3
"""Run as root with system Python: sudo python3 experiments/run.py /path/to/ryu-manager"""
import os
import sys
import time
import subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from p1_topo import CustomTopo as Two
from p3_topo import CustomTopo as Ring
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
OUT=ROOT/'results'; OUT.mkdir(exist_ok=True)
ryu=sys.argv[1]

def run(name,app,topo,extra=None,congestion=False):
    subprocess.run(['mn','-c'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    env=os.environ.copy(); env.update(extra or {})
    with open(OUT/(name+'-controller.log'),'w') as log, open(OUT/(name+'.txt'),'w') as out:
        controller=subprocess.Popen([ryu,'--ofp-tcp-listen-port','6633',app],stdout=log,stderr=log,env=env)
        net=None
        try:
            time.sleep(3)
            if controller.poll() is not None: raise RuntimeError('Controller failed: '+name)
            net=Mininet(topo=topo(),controller=None,switch=OVSKernelSwitch,link=TCLink,autoSetMacs=True)
            net.addController('c0',controller=RemoteController,ip='127.0.0.1',port=6633)
            net.start(); net.waitConnected(timeout=10); time.sleep(2)
            out.write('INITIAL FLOW TABLES\n')
            for s in net.switches: out.write(s.cmd('ovs-ofctl -O OpenFlow13 dump-flows '+s.name))
            out.write('PINGALL loss percent: '+str(net.pingAll())+'\n')
            # Remove warm-up rules before measuring a fresh experiment.
            if topo is Ring: time.sleep(6)
            h1,h2=net.get('h1','h2')
            if congestion:
                h3=net.get('h3')
                h2.cmd('iperf -s -u -p 5001 > /tmp/a3-bg.txt 2>&1 &')
                h1.cmd('iperf -c 10.0.0.2 -u -b 1.8M -t 24 -p 5001 > /tmp/a3-load.txt 2>&1 &')
                time.sleep(5)
                out.write('UNDER LOAD PING h1 -> h3\n'+h1.cmd('ping -c 5 -i 0.2 10.0.0.3'))
                h3.cmd('iperf -s -u -i 1 -p 5002 > /tmp/a3-fg.txt 2>&1 &')
                out.write('FOREGROUND UDP 0.6 Mbps h1 -> h3\n'+h1.cmd('iperf -c 10.0.0.3 -u -b 600K -t 8 -p 5002'))
                out.write('SERVER\n'+h3.cmd('cat /tmp/a3-fg.txt'))
            else:
                target='10.0.0.5' if topo is Two else '10.0.0.3'
                out.write('MEASURED PING\n'+h1.cmd('ping -c 10 -i 0.2 '+target))
            out.write('FINAL FLOW TABLES\n')
            for s in net.switches: out.write(s.cmd('ovs-ofctl -O OpenFlow13 dump-flows '+s.name))
            for h in net.hosts: h.cmd('killall iperf 2>/dev/null')
        finally:
            if net: net.stop()
            controller.terminate(); controller.wait(timeout=10)
    if topo is Two:
        count=(OUT/(name+'-controller.log')).read_text().count('Packet-In:')
        with open(OUT/(name+'.txt'),'a') as out: out.write('Logged forwarding Packet-In events: '+str(count)+'\n')

for args in [('p1-reactive','p1/reactive.py',Two),('p1-proactive','p1/proactive.py',Two),('p2-base','p2/routing.py',Ring),('p2-changed','p2/routing.py',Ring,{'DELAY12':'40'}),('p3-static','p2/routing.py',Ring,{},True),('p3-adaptive','p2/routing.py',Ring,{'CONGESTION':'1'},True)]:
    if not os.getenv("ONLY_P3") or args[0].startswith("p3-"):
        run(*args)
