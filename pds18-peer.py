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
import argparse
#TODO
#   spravit ukoncovanie vlaken
#   vypisovat prichodzie spravy typu MESSAGE

class RecieveMessagesThread (threading.Thread):
    def __init__(self, sock, msgDict, lstDict, ackDict, errDict, mutexes):
        threading.Thread.__init__(self)
        self.stopevent = threading.Event()
        self.sock = sock
        self.msgDict = msgDict
        self.lstDict = lstDict
        self.ackDict = ackDict
        self.errDict = errDict
        self.dictMutex = mutexes["dictMutex"]
        self.msgDictMutex = mutexes["msgDictMutex"]
        self.lstDictMutex = mutexes["lstDictMutex"]
        self.ackDictMutex = mutexes["ackDictMutex"]
        self.errDictMutex = mutexes["errDictMutex"]

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
                # print("-"*20)
                self.dictMutex.acquire()
                if msgType == "message":
                    command = messages.MessageCommand(data)
                    # print("Idem poslat ACK na adresu ", message_ip_from, " a port ", message_port_from)
                    command.sendAck(self.sock, message_ip_from, message_port_from)
                    # print("Poslal som ACK...")
                    # self.msgDictMutex.acquire()
                    # self.msgDict[command.txid] = command
                    # self.msgDictMutex.release()
                    print(command.fromWho, " wrote: ", command.message)
                    # print("@"*5)
                    # for key in self.msgDict:
                    #     print(self.msgDict[key].message)
                    # print("@"*5)
                elif msgType == "list":
                    command = messages.ListCommand(data)
                    command.sendAck(self.sock, message_ip_from, message_port_from)
                    self.lstDictMutex.acquire()
                    self.lstDict[command.txid] = command
                    self.lstDictMutex.release()
                    pass
                elif msgType == "ack":
                    self.ackDictMutex.acquire()
                    command = messages.AckCommand(data)
                    self.ackDict[command.txid] = command
                    self.ackDictMutex.release()
                    pass
                elif msgType == "error":
                    self.errDictMutex.acquire()                    
                    command = messages.ErrorCommand(data)
                    self.errDict[command.txid] = command
                    self.errDictMutex.release()

                    pass
                else:
                    print("Peer recieved unsupported type of message. Message is being ignored", sys.stderr)
                # print("msgDict", self.msgDict)
                # print("lstDict", self.lstDict)
                # print("ackDict", self.ackDict)
                # print("errDict", self.errDict)
                self.dictMutex.release()  
    def stop(self):
        self.stopevent.set()

class KeepConnectionThread(threading.Thread):
    def __init__(self, sock, my_ip, my_port, reg_node_ip, reg_node_port, username):
        threading.Thread.__init__(self)
        self.stopevent = threading.Event()
        self.sock = sock
        self.reg_node_ip = reg_node_ip
        self.reg_node_port = reg_node_port
        self.username = username
        self.my_ip = my_ip
        self.my_port = my_port
    def run(self):
        while not self.stopevent.isSet():
            # sprava na poslanie v json a nasledne ju zakoduj
            messageJSON = {
                "type":"hello", 
                "txid": messages.Command.txidGenerate(), 
                "username": self.username, 
                "ipv4": self.my_ip, 
                "port": self.my_port
            }
            toBeSent = bencode.bencode(messageJSON)
            self.sock.sendto(toBeSent, (self.reg_node_ip, self.reg_node_port))
            time.sleep(3)
    def logout(self):
        self.stopevent.set()
        logoutMessageJson = {
            "type":"hello", 
            "txid": messages.Command.txidGenerate(),
            "username": self.username,
            "ipv4": "0.0.0.0",
            "port": 0
        }
        logoutMessage = messages.HelloCommand(logoutMessageJson)
        logoutMessage.send(self.sock, self.reg_node_ip, self.reg_node_port)
        


class RecieveCommandsFromRPC(threading.Thread):
    def __init__(self, sock, my_ip, my_port, reg_node_ip, reg_node_port, username, peer_id, msgDict, lstDict, ackDict, errDict, mutexes, keepConnectionThread):
        threading.Thread.__init__(self)
        self.stopevent = threading.Event()
        self.sock = sock
        self.reg_node_ip = reg_node_ip
        self.reg_node_port = reg_node_port
        self.my_ip = my_ip
        self.my_port = my_port
        self.username = username
        self.peerId = peer_id
        if os.path.exists("/tmp/pds_rpc_peer_socket" + str(self.peerId)):
            os.remove("/tmp/pds_rpc_peer_socket" + str(self.peerId))
        self.rpcSocket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.rpcSocket.bind("/tmp/pds_rpc_peer_socket" + str(self.peerId))
        self.dictMutex = mutexes["dictMutex"]
        self.msgDictMutex = mutexes["msgDictMutex"]
        self.lstDictMutex = mutexes["lstDictMutex"]
        self.ackDictMutex = mutexes["ackDictMutex"]
        self.errDictMutex = mutexes["errDictMutex"]
        self.msgDict = msgDict
        self.lstDict = lstDict
        self.ackDict = ackDict
        self.errDict = errDict
        self.keepConnectionThread = keepConnectionThread
    def run(self):
        if os.path.exists("/tmp/pds_rpc_peer_socket" + str(self.peerId)):
            # print("existuje socket!")
            
            while True:
                # {'command': 'message', 'from': 'marekschauer', 'to': 'shukarfale', 'message': None}
                rpcCommand = self.rpcSocket.recv(4096)
                recievedCommand = rpcCommand.decode("utf-8")
                recievedCommandDict = json.loads(recievedCommand)

                if recievedCommandDict["command"] == "message":
                    messageToLogin = recievedCommandDict["to"]
                    messageFromLogin = recievedCommandDict["from"]
                    if messageFromLogin != self.username:
                        print("Recieved command from RPC to send message with sender username set to ", messageFromLogin, ", but my username is ", self.username, ". Message will not be sent.", sys.stderr)
                        continue
                    msgToBeSentBody = recievedCommandDict["message"]
                    txid = random.randrange(0,65535)
                    getListMSG = messages.GetListCommand("").fromObject({"type":"getlist","txid":txid})
                    getListMSG.send(self.sock, self.reg_node_ip, self.reg_node_port)
                    thisMoment = datetime.now()
                    while((datetime.now() - thisMoment).seconds < 2):
                        if getListMSG.txid in self.ackDict:
                            # print("prisiel nam ACK na spravu " + str(getListMSG.txid))
                            ack = self.ackDict[getListMSG.txid]
                            self.ackDictMutex.acquire()
                            del self.ackDict[getListMSG.txid]
                            self.ackDictMutex.release()
                            # prijmem LIST spravu
                            while True:
                                if getListMSG.txid in self.lstDict:
                                    listMsg = self.lstDict[getListMSG.txid]
                                    # print("$"*15)
                                    # print("jupiii, prijal som LIST spravu!")
                                    # print(listMsg.peers)
                                    self.lstDictMutex.acquire()
                                    del self.lstDict[getListMSG.txid]
                                    self.lstDictMutex.release()
                                    if listMsg.isUserThere(messageToLogin):
                                        messageToBeSent = messages.MessageCommand({
                                            "type":"message",
                                            "txid":messages.Command.txidGenerate(),
                                            "from":self.username,
                                            "to":messageToLogin,
                                            "message": msgToBeSentBody
                                            })
                                        dstIp, dstPort = listMsg.getUserAddr(messageToLogin)
                                        if dstIp != False and dstPort != False:
                                            messageToBeSent.send(self.sock, dstIp, dstPort)
                                            # print("Poslal som spravu na ", dstIp, ":", dstPort)
                                            thisMoment = datetime.now()
                                            while((datetime.now() - thisMoment).seconds < 2):
                                                if messageToBeSent.txid in self.ackDict:
                                                    ack = self.ackDict[messageToBeSent.txid]
                                                    # print("Dostal som ACK na MESSAGE, ktoru som odoslal")
                                                    self.ackDictMutex.acquire()
                                                    del self.ackDict[messageToBeSent.txid]
                                                    self.ackDictMutex.release()
                                                    break
                                                elif messageToBeSent.txid in self.errDict:
                                                    errMsg = errDict[messageToBeSent.txid]
                                                    self.errDictMutex.acquire()
                                                    del self.errDict[messageToBeSent.txid]
                                                    self.errDictMutex.release()
                                                    print("Following ERR mesage has been recieved from another peer as an answer to MESSAGE message:", sys.stderr)
                                                    print("\t\"" + errMsg.verbose + "\"")
                                                    break
                                    # print("$"*15)
                                    break
                            break
                        elif getListMSG.txid in self.errDict:
                            errMsg = errDict[getListMSG.txid]
                            self.errDictMutex.acquire()
                            del self.errDict[getListMSG.txid]
                            self.errDictMutex.release()
                            print("Following ERR mesage has been recieved from registration node as an answer to GETLIST message:", sys.stderr)
                            print("\t\"" + errMsg.verbose + "\"")
                            break
                        else:
                            # print("nedoslo nic, opakujem")
                            pass
                    # print("doslo ci nedoslo, som vonku")
                elif recievedCommandDict["command"] == "getlist":
                    txid = messages.Command.txidGenerate()
                    getListMSG = messages.GetListCommand("").fromObject({
                        "type":"getlist",
                        "txid":txid
                        })
                    getListMSG.send(self.sock, self.reg_node_ip, self.reg_node_port)
                    answerRecieved = False
                    thisMoment = datetime.now()
                    while((datetime.now() - thisMoment).seconds < 2):
                        if getListMSG.txid in self.ackDict:
                            ack = self.ackDict[getListMSG.txid]
                            self.ackDictMutex.acquire()
                            del self.ackDict[getListMSG.txid]
                            self.ackDictMutex.release()
                            answerRecieved = True
                            break
                        elif getListMSG.txid in self.errDict:
                            errMsg = errDict[getListMSG.txid]
                            self.errDictMutex.acquire()
                            del self.errDict[getListMSG.txid]
                            self.errDictMutex.release()
                            print("Following ERR mesage has been recieved from registration node as an answer to GETLIST message:", sys.stderr)
                            print("\t\"" + errMsg.verbose + "\"")
                            answerRecieved = True
                            break
                        else:
                            pass
                    if not answerRecieved:
                        print("No answer has been recieved to GETLIST message", sys.stderr)
                elif recievedCommandDict["command"] == "peers":
                    txid = messages.Command.txidGenerate()
                    getListMSG = messages.GetListCommand("").fromObject({
                        "type":"getlist",
                        "txid":txid
                        })
                    getListMSG.send(self.sock, self.reg_node_ip, self.reg_node_port)
                    answerRecieved = False
                    thisMoment = datetime.now()
                    while((datetime.now() - thisMoment).seconds < 2):
                        if getListMSG.txid in self.ackDict:
                            ack = self.ackDict[getListMSG.txid]
                            self.ackDictMutex.acquire()
                            del self.ackDict[getListMSG.txid]
                            self.ackDictMutex.release()
                            answerRecieved = True
                            while True:
                                if getListMSG.txid in self.lstDict:
                                    listMsg = self.lstDict[getListMSG.txid]
                                    listMsg.printPeers()
                                    self.lstDictMutex.acquire()
                                    del self.lstDict[getListMSG.txid]
                                    self.lstDictMutex.release()
                                    break
                            break
                        elif getListMSG.txid in self.errDict:
                            errMsg = errDict[getListMSG.txid]
                            self.errDictMutex.acquire()
                            del self.errDict[getListMSG.txid]
                            self.errDictMutex.release()
                            answerRecieved = True
                            print("Following ERR mesage has been recieved from registration node as an answer to GETLIST message:", sys.stderr)
                            print("\t\"" + errMsg.verbose + "\"")
                            break
                        else:
                            pass
                    if not answerRecieved:
                        print("No answer has been recieved to GETLIST message", sys.stderr)
                elif recievedCommandDict["command"] == "reconnect":
                    self.keepConnectionThread.logout()
                    newRegNodeIp = recievedCommandDict["reg_ipv4"]
                    newRegNodePort = recievedCommandDict["reg_port"]
                    print("hello")
                    self.keepConnectionThread = KeepConnectionThread(self.sock, self.my_ip, self.my_port, newRegNodeIp, int(newRegNodePort), self.username)
                    self.keepConnectionThread.start()

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
=================================================================
=================================================================
== Let's the magic happen! Starting point of peer application ===
=================================================================
=================================================================
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
parser = argparse.ArgumentParser()
parser.add_argument("--id", help="increase output verbosity", required=True, type=str)
parser.add_argument("--username", help="your username, which will be unique throghout the network", required=True, type=str)
parser.add_argument("--chat-ipv4", help="your ipv4 address", required=True, type=str)
parser.add_argument("--chat-port", help="your port", required=True, type=int)
parser.add_argument("--reg-ipv4", help="ipv4 of your registration node", required=True, type=str)
parser.add_argument("--reg-port", help="port of your registration node", required=True, type=int)
args = parser.parse_args()

UDP_IP   = args.chat_ipv4
UDP_PORT = args.chat_port
REG_NODE_UDP_IP = args.reg_ipv4
REG_NODE_UDP_PORT = args.reg_port
PEER_ID = args.id
PEER_USERNAME = args.username
DEBUG_MODE = True

msgDict = dict()
lstDict = dict()
ackDict = dict()
errDict = dict()

mutexes = dict()
mutexes["dictMutex"] = threading.Lock()
mutexes["msgDictMutex"] = threading.Lock()
mutexes["lstDictMutex"] = threading.Lock()
mutexes["ackDictMutex"] = threading.Lock()
mutexes["errDictMutex"] = threading.Lock()

if DEBUG_MODE:
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("My IP: ", UDP_IP)
    print("My PORT: ", UDP_PORT)
    print("Registration node IP: ", REG_NODE_UDP_IP)
    print("Registration node PORT: ", REG_NODE_UDP_PORT)
    print("Peer id: ", PEER_ID)
    print("Peer username: ", PEER_USERNAME)
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

recieveMessagesThread = RecieveMessagesThread(sock, msgDict, lstDict, ackDict, errDict, mutexes)
recieveMessagesThread.start()

keepConnectionThread = KeepConnectionThread(sock, UDP_IP, UDP_PORT, REG_NODE_UDP_IP, REG_NODE_UDP_PORT, PEER_USERNAME)
keepConnectionThread.start()

recieveRPCCommands = RecieveCommandsFromRPC(sock, UDP_IP, UDP_PORT, REG_NODE_UDP_IP, REG_NODE_UDP_PORT, PEER_USERNAME, PEER_ID, msgDict, lstDict, ackDict, errDict, mutexes, keepConnectionThread)
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
