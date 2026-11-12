
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3


class P1_ProactiveSwitch(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    # Known topology: destination host -> switch output port
    PORT_MAP = {
        1: {1: 1, 2: 2, 3: 3, 4: 4, 5: 4},
        2: {1: 3, 2: 3, 3: 3, 4: 1, 5: 2},
    }

    # Helper: Install a forwarding rule in OVS
    def add_flow(self, dp, priority, match, actions):
        parser = dp.ofproto_parser
        ofp = dp.ofproto

        instructions = [
            parser.OFPInstructionActions(
                ofp.OFPIT_APPLY_ACTIONS, actions
            )
        ]

        rule = parser.OFPFlowMod(
            datapath=dp,
            priority=priority,
            match=match,
            instructions=instructions
        )

        dp.send_msg(rule)

    # Called when a switch connects
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_connected(self, ev):
        dp = ev.msg.datapath
        parser = dp.ofproto_parser
        ofp = dp.ofproto

        self.logger.info("Switch %s connected", dp.id)

        # Install forwarding rules for all five hosts
        for host_id, out_port in self.PORT_MAP[dp.id].items():

            host_mac = f"00:00:00:00:00:{host_id:02x}"

            match = parser.OFPMatch(eth_dst=host_mac)
            actions = [parser.OFPActionOutput(out_port)]

            self.add_flow(dp, 10, match, actions)

            self.logger.info(
                "Installed: switch=%s dst=h%s out=%s",
                dp.id, host_id, out_port
            )

        # Forward ARP broadcasts without contacting controller
        match = parser.OFPMatch(
            eth_dst="ff:ff:ff:ff:ff:ff"
        )
        actions = [parser.OFPActionOutput(ofp.OFPP_FLOOD)]

        self.add_flow(dp, 5, match, actions)

        self.logger.info(
            "All proactive rules installed on switch %s", dp.id
        )
