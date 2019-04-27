import json
import bencode
import abc
import random

#TODO: implementuj vsade bencode metodu

class Command(metaclass=abc.ABCMeta):
	def __init__(self, cmdType, commandBody):
		try:
			self.type = cmdType
			self.commandDict = bencode.decode(commandBody)
			self.txid = self.commandDict['txid']
			pass
		except:
			self.ready = False
		else:
			self.ready = True
		
	def fromBencode(self, commandBody):
		self.commandDict = bencode.decode(commandBody)
		self.type = self.commandDict['type']
		self.txid = self.commandDict['txid']
		return self
	def fromObject(self, obj):
		self.commandDict = bencode.decode(bencode.encode(obj))
		self.type = obj['type']
		self.txid = obj['txid']
		return self
	def bencode(self):
		""" Bencode message """
		return ""
	def send(self, sckt, dstIp, dstPort):
		toBeSent = self.bencode()
		sckt.sendto(bytes(toBeSent), (dstIp, dstPort))
	def sendAck(self, sckt, dstIp, dstPort):
		ack = AckCommand(("d4:txidi" + str(self.txid) + "e4:type3:acke").encode("utf-8"))
		ack.send(sckt, dstIp, dstPort)
	def sendError(self, sckt, dstIp, dstPort, errMessage):
		err = ErrorCommand({
			"txid":self.txid,
			"type":"error",
			"verbose":errMessage
			})
		err.send(sckt, dstIp, dstPort)
		print(err.verbose)
	@staticmethod
	def msgType(bencodedMessage):
		msgDict = bencode.decode(bencodedMessage)
		return msgDict['type']
	@staticmethod
	def txidGenerate():
		return random.randrange(0,65535)
	
		

class HelloCommand(Command):
	"""docstring for HelloCommand"""
	def __init__(self, commandBody):
		super(HelloCommand, self).__init__("hello", commandBody)
		if not self.ready:
			self.fromObject(commandBody)
		self.username = self.commandDict['username']
		self.ipv4 = self.commandDict['ipv4']
		self.port = self.commandDict['port']
	def bencode(self):
		return bencode.bencode({
			"type": self.type,
			"txid": self.txid,
			"username": self.username,
			"ipv4": self.ipv4,
			"port": self.port
			})

class GetListCommand(Command):
	def __init__(self, commandBody):
		super(GetListCommand, self).__init__("getlist", commandBody)
	def bencode(self):
		return bencode.bencode({"type": self.type, "txid": self.txid})

class DisconnectCommand(Command):
	def __init__(self, commandBody):
		super(DisconnectCommand, self).__init__("disconnect", commandBody)

class AckCommand(Command):
	def __init__(self, commandBody):
		super(AckCommand, self).__init__("ack", commandBody)
	def bencode(self):
	 return bencode.bencode({"type": self.type, "txid": self.txid})

class ErrorCommand(Command):
	def __init__(self, commandBody):
		super(ErrorCommand, self).__init__("error", commandBody)
		if not self.ready:
			self.fromObject(commandBody)
		self.verbose = self.commandDict['verbose']
	def bencode(self):
		return bencode.bencode({"type":self.type, "txid":self.txid, "verbose": self.verbose})

class ListCommand(Command):
	def __init__(self, commandBody):
		super(ListCommand, self).__init__("list", commandBody)
		if not self.ready:
			self.fromObject(commandBody)
		self.peers = self.commandDict['peers']
	def bencode(self):
		return bencode.bencode({"type":self.type, "txid":self.txid, "peers": self.peers})
	def isUserThere(self, username):
		for key in self.peers:
			if self.peers[key]["username"] == username:
				return True
		return False
	def getUserAddr(self, username):
		for key in self.peers:
			if self.peers[key]["username"] == username:
				return (self.peers[key]["ipv4"],self.peers[key]["port"])
		return (False, False)
	def printPeers(self):
		for key in self.peers:
			peerUsername = self.peers[key]["username"]
			peerPort = self.peers[key]["port"]
			peerIp = self.peers[key]["ipv4"]
			print(peerUsername, "\t\t\t", str(peerIp) + ":" + str(peerPort))


class MessageCommand(Command):
	def __init__(self, commandBody):
		super(MessageCommand, self).__init__("message", commandBody)
		if not self.ready:
			self.fromObject(commandBody)
		self.fromWho = self.commandDict['from']
		self.to = self.commandDict['to']
		self.message = self.commandDict['message']
	def bencode(self):
		return bencode.bencode({"type":self.type, "txid":self.txid, "from":self.fromWho, "to":self.to, "message":self.message})

class UpdateCommand(Command):
	def __init__(self, commandBody):
		super(UpdateCommand, self).__init__("update", commandBody)
		self.db = self.commandDict['db']
		

# someCommand = UpdateCommand('d2:dbd17:192.0.2.198,12345d1:0d4:ipv49:192.0.2.14:porti34567e8:username8:xlogin00e1:1d4:ipv49:192.0.2.24:porti45678e8:username8:xnigol99ee17:192.0.2.199,12345d1:0d4:ipv49:192.0.2.34:porti65432e8:username8:xtestx00eee4:txidi123e4:type6:updatee')
#tmp = bencode.decode(b"d4:txidi123e4:type7:getliste").decode("utf-8")
#tmp = bencode.encode('{"type":"getlist", "txid":123}')

# print(someCommand.db)

