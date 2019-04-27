#!/usr/bin/env python3
import socket
import threading
import time
import json
import random
import bencode
import fileinput
import sys
import os
import messages
import argparse
import queue
from datetime import datetime

class RecieveMessagesThread (threading.Thread):
    def __init__(self, sock, msgDict, lstDict, ackDict, errDict, dict_mutex):
        threading.Thread.__init__(self)
        self.stopevent = threading.Event()
        self.sock = sock
        self.msgDict = msgDict
        self.lstDict = lstDict
        self.ackDict = ackDict
        self.errDict = errDict
        self.dictMutex = dict_mutex
    def run(self):
        while True:
            
            data, (message_ip_from, message_port_from) = self.sock.recvfrom(4096)
            
            try:
                msgType = messages.Command.msgType(data)
            except:
                print("Error while message decoding", sys.stderr)
                print(data, sys.stderr)
            else:
                command = None
            
                self.dictMutex.acquire()
                if msgType == "hello":
                    print("*******************Prijal som hello od ", message_ip_from
                    , ":", message_port_from)
                    # command = messages.MessageCommand(data)
                    # command.sendAck(self.sock, message_ip_from, message_port_from)
                    # self.msgDict[command.txid] = command
                    pass
                elif msgType == "getlist":
                    command = messages.GetListCommand(data)
                    if True:
                        command.sendAck(self.sock, message_ip_from, message_port_from)
                        #TODO - posleme list peerov, ktore mame uschovane
                        answer = messages.ListCommand({"type":"list", "txid":command.txid, "peers": {"0":{"username":"marekschauer", "ipv4": "192.168.1.17", "port": 34567}, "1":{"username":"shukarfale", "ipv4": "192.168.1.17", "port": 35765}}})
                        answer.send(self.sock, message_ip_from, message_port_from)
                    else:
                        command.sendError(self.sock, message_ip_from, message_port_from, "Ahhh, nieco sa mi tu pokazilo :-(")
                    pass
                elif msgType == "update":
                    # command = messages.ListCommand(data)
                    # command.sendAck(self.sock, message_ip_from, message_port_from)
                    # self.lstDict[command.txid] = command
                    pass
                elif msgType == "disconnect":
                    # command = messages.ListCommand(data)
                    # command.sendAck(self.sock, message_ip_from, message_port_from)
                    # self.lstDict[command.txid] = command
                    pass
                elif msgType == "ack":
                    # command = messages.AckCommand(data)
                    # # self.ackDict[command.txid] = command
                    pass
                elif msgType == "error":
                    # command = messages.ErrorCommand(data)
                    # # self.errDict[command.txid] = command
                    pass
                else:
                    print("Peer recieved unsupported type of message. Message is being ignored", sys.stderr)
                print("-"*20)
                print("msgDict", self.msgDict)
                print("lstDict", self.lstDict)
                print("ackDict", self.ackDict)
                print("errDict", self.errDict)
                self.dictMutex.release()


# --id <identifikátor> --reg-ipv4 <IP> --reg-port <port>
parser = argparse.ArgumentParser()
parser.add_argument("--id", help="increase output verbosity", required=True, type=str)
parser.add_argument("--reg-ipv4", help="your ipv4 address", required=True, type=str)
parser.add_argument("--reg-port", help="your port", required=True, type=int)
args = parser.parse_args()


UDP_IP   = args.reg_ipv4
UDP_PORT = args.reg_port
PEER_ID = args.id

msgDict = dict()
lstDict = dict()
ackDict = dict()
errDict = dict()

dictMutex = threading.Lock()


print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("~~~~~~~~~~I AM REGISTRATION NODE~~~~~~~~~~~~~~~")
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("My IP: ", UDP_IP)
print("My PORT: ", UDP_PORT)
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

recieveMessagesThread = RecieveMessagesThread(sock, msgDict, lstDict, ackDict, errDict, dictMutex)
recieveMessagesThread.start()
