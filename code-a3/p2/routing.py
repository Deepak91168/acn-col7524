"""Delay routing; CONGESTION=1 enables Part 3. Fixed supplied ring/hosts."""
import os
import time
import networkx as nx
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.lib.packet import packet, ethernet

# (switch, switch, port at first, port at second, Mbps, delay ms)
LINKS = [(1,2,2,2,2,20),(2,3,3,2,2,10),(3,4,3,2,1,20),(4,1,3,3,1,15)]

class Routing(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dps, self.previous, self.util = {}, {}, {}
        self.adaptive = os.getenv('CONGESTION', '0') == '1'
        self.graph = nx.Graph()
        self.ports, self.capacity = {}, {}
        for a,b,pa,pb,bw,delay in LINKS:
            if (a,b)==(1,2):
                delay = float(os.getenv('DELAY12', '20'))
            self.graph.add_edge(a,b,weight=delay)
            self.ports[a,b], self.ports[b,a] = pa,pb
            self.capacity[a,pa] = self.capacity[b,pb] = bw*1e6
        self.monitor = hub.spawn(self.poll)

    def flow(self, dp, match, actions, priority=10, idle=0):
        p, o = dp.ofproto_parser, dp.ofproto
        dp.send_msg(p.OFPFlowMod(datapath=dp, priority=priority, match=match,
            idle_timeout=idle, instructions=[p.OFPInstructionActions(o.OFPIT_APPLY_ACTIONS,actions)]))

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def connected(self, ev):
        dp = ev.msg.datapath
        self.dps[dp.id] = dp
        p,o = dp.ofproto_parser, dp.ofproto
        self.flow(dp,p.OFPMatch(),[p.OFPActionOutput(o.OFPP_CONTROLLER,o.OFPCML_NO_BUFFER)],0)

    def poll(self):
        while True:
            for dp in list(self.dps.values()):
                dp.send_msg(dp.ofproto_parser.OFPPortStatsRequest(dp,0,dp.ofproto.OFPP_ANY))
            hub.sleep(1)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def stats(self,ev):
        now=time.monotonic()
        for s in ev.msg.body:
            key=(ev.msg.datapath.id,s.port_no)
            if key not in self.capacity: continue
            if key in self.previous:
                old,stamp=self.previous[key]
                self.util[key]=max(0,(s.tx_bytes-old)*8/(now-stamp)/self.capacity[key])
            self.previous[key]=(s.tx_bytes,now)

    def path(self,a,b):
        g=self.graph.copy()
        for x,y in g.edges:
            u=max(self.util.get((x,self.ports[x,y]),0),self.util.get((y,self.ports[y,x]),0))
            if self.adaptive and u>0.70: g[x][y]['weight']+=100
        return nx.shortest_path(g,a,b,weight='weight')

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def received(self,ev):
        msg=ev.msg
        eth=packet.Packet(msg.data).get_protocol(ethernet.ethernet)
        if not eth: return
        hosts={f'00:00:00:00:00:{i:02x}':i for i in range(1,5)}
        if eth.src not in hosts: return
        # Deliver broadcasts directly to host ports; never flood the ring.
        if eth.dst=='ff:ff:ff:ff:ff:ff':
            for sid,dp in self.dps.items():
                if sid==hosts[eth.src]: continue
                p,o=dp.ofproto_parser,dp.ofproto
                dp.send_msg(p.OFPPacketOut(datapath=dp,buffer_id=o.OFP_NO_BUFFER,in_port=o.OFPP_CONTROLLER,actions=[p.OFPActionOutput(1)],data=msg.data))
            return
        if eth.dst not in hosts: return
        a,b=hosts[eth.src],hosts[eth.dst]
        path=self.path(a,b)
        if any(s not in self.dps for s in path): return
        self.logger.info('PATH %s -> %s: %s adaptive=%s utilization=%s',a,b,path,self.adaptive,{str(k):round(v,2) for k,v in self.util.items()})
        # Install only this direction. Reverse traffic independently chooses a path.
        # Match host pair + EtherType; expire after 5 idle seconds for later flows.
        for i,sid in reversed(list(enumerate(path))):
            dp=self.dps[sid]; p=dp.ofproto_parser
            port=1 if i==len(path)-1 else self.ports[sid,path[i+1]]
            self.flow(dp,p.OFPMatch(eth_src=eth.src,eth_dst=eth.dst,eth_type=eth.ethertype),[p.OFPActionOutput(port)],idle=5)
        dp=msg.datapath; p,o=dp.ofproto_parser,dp.ofproto
        sid=dp.id
        if sid not in path: return
        i=path.index(sid)
        port=1 if i==len(path)-1 else self.ports[sid,path[i+1]]
        dp.send_msg(p.OFPPacketOut(datapath=dp,buffer_id=o.OFP_NO_BUFFER,in_port=msg.match['in_port'],actions=[p.OFPActionOutput(port)],data=msg.data))
