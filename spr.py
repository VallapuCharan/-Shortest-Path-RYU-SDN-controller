from ryu.base import app_manager  
from ryu.controller import ofp_event  
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER  
from ryu.controller.handler import set_ev_cls  
from ryu.ofproto import ofproto_v1_3  
from ryu.lib.packet import packet  
from ryu.lib.packet import ethernet  
from ryu.lib.packet import arp  
from ryu.lib.packet import ipv4  
from collections import defaultdict  
from ryu.topology.api import get_switch,get_link  
from ryu.topology import event,switches  
  
ARP = arp.arp.__name__  
ETHERNET = ethernet.ethernet.__name__  
ETHERNET_MULTICAST = "ff:ff:ff:ff:ff:ff"  
  
adjacency = defaultdict(lambda: defaultdict(lambda: None))  
path_map = defaultdict(lambda: defaultdict(lambda: (None, None)))  
sws = []  
switches={}  
mac_map={}  
  
def _get_raw_path(src, dst):  
    """ 
    Get a raw path (just a list of nodes to traverse) 
    """  
    if len(path_map) == 0: _dijkstra_paths()  
    if src is dst:  
        # We're here!  
        return []  
  
    if path_map[src][dst][0] is None:  
        return None  
    intermediate = path_map[src][dst][1]  
    if intermediate is None:  
        # Directly connected  
        return []  
    return _get_raw_path(src, intermediate) + [intermediate] + _get_raw_path(intermediate, dst)
  
def _get_path(src, dst, first_port, final_port):  
    """ 
    Gets a cooked path -- a list of (node,in_port,out_port) 
    """  
    # Start with a raw path...  
    print src  
    print dst  
    if src == dst:  
        path = [src]  
    else:  
        path = _get_raw_path(src, dst)  
        if path is None: return None  
        path = [src] + path + [dst]  
  
    # Now add the ports  
    r = []  
    in_port = first_port  
    for s1, s2 in zip(path[:-1], path[1:]):  
        out_port = adjacency[s1][s2]  
        r.append((s1, in_port, out_port))  
        in_port = adjacency[s2][s1]  
    r.append((dst, in_port, final_port))  
    print 'R is %s' % r  
    return r  
  
def _dijkstra_paths():  
    path_map.clear()  
    for k in sws:  
        for j, port in adjacency[k].iteritems():  
            if port is None:  
                continue  
            path_map[k][j] = (1, None)  
        path_map[k][k] = (0, None)  
        print adjacency[k]  
  
    for t in sws:  
        final_point = []  
        final_point.append(t)  
        for i in range(len(sws) - 1):  
            min_path = 999
            # HERE
            temp = None
            for p in sws:  
                if p not in final_point:  
                    if path_map[t][p][0] is not None and path_map[t][p][0] < min_path:  
                        min_path = path_map[t][p][0]  
                        temp = p  
            # HERE
            if temp != None:
                final_point.append(temp)  

                for m in sws:  
                    if m not in final_point:  
                        if path_map[t][m][0] is None and \
                        path_map[t][temp][0] is not None and \
                        path_map[temp][m][0] is not None:
                            path_map[t][m] = (path_map[t][temp][0] + path_map[temp][m][0], temp)  

                        elif path_map[t][temp][0] is not None and \
                        path_map[temp][m][0] is not None and \
                        path_map[t][m][0] is not None:
                            if path_map[t][temp][0] + path_map[temp][m][0] < path_map[t][m][0]:  
                                path_map[t][m] = (path_map[t][temp][0] + path_map[temp][m][0], temp)  
    print path_map  
  
  
class SimpleSwitch13(app_manager.RyuApp):  
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]  
  
    def __init__(self, *args, **kwargs):  
        super(SimpleSwitch13, self).__init__(*args, **kwargs)  
        self.mac_to_port = {}  
        self.arp_table = {}  
        self.sw = {}  
        self.port_tx = {}  
        self.datapaths = {}  
        self.datapath_list={}  
        self.topology_api_app=self  
 
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)  
    def switch_features_handler(self, ev):  
        datapath = ev.msg.datapath  
        ofproto = datapath.ofproto  
        parser = datapath.ofproto_parser  
        switches[datapath.id]=datapath  
  
        match = parser.OFPMatch()  
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,  
                                          ofproto.OFPCML_NO_BUFFER)]  
        self.add_flow(datapath, 0, match, actions)  
  
    def add_flow(self, datapath, priority, match, actions):  
        ofproto = datapath.ofproto  
        parser = datapath.ofproto_parser  
  
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,  
                                             actions)]  
  
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,  
                                hard_timeout=20,  
                                match=match, instructions=inst)  
  
        datapath.send_msg(mod)  
 
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)  
    def _packet_in_handler(self, ev):  
        if ev.msg.msg_len < ev.msg.total_len:  
            self.logger.debug("packet truncated: only %s of %s bytes",  
                              ev.msg.msg_len, ev.msg.total_len)  
        msg = ev.msg  
        datapath = msg.datapath  
        ofproto = datapath.ofproto  
        parser = datapath.ofproto_parser  
        in_port = msg.match['in_port']  
  
        pkt = packet.Packet(msg.data)  
        eth = pkt.get_protocols(ethernet.ethernet)[0]  
        #avoid broadcast from LLDP  
        if eth.ethertype==35020:  
            return  
              
        dst = eth.dst  
        src = eth.src  
  
        loc=('00-00-00-00-00-0'+str(datapath.id),in_port)  
        oldloc=mac_map.get(src)  
        if oldloc is None:  
            mac_map[src]=loc
        elif src not in mac_map:  
            mac_map[src]=loc
  
        dpid = datapath.id  
        self.mac_to_port.setdefault(dpid, {})  
  
        header_list = dict(  
            (p.protocol_name, p) for p in pkt.protocols if type(p) != str)  
        if ARP in header_list:  
            self.arp_table[header_list[ARP].src_ip] = src  # ARP learning  
  
        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)  
  
        # learn a mac address to avoid FLOOD next time.  
        if src not in self.mac_to_port[dpid]:  #record only one in_port  
            self.mac_to_port[dpid][src] = in_port  
  
        if dst in self.mac_to_port[dpid]:  
            out_port = self.mac_to_port[dpid][dst]  
            temp_src=mac_map[src]
            temp_dst=mac_map[dst]
            self.install_path(temp_src[0],temp_dst[0], temp_src[1], temp_dst[1], ev)  
            self.logger.info("out_port: %s", out_port)  
        else:  
            out_port = ofproto.OFPP_FLOOD  
            print"flood!"  
  
        actions = [parser.OFPActionOutput(out_port)]  
  
        # install a flow to avoid packet_in next time  
        if out_port != ofproto.OFPP_FLOOD:  
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)              
  
        data = None  
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:  
            data = msg.data  
  
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,  
                                  in_port=in_port, actions=actions, data=data)  
        datapath.send_msg(out)  
 
    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])  
    def state_change_handler(self, ev):  
        datapath = ev.datapath  
        if ev.state == MAIN_DISPATCHER:  
            if datapath.id == 1:  
                self.datapaths[datapath.id] = datapath  
            if not datapath.id in self.datapath_list:  
                self.datapath_list[datapath.id]=datapath  
        elif ev.state == DEAD_DISPATCHER:  
            if datapath.id in self.datapaths:  
                del self.datapaths[datapath.id]  
  
    def install_path(self,src_sw, dst_sw, in_port, last_port, ev):  
        """ 
        Attempts to install a path between this switch and some destination 
        """  
        p = _get_path(src_sw, dst_sw, in_port, last_port)  

        # HERE
        if p != None:
            self._install_path(p, ev)  
            # Now reverse it and install it backwards  
            # (we'll just assume that will work)  
            p = [(sw, out_port, in_port) for sw, in_port, out_port in p]  
            self._install_path(p, ev)  
  
    def _install_path(self, p, ev):  
        msg = ev.msg  
        datapath = msg.datapath  
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser  
        pkt = packet.Packet(msg.data)  

        # HERE
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst

        # HERE
        if p != None:
            for sw, in_port, out_port in p:  

                # HERE
                match = parser.OFPMatch(in_port=in_port, eth_dst=dst)  
                actions = [parser.OFPActionOutput(out_port)]  
                ID=int(sw[-1:])  
                datapath=self.datapath_list[ID]  
                self.add_flow(datapath, 1, match, actions)  
 
    @set_ev_cls(event.EventSwitchEnter)  
      
    def get_topology(self,ev):
        # TO get switches and links automatically
        switch_list=get_switch(self.topology_api_app,None)  
        global sws  
        # assign mac for swtich to easy read  
        sws=['00-00-00-00-00-0'+ str(switch.dp.id) for switch in switch_list]  
        links_list=get_link(self.topology_api_app,None)  
        for link in links_list:  
            sw_src='00-00-00-00-00-0'+ str(link.src.dpid)  
            sw_dst='00-00-00-00-00-0'+ str(link.dst.dpid)  
            adjacency[sw_src][sw_dst]=link.src.port_no  
