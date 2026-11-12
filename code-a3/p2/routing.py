"""Part 2: shortest-delay routing for the supplied fixed ring. DELAY12 changes one cost."""
import os
import networkx as nx
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet

# (switch, switch, port at first, port at second, Mbps, delay ms)
LINKS = [(1,2,2,2,2,20),(2,3,3,2,2,10),(3,4,3,2,1,20),(4,1,3,3,1,15)]

class Routing(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dps = {}
        self.graph = nx.Graph()
        self.ports = {}
        for a,b,pa,pb,bw,delay in LINKS:
            if (a,b)==(1,2):
                delay = float(os.getenv('DELAY12', '20'))
            self.graph.add_edge(a,b,weight=delay)
            self.ports[a,b], self.ports[b,a] = pa,pb

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

    def path(self, a, b):
        return nx.shortest_path(self.graph, a, b, weight='weight')

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
        self.logger.info('PATH %s -> %s: %s adaptive=False', a, b, path)
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
