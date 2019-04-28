#!/usr/bin/env python3

"""
RPC application for sending messages to peer or registration node
PDS project
Hybrid chat 
Author: Marek Schauer (xschau00)
Year: 2018/2019

"""
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
parser.add_argument("--node", help="send controll message to the peer", action="store_true")
parser.add_argument("--command", help="send controll message to the peer", type=str)
parser.add_argument("--from", help="from username", type=str)
parser.add_argument("--to", help="to username", type=str)
parser.add_argument("--message", help="the text of message", type=str)
parser.add_argument("--reg-ipv4", help="the ipv4 address of registration node", type=str)
parser.add_argument("--reg-port", help="the port number of registration node", type=str)
args = parser.parse_args()
supportedCommand = True

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
    else:
        print("Command", args.command, "is not supported", sys.stderr)
        supportedCommand = False

    if supportedCommand:
        if os.path.exists("/tmp/pds_rpc_peer_socket" + args.id):
            peer = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            peer.connect("/tmp/pds_rpc_peer_socket" + args.id)
            peer.send(toBeSent.encode("utf-8"))
        else:
            print("Could not send command to the peer, socket does not exist", sys.stderr)
elif args.node:
    if args.command == "database":
        # zobrazí aktuální databázi peerů a jejich mapování
        toBeSent = json.dumps({
            "command":"database",
        })
        pass
    elif args.command == "neighbors":
        # zobrazí seznam aktuálních sousedů registračního uzlu
        toBeSent = json.dumps({
            "command":"neighbors",
        })
        pass
    elif args.command == "connect":
        toBeSent = json.dumps({
            "command":"connect",
            "reg_ipv4":args.reg_ipv4,
            "reg_port":args.reg_port
        })
        pass
    elif args.command == "disconnect":
        toBeSent = json.dumps({
            "command":"disconnect",
        })
        pass
    elif args.command == "sync":
        toBeSent = json.dumps({
            "command":"sync",
        })
        pass
    else:
        print("Command", args.command, "is not supported", sys.stderr)
        supportedCommand = False

    if supportedCommand:
        if os.path.exists("/tmp/pds_rpc_node_socket" + args.id):
            peer = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            peer.connect("/tmp/pds_rpc_node_socket" + args.id)
            peer.send(toBeSent.encode("utf-8"))
        else:
            print("Could not send command to the node, socket does not exist", sys.stderr)
