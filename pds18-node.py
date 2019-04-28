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
    def __init__(self, sock, instanceInfo, hello_queue, peersDictMutex, nodes_dict_mutex):
        threading.Thread.__init__(self)
        global peersDict
        global nodesDict
        self.stopevent = threading.Event()
        self.sock = sock
        self.instanceInfo = instanceInfo
        # peersDict = peersDict
        self.nodesDict = nodesDict
        self.helloQueue = hello_queue
        self.peersDictMutex = peersDictMutex
        self.nodesDictMutex = nodes_dict_mutex
        # self.maintainPeersDatabaseThread = maintainPeersDatabaseThread

        # self.lstDict = lstDict
        # self.ackDict = ackDict
        # self.errDict = errDict
        # self.dictMutex = dict_mutex
    def run(self):
        global peersDict
        global nodesDict
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
                    # print("*******************Prijal som hello od ", message_ip_from
                    # , ":", message_port_from)

                    # TODO - ak prisla sprava s ip adresou 0.0.0.0 a portom 0,
                    # vymazeme dany zaznam z nasej DB a posleme UPDATE spravu
                    helloCommand = messages.HelloCommand(data)
                    peerEntry = PeersDBRecord(
                        helloCommand.ipv4, 
                        helloCommand.port, 
                        helloCommand.username, 
                        self.instanceInfo["UDP_IP"], 
                        self.instanceInfo["UDP_PORT"],
                        True)
                    self.peersDictMutex.acquire()
                    peersDict[helloCommand.username] = peerEntry
                    self.peersDictMutex.release()
                    # self.maintainPeersDatabaseThread.updatePeers(self.peersDict)

                    pass
                elif msgType == "getlist":
                    # print("!"*30)
                    # print("SOM TU SOM TU WOOOHO SOM TU")
                    # print("!"*30)
                    command = messages.GetListCommand(data)
                    if True:
                        command.sendAck(self.sock, message_ip_from, message_port_from)
                        
                        # posleme list peerov, ktore mame uschovane                        
                        self.peersDictMutex.acquire()
                        peersToBeSent = copy.copy(peersDict)
                        self.peersDictMutex.release()

                        dbToBeSent = dict()
                        counter = 0
                        for key in peersToBeSent:
                            dbToBeSent[str(counter)] = {
                                    "username":peersDict[key].username, 
                                    "ipv4": peersDict[key].ipv4, 
                                    "port": peersDict[key].port
                                    }
                            counter += 1
                        answer = messages.ListCommand({
                            "type":"list", 
                            "txid":command.txid, 
                            "peers": dbToBeSent
                            })
                        
                        # print(bencode.decode(bencode.encode(dbToBeSent)))
                        
                        answer.send(self.sock, message_ip_from, message_port_from)
                    else:
                        command.sendError(self.sock, message_ip_from, message_port_from, "Ahhh, nieco sa mi tu pokazilo :-(")
                    pass
                elif msgType == "update":
                    updateMessage = messages.UpdateCommand(data)

                    # Pri kazdej prichodzej UPDATE sprave vlozim do databazy
                    # nodov zaznam pre odosielatela a potom zaznamy pre vsetkych,
                    # co mi boli poslane v tejto sprave (tu musim kontrolovat, ci to nie som ja)
                    senderIp = message_ip_from
                    senderPort = message_port_from
                    newNodeEntry = NodesDBRecord(senderIp, senderPort, True)
                    self.nodesDictMutex.acquire()
                    nodesDict[newNodeEntry.nodeHash] = newNodeEntry
                    self.nodesDictMutex.release()

                    for ipAndPort in updateMessage.db:
                        
                        ipPortList = ipAndPort.split(",")
                        if (len(ipPortList) == 2):
                            nodeIp = ipPortList[0]
                            nodePort = ipPortList[1]
                        else:
                            continue

                        if not (nodeIp == self.instanceInfo["UDP_IP"] and nodePort == self.instanceInfo["UDP_PORT"]):
                            # pridam vsetkych, ktori su v tej sprave okrem mna sameho seba
                            # ak uz tam taky zaznam je, nedam ho tam znova ale necham
                            # ho zit vlastnym zivotom
                            newNodeEntry = NodesDBRecord(nodeIp, nodePort, False)
                            if not newNodeEntry.nodeHash in nodesDict:
                                self.nodesDictMutex.acquire()
                                nodesDict[newNodeEntry.nodeHash] = newNodeEntry
                                self.nodesDictMutex.release()
                        
                        for peerKey, peerRecord in updateMessage.db[ipAndPort].items():
                            if ipAndPort != str(self.instanceInfo["UDP_IP"] + "," + str(self.instanceInfo["UDP_PORT"])):
                            # ulozim si len tych peerov, ktorych nepoznam
                                # print("!"*20, 
                                #     "\n", 
                                #     "Zapisujem si k sebe", 
                                #     peerRecord["username"], 
                                #     "lebo",
                                #     ipAndPort,
                                #     "!=",
                                #     str(self.instanceInfo["UDP_IP"] + "," + str(self.instanceInfo["UDP_PORT"])),
                                #     "!"*20, 
                                #     "\n")
                                authoritative = False
                                if peerKey == str(senderIp + "," + str(senderPort)):
                                    authoritative = True
                                
                                peerEntry = PeersDBRecord(
                                        peerRecord["ipv4"], 
                                        peerRecord["port"], 
                                        peerRecord["username"], 
                                        nodeIp,
                                        nodePort,
                                        authoritative)

                                self.peersDictMutex.acquire()
                                peersDict[peerRecord["username"]] = peerEntry
                                self.peersDictMutex.release()
                            else:
                                pass
                    # Prejdem si databazu a pozriem sa na IP a port odosielatela
                    # najdem si v databaze, ktoru mi poslal zaznam pre IP a port odosielatela
                    # vsetky jeho zaznamy si pridam do mojej databazy peerov
                    # for key, record in updateMessage.db[senderIp + "," + str(senderPort)].items():
                    #     # print("*"*30, record, "*"*30)
                    #     # helloCommand = messages.HelloCommand({
                    #     #                 "type": "hello",
                    #     #                 "txid": messages.Command.txidGenerate(),
                    #     #                 "username": record["username"],
                    #     #                 "ipv4": record["ipv4"],
                    #     #                 "port": record["port"]
                    #     #                 })
                    #     peerEntry = PeersDBRecord(
                    #             record["ipv4"], 
                    #             record["port"], 
                    #             record["username"], 
                    #             senderIp,
                    #             senderPort,
                    #             True)
                    #     self.peersDictMutex.acquire()
                    #     peersDict[record["username"]] = peerEntry
                    #     self.peersDictMutex.release()

                    # self.maintainPeersDatabaseThread.updatePeers(self.peersDict)
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
                # print("-"*20)
                # print("peersDict", peersDict)
                # print("nodesDict obsahuje", len(nodesDict), "prvkov:", nodesDict)
                # print("lstDict", self.lstDict)
                # print("ackDict", self.ackDict)
                # print("errDict", self.errDict)
                # self.dictMutex.release()
    # # def updatePeers(self, peersDict):
    # #     self.peersDictMutex.acquire()
    # #     self.peersDict = peersDict
    # #     self.peersDictMutex.release()
    # def updateNodes(self, nodesDict):
    #     self.nodesDictMutex.acquire()
    #     self.nodesDict = nodesDict
    #     self.nodesDictMutex.release()
    def setMaintainPeersDatabaseThread(self, maintainPeersDatabaseThread):
        self.maintainPeersDatabaseThread = maintainPeersDatabaseThread


class MaintainPeersDatabaseThread (threading.Thread):
    def __init__(self, socket, instanceInfo, hello_queue, peers_mutex, nodes_dict_mutex):
        threading.Thread.__init__(self)
        global peersDict
        global nodesDict
        self.stopevent = threading.Event()
        # self.peersDict = peersDict
        # self.nodes = nodesDict
        self.helloQueue = hello_queue
        self.peersMutex = peers_mutex
        self.nodesDictMutex = nodes_dict_mutex
        self.instanceInfo = instanceInfo
        self.sock = socket

        #TODO - zmaz cely nasledujuci if aj s telom
        # if self.instanceInfo["UDP_PORT"] == 13002:
        #     anotherNode = NodesDBRecord("192.168.1.15", 13001, True)
        #     nodesDict[anotherNode.nodeHash] = anotherNode
        #     anotherNode = NodesDBRecord("192.168.1.15", 13003, True)
        #     nodesDict[anotherNode.nodeHash] = anotherNode
        #     anotherNode = NodesDBRecord("192.168.1.15", 13004, True)
        #     nodesDict[anotherNode.nodeHash] = anotherNode
    def run(self):
        global peersDict
        global nodesDict
        while True:
            # V tomto vlakne budem odosielat UPDATE spravy vsetkym
            # nodeom, ktore mam v self.nodes a budem im odosielat
            # moju databazu peerov.
            # 
            # Pred odoslanim peerov sa tato databaza updatuje
            # (zmazu sa stari peerovia):
            self.peersMutex.acquire()
            newPeersDict = copy.copy(peersDict)
            for key in peersDict:
                # print(type(peersDict[key]))
                if (datetime.now() - (peersDict[key]).arrived).seconds > 10:
                    # TODO - limit ma byt 30 sekund
                    del newPeersDict[key]
            peersDict = newPeersDict
            self.peersMutex.release()
            # self.recieveMessagesThread.updatePeers(peersDict)
            
            # Teraz mozeme odoslat nasu DB peerov ostatnym peerom
            # posleme list peerov, ktore mame uschovane                        
            self.peersMutex.acquire()
            peersToBeSent = copy.copy(peersDict)
            self.peersMutex.release()

            myPeersDBToBeSent = dict()
            counter = 0
            peersToBeSent = getPeersByNode(peersToBeSent, self.instanceInfo["UDP_IP"], self.instanceInfo["UDP_PORT"])
            for key in peersToBeSent:
                myPeersDBToBeSent[str(counter)] = {
                        "username":peersDict[key].username, 
                        "ipv4": peersDict[key].ipv4, 
                        "port": peersDict[key].port
                        }
                counter += 1
            
            peersDatabase = {
                self.instanceInfo["UDP_IP"] + "," + str(self.instanceInfo["UDP_PORT"]): myPeersDBToBeSent
            }

            for key, node in nodesDict.items():
                peersOfNode = getPeersByNode(peersDict, node.ip, node.port)
                peersOfNodeDb = dict()
                counter = 0
                for username, peer in peersOfNode.items():
                    peersOfNodeDb[str(counter)] = {
                            "username":peer.username, 
                            "ipv4": peer.ipv4, 
                            "port": peer.port
                            }
                    counter += 1
                peersDatabase[node.ip + "," + str(node.port)] = peersOfNodeDb

            commandToBeSent = messages.UpdateCommand({
                "type":"update", 
                "txid":messages.Command.txidGenerate(), 
                "db": peersDatabase
            })

            for key in nodesDict:
                commandToBeSent.send(self.sock, (nodesDict[key]).ip, (nodesDict[key]).port)
                pass
            
            time.sleep(3)
        pass
    def setRecieveMessagesThread(self, recieveMessagesThread):
        self.recieveMessagesThread = recieveMessagesThread

class MaintainNodesDatabaseThread (threading.Thread):
    def __init__(self, nodesDictMutex, recieveMessagesThread):
        global nodesDict
        threading.Thread.__init__(self)
        # nodesDict = nodesDict
        self.nodesDictMutex = nodesDictMutex
        self.recieveMessagesThread = recieveMessagesThread
    def run(self):
        global nodesDict
        while True:
            self.nodesDictMutex.acquire()
            newNodesDict = copy.copy(nodesDict)
            for key in nodesDict:
                if (datetime.now() - nodesDict[key].arrived).seconds > 12:
                    print("... deleting node from my DB of nodes ...")
                    del newNodesDict[key]
            nodesDict = newNodesDict
            self.nodesDictMutex.release()
            # self.recieveMessagesThread.updateNodes(nodesDict)
            time.sleep(3)
            pass

class RecieveCommandsFromRPC(threading.Thread):
    def __init__(self, sock, instanceInfo, nodesDictMutex):
        global peersDict
        global nodesDict
        threading.Thread.__init__(self)
        self.sock = sock
        self.instanceInfo = instanceInfo
        self.nodesDictMutex = nodesDictMutex
        # self.peersDict = peersDict
        # self.nodesDict = nodesDict
        if os.path.exists("/tmp/pds_rpc_node_socket" + str(self.instanceInfo["PEER_ID"])):
            os.remove("/tmp/pds_rpc_node_socket" + str(self.instanceInfo["PEER_ID"]))
        self.rpcSocket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.rpcSocket.bind("/tmp/pds_rpc_node_socket" + str(self.instanceInfo["PEER_ID"]))
        pass
    def run(self):
        global nodesDict
        global peersDict
        if os.path.exists("/tmp/pds_rpc_node_socket" + str(self.instanceInfo["PEER_ID"])):
            while True:
                rpcCommand = self.rpcSocket.recv(4096)
                recievedCommand = rpcCommand.decode("utf-8")
                recievedCommandDict = json.loads(recievedCommand)

                if recievedCommandDict["command"] == "database":
                    # print("command 'database' has been recieved...")
                    for key, peer in peersDict.items():
                        print(peer.username + "\t\t\t is registered to", peer.regNodeIp + ":" + str(peer.regNodePort))
                    pass
                if recievedCommandDict["command"] == "neighbors":
                    # print("command 'neighbors' has been recieved...")
                    noNeighbors = True
                    toBeIterated = copy.copy(nodesDict)
                    if len(toBeIterated) != 0:
                        for k,node in toBeIterated.items():
                            if node.connectionEstablished:
                                noNeighbors = False
                                print(node.ip + ":" + str(node.port))
                    
                    if noNeighbors:
                        print("I have no neighbors")
                    pass
                if recievedCommandDict["command"] == "connect":
                    print("command 'connect' has been recieved...")
                    print(recievedCommand)
                    nodeIp = recievedCommandDict["reg_ipv4"]
                    nodePort = recievedCommandDict["reg_port"]
                    newNodeEntry = NodesDBRecord(nodeIp, nodePort, False)
                    if not newNodeEntry.nodeHash in nodesDict:
                        self.nodesDictMutex.acquire()
                        nodesDict[newNodeEntry.nodeHash] = newNodeEntry
                        self.nodesDictMutex.release()
                    pass
                if recievedCommandDict["command"] == "disconnect":
                    print("command 'disconnect' has been recieved...")
                    pass
                if recievedCommandDict["command"] == "sync":
                    print("command 'sync' has been recieved...")
                    pass                                        
        pass


class NodesDBRecord(object):
    def __init__(self, nodeIp, nodePort, connectionEstablished):
        self.ip = nodeIp
        self.port = int(nodePort)
        self.nodeHash = hash(self.ip + str(self.port))
        self.arrived = datetime.now()
        self.connectionEstablished = connectionEstablished
    # def findInDict(keyHash, toBeSearched):
    #     for key, entry in toBeSearched.items():
    #         if key == keyHash:
    #             return entry
    #         return None

class PeersDBRecord(object):
    def __init__(self, ipv4, port, username, regNodeIp, regNodePort, authoritative):
        self.ipv4 = ipv4
        self.port = port
        self.username = username
        self.regNodeIp = regNodeIp
        self.regNodePort = regNodePort
        self.authoritative = authoritative
        self.arrived = datetime.now()

def getPeersByNode(peersDatabase, regNodeIp, regNodePort):
    toBeReturned = dict()
    for key, peer in peersDatabase.items():
        if peer.regNodeIp == regNodeIp and peer.regNodePort == regNodePort:
            toBeReturned[key] = peersDatabase[key]
    return toBeReturned


# --id <identifikátor> --reg-ipv4 <IP> --reg-port <port>
parser = argparse.ArgumentParser()
parser.add_argument("--id", help="increase output verbosity", required=True, type=str)
parser.add_argument("--reg-ipv4", help="your ipv4 address", required=True, type=str)
parser.add_argument("--reg-port", help="your port", required=True, type=int)
args = parser.parse_args()


UDP_IP   = args.reg_ipv4
UDP_PORT = args.reg_port
PEER_ID = args.id
DEBUG_MODE = True
instanceInfo = dict()
instanceInfo["UDP_IP"] = args.reg_ipv4
instanceInfo["UDP_PORT"] = args.reg_port
instanceInfo["PEER_ID"] = args.id


peersDict = dict()
nodesDict = dict()
helloQueue = queue.Queue()

dictMutex = threading.Lock()
nodesDictMutex = threading.Lock()

if DEBUG_MODE:
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("~~~~~~~~~~I AM REGISTRATION NODE~~~~~~~~~~~~~~~")
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("My IP: ", UDP_IP)
    print("My PORT: ", UDP_PORT)
    print("My ID: ", PEER_ID)
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))


recieveMessagesThread = RecieveMessagesThread(sock, instanceInfo, helloQueue, dictMutex, nodesDictMutex)
maintainPeersDatabaseThread = MaintainPeersDatabaseThread(sock, instanceInfo, helloQueue, dictMutex, nodesDictMutex)

recieveMessagesThread.setMaintainPeersDatabaseThread(maintainPeersDatabaseThread)
maintainPeersDatabaseThread.setRecieveMessagesThread(recieveMessagesThread)

recieveRPCCommands = RecieveCommandsFromRPC(sock, instanceInfo, nodesDictMutex)
recieveRPCCommands.start()

maintainNodesDatabaseThread = MaintainNodesDatabaseThread(nodesDictMutex, recieveMessagesThread)
maintainNodesDatabaseThread.start()

recieveMessagesThread.start()
maintainPeersDatabaseThread.start()
