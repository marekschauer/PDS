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
import copy

class RecieveMessagesThread (threading.Thread):
    def __init__(self, sock, peersDict, hello_queue, peersDictMutex):
        threading.Thread.__init__(self)
        self.stopevent = threading.Event()
        self.sock = sock
        self.peersDict = peersDict
        self.helloQueue = hello_queue
        self.peersDictMutex = peersDictMutex
        # self.lstDict = lstDict
        # self.ackDict = ackDict
        # self.errDict = errDict
        # self.dictMutex = dict_mutex
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
            
                # self.dictMutex.acquire()
                if msgType == "hello":
                    print("*******************Prijal som hello od ", message_ip_from
                    , ":", message_port_from)
                    # TODO - ak prisla sprava s ip adresou 0.0.0.0 a portom 0,
                    # vymazeme dany zaznam z nasej DB a posleme UPDATE spravu
                    helloCommand = messages.HelloCommand(data)
                    self.peersDictMutex.acquire()
                    self.peersDict[helloCommand.username] = helloCommand
                    self.peersDictMutex.release()
                    pass
                elif msgType == "getlist":
                    print("!"*30)
                    print("SOM TU SOM TU WOOOHO SOM TU")
                    print("!"*30)
                    command = messages.GetListCommand(data)
                    if True:
                        command.sendAck(self.sock, message_ip_from, message_port_from)
                        # posleme list peerov, ktore mame uschovane
                        # najprv ale spravme poriadok:
                        newPeersDict = copy.copy(self.peersDict)
                        for key in self.peersDict:
                            if (datetime.now() - self.peersDict[key].arrived).seconds > 30:
                                del newPeersDict[key]
                        self.peersDict = newPeersDict
                        
                        dbToBeSent = dict()
                        counter = 0
                        self.peersDictMutex.acquire()
                        for key in self.peersDict:
                            dbToBeSent[str(counter)] = {
                                    "username":self.peersDict[key].username, 
                                    "ipv4": self.peersDict[key].ipv4, 
                                    "port": self.peersDict[key].port
                                    }
                            counter += 1
                        self.peersDictMutex.release()
                        answer = messages.ListCommand({
                            "type":"list", 
                            "txid":command.txid, 
                            "peers": dbToBeSent
                            })
                        
                        print(bencode.decode(bencode.encode(dbToBeSent)))
                        
                        answer.send(self.sock, message_ip_from, message_port_from)
                    else:
                        command.sendError(self.sock, message_ip_from, message_port_from, "Ahhh, nieco sa mi tu pokazilo :-(")
                    pass
                elif msgType == "update":
                    # TODO - zasielat update spravy kazde 4 sekundy
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
                print("peersDict", self.peersDict)
                # print("lstDict", self.lstDict)
                # print("ackDict", self.ackDict)
                # print("errDict", self.errDict)
                # self.dictMutex.release()


class MaintainPeersDatabaseThread (threading.Thread):
    def __init__(self, peersDict, hello_queue, peers_mutex):
        threading.Thread.__init__(self)
        self.stopevent = threading.Event()
        self.peers = peersDict
        self.helloQueue = hello_queue
        self.peersMutex = peers_mutex
    def run(self):
        while True:
            self.peersMutex.acquire()
            for key in self.peers:
                if (datetime.now() - self.peers[key].arrived).seconds > 10:
                    del self.peers[key]
            self.peersMutex.release()
            time.sleep(2)
            # if not self.helloQueue.empty():



# --id <identifikátor> --reg-ipv4 <IP> --reg-port <port>
parser = argparse.ArgumentParser()
parser.add_argument("--id", help="increase output verbosity", required=True, type=str)
parser.add_argument("--reg-ipv4", help="your ipv4 address", required=True, type=str)
parser.add_argument("--reg-port", help="your port", required=True, type=int)
args = parser.parse_args()


UDP_IP   = args.reg_ipv4
UDP_PORT = args.reg_port
PEER_ID = args.id

peersDict = dict()
lstDict = dict()
ackDict = dict()
errDict = dict()
helloQueue = queue.Queue()

dictMutex = threading.Lock()


print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("~~~~~~~~~~I AM REGISTRATION NODE~~~~~~~~~~~~~~~")
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("My IP: ", UDP_IP)
print("My PORT: ", UDP_PORT)
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

recieveMessagesThread = RecieveMessagesThread(sock, peersDict, helloQueue, dictMutex)
recieveMessagesThread.start()

# maintainPeersDatabaseThread = MaintainPeersDatabaseThread(peersDict, helloQueue, dictMutex)
# maintainPeersDatabaseThread.start()

