#!/usr/bin/env python3

import socket
import threading
import time
import json
import random
import bencode
import os

if os.path.exists("/tmp/pds_rpc_peer_socket951627843"):
    peer = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    peer.connect("/tmp/pds_rpc_peer_socket951627843")
    peer.send("pod do toho".encode("utf-8"))

    




# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# sock.bind(("127.0.0.1", 25010))
# while True:
#     data, addr = sock.recvfrom(4096)
#     print(data.decode("utf-8"))
