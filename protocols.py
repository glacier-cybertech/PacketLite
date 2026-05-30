class DHCPrequest:
    def __init__(self, opcode, client_mac):
        self.opcode = opcode
        self.client_mac = client_mac
        self.returned_localip = None
        self.returned_gateway = None
        self.returned_subnet = None
        self.server_id = None

class ARPmessage:
    def __init__(self, opcode, src_mac, src_ip, dst_ip, dst_mac = None):
        self.opcode = opcode
        self.src_mac = src_mac
        self.src_ip = src_ip
        self.dst_mac = dst_mac
        self.dst_ip = dst_ip

class ICMPmessage:
    def __init__(self, opcode, identifier, sequence_num, response):
        self.opcode = opcode
        self.identifier = identifier
        self.sequence_num = sequence_num
        self.payload = response
