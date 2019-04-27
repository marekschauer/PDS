#!/usr/bin/env python3

import socket
import threading
import time
import json
import random
import bencode
import os
import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--id", help="identification of peer/node instance", type=str)
parser.add_argument("--peer", help="send controll message to the peer", action="store_true")
parser.add_argument("--command", help="send controll message to the peer", type=str)
parser.add_argument("--from", help="from username", type=str)
parser.add_argument("--to", help="to username", type=str)
parser.add_argument("--message", help="the text of message", type=str)
parser.add_argument("--reg-ipv4", help="the ipv4 address of new registration node", type=str)
parser.add_argument("--reg-port", help="the port number of new registration node", type=str)
args = parser.parse_args()

if args.peer:
    if args.command == "message":
        toBeSent = json.dumps({
            "command":"message",
            "from":getattr(args, 'from'),
            "to":args.to,
            "message": args.message
            })
         
    
    elif args.command == "getlist":
        # peer odešle zprávu GETLIST a nechá si ji potvrdit
        toBeSent = json.dumps({
            "command":"getlist"
        })
        pass
    elif args.command == "peers":
        toBeSent = json.dumps({
            "command":"peers"
        })
        pass
    elif args.command == "reconnect":
        # peer se odpojí od současného registračního uzlu (nulové 
        # HELLO) a připojí se k uzlu specifikovaném v parametrech
        toBeSent = json.dumps({
            "command":"reconnect",
            "reg_ipv4":args.reg_ipv4,
            "reg_port":args.reg_port
        })
        pass
    if os.path.exists("/tmp/pds_rpc_peer_socket" + args.id):
        peer = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        peer.connect("/tmp/pds_rpc_peer_socket" + args.id)
        peer.send(toBeSent.encode("utf-8"))
    else:
        print("Could not send command to the peer, socket does not exist", sys.stderr)

    




# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# sock.bind(("127.0.0.1", 25010))
# while True:
#     data, addr = sock.recvfrom(4096)
#     print(data.decode("utf-8"))
