#!/usr/bin/python
from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSController
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch, UserSwitch
from mininet.node import IVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, Intf
from subprocess import call
from mininet.link import TCLink

def myNetwork():
    #Define Controller with host 0.0.0.0 and port 6633
    c0 = RemoteController('c0', '0.0.0.0', 6633)
    net = Mininet(topo=None, host=CPULimitedHost, controller=OVSController)
    net.addController(c0)
    # Add switches to the network   
    info( '* Add switches\n')
    s1 = net.addSwitch('s1',stp=True)
    s2 = net.addSwitch('s2',stp=True)
    s3 = net.addSwitch('s3',stp=True)
    s4 = net.addSwitch('s4',stp=True)
    s5 = net.addSwitch('s5',stp=True)
    s6 = net.addSwitch('s6',stp=True)
    s7 = net.addSwitch('s7',stp=True)
    s8 = net.addSwitch('s8',stp=True)
    s9 = net.addSwitch('s9',stp=True)
    s10 = net.addSwitch('s10',stp=True)
    s11 = net.addSwitch('s11',stp=True)
    #Add links to the network
    info( '* Add hosts\n')
    PC = net.addHost('PC', ip='10.0.0.1')
    Server = net.addHost('Server', ip='10.0.0.254')
    info( '* Add links\n')
    net.addLink(PC,s1);
    net.addLink(Server,s11);
#-----------------------------------
    net.addLink(s1, s5,cls = TCLink, bw=10)
    net.addLink(s2, s5,cls = TCLink, bw=15)
    net.addLink(s2, s6,cls = TCLink, bw=20)
    net.addLink(s3, s6,cls = TCLink, bw=15)
    net.addLink(s3, s7,cls = TCLink, bw=10)
    net.addLink(s4, s7,cls = TCLink, bw=15)
    net.addLink(s5, s6,cls = TCLink, bw=20)
    net.addLink(s6, s7,cls = TCLink, bw=20)
    net.addLink(s5, s8,cls = TCLink, bw=15)
    net.addLink(s5, s9,cls = TCLink, bw=15)
    net.addLink(s6, s9,cls = TCLink, bw=15)
    net.addLink(s6, s10,cls = TCLink, bw=10)
    net.addLink(s7, s10,cls = TCLink, bw=15)
    net.addLink(s7, s11,cls = TCLink, bw=10)
#------------------------------------
    info( '* Starting network\n')
    net.build()
    info( '* Starting controllers\n')
    for controller in net.controllers:
        controller.start()
    info( '* Starting switches\n')
    net.get('s1').start([c0])
    net.get('s2').start([c0])
    net.get('s3').start([c0])
    net.get('s4').start([c0])
    net.get('s5').start([c0])
    net.get('s6').start([c0])
    net.get('s7').start([c0])
    net.get('s8').start([c0])
    net.get('s9').start([c0])
    net.get('s10').start([c0])
    net.get('s11').start([c0])
    # this settings will not allow loops in the network
    s1.cmd('ovs-vsctl set bridge s1 stp_enable=true')
    s2.cmd('ovs-vsctl set bridge s2 stp_enable=true')
    s3.cmd('ovs-vsctl set bridge s3 stp_enable=true')
    s4.cmd('ovs-vsctl set bridge s4 stp_enable=true')
    s5.cmd('ovs-vsctl set bridge s5 stp_enable=true')
    s6.cmd('ovs-vsctl set bridge s6 stp_enable=true')
    s7.cmd('ovs-vsctl set bridge s7 stp_enable=true')
    s8.cmd('ovs-vsctl set bridge s8 stp_enable=true')
    s9.cmd('ovs-vsctl set bridge s9 stp_enable=true')
    s10.cmd('ovs-vsctl set bridge s10 stp_enable=true')
    s11.cmd('ovs-vsctl set bridge s11 stp_enable=true')
    
    info( '* Post configure switches and hosts\n')
    # Ping until we get 0.0 percent drop
    while(net.pingAll()>0.0):
    	print(net.pingAll())
    
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    topo=myNetwork()
