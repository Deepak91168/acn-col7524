"""Build Report.pdf from saved results using ReportLab and installed Arial fonts.
Usage from code-a3: .venv/bin/pip install reportlab
                    .venv/bin/python experiments/report.py
"""
from pathlib import Path
import re
import subprocess
from xml.sax.saxutils import escape
from reportlab.graphics.shapes import Drawing, Line, Rect, String, Circle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from verify import CASES, check, text, mean_rtt, receiver_rates, RESULTS, ROOT


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
    lines=(RESULTS/(name+'-controller.log')).read_text().splitlines()
    return [s for s in lines if f'PATH {source} -> {dest}:' in s][-1]


def forwarding(name):
    final=text(name).split('FINAL FLOW TABLES\n',1)[1]
    rows=[]
    for block in final.split('SWITCH ')[1:]:
        switch=block.splitlines()[0]
        for line in block.splitlines()[1:]:
            if 'priority=10,ip,' in line and 'dl_src=00:00:00:00:00:01' in line and 'dl_dst=00:00:00:00:00:03' in line:
                rows.append([switch, re.search(r'n_packets=(\d+)',line)[1], line.split('actions=',1)[1].strip()])
    return rows


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
p('The proactive count is supported by its flow tables: there is no output-to-controller rule. The flow-table excerpts on page 4 show this difference.',small)

story.append(PageBreak()); h('2. Link-metric-based path selection')
diagram(2)
p('Figure 2. Parts 2 and 3 use this four-switch ring. Link labels give bandwidth and delay.',caption)
p('We chose delay as the static metric. The controller in p2/routing.py stores the ring in a NetworkX graph and uses the sum of link delays as path cost. The host MAC addresses and switch ports are fixed to the supplied topology: h1-h4 connect to port 1 of s1-s4. This keeps the implementation small; automatic topology or host discovery is not needed for this fixed experiment.')
p('For each new source/destination MAC pair and EtherType, the controller finds the lowest-cost path and installs OpenFlow 1.3 rules along it. Reply traffic independently installs the reverse direction. Rules expire after five idle seconds. Broadcast ARP is sent directly to the other host ports by Ryu, rather than flooded around the ring, so there is no broadcast loop.')
table([['Test','Cost through s2','Cost through s4','Chosen h1-h3 route'],['Normal costs','20 + 10 = 30 ms','15 + 20 = 35 ms','s1 -> s2 -> s3'],['DELAY12=40','40 + 10 = 50 ms','15 + 20 = 35 ms','s1 -> s4 -> s3']], [89,120,120,182])
p('In the second test, DELAY12=40 changes only the controller\'s s1-s2 cost. The physical topology stays unchanged. This is a link-cost-change test: the controller should prefer the other route because its total cost is now smaller.')
table([['Measured result','Normal costs','Changed cost'],['pingAll loss','0%','0%'],['Mean h1-h3 RTT (ms)',f'{mean_rtt("p2-base"):.3f}',f'{mean_rtt("p2-changed"):.3f}']], [235,138,138])
logs('Selected controller log lines (utilization dictionaries omitted here):', [decision('p2-base').split(' utilization=')[0],decision('p2-base',3,1).split(' utilization=')[0],decision('p2-changed').split(' utilization=')[0],decision('p2-changed',3,1).split(' utilization=')[0]])
p('The unloaded round-trip delays are close to twice the physical one-way path delay: about 60 ms through s2 and 70 ms through s4. The cost change therefore selects the expected path, and the measured RTT follows the physical route. Both forward and reverse paths are present in the logs; pingAll also checks every host pair in both directions.')

story.append(PageBreak()); h('3. Congestion-aware routing')
diagram(3,adaptive=True)
p('Figure 3. The background flow loads s1-s2. The later h1-h3 traffic can use the lower route.',caption)
p('Part 3 enables CONGESTION=1 in the same controller. Ryu requests port statistics once per second. For each inter-switch port we calculate utilization from the change in transmitted bytes:')
logs('Utilization rule', ['utilization = 8 x (new tx_bytes - old tx_bytes) / (elapsed seconds x link capacity in bits/s)', 'link utilization = max(utilization in the two directions)', 'if link utilization > 0.70: routing cost = link delay + 100 ms', 'otherwise: routing cost = link delay'])
p('We ran the same workload once with static routing and once with congestion-aware routing. After pingAll, we waited six seconds for the warm-up rules to expire. A h1-h2 UDP flow, configured for 24 seconds, used iperf -b 1.8M (about 1.89 Mbps) to load the 2 Mbps s1-s2 link. The script stops it after the foreground measurement. Five seconds later, we sent five h1-h3 pings and started an eight-second h1-h3 UDP flow at 600K bits/s. The nominal UDP rate is about 0.6 Mbps; iperf uses binary K units, so its offered rate is approximately 0.614 Mbps.')
p('The h1-h3 host pair is new at this stage. It gets a path using the current measurements, while the active h1-h2 rules stay in place. Rules match a host pair and EtherType, so the UDP traffic reuses the path chosen for the preceding h1-h3 ping. A later flow for the same pair can choose again after five idle seconds.')
static=sum(receiver_rates('p3-static'))/7
adaptive=sum(receiver_rates('p3-adaptive'))/7
table([['Routing mode','h1-h3 route','Mean RTT (ms)','Receiver Mbps'],['Static','s1 -> s2 -> s3',f'{mean_rtt("p3-static"):.3f}',f'{static:.3f}'],['Congestion-aware','s1 -> s4 -> s3',f'{mean_rtt("p3-adaptive"):.3f}',f'{adaptive:.3f}']], [110,155,120,126])
p('Receiver throughput is the mean of the first seven complete one-second server intervals in each run. We use the same window in both modes and exclude the final UDP summary/ACK, which can be delayed or lost under load. Both runs passed pingAll and the later ping test without loss.',small)
util=float(re.search(r"'\(1, 2\)': ([\d.]+)",decision('p3-adaptive'))[1])
p(f'At the adaptive h1-h3 decision, s1 port 2 utilization was {util:.2f}, above the 0.70 threshold. The upper route therefore costs at least 130 ms, compared with 35 ms through s4. The alternate route delivered more of the foreground traffic in this run, although its propagation delay is longer.')
p('One limitation is the one-second sampling interval: a short burst may finish before it is detected. OVS byte counters can include traffic waiting in the shaped egress queue, so the estimate may reflect offered load rather than exact wire utilization. There is no hysteresis, so paths can alternate near the threshold. We do not reroute active flows, and the fixed host-pair rules do not distinguish individual TCP or UDP sessions.')

story.append(PageBreak()); h('4. Selected flow tables and receiver logs')
p('These excerpts come from the saved runs. Timing and cookie fields are omitted from the Part 1 excerpt so the match and action are easier to read. Full unedited flow dumps and controller logs are in results/.')
reactive=text('p1-reactive')
proactive=text('p1-proactive')
rinitial=reactive.split('PINGALL',1)[0]
pinitial=proactive.split('PINGALL',1)[0]
rlines=[s[s.index('priority='):] for s in rinitial.splitlines() if 'priority=' in s][:1]
plines=[s[s.index('priority='):] for s in pinitial.splitlines() if 'priority=10' in s and '00:00:00:00:00:05' in s][:1]
logs('Part 1: s1 initial tables', ['Reactive: '+rlines[0], 'Proactive: '+plines[0]])
p('The rows below are parsed from the final flow tables. All rules match IPv4, source MAC 00:00:00:00:00:01 and destination MAC 00:00:00:00:00:03, with priority 10 and idle timeout 5 seconds. Packet counters confirm that the selected switches forwarded the traffic.',small)
rows=[['Run','Switch','Packets','Installed output action']]
for name in CASES[2:]:
    for row in forwarding(name): rows.append([name]+row)
table(rows,[125,70,70,246])
logs('Part 3 controller decisions (utilization dictionaries omitted):',[decision('p3-static').split(' utilization=')[0],decision('p3-adaptive').split(' utilization=')[0]])
for name in ('p3-static','p3-adaptive'):
    section=text(name).split('SERVER\n',1)[1].split('FINAL FLOW TABLES',1)[0]
    intervals=[s.strip() for s in section.splitlines() if re.search(r'0\.0000-1\.0000 sec|1\.0000-2\.0000 sec',s)]
    logs(name+' receiver: first two intervals (iperf output)',intervals)
p('The static receiver can continue draining queued packets after the client stops sending; its final UDP acknowledgement may also time out. This is why the comparison uses the complete early receiver intervals rather than treating the offered client rate as received throughput.',small)

story.append(PageBreak()); h('5. Running and checking the submission')
p('The experiments were rerun in an isolated copy with a new virtual environment. The tested system uses Linux, Python 3.12.3, Open vSwitch 3.3.9, Ryu 4.34, Mininet and iperf 2.1.9. Both supplied topology files and both Part 1 controllers are unchanged.')
p('From the extracted code-a3 folder:',subhead)
logs('Setup and complete experiment run',[
'sudo apt install mininet openvswitch-switch iperf python3-venv',
'python3 -m venv .venv',
'.venv/bin/pip install setuptools==67.6.1 wheel',
'.venv/bin/pip install -r requirements.txt',
'sudo systemctl start openvswitch-switch',
'sudo python3 experiments/run.py "$PWD/.venv/bin/ryu-manager"',
'python3 experiments/verify.py'])
p('The experiment script runs six cases and replaces results/. A failed connectivity check stops the run. Mininet runs with system Python and sudo; Ryu runs from the virtual environment. Stop other controllers before running. Use sudo mn -c after an interrupted Mininet run.')
p('For an interactive run, start Ryu and the topology in separate terminals. All controllers listen on port 6633:',small)
table([['Part','Controller command after .venv/bin/ryu-manager','Topology command'],['1 reactive','--ofp-tcp-listen-port 6633 p1/reactive.py','sudo python3 p1_topo.py'],['1 proactive','--ofp-tcp-listen-port 6633 p1/proactive.py','sudo python3 p1_topo.py'],['2','--ofp-tcp-listen-port 6633 p2/routing.py','sudo python3 p3_topo.py'],['3','Prefix the Part 2 command with CONGESTION=1','sudo python3 p3_topo.py']], [74,274,163])
p('For the changed-cost Part 2 case, prefix the controller command with DELAY12=40. Inside Mininet, use pingall and h1 ping -c 10 h3. Inspect a switch with sh ovs-ofctl -O OpenFlow13 dump-flows s1.',small)
table([['Requirement checked','Evidence in this submission'],['Part 1: both approaches, connectivity, comparison and trade-off','Controllers in p1/; results/p1-*; page 1 and page 4'],['Part 2: graph, host ports, delay costs, bidirectional routes and changed-cost test','p2/routing.py; results/p2-*; page 2 and page 4'],['Part 3: statistics, threshold rule, later-flow routing and static comparison','CONGESTION=1; results/p3-*; page 3 and page 4'],['Source, topologies, setup, report and correctly named archive','All required files are included under code-a3/']], [255,256])
p('The bundled Ryu wheel is third-party Apache-2.0 software, with the existing eventlet ALREADY_HANDLED compatibility fix used on this machine. It removes the dependency on an external local Ryu source directory. pip downloads its other dependencies. SETUP.txt includes individual commands. Report regeneration additionally needs ReportLab and installed Arial fonts; neither is needed to run the networking experiments.',small)


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
