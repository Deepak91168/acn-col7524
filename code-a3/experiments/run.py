#!/usr/bin/env python3
"""From code-a3: sudo python3 experiments/run.py "$PWD/.venv/bin/ryu-manager".
Runs all six cases and replaces results. ONLY_P3=1 runs just the two load cases.
"""
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from p1_topo import CustomTopo as Two
from p3_topo import CustomTopo as Ring

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results'


def tables(net, out, label):
    out.write(label + '\n')
    for switch in net.switches:
        out.write('SWITCH ' + switch.name + '\n')
        out.write(switch.cmd('ovs-ofctl -O OpenFlow13 dump-flows ' + switch.name))


def run(name, app, topo, extra=None, congestion=False):
    print('RUN ' + name, flush=True)
    subprocess.run(['mn', '-c'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    env = os.environ.copy()
    # Prevent shell settings from accidentally changing the static comparison.
    for key in ('CONGESTION', 'DELAY12'):
        env.pop(key, None)
    env.update(extra or {})
    net = None
    processes, handles = [], []
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
            if topo is Ring:
                time.sleep(6)  # Warm-up rules have a five-second idle timeout.
            h1, h2 = net.get('h1', 'h2')
            if congestion:
                h3 = net.get('h3')
                # Track just our processes; do not kill unrelated iperf sessions.
                for host, args, suffix in [
                    (h2, ['iperf', '-s', '-u', '-p', '5001'], '-background-server.log'),
                    (h1, ['iperf', '-c', '10.0.0.2', '-u', '-b', '1.8M', '-t', '24', '-p', '5001'], '-background-client.log'),
                ]:
                    handle = open(OUT / (name + suffix), 'w')
                    handles.append(handle)
                    processes.append(host.popen(args, stdout=handle, stderr=subprocess.STDOUT))
                    if host is h2:
                        time.sleep(0.2)
                time.sleep(5)
                out.write('UNDER LOAD PING h1 -> h3\n' + h1.cmd('ping -c 5 -i 0.2 10.0.0.3'))
                receiver = open(OUT / (name + '-receiver.log'), 'w')
                handles.append(receiver)
                processes.append(h3.popen(['iperf', '-s', '-u', '-i', '1', '-p', '5002'], stdout=receiver, stderr=subprocess.STDOUT))
                time.sleep(0.2)
                out.write('FOREGROUND UDP 0.6 Mbps h1 -> h3\n' + h1.cmd('iperf -c 10.0.0.3 -u -b 600K -t 8 -p 5002'))
                out.write('SERVER\n' + (OUT / (name + '-receiver.log')).read_text())
            else:
                target = '10.0.0.5' if topo is Two else '10.0.0.3'
                out.write('MEASURED PING\n' + h1.cmd('ping -c 10 -i 0.2 ' + target))
            tables(net, out, 'FINAL FLOW TABLES')
        finally:
            for process in processes:
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=5)
            for handle in handles:
                handle.close()
            if net:
                net.stop()
            controller.terminate()
            controller.wait(timeout=10)
    if topo is Two:
        count = (OUT / (name + '-controller.log')).read_text().count('Packet-In:')
        with open(OUT / (name + '.txt'), 'a') as out:
            out.write('Logged forwarding Packet-In events: ' + str(count) + '\n')
    print('DONE ' + name, flush=True)


if __name__ == '__main__':
    if os.geteuid() != 0:
        sys.exit('Run this script with sudo and system Python (Mininet).')
    if len(sys.argv) != 2:
        sys.exit('Usage: sudo python3 experiments/run.py /absolute/path/to/ryu-manager')
    ryu = str(Path(sys.argv[1]).resolve())
    os.chdir(ROOT)
    OUT.mkdir(exist_ok=True)
    for args in [
        ('p1-reactive', 'p1/reactive.py', Two),
        ('p1-proactive', 'p1/proactive.py', Two),
        ('p2-base', 'p2/routing.py', Ring),
        ('p2-changed', 'p2/routing.py', Ring, {'DELAY12': '40'}),
        ('p3-static', 'p2/routing.py', Ring, {}, True),
        ('p3-adaptive', 'p2/routing.py', Ring, {'CONGESTION': '1'}, True),
    ]:
        if not os.getenv('ONLY_P3') or args[0].startswith('p3-'):
            run(*args)
