from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, set_ev_cls, MAIN_DISPATCHER
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types


class P1_ReactiveSwitch(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac_to_port = {}

    # Helper: Install a rule in an OVS switch
    def add_flow(self, dp, priority, match, actions):
        parser = dp.ofproto_parser
        ofp = dp.ofproto

        instructions = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]

        rule = parser.OFPFlowMod(
            datapath=dp, priority=priority, match=match, instructions=instructions
        )
        dp.send_msg(rule)

    # Called when a switch connects
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_connected(self, ev):
        dp = ev.msg.datapath
        parser = dp.ofproto_parser
        ofp = dp.ofproto

        # Unmatched packets go to Ryu
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        self.add_flow(dp, 0, match, actions)

        self.logger.info("Switch %s connected", dp.id)

    # Called when OVS sends a PacketIN - Unmached packet handling
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        in_port = msg.match["in_port"]
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth is None or eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dpid = dp.id
        self.mac_to_port.setdefault(dpid, {})

        # Learn source MAC address
        self.mac_to_port[dpid][eth.src] = in_port

        # Find destination port, otherwise flood
        out_port = self.mac_to_port[dpid].get(eth.dst, ofp.OFPP_FLOOD)

        self.logger.info(
            "Packet-In: switch=%s src=%s dst=%s out=%s",
            dpid,
            eth.src,
            eth.dst,
            out_port,
        )

        actions = [parser.OFPActionOutput(out_port)]

        # Reactive installation: only when destination is known
        if out_port != ofp.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=eth.dst)
            self.add_flow(dp, 1, match, actions)

        # Forward the current packet
        out = parser.OFPPacketOut(
            datapath=dp,
            buffer_id=ofp.OFP_NO_BUFFER,
            in_port=in_port,
            actions=actions,
            data=msg.data,
        )
        dp.send_msg(out)
