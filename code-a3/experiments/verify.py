"""Check saved experiment evidence: python3 experiments/verify.py."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'results'
CASES = ['p1-reactive', 'p1-proactive', 'p2-base', 'p2-changed', 'p3-static', 'p3-adaptive']


def text(name):
    return (RESULTS / (name + '.txt')).read_text()


def mean_rtt(name):
    match = re.search(r'rtt min/avg/max/mdev = [\d.]+/([\d.]+)/', text(name))
    if not match:
        raise AssertionError('Missing RTT: ' + name)
    return float(match[1])


def receiver_rates(name):
    section = text(name).split('SERVER\n', 1)[1].split('FINAL FLOW TABLES', 1)[0]
    rates = []
    for line in section.splitlines():
        m = re.search(r'(\d+\.\d+)-(\d+\.\d+) sec.*?([\d.]+) ([KMG]?)bits/sec', line)
        if m and abs(float(m[2]) - float(m[1]) - 1) < 0.01 and float(m[2]) <= 7.01:
            rates.append(float(m[3]) * {'': 1, 'K': 1000, 'M': 1000000, 'G': 1000000000}[m[4]] / 1e6)
    assert len(rates) == 7, (name, rates)
    return rates


def check():
    for name in CASES:
        data = text(name)
        log = (RESULTS / (name + '-controller.log')).read_text()
        assert 'PINGALL loss percent: 0.0' in data, name
        assert re.search(r'(10|5) packets transmitted, \1 received, 0% packet loss', data), name
        assert 'Traceback' not in log and 'OFPError' not in log, name
        assert 'INITIAL FLOW TABLES' in data and 'FINAL FLOW TABLES' in data, name
        mean_rtt(name)
        print('PASS connectivity, ping and controller log: ' + name)
    reactive = text('p1-reactive')
    proactive = text('p1-proactive')
    assert int(re.search(r'events: (\d+)', reactive)[1]) > 0
    assert 'priority=1,in_port=' in reactive
    initial = proactive.split('PINGALL', 1)[0]
    assert initial.count('priority=10') == 10 and initial.count('priority=5') == 2
    assert 'CONTROLLER' not in proactive
    print('PASS Part 1: reactive demand rules, proactive rules before traffic')
    for name, path, reverse, port in [
        ('p2-base', '[1, 2, 3]', '[3, 2, 1]', 2),
        ('p2-changed', '[1, 4, 3]', '[3, 4, 1]', 3),
        ('p3-static', '[1, 2, 3]', '[3, 2, 1]', 2),
        ('p3-adaptive', '[1, 4, 3]', '[3, 4, 1]', 3),
    ]:
        log = (RESULTS / (name + '-controller.log')).read_text()
        decisions = [l for l in log.splitlines() if 'PATH 1 -> 3:' in l]
        assert ': ' + path + ' adaptive=' in decisions[-1], name
        assert 'PATH 3 -> 1: ' + reverse in log, name
        final = text(name).split('FINAL FLOW TABLES', 1)[1]
        s1 = final.split('SWITCH s1\n', 1)[1].split('SWITCH s2', 1)[0]
        assert any('priority=10,ip,' in l and 'dl_src=00:00:00:00:00:01' in l
                   and 'dl_dst=00:00:00:00:00:03' in l and 's1-eth' + str(port) in l
                   for l in s1.splitlines()), name
        if name == 'p3-adaptive':
            assert float(re.search(r"'\(1, 2\)': ([\d.]+)", decisions[-1])[1]) > 0.70
            assert any('PATH 1 -> 3: [1, 2, 3] adaptive=True' in l for l in decisions)
            assert any('priority=10,ip,' in l and 'dl_src=00:00:00:00:00:01' in l
                       and 'dl_dst=00:00:00:00:00:02' in l and 's1-eth2' in l
                       for l in s1.splitlines()), 'Existing background rule moved'
        print('PASS forward/reverse selected paths and s1 output rule: ' + name)
    static = sum(receiver_rates('p3-static')) / 7
    adaptive = sum(receiver_rates('p3-adaptive')) / 7
    assert adaptive > static, (static, adaptive)
    print(f'PASS congestion comparison: receiver {static:.3f} -> {adaptive:.3f} Mbps')
    assert ROOT.joinpath('p1_topo.py').is_file() and ROOT.joinpath('p3_topo.py').is_file()
    print('All saved experiment checks passed.')


if __name__ == '__main__':
    check()
