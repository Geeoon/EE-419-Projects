import socket, sys
import ast
import threading, time
import random
from uuid import UUID, uuid4
import json

BUFSIZE = 1024  # size of receiving buffer
ALIVE_SGN_INTERVAL = 0.5  # interval to send alive signal
TIMEOUT_INTERVAL = 10*ALIVE_SGN_INTERVAL
UPSTREAM_PORT_NUMBER = 1111 # socket number for UL transmission

##
#
# FOR TRANSMITTING PACKET USE THE FOLLOWING CODE
#
#self.ul_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#try:
#   self.ul_socket.connect((host, backend_port))
#   self.ul_socket.send(("STRING TO SEND").encode())
#   self.ul_socket.close()
#except socket.error:
#   pass
#
#
#
#

class Content_server():
    def __init__(self, conf_file_addr):
        self.peers = {}
        self.peers_lock = threading.Lock()
        self.remain_threads = True
        self.uuid = None
        self.name = None
        self.backend_port = None
        self.peer_count = None

        # load and read configuration file
        with open(conf_file_addr, "r") as f:
            for line in f:
                line = line.strip()
                values = line.split(" ")
                if values[0] == "uuid":
                    self.uuid = values[-1]
                elif values[0] == "name":
                    self.name = values[-1]
                elif values[0] == "backend_port":
                    self.backend_port = int(values[-1])
                elif values[0] == "peer_count":
                    self.peer_count = int(values[-1])
                elif "peer_" in values[0]:
                    # spec states only that it will be seperated by commas, not commas and spaces, so we need to do some weird stuff
                    peer_vals = line.split("=")[-1].strip().split(",")
                    metric = int(peer_vals[-1].strip())  # guaranteed to be last
                    for val in peer_vals[:-1]:
                        stripped = val.strip()
                        if stripped.isdecimal():
                            port = int(stripped)
                        else:
                            # check if UUID
                            try:
                                temp = UUID(stripped)
                                if not str(temp) == val: raise Exception()
                                uuid = stripped
                            except:
                                # not a UUID
                                hostname = stripped
                    self.addneighbor(uuid, hostname, port, metric)
                else:
                    raise Exception("Unknown configuration:", values[0])
        # create the receive socket
        self.dl_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.dl_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # TODO: ask about the listen address, no example included
        self.dl_socket.bind(("0.0.0.0", self.backend_port))
        self.dl_socket.listen(100)

        # generate uuid if it doesn't exist
        if not self.uuid:
            self.uuid = uuid4()

        # Initialize link state advertisement that repeats using a neighbor variable
        self.link_state_adv()
        self.alive()
    
    def addneighbor(self, uuid, host, backend_port, metric):
        with self.peers_lock:
            self.peers[uuid] = {
                "name": None,  # will be filled in from the keepAlive messages
                "host": host,
                "port": backend_port,
                "metric": metric
            }
    
    def link_state_adv(self):
        # Perform Link State Advertisement to all your neighbors periodically 
        pass

    
    def link_state_flood(self, send_time, host, msg):
        # If new information then send to all your neighbors, if old information then drop.
        pass
    
    def dead_adv(self, peer):
        # Advertise death before kill
        pass
    
    def dead_flood(self, send_time, host, peer):
        # Forward the death message information to other peers
        pass

    def keep_alive(self):
        # Tell that you are alive to all your neighbors, periodically.
        while self.remain_threads:
            pass
    
   
   ## THIS IS THE RECEIVE FUNCTION THAT IS RECEIVING THE PACKETS
    def listen(self):
        self.dl_socket.settimeout(0.1)  # for killing the application
        while self.remain_threads:
            try:
                connection_socket, client_address = self.dl_socket.accept()
                msg_string = connection_socket.recv(BUFSIZE).decode()
                # print("received", connection_socket, client_address, msg_string)
            except socket.timeout:
                msg_string = ""

            if msg_string == "":    # empty message
                pass
            elif msg_string == "Alive message": # Update the timeout time if known node, otherwise add new neighbor
                pass
            elif msg_string == "Link State Packet":     # Update the map based on new information, drop if old information
                #If new information, also flood to other neighbors
                pass
            elif msg_string == "Death message": # Delete the node if it sends the message before executing kill.
                pass
            # otherwise the msg is dropped

    def timeout_old(self):
        # drop the neighbors whose information is old
        while self.remain_threads:
            pass

    def shortest_path(self):
        # derive the shortest path according to the current link state
        rank = {}
        return rank

    
    def alive(self):
        keep_alive = threading.Thread(target=self.keep_alive) # A thread that keeps sending keep_alive messages
        listen = threading.Thread(target=self.listen) # A thread that keeps listening to incoming packets
        timeout_old = threading.Thread(target=self.timeout_old) # A thread to eliminate old neighbors
        link_state_adv = threading.Thread(target=self.link_state_adv) # A thread that keeps doing link_state_adv
        keep_alive.start()
        listen.start()
        timeout_old.start()
        link_state_adv.start()
        while self.remain_threads:
            time.sleep(ALIVE_SGN_INTERVAL)  # wait for the network to settle
            command_line = input().split(" ")
            command = command_line[0]
            # print("Received command: ", command)
            if command == "kill":
                # Send death message
                # Kill all threads
                pass
            elif command == "uuid":
                print(json.dumps({"uuid":self.uuid}))
            elif command == "neighbors":
                # Print Neighbor information
                pass
            elif command == "addneighbor":
                # Update Neighbor List with new neighbor
                pass
            elif command == "map":
                # Print Map
                pass
            elif command == "rank": 
                # Compute and print the rank
                pass

if __name__ == "__main__":
    content_sever = Content_server(sys.argv[2])
