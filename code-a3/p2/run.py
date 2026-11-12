#!/usr/bin/env python3
"""Part 2 experiments. From the submission root:
sudo python3 p2/run.py "$PWD/.venv/bin/ryu-manager"
Replaces this part's results.
"""
import os
from pathlib import Path
import subprocess
import sys
import time

from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from p3_topo import CustomTopo

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results'


def tables(net, out, label):
    out.write(label + '\n')
    for switch in net.switches:
        out.write('SWITCH ' + switch.name + '\n')
        out.write(switch.cmd('ovs-ofctl -O OpenFlow13 dump-flows ' + switch.name))


def run(name, app, topo, extra=None):
    print('RUN ' + name, flush=True)
    subprocess.run(['mn', '-c'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    env = os.environ.copy()
    # Prevent shell settings from accidentally changing the static comparison.
    for key in ('CONGESTION', 'DELAY12'):
        env.pop(key, None)
    env.update(extra or {})
    net = None
    with open(OUT / (name + '-controller.log'), 'w') as log, open(OUT / (name + '.txt'), 'w') as out:
        controller = subprocess.Popen([ryu, '--ofp-tcp-listen-port', '6633', app], stdout=log, stderr=log, env=env)
        try:
            time.sleep(3)
            if controller.poll() is not None:
                raise RuntimeError('Controller failed: ' + name)
            net = Mininet(topo=topo(), controller=None, switch=OVSKernelSwitch, link=TCLink, autoSetMacs=True)
            net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
            net.start()
            if not net.waitConnected(timeout=10):
                raise RuntimeError('Switch connection failed: ' + name)
            time.sleep(2)
            tables(net, out, 'INITIAL FLOW TABLES')
            loss = net.pingAll()
            out.write('PINGALL loss percent: ' + str(loss) + '\n')
            if loss != 0:
                raise RuntimeError('Connectivity failed: ' + name)
            time.sleep(6)  # Warm-up rules have a five-second idle timeout.
            h1, h2 = net.get('h1', 'h2')
            target = '10.0.0.3'
            out.write('MEASURED PING\n' + h1.cmd('ping -c 10 -i 0.2 ' + target))
            tables(net, out, 'FINAL FLOW TABLES')
        finally:
            if net:
                net.stop()
            controller.terminate()
            controller.wait(timeout=10)
    print('DONE ' + name, flush=True)


if __name__ == '__main__':
    if os.geteuid() != 0:
        sys.exit('Run this script with sudo and system Python (Mininet).')
    if len(sys.argv) != 2:
        sys.exit('Usage: sudo python3 p2/run.py /absolute/path/to/ryu-manager')
    ryu = str(Path(sys.argv[1]).resolve())
    os.chdir(ROOT)
    OUT.mkdir(exist_ok=True)
    for args in [
        ('p2-base', 'routing.py', CustomTopo),
        ('p2-changed', 'routing.py', CustomTopo, {'DELAY12': '40'}),
    ]:
        run(*args)
