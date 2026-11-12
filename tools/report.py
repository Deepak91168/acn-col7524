"""Build Report.pdf from saved results using ReportLab and installed Arial fonts.
Usage from the repository root: .venv/bin/pip install -r tools/requirements.txt
                               .venv/bin/python tools/report.py
"""
from pathlib import Path
import re
import subprocess
from xml.sax.saxutils import escape
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from verify import CASES, check, text, mean_rtt, receiver_rates, result_path, ROOT


def font_path(pattern):
    return subprocess.check_output(['fc-match', '-f', '%{file}', pattern], text=True).strip()


for name, pattern in [('Arial', 'Arial'), ('Arial-Bold', 'Arial:style=Bold'), ('Arial-Italic', 'Arial:style=Italic')]:
    path = font_path(pattern)
    if 'arial' not in Path(path).name.lower():
        raise RuntimeError('Arial is required to regenerate this report; install Arial first.')
    pdfmetrics.registerFont(TTFont(name, path))
pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='Arial-Bold', italic='Arial-Italic', boldItalic='Arial-Bold')
body = ParagraphStyle('Body', fontName='Arial', fontSize=10.2, leading=14, spaceAfter=8)
heading = ParagraphStyle('Heading', parent=body, fontName='Arial-Bold', fontSize=15, leading=19, spaceAfter=12)
subhead = ParagraphStyle('Subheading', parent=body, fontName='Arial-Bold', fontSize=11, leading=15, spaceBefore=5)
small = ParagraphStyle('Small', parent=body, fontSize=9, leading=12, spaceAfter=5)
logstyle = ParagraphStyle('Log', parent=small, fontSize=8.5, leading=11, leftIndent=7, rightIndent=7, spaceAfter=3)
caption = ParagraphStyle('Caption', parent=small, fontName='Arial-Italic', alignment=1, spaceAfter=10)
story = []
WIDTH = 511


def p(s, style=body):
    story.append(Paragraph(s, style))


def h(s):
    p(s, heading)


def table(rows, widths=None):
    cells = [[Paragraph(escape(str(cell)), small) for cell in row] for row in rows]
    t = Table(cells, colWidths=widths, hAlign='LEFT', repeatRows=1)
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEABOVE', (0, 0), (-1, 0), 0.8, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 0.6, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 0.8, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 9))


def logs(label, lines):
    content = [Paragraph(escape(label), small)]
    for line in lines:
        content.append(Paragraph(escape(line), logstyle))
    t = Table([[content]], colWidths=[WIDTH])
    t.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 0.5, colors.black), ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
    story.append(t)
    story.append(Spacer(1, 9))


def label(d, x, y, text, size=9, bold=False):
    d.add(String(x, y, text, fontName='Arial-Bold' if bold else 'Arial', fontSize=size, textAnchor='middle', fillColor=colors.black))


def node(d, x, y, name):
    d.add(Rect(x-17, y-11, 34, 22, strokeColor=colors.black, fillColor=colors.white))
    label(d, x, y-3, name, bold=True)


def diagram(part, adaptive=False):
    if part == 1:
        d = Drawing(WIDTH, 115)
        for x, name in [(150, 's1'), (365, 's2')]:
            node(d, x, 65, name)
        d.add(Line(167, 65, 348, 65, strokeColor=colors.black))
        label(d, 258, 77, '10 Mbps, 5 ms')
        for x, host in [(85, 'h1'), (150, 'h2'), (215, 'h3')]:
            d.add(Line(x, 18, 150, 54, strokeColor=colors.black)); node(d, x, 12, host)
        for x, host in [(330, 'h4'), (400, 'h5')]:
            d.add(Line(x, 18, 365, 54, strokeColor=colors.black)); node(d, x, 12, host)
        label(d, 258, 103, 'Ryu controller: 127.0.0.1:6633', size=10)
        for x in (150, 365):
            d.add(Line(258, 95, x, 77, strokeColor=colors.black, strokeDashArray=[3, 3]))
    else:
        d = Drawing(WIDTH, 160)
        points = {1:(140,110), 2:(370,110), 3:(370,30), 4:(140,30)}
        for a,b in [(1,2),(2,3),(3,4),(4,1)]:
            x,y=points[a]; xx,yy=points[b]
            d.add(Line(x,y,xx,yy,strokeColor=colors.black,strokeWidth=1))
        # The adaptive route is bold; the static route is dashed in the load figure.
        if adaptive:
            for a,b in [(1,4),(4,3)]:
                x,y=points[a]; xx,yy=points[b]
                d.add(Line(x,y,xx,yy,strokeColor=colors.black,strokeWidth=2.7))
            for a,b in [(1,2),(2,3)]:
                x,y=points[a]; xx,yy=points[b]
                dx, dy = (3, 0) if x == xx else (0, 3)
                d.add(Line(x+dx,y+dy,xx+dx,yy+dy,strokeColor=colors.black,strokeDashArray=[4,3]))
        label(d,255,124,'2 Mbps, 20 ms' + (' | background h1 -> h2' if adaptive else ''))
        label(d,430,73,'2 Mbps, 10 ms')
        label(d,255,10,'1 Mbps, 20 ms')
        label(d,76,73,'1 Mbps, 15 ms')
        for i,(x,y) in points.items():
            direction=-1 if i in (1,4) else 1
            d.add(Line(x,y,x+direction*62,y,strokeColor=colors.black))
            node(d,x+direction*80,y,'h'+str(i)); node(d,x,y,'s'+str(i))
        if adaptive:
            label(d,255,146,'New h1 -> h3 traffic: bold = adaptive, dashed = static',size=9)
        else:
            label(d,255,146,'Unchanged supplied ring; each host uses switch port 1',size=9)
    story.append(d)


def decision(name, source=1, dest=3):
    lines=result_path(name+'-controller.log').read_text().splitlines()
    return [s for s in lines if f'PATH {source} -> {dest}:' in s][-1]


def p1_rules(name, stage, include_broadcast=False):
    data = text(name)
    if stage == 'before':
        section = data.split('INITIAL FLOW TABLES\n', 1)[1].split('PINGALL', 1)[0]
    else:
        section = data.split('FINAL FLOW TABLES\n', 1)[1]
    lines = []
    for block in section.split('SWITCH ')[1:]:
        switch = block.splitlines()[0]
        for line in block.splitlines()[1:]:
            if 'priority=' not in line:
                continue
            if stage == 'before' and name == 'p1-reactive':
                selected = True
            else:
                # Show both directions of the cross-switch h1/h5 conversation.
                selected = ('dl_dst=00:00:00:00:00:05' in line or
                            'dl_dst=00:00:00:00:00:01' in line)
                if name == 'p1-reactive':
                    selected = selected and ('in_port="'+switch+'-eth'+('1' if switch=='s1' else '3')+'"' in line
                        if 'dl_dst=00:00:00:00:00:05' in line else
                        'in_port="'+switch+'-eth'+('4' if switch=='s1' else '2')+'"' in line)
                if include_broadcast and 'priority=5,' in line:
                    selected = True
            if selected:
                lines.append(switch + ': ' + line[line.index('n_packets='):].strip())
    return lines


def p1_success(name):
    return [line.strip() for line in text(name).splitlines()
            if line.startswith(('PINGALL loss percent:', '10 packets transmitted,',
                                'rtt min/avg/max/mdev =', 'Logged forwarding Packet-In events:'))]


def p1_evidence(name, proactive=False):
    story.append(PageBreak())
    h('1.' + ('2 Proactive' if proactive else '1 Reactive') + ' forwarding: recorded evidence')
    p('Source: p1/results/' + name + '.txt and p1/results/' + name + '-controller.log. Flow rows retain packet/byte counters, priority, match and action; only the cookie, duration and table number are omitted.', small)
    logs('Commands used for controller and switch inspection', [
        '.venv/bin/ryu-manager --ofp-tcp-listen-port 6633 p1/' + ('proactive.py' if proactive else 'reactive.py'),
        'sudo python3 p1/p1_topo.py',
        'ovs-ofctl -O OpenFlow13 dump-flows s1',
        'ovs-ofctl -O OpenFlow13 dump-flows s2'])
    p('The driver takes the first table dump before pingAll and the ten h1-h5 pings, then takes the final dump after those tests. It runs the same controller/topology and invokes these flow-table commands through Mininet.',small)
    if proactive:
        logs('Before tests: destination rules and broadcast rule already present', p1_rules(name,'before',True))
    else:
        logs('Before tests: only the table-miss rule on each switch', p1_rules(name,'before'))
    controller = result_path(name+'-controller.log').read_text().splitlines()
    if proactive:
        selected = [line for line in controller if line.startswith('Switch ') or
                    line.startswith('All proactive rules') or
                    (line.startswith('Installed:') and 'dst=h5 ' in line)]
    else:
        selected = [line for line in controller if line.startswith('Switch ') or
                    ('Packet-In:' in line and
                     'src=00:00:00:00:00:01 dst=00:00:00:00:00:05' in line)]
    logs('Selected Ryu output',selected)
    logs('After tests: h1/h5 forwarding rules and their packet counters',p1_rules(name,'after'))
    logs('Connectivity and controller-workload results',p1_success(name))
    if proactive:
        p('The h5 rules exist before testing with zero packet counters. Afterwards, those same matches and output ports have nonzero counters: s1 sends h5 traffic over port 4, and s2 sends it to host port 2. Rules for h1 carry replies in the other direction. This shows that the preinstalled rules actually forwarded packets.')
        p('Both switches also have a broadcast rule before the test. There is no CONTROLLER action in the proactive tables, so normal forwarding does not need Packet-In handling. The two successful ping checks provide the connectivity evidence alongside the installation log.',small)
    else:
        p('Initially, unmatched packets go to Ryu. The Packet-In lines show h1-to-h5 packets reaching the controller on both switches. The final tables then contain priority-1 unicast rules with nonzero counters: h1-to-h5 uses s1 port 4 and s2 port 2; replies use s2 port 3 and s1 port 1.')
        p('The initial table-miss counters are already nonzero because hosts generate background Ethernet traffic before the controlled ping tests. There are still no learned unicast rules in that first snapshot. The total Packet-In count includes that startup traffic, pingAll and the measured pings.',small)


def ring_rules(name, initial=False, only_s1=False, background=False):
    data = text(name)
    section = (data.split('INITIAL FLOW TABLES\n',1)[1].split('PINGALL',1)[0]
               if initial else data.split('FINAL FLOW TABLES\n',1)[1])
    rows = []
    for block in section.split('SWITCH ')[1:]:
        switch = block.splitlines()[0]
        if only_s1 and switch != 's1':
            continue
        for line in block.splitlines()[1:]:
            if 'priority=' not in line:
                continue
            destination = '02' if background else '03'
            if initial or ('priority=10,ip,' in line and
                           'dl_src=00:00:00:00:00:01' in line and
                           'dl_dst=00:00:00:00:00:'+destination in line):
                rows.append(switch+': '+line[line.index('n_packets='):].strip())
    return rows


def ping_summary(name):
    return [line.strip() for line in text(name).splitlines()
            if line.startswith(('PINGALL loss percent:', '10 packets transmitted,',
                                '5 packets transmitted,', 'rtt min/avg/max/mdev ='))]


def p2_evidence():
    story.append(PageBreak()); h('2.1 Route selection: recorded evidence')
    p('Source: p2/results/p2-base.txt, p2/results/p2-changed.txt and their controller logs. The selected flow rows retain counters, timeout, match and action; cookie, duration and table number are omitted.',small)
    logs('Before traffic: table-miss rules on the four switches',ring_rules('p2-base',initial=True))
    for name, label in [('p2-base','Normal costs'),('p2-changed','DELAY12=40')]:
        logs(label+': Ryu forward and reverse paths',[
            decision(name).split(' utilization=')[0],
            decision(name,3,1).split(' utilization=')[0]])
        logs(label+': final h1-to-h3 IPv4 rules',ring_rules(name))
        logs(label+': connectivity and h1-h3 ping',ping_summary(name))
    p('The normal-cost rules send packets from s1 port 2 to s2 port 3 and then s3 port 1. After changing the s1-s2 cost, s1 uses port 3 instead, s4 forwards through port 2, and s3 still delivers through host port 1. Each rule has a nonzero packet counter. The reverse PATH entries and zero-loss pings confirm that replies work too.')


def p3_evidence():
    story.append(PageBreak()); h('3.1 Congestion test: recorded evidence')
    p('Source: p3/results/p3-static.txt, p3/results/p3-adaptive.txt and their controller/receiver logs. The workload and routing rules are shown below.',small)
    logs('Traffic commands (started on the indicated Mininet hosts)',[
        'h2: iperf -s -u -p 5001',
        'h1: iperf -c 10.0.0.2 -u -b 1.8M -t 24 -p 5001',
        'h3: iperf -s -u -i 1 -p 5002',
        'h1: iperf -c 10.0.0.3 -u -b 600K -t 8 -p 5002'])
    logs('Under load: Ryu path decisions with measured utilization',[
        decision('p3-static'), decision('p3-adaptive')])
    logs('Final s1 rules: static foreground, adaptive foreground, adaptive background',
         ring_rules('p3-static',only_s1=True)+ring_rules('p3-adaptive',only_s1=True)+
         ring_rules('p3-adaptive',only_s1=True,background=True))
    p('For h1-h3, s1 changes from output port 2 to port 3. The active h1-h2 background rule still uses port 2. Thus the later host pair uses the updated measurements without moving the existing background traffic.',small)
    for name in ('p3-static','p3-adaptive'):
        section=text(name).split('SERVER\n',1)[1].split('FINAL FLOW TABLES',1)[0]
        intervals=[line.strip() for line in section.splitlines()
                   if re.search(r'0\.0000-1\.0000 sec|1\.0000-2\.0000 sec',line)]
        logs(name+': first two receiver intervals',intervals)
    logs('Static h1-h3 ping',ping_summary('p3-static'))
    logs('Adaptive h1-h3 ping',ping_summary('p3-adaptive'))
    p('The receiver intervals show the reduced delivery rate on the shared upper link and the higher rate on the alternate route. The comparison uses seven complete intervals from each log. Queued traffic can keep arriving after the static sender stops, so its final summary/ACK is excluded.',small)


check()
h('Assignment 3: Software-Defined Networking')
p('COL7524: Advanced Networks<br/><b>Deepak - 2025CSY7616</b><br/><b>Pratik - 2025MCS2096</b>')
p('We used the two supplied topologies without changing their links, delays or host connections. The experiments below compare reactive and proactive rules, shortest-delay routing, and routing that reacts to link load. All results come from the saved Mininet runs included with this report.')
p('1. Reactive and proactive flow management', subhead)
diagram(1)
p('Figure 1. The two-switch topology used in Part 1. Dashed lines show controller connections.', caption)
p('The reactive controller learns the incoming port for each source MAC. An unknown destination is flooded; once its port is known, the controller installs a forwarding rule. The proactive controller already knows where all five hosts are connected, so it installs five destination rules and one broadcast rule on each switch before testing begins.')
p('For each controller, we started a clean network, saved the initial tables, ran pingAll, and sent ten pings from h1 to h5. We then saved the final tables and counted the reactive controller\'s Packet-In log entries. The count covers the whole test sequence, including ARP and other non-LLDP Ethernet traffic handled by that application.')
counts=[int(re.search(r'events: (\d+)',text(n))[1]) for n in CASES[:2]]
table([['Measure','Reactive','Proactive'],['pingAll loss','0%','0%'],['Forwarding Packet-In events',*counts],['Mean h1-h5 ping RTT (ms)',f'{mean_rtt(CASES[0]):.3f}',f'{mean_rtt(CASES[1]):.3f}'],['Initial rules per switch','1 table-miss rule','6 forwarding rules']], [235,138,138])
p('The warmed-up RTTs are close because both switches then forward locally. The main difference is at setup: reactive forwarding needs controller decisions for initial traffic but installs rules only when needed. Proactive forwarding avoids that initial controller work, but needs advance knowledge and installs rules even for unused destinations. First-packet delay was not measured separately here.')
p('The proactive count is supported by its flow tables: there is no output-to-controller rule. The before/after tables, Ryu output and successful ping summaries on pages 2-3 show this difference.',small)

p1_evidence('p1-reactive')
p1_evidence('p1-proactive', proactive=True)

story.append(PageBreak()); h('2. Link-metric-based path selection')
diagram(2)
p('Figure 2. Parts 2 and 3 use this four-switch ring. Link labels give bandwidth and delay.',caption)
p('We chose delay as the static metric. The controller in p2/routing.py stores the ring in a NetworkX graph and uses the sum of link delays as path cost. The host MAC addresses and switch ports are fixed to the supplied topology: h1-h4 connect to port 1 of s1-s4. This keeps the implementation small; automatic topology or host discovery is not needed for this fixed experiment.')
p('For each new source/destination MAC pair and EtherType, the controller finds the lowest-cost path and installs OpenFlow 1.3 rules along it. Reply traffic independently installs the reverse direction. Rules expire after five idle seconds. Broadcast ARP is sent directly to the other host ports by Ryu, rather than flooded around the ring, so there is no broadcast loop.')
table([['Test','Cost through s2','Cost through s4','Chosen h1-h3 route'],['Normal costs','20 + 10 = 30 ms','15 + 20 = 35 ms','s1 -> s2 -> s3'],['DELAY12=40','40 + 10 = 50 ms','15 + 20 = 35 ms','s1 -> s4 -> s3']], [89,120,120,182])
p('In the second test, DELAY12=40 changes only the controller\'s s1-s2 cost. The physical topology stays unchanged. This is a link-cost-change test: the controller should prefer the other route because its total cost is now smaller.')
table([['Measured result','Normal costs','Changed cost'],['pingAll loss','0%','0%'],['Mean h1-h3 RTT (ms)',f'{mean_rtt("p2-base"):.3f}',f'{mean_rtt("p2-changed"):.3f}']], [235,138,138])
logs('Selected controller log lines:', [decision('p2-base').split(' utilization=')[0],decision('p2-base',3,1).split(' utilization=')[0],decision('p2-changed').split(' utilization=')[0],decision('p2-changed',3,1).split(' utilization=')[0]])
p('The unloaded round-trip delays are close to twice the physical one-way path delay: about 60 ms through s2 and 70 ms through s4. The cost change therefore selects the expected path, and the measured RTT follows the physical route. Both forward and reverse paths are present in the logs; pingAll also checks every host pair in both directions.')

p2_evidence()

story.append(PageBreak()); h('3. Congestion-aware routing')
diagram(3,adaptive=True)
p('Figure 3. The background flow loads s1-s2. The later h1-h3 traffic can use the lower route.',caption)
p('The Part 3 controller is in p3/routing.py. It extends the static routing logic with link-utilization measurements; CONGESTION=0 selects the static comparison mode. Ryu requests port statistics once per second. For each inter-switch port we calculate utilization from the change in transmitted bytes:')
logs('Utilization rule', ['utilization = 8 x (new tx_bytes - old tx_bytes) / (elapsed seconds x link capacity in bits/s)', 'link utilization = max(utilization in the two directions)', 'if link utilization > 0.70: routing cost = link delay + 100 ms', 'otherwise: routing cost = link delay'])
p('We ran the same workload once with static routing and once with congestion-aware routing. After pingAll, we waited six seconds for the warm-up rules to expire. A h1-h2 UDP flow, configured for 24 seconds, used iperf -b 1.8M (about 1.89 Mbps) to load the 2 Mbps s1-s2 link. After five seconds of background traffic, we sent five h1-h3 pings and started an eight-second h1-h3 UDP flow at 600K bits/s. The script stops the background flow after this measurement. The nominal UDP rate is about 0.6 Mbps; iperf uses binary K units, so its offered rate is approximately 0.614 Mbps.')
p('The h1-h3 host pair is new at this stage. It gets a path using the current measurements, while the active h1-h2 rules stay in place. Rules match a host pair and EtherType, so the UDP traffic reuses the path chosen for the preceding h1-h3 ping. A later flow for the same pair can choose again after five idle seconds.')
static=sum(receiver_rates('p3-static'))/7
adaptive=sum(receiver_rates('p3-adaptive'))/7
table([['Routing mode','h1-h3 route','Mean RTT (ms)','Receiver Mbps'],['Static','s1 -> s2 -> s3',f'{mean_rtt("p3-static"):.3f}',f'{static:.3f}'],['Congestion-aware','s1 -> s4 -> s3',f'{mean_rtt("p3-adaptive"):.3f}',f'{adaptive:.3f}']], [110,155,120,126])
p('Receiver throughput is the mean of the first seven complete one-second server intervals in each run. We use the same window in both modes and exclude the final UDP summary/ACK, which can be delayed or lost under load. Both runs passed pingAll and the later ping test without loss.',small)
util=float(re.search(r"'\(1, 2\)': ([\d.]+)",decision('p3-adaptive'))[1])
p(f'At the adaptive h1-h3 decision, s1 port 2 utilization was {util:.2f}, above the 0.70 threshold. The upper route therefore costs at least 130 ms, compared with 35 ms through s4. The alternate route delivered more of the foreground traffic in this run, although its propagation delay is longer.')
p('One limitation is the one-second sampling interval: a short burst may finish before it is detected. OVS byte counters can include traffic waiting in the shaped egress queue, so the estimate may reflect offered load rather than exact wire utilization. There is no hysteresis, so paths can alternate near the threshold. We do not reroute active flows, and the fixed host-pair rules do not distinguish individual TCP or UDP sessions.')

p3_evidence()

story.append(PageBreak()); h('4. Setup and run commands')
p('Tested on Linux with Python 3.12.3, Open vSwitch 3.3.9, Ryu 4.34, Mininet and iperf 2.1.9. The supplied topologies are unchanged.')
p('Extract the ZIP. The root contains the three part folders, report, README and shared dependencies. Each part contains its controller, supplied topology, run.py and results/. Run the following commands from that top level:',small)
logs('Setup and complete experiment run',[
'sudo apt install mininet openvswitch-switch iperf python3-venv',
'python3 -m venv .venv',
'.venv/bin/pip install setuptools==67.6.1 wheel',
'.venv/bin/pip install -r requirements.txt',
'sudo systemctl start openvswitch-switch',
'sudo python3 p1/run.py "$PWD/.venv/bin/ryu-manager"',
'sudo python3 p2/run.py "$PWD/.venv/bin/ryu-manager"',
'sudo python3 p3/run.py "$PWD/.venv/bin/ryu-manager"'])
p('Each run.py executes the two cases for its part and replaces its results/. A failed connectivity check stops the run. Mininet runs with system Python and sudo; Ryu runs from the virtual environment. Stop other controllers before running. Use sudo mn -c after an interrupted Mininet run.')
p('For an interactive run, start Ryu and the topology in separate terminals. All controllers listen on port 6633:',small)
table([['Part','Controller command after .venv/bin/ryu-manager','Topology command'],['1 reactive','--ofp-tcp-listen-port 6633 p1/reactive.py','sudo python3 p1/p1_topo.py'],['1 proactive','--ofp-tcp-listen-port 6633 p1/proactive.py','sudo python3 p1/p1_topo.py'],['2','--ofp-tcp-listen-port 6633 p2/routing.py','sudo python3 p2/p3_topo.py'],['3','--ofp-tcp-listen-port 6633 p3/routing.py','sudo python3 p3/p3_topo.py']], [74,274,163])
p('For the changed-cost Part 2 case, prefix its controller command with DELAY12=40. For static Part 3, prefix its controller command with CONGESTION=0. Inside Mininet, use pingall and h1 ping -c 10 h3. Inspect a switch with sh ovs-ofctl -O OpenFlow13 dump-flows s1.',small)



def footer(canvas, doc):
    canvas.setStrokeColor(colors.black)
    canvas.line(42, 37, 553, 37)
    canvas.setFont('Arial', 8)
    canvas.drawString(42, 24, 'COL7524 | Assignment 3 | Deepak and Pratik')
    canvas.drawRightString(553, 24, str(doc.page))


SimpleDocTemplate(str(ROOT/'Report.pdf'), pagesize=(595.28,841.89), leftMargin=42, rightMargin=42,
                  topMargin=35, bottomMargin=48, title='Assignment 3: Software-Defined Networking',
                  author='Deepak and Pratik', initialFontName='Arial').build(story,onFirstPage=footer,onLaterPages=footer)
print('Created',ROOT/'Report.pdf')
