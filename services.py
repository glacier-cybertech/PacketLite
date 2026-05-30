from engine import Frame, Packet, Data
from protocols import DHCPrequest, ARPmessage, ICMPmessage

class DHCPserver:
    def __init__(self, port, subnet, gateway, ip):
        self.ip = ip
        self.port = port
        self.subnet = subnet
        self.gateway = gateway
        self.leaseTable = []

        self.prefix = ".".join(self.gateway.split('.')[:-1]) + "."

    def get_available_ip(self):
        for i in range(10, 255):
            test_ip = f"{self.prefix}{i}" # Use the prefix here
            
            is_assigned = False
            for lease in self.leaseTable:
                if lease.ip == test_ip:
                    is_assigned = True
                    break
            
            if not is_assigned:
                return test_ip
        return None

    def create_packet(self, opcode, ip,  client_mac):
        dhcp_req_payload = DHCPrequest(opcode, client_mac)
        dhcp_req_payload.returned_localip = ip
        dhcp_req_payload.returned_subnet = self.subnet
        dhcp_req_payload.returned_gateway = self.gateway
        dhcp_req_payload.server_id = self.ip

        dhcp_req_data = Data(self.port, 68, dhcp_req_payload)

        dhcp_req_packet = Packet(self.ip, "255.255.255.255", "UDP", dhcp_req_data)
        return dhcp_req_packet

    def process_dhcp_req(self, frame):
        data = frame.packet.data
        payload = data.payload

        if data.dst_port == self.port:
            opcode = payload.opcode
            if opcode == 1:
                available = self.get_available_ip()

                if available != None:
                    offer_packet = self.create_packet(2, available, payload.client_mac)
                    return offer_packet
            if opcode == 3:
                print("Recieved dhcp request: ")
                print(payload.server_id)
                if payload.server_id == self.ip:
                    ack_packet = self.create_packet(4, payload.returned_localip, payload.client_mac)
                    leaseobj = leaseObject(payload.returned_localip, payload.client_mac, 999)
                    self.leaseTable.append(leaseobj)
                    return ack_packet

class leaseObject:
	def __init__(self, ip, mac, time):
		self.ip = ip
		self.mac = mac
		self.time = time

class DHCPClient:
    def __init__(self, host, src_port, dst_port):
        self.host = host
        self.src_port = src_port
        self.dst_port = dst_port
        self.server_id = None

    def create_discover_packet(self):
        dhcp_discover = DHCPrequest(1, self.host.mac_address)
        dhcp_data = Data(self.src_port, self.dst_port, dhcp_discover)
        dhcp_packet = Packet(self.host.local_ip, "255.255.255.255", "UDP", dhcp_data)
        return dhcp_packet

    def create_req_packet(self, returned_localip):
        dhcp_payload = DHCPrequest(3, self.host.mac_address)
        dhcp_payload.returned_localip = returned_localip
        dhcp_payload.server_id = self.server_id
        dhcp_data = Data(self.src_port, self.dst_port, dhcp_payload)
        dhcp_packet = Packet(self.host.local_ip, "255.255.255.255", "UDP", dhcp_data)
        return dhcp_packet

    def processFrame(self, frame):
        packet = frame.packet
        data = packet.data
        payload = data.payload
        if data.dst_port == self.src_port:
            opcode = payload.opcode

            if opcode == 2:
                print("Recieved offer: ")
                print(payload.returned_localip)
                if self.server_id == None:
                    self.server_id = payload.server_id
                    req_packet = self.create_req_packet(payload.returned_localip)
                    self.server_id = payload.server_id
                    return req_packet
            if opcode == 4:
                print("Recieved ack: ")
                print(payload.returned_localip)
                self.host.local_ip = payload.returned_localip
                self.host.default_gateway = payload.returned_gateway
                self.host.subnet_mask = payload.returned_subnet
                self.server_id = None
                return None

class ARPhandler:
    def __init__(self, host):
        self.host = host

    def get_mac_from_table(self, ip):
        for entry in self.host.arp_table:
            if entry.ip_address == ip:
                return entry.mac_address
        return None

    def construct_arp_message(self, ip, opcode):
        if opcode == 1:
            arp_message = ARPmessage(1, self.host.mac_address, self.host.local_ip, ip)
        elif opcode == 2:
            arp_message = ARPmessage(2, self.host.mac_address, self.host.local_ip, ip, self.host.mac_address)
        return arp_message

    def handle_arp_message(self, frame):
        if frame.ethernet_type == 2:
            arp_message = frame.packet
            opcode = arp_message.opcode
            dst_ip = arp_message.dst_ip
            src_ip = arp_message.src_ip
            returned_mac = arp_message.dst_mac
            if opcode == 1:
                if dst_ip == self.host.local_ip:
                    response = self.construct_arp_message(src_ip, 2)
                    return response
            if opcode == 2:
                if frame.destination_mac == self.host.mac_address:
                    from engine import ARPobject
                    arp_obj = ARPobject(returned_mac, src_ip)
                    self.host.arp_table.append(arp_obj)

class ICMPhandler:
    def __init__(self, host):
        self.host = host

    def construct_icmp_message(self, opcode, identifier, sequence_num):
        if opcode == 1:
            icmp_message = ICMPmessage(1, identifier, sequence_num, "Hello!")
        if opcode == 2:
            icmp_message = ICMPmessage(2, identifier, sequence_num, "Recieved!")
        return icmp_message

    def handle_icmp_message(self, frame):
        packet = frame.packet
        icmp_message = packet.data

        if packet.protocol == "ICMP":
            opcode = icmp_message.opcode

            if opcode == 1:
                response = self.construct_icmp_message(2, icmp_message.identifier, icmp_message.sequence_num)
                response_packet = Packet(self.host.local_ip, packet.source_ip, "ICMP", response)
                print(f"{icmp_message.payload} from {packet.source_ip}")
                return response_packet
            if opcode == 2:
                print(f"{icmp_message.payload} from {packet.source_ip}")
                return None
