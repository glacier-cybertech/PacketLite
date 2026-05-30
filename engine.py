import random
from datetime import datetime, UTC

def generate_random_mac():
    return "00:00:00:%02x:%02x:%02x" % (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

def ip_to_int(ip):
    parts = list(map(int, ip.split('.')))
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]

def check_is_local(src_ip, dst_ip, subnet_mask):
    if src_ip == "0.0.0.0" or dst_ip == "255.255.255.255":
        return True
    src_int = ip_to_int(src_ip)
    dst_int = ip_to_int(dst_ip)
    mask_int = ip_to_int(subnet_mask)
    return (src_int & mask_int) == (dst_int & mask_int)

class Router:
    def __init__(self):
        self.name = "Router"
        self.mac_address = generate_random_mac()
        self.local_ip = "192.168.68.1"
        self.subnet_mask = "255.255.255.0"
        self.cables = [] 
        
        from services import DHCPserver, ARPhandler, ICMPhandler
        self.dhcp_service = DHCPserver(67, self.subnet_mask, self.local_ip, self.local_ip)
        self.ARPhandler = ARPhandler(self)
        self.ICMPhandler = ICMPhandler(self)
        self.arp_table = []
        self.packet_buffer = []

    def construct_frame(self, dst_mac, packet, type=1):
        return Frame(self.mac_address, dst_mac, packet, type)

    def send(self, cable, frame):
        if cable: cable.sendFrame(frame, self)

    def send_broadcast(self, frame, incoming_cable=None):
        """Sends the frame to every connected device except the source."""
        for cable in self.cables:
            if cable != incoming_cable:
                self.send(cable, frame)

    def send_data(self, target_ip, packet, incoming_cable=None):
        # 1. Handle Broadcast IP (255.255.255.255)
        if target_ip == "255.255.255.255":
            self.send_broadcast(self.construct_frame("FF:FF:FF:FF:FF:FF", packet), incoming_cable)
            return

        # 2. Handle Unicast
        dst_mac = self.ARPhandler.get_mac_from_table(target_ip)
        if dst_mac:
            # Note: In a multi-port router, you'd track which cable leads to which MAC.
            # Simplified: try to send to all cables if you aren't sure, or cables[0]
            self.send_broadcast(self.construct_frame(dst_mac, packet), incoming_cable)
        else:
            # Buffer and initiate ARP discovery across all ports
            self.packet_buffer.append({'target': target_ip, 'packet': packet})
            arp_msg = self.ARPhandler.construct_arp_message(target_ip, 1)
            self.send_broadcast(self.construct_frame("FF:FF:FF:FF:FF:FF", arp_msg, 2), incoming_cable)

    def process_buffer(self):
        """Safe buffer processing to avoid ValueError recursion."""
        while self.packet_buffer:
            item = self.packet_buffer[0]
            mac = self.ARPhandler.get_mac_from_table(item['target'])
            if mac:
                self.packet_buffer.pop(0)
                # Flood the buffered packet to ensure it reaches the correct segment
                self.send_broadcast(self.construct_frame(mac, item['packet']))
            else:
                break

    def receive(self, frame, cable):
        packet = frame.packet
        is_me = frame.destination_mac == self.mac_address
        is_bcast = frame.destination_mac == "FF:FF:FF:FF:FF:FF"

        # ARP/IP Logic
        if is_me or is_bcast:
            if frame.ethernet_type == 2: # ARP
                response = self.ARPhandler.handle_arp_message(frame)
                if response: 
                    self.send(cable, self.construct_frame(frame.source_mac, response, 2))
                else:
                    # If it's a broadcast ARP not for us, flood it so other PCs hear it
                    if is_bcast: self.send_broadcast(frame, cable)
                self.process_buffer()

            elif frame.ethernet_type == 1: # IP
                is_local_ip = packet.destination_ip in [self.local_ip, "255.255.255.255"]
                
                if is_local_ip:
                    if packet.protocol == "ICMP":
                        reply = self.ICMPhandler.handle_icmp_message(frame)
                        if reply: self.send_data(packet.source_ip, reply, cable)
                    elif packet.data and getattr(packet.data, 'dst_port', None) == 67:
                        response = self.dhcp_service.process_dhcp_req(frame)
                        if response: self.send(cable, self.construct_frame(frame.source_mac, response))
                else:
                    # Forwarding to other connected segments
                    self.send_data(packet.destination_ip, packet, cable)
        else:
            # Not for router MAC: In a bridge/router hybrid, you can flood unknown unicast
            self.send_broadcast(frame, cable)

class PC:
    def __init__(self):
        self.name = "PC"
        self.mac_address = generate_random_mac()
        self.local_ip = "0.0.0.0"
        self.default_gateway = None
        self.subnet_mask = None
        self.cables = []
        from services import DHCPClient, ARPhandler, ICMPhandler
        self.DHCPClient = DHCPClient(self, 68, 67)
        self.ARPhandler = ARPhandler(self)
        self.ICMPhandler = ICMPhandler(self)
        self.arp_table = []
        self.packet_buffer = []

    def construct_frame(self, dst_mac, packet, type=1):
        return Frame(self.mac_address, dst_mac, packet, type)

    def send_dhcp_request(self):
        print(f"[{self.name}] Initiating DHCP Discover...")
        dhcp_packet = self.DHCPClient.create_discover_packet()
        # DHCP must be type 1 (IP) and Broadcast
        dhcp_frame = self.construct_frame("FF:FF:FF:FF:FF:FF", dhcp_packet, 1)
        if self.cables: self.send(self.cables[0], dhcp_frame)

    def send_icmp_request(self, target_ip):
        if self.local_ip == "0.0.0.0":
            print("Cannot ping: No IP address assigned.")
            return
        icmp_msg = self.ICMPhandler.construct_icmp_message(1, datetime.now(UTC), 1)
        icmp_packet = Packet(self.local_ip, target_ip, "ICMP", icmp_msg)
        self.send_data(target_ip, icmp_packet)

    def send_data(self, target_ip, packet):
        # DHCP/Initial Boot Bypass: If no IP or broadcasting, don't ARP.
        if self.local_ip == "0.0.0.0" or target_ip == "255.255.255.255":
            self.send(self.cables[0], self.construct_frame("FF:FF:FF:FF:FF:FF", packet, 1))
            return

        target = target_ip if check_is_local(self.local_ip, target_ip, self.subnet_mask) else self.default_gateway
        dst_mac = self.ARPhandler.get_mac_from_table(target)

        if dst_mac:
            self.send(self.cables[0], self.construct_frame(dst_mac, packet))
        else:
            self.packet_buffer.append({'target': target, 'packet': packet})
            arp_msg = self.ARPhandler.construct_arp_message(target, 1)
            self.send(self.cables[0], self.construct_frame("FF:FF:FF:FF:FF:FF", arp_msg, 2))

    def receive(self, frame, cable):
        if frame.destination_mac == self.mac_address or frame.destination_mac == "FF:FF:FF:FF:FF:FF":
            packet = frame.packet
            if frame.ethernet_type == 2:
                response = self.ARPhandler.handle_arp_message(frame)
                if response: self.send(cable, self.construct_frame(frame.source_mac, response, 2))
                self.process_buffer()
            elif frame.ethernet_type == 1:
                if packet.data:
                    if packet.protocol == "ICMP":
                        reply = self.ICMPhandler.handle_icmp_message(frame)
                        if reply: self.send_data(packet.source_ip, reply)
                    
                    if hasattr(packet.data, 'dst_port') and packet.data.dst_port == 68:
                        response = self.DHCPClient.processFrame(frame)
                        if response:
                            self.send(cable, self.construct_frame("FF:FF:FF:FF:FF:FF", response, 1))

    def process_buffer(self):
        # Iterate using a while loop to safely modify the list
        while self.packet_buffer:
            # Check if the first item's target now has a known MAC
            item = self.packet_buffer[0]
            target = item['target']
            mac = self.ARPhandler.get_mac_from_table(target)
        
            if mac:
                # Remove it BEFORE sending to prevent recursive removal crashes
                self.packet_buffer.pop(0) 
            
                new_frame = self.construct_frame(mac, item['packet'])
                self.send(self.cables[0], new_frame)
            else:
                # If the first item can't be sent yet, 
                # we stop to maintain packet order or skip to next
                break

    def send(self, cable, frame):
        if cable: cable.sendFrame(frame, self)

class Switch:
    def __init__(self):
        self.name = "Switch"
        self.mac_address = generate_random_mac()
        self.mac_table = {} 
        self.cables = []

    def receive(self, frame, incoming_cable):
        self.mac_table[frame.source_mac] = incoming_cable
        if frame.destination_mac == "FF:FF:FF:FF:FF:FF":
            for cable in self.cables:
                if cable != incoming_cable: cable.sendFrame(frame, self)
        else:
            target_cable = self.mac_table.get(frame.destination_mac)
            if target_cable:
                target_cable.sendFrame(frame, self)
            else:
                for cable in self.cables:
                    if cable != incoming_cable: cable.sendFrame(frame, self)

class Cable:
    def __init__(self, obj1, obj2, c_type="Ethernet"):
        self.connection1 = obj1 
        self.connection2 = obj2 

    def sendFrame(self, frame, sender):
        if self.connection1 == sender:
            self.connection2.receive(frame, self)
        else:
            self.connection1.receive(frame, self)

class Frame:
    def __init__(self, source_mac, destination_mac, packet, ether_type=1):
        self.source_mac = source_mac
        self.destination_mac = destination_mac
        self.packet = packet
        self.ethernet_type = ether_type

class Packet:
    def __init__(self, source_ip, destination_ip, protocol, data):
        self.source_ip = source_ip
        self.destination_ip = destination_ip
        self.protocol = protocol
        self.data = data

class Data:
    def __init__(self, src_port, dst_port, payload):
        self.src_port = src_port
        self.dst_port = dst_port
        self.payload = payload

class ARPobject:
    def __init__(self, mac, ip):
        self.mac_address = mac
        self.ip_address = ip