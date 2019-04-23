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

def hovadina(someStr):
    for c in someStr:
        print(ord(c))

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
                if msgType == "message":
                    command = messages.MessageCommand(data)
                    command.sendAck(self.sock, message_ip_from, message_port_from)
                    self.msgDict[command.txid] = command
                elif msgType == "list":
                    command = messages.ListCommand(data)
                    command.sendAck(self.sock, message_ip_from, message_port_from)
                    self.lstDict[command.txid] = command
                    pass
                elif msgType == "ack":
                    command = messages.AckCommand(data)
                    self.ackDict[command.txid] = command
                    pass
                elif msgType == "error":
                    command = messages.ErrorCommand(data)
                    self.errDict[command.txid] = command
                    pass
                else:
                    print("Peer recieved unsupported type of message. Message is being ignored", sys.stderr)
                print("-"*20)
                print("msgDict", self.msgDict)
                print("lstDict", self.lstDict)
                print("ackDict", self.ackDict)
                print("errDict", self.errDict)
                self.dictMutex.release()
            
            

            
    def stop(self):
        self.stopevent.set()

class KeepConnectionThread(threading.Thread):
    def __init__(self, sock, reg_node_ip, reg_node_port, username):
        threading.Thread.__init__(self)
        self.stopevent = threading.Event()
        self.sock = sock
        self.reg_node_ip = reg_node_ip
        self.reg_node_port = reg_node_port
        self.username = username
    def run(self):
        while not self.stopevent.isSet():
            # sprava na poslanie v json a nasledne ju zakoduj
            messageJSON = {
                "type":"hello", 
                "txid": random.randint(0,65535), 
                "username": self.username, 
                "ipv4": self.reg_node_ip, 
                "port": self.reg_node_port
            }
            toBeSent = bencode.bencode(messageJSON)
            print("~~~~~~~~~~~~~~~~~~~~~~~~~")
            print(toBeSent)
            print("~~~~~~~~~~~~~~~~~~~~~~~~~")
            print("idem poslat hello...")
            print(self.reg_node_ip)
            print(self.reg_node_port)
            self.sock.sendto(toBeSent, (self.reg_node_ip, self.reg_node_port))
            print("poslal som hello, idem odznova...")
            time.sleep(3)
    def logout(self):
        # logoutMessageJson = {
        #     "type":"hello", 
        #     "txid": random.randint(0,65535),
        #     "username": self.username,
        #     "ipv4": "0.0.0.0",
        #     "port": 0
        # }
        # toBeSent = bencode.bencode(logoutMessageJson)
        # self.sock.sendto(toBeSent, (self.reg_node_ip, self.reg_node_port))
        self.stopevent.set()
        # while True:
        #     print("Som v logout metode a uvidime, ci pojde aj run metoda...")
        #     time.sleep(2)


class RecieveCommandsFromRPC(threading.Thread):
    def __init__(self, sock, reg_node_ip, reg_node_port, username, peer_id, msgDict, lstDict, ackDict, errDict, dict_mutex):
        threading.Thread.__init__(self)
        self.stopevent = threading.Event()
        self.sock = sock
        self.reg_node_ip = reg_node_ip
        self.reg_node_port = reg_node_port
        self.username = username
        self.peerId = peer_id
        if os.path.exists("/tmp/pds_rpc_peer_socket" + str(self.peerId)):
            os.remove("/tmp/pds_rpc_peer_socket" + str(self.peerId))
        self.rpcSocket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.rpcSocket.bind("/tmp/pds_rpc_peer_socket" + str(self.peerId))
        self.dictMutex = dict_mutex
        self.msgDict = msgDict
        self.lstDict = lstDict
        self.ackDict = ackDict
        self.errDict = errDict
    def run(self):
        if os.path.exists("/tmp/pds_rpc_peer_socket" + str(self.peerId)):
            print("existuje socket!")
            #1 citanie z BSD schranok pre zistenie, ci sa ma alebo nema odoslat sprava
            #  sprava sa zada RPCcku, RPCcko to posle tomuto programu, ktory si to precita
            #2 poslem GETLIST spravu svojmu registracnemu uzlu (musim prijat ACK/ERROR)
            #  a potom prijmem spravu LIST (na ktoru zase musim poslat ACK/ERROR)
            #3 zo spravy LIST zistim, ci viem spravu poslat danemu uzivatelovi (podla toho,
            #  ci je dany uzivatel obsiahnuty v sprave list)
            #4 ak je username v sprave LIST, mam jeho IP adresu a port a poslem mu spravu MESSAGE
            #5 cakam, ci dostanem ACK/ERROR na poslanu message
            while True:
                rpcCommand = self.rpcSocket.recv(4096)
                print(rpcCommand.decode("utf-8"))
                
                # Mame pokyn, ze treba poslat spravu - podme poslat GETLIST nasmu reg. uzlu
                # while True:
                txid = random.randrange(0,65535)
                getListMSG = messages.GetListCommand("").fromObject({"type":"getlist","txid":txid})
                getListMSG.send(self.sock, self.reg_node_ip, self.reg_node_port)
                thisMoment = datetime.now()
                while((datetime.now() - thisMoment).seconds < 2):
                    if getListMSG.txid in self.ackDict:
                        print("prisiel nam ACK na spravu " + str(getListMSG.txid))
                        self.dictMutex.acquire()
                        del self.ackDict[getListMSG.txid]
                        self.dictMutex.release()
                        break
                    elif getListMSG.txid in self.errDict:
                        print("prisiel nam ERR na spravu " + str(getListMSG.txid))
                        self.dictMutex.acquire()
                        del self.errDict[getListMSG.txid]
                        self.dictMutex.release()
                        break
                    else:
                        print("nedoslo nic, opakujem")
                        pass
                print("doslo ci nedoslo, som vonku")
                



UDP_IP   = '192.168.1.17'
UDP_PORT = 5678
REG_NODE_UDP_IP = '192.168.1.17'
# REG_NODE_UDP_IP = '127.0.0.1'
REG_NODE_UDP_PORT = 13005
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

# keepConnectionThread = KeepConnectionThread(sock, REG_NODE_UDP_IP, REG_NODE_UDP_PORT, "soskemange")
# keepConnectionThread.start()

recieveRPCCommands = RecieveCommandsFromRPC(sock, REG_NODE_UDP_IP, REG_NODE_UDP_PORT, "soskemange", PEER_ID, msgDict, lstDict, ackDict, errDict, dictMutex)
recieveRPCCommands.start()



# for line in fileinput.input():
#     print("idem von...")
#     # keepConnectionThread.logout()
#     recieveMessagesThread.stop()
#     print("idem cakat na stop connection threadu")
#     # keepConnectionThread.join()
#     print("idem cakat na stop message threadu")
#     recieveMessagesThread.join()
#     print("skoncene, idem breaknut")
#     break

# print("som tu mehehe")
# sys.exit()
    


# time.sleep(10)

# print("Poslal som")
