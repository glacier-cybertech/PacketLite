# PacketLite
A simple network simulator tool with a GUI coded in python
Simulates Layers 1 and 2 of the OSI model
Includes functional DHCP, ARP, ICMP, Subnets, Local ips, mac addresses, and default gateways.

This is my first python program ive written, it took me about 3 days to create and I made it to help me learn networking and the first two layers of the OSI model better, aswell as learn basics of python.

![Screenshot](https://raw.githubusercontent.com/glacier-cybertech/PacketLite/refs/heads/main/assets/screenshot.png)

## Download
Download the project, then install requirements using 

```bash
pip install -r requirements.txt
```

Run main.py to start the program

```bash
python main.py
```

## Usage guide

### Placing a node
Right click any empty area in the workspace to bring up the options selection, then select the node you wish to place down,
Options include:
-Router (has no routing or interface capabilities currently, acts as a dhcp server)
-Pc
-Switch

### Connecting nodes
Right click any placed node and select connect, then left click the node you wish to connect it to.

### Using DHCP
Once you have a PC placed with a valid connection path to a router, you can right click the pc and select "Send DHCP request" to send out a DHCP discover request, if it is succesfuly connected to a router it will recieve and apply the offered IP, subnet mask, and default gateway.

### Pinging another PC
Once you have two pcs connected to a router that have both recieved IP addresses, you can select the "Send Ping" option and type the ip of the PC you wish to ping.

### ARP 
When using the ping, the pc will automatically send out an ARP request for the given IP address if it is not already stored in its ARP table.

## Limitations
Currently, the router is the most limited, not supporting multiple interfaces, different subnets, routing to different networks, etc. It essentially acts as a DHCP server with switching capabilities. I plan to add routing functionality in the future when I feel like it

## Notes
The main.py file which purely handles the GUI was written by gemini, while the rest of the logic was written 95% by me with some help from gemini for logic errors and small bug fixes.
this is just a silly lil project i did to learn networking and some protocols, not meant to be used as an actual tool. feedback is appreciated but remember this is my first ever project :D 
