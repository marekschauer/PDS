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
                    # command = messages.MessageCommand(data)
                    # command.sendAck(self.sock, message_ip_from, message_port_from)
                    # self.msgDict[command.txid] = command
                    pass
                elif msgType == "getlist":
                    command = messages.GetListCommand(data)
                    print("idem poslat ack...")
                    command.sendAck(self.sock, message_ip_from, message_port_from)
                    print("poslal som ack...")
                    #TODO - posleme list peerov, ktore mame uschovane
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



UDP_IP   = '192.168.1.17'
UDP_PORT = 13005
REG_NODE_UDP_IP = '192.168.1.17'
REG_NODE_UDP_PORT = 5678
PEER_ID = "951627843"

msgDict = dict()
lstDict = dict()
ackDict = dict()
errDict = dict()

dictMutex = threading.Lock()


print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("My IP: ", UDP_IP)
print("My PORT: ", UDP_PORT)
print("Registration node IP: ", REG_NODE_UDP_IP)
print("Registration node PORT: ", REG_NODE_UDP_PORT)
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

recieveMessagesThread = RecieveMessagesThread(sock, msgDict, lstDict, ackDict, errDict, dictMutex)
recieveMessagesThread.start()

print("Idem poslat tu spravu teda...")
toBeSent = messages.MessageCommand(bytes("d4:from8:xlogin007:message9:blablabla2:to8:xnigol994:txidi6546e4:type7:messagee".encode("utf-8")))
toBeSent.send(sock, REG_NODE_UDP_IP, REG_NODE_UDP_PORT)


