import json
import bencode
import abc

#TODO: implementuj vsade bencode metodu

class Command(metaclass=abc.ABCMeta):
	def __init__(self, cmdType, commandBody):
		try:
			self.type = cmdType
			self.commandDict = bencode.decode(commandBody)
			self.txid = self.commandDict['txid']
			pass
		except:
			# Neslo mi to rozdekodovat...
			self.ready = False
		else:
			self.ready = True
		
	def fromBencode(self, commandBody):
		self.commandDict = bencode.decode(commandBody)
		self.type = self.commandDict['type']
		self.txid = self.commandDict['txid']
		return self
	def fromObject(self, obj):
		self.type = obj['type']
		self.txid = obj['txid']
		return self
	def bencode(self):
		""" Bencode message """
		return ""
	def send(self, sckt, dstIp, dstPort):
		toBeSent = self.bencode()
		# ak tu nema byt to encode("utf-8"), tak to presetri, lebo
		# pri posielani ack to tu bolo treba
		sckt.sendto(bytes(toBeSent), (dstIp, dstPort))
	def sendAck(self, sckt, dstIp, dstPort):
		ack = AckCommand(("d4:txidi" + str(self.txid) + "e4:type3:acke").encode("utf-8"))
		ack.send(sckt, dstIp, dstPort)
	@staticmethod
	def msgType(bencodedMessage):
		msgDict = bencode.decode(bencodedMessage)
		return msgDict['type']
		

class HelloCommand(Command):
	"""docstring for HelloCommand"""
	def __init__(self, commandBody):
		super(HelloCommand, self).__init__("hello", commandBody)
		self.username = self.commandDict['username']
		self.ipv4 = self.commandDict['ipv4']
		self.port = self.commandDict['port']

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
		self.verbose = self.commandDict['verbose']

class ListCommand(Command):
	def __init__(self, commandBody):
		super(ListCommand, self).__init__("list", commandBody)
		self.peers = self.commandDict['peers']
	def bencode(self):
	 return bencode.bencode({"type":self.type, "txid":self.txid, "peers": self.peers})

class MessageCommand(Command):
	def __init__(self, commandBody):
		super(MessageCommand, self).__init__("message", commandBody)
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

