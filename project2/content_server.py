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


class Content_server():
    def __init__(self, conf_file_addr):
        self.peers = {}
        self.peers_lock = threading.Lock()
        self.remain_threads = True
        self.uuid = None
        self.name = None
        self.backend_port = None
        self.peer_count = None
        self.tables = {}  # stores the peers of all other devices on the network
        self.sequence_num = 0

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
        self.dl_socket.bind(("0.0.0.0", self.backend_port))
        self.dl_socket.listen(100)

        # generate uuid if it doesn't exist
        if not self.uuid:
            self.uuid = str(uuid4())

        # Initialize link state advertisement that repeats using a neighbor variable
        # self.link_state_adv()  a seperate thread will do this
        self.alive()
    
    def addneighbor(self, uuid, host, backend_port, metric):
        with self.peers_lock:
            self.peers[uuid] = {
                "name": None,  # will be filled in from the keepAlive messages
                "host": host,
                "port": backend_port,
                "metric": metric,
                "last_alive": time.time()
            }
        self.sequence_num += 1
        self.link_state_flood()
    
    def link_state_adv(self):
        # Perform Link State Advertisement to all your neighbors periodically 
        while self.remain_threads:
            self.link_state_flood()
            time.sleep(TIMEOUT_INTERVAL)  # wait

    
    def link_state_flood(self):
        # send state to all neighbors
        print("Link state flood!")
        self.flood(f"L{json.dumps({"name": self.name, "uuid": self.uuid, "port": self.backend_port, "peers": self.get_alive_peers(), "sequence": self.sequence_num})}")

    def flood(self, msg):
        # send a message to all peers
        alive_peers = self.get_alive_peers()
        for peer in alive_peers.values():
            self._send_msg(peer["host"], peer["port"], msg)

    def _send_msg(self, host, port, msg):
        t = threading.Thread(target=lambda: self._send_msg_worker(host, port, msg))
        t.start()

    def _send_msg_worker(self, host, port, msg):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT_INTERVAL)
        try:
            sock.connect((host, port))
            sock.send(msg.encode())
            sock.close()
        except Exception as e:
            pass  # host unreachable

    def keep_alive(self):
        # Tell that you are alive to all your neighbors, periodically.
        while self.remain_threads:
            data = {
                "name": self.name,
                "uuid": self.uuid,
                "port": self.backend_port,
                # "metric": 0  # NOTE: do not need to consider
            }
            # send to all peers possible, not just alive ones
            with self.peers_lock:
                for peer in self.peers.values():
                    # print(f"Sending keep alive to {peer["host"]}")
                    self._send_msg(peer["host"], peer["port"], f"A{json.dumps(data)}")
                    # print(f"Done sending keep alive to {peer["host"]}")
            time.sleep(ALIVE_SGN_INTERVAL)
    
    ## THIS IS THE RECEIVE FUNCTION THAT IS RECEIVING THE PACKETS
    def listen(self):
        self.dl_socket.settimeout(0.1)  # for killing the application
        while self.remain_threads:
            try:
                connection_socket, client_address = self.dl_socket.accept()
                msg_string = connection_socket.recv(BUFSIZE).decode()
            except socket.timeout:
                msg_string = ""

            if not msg_string or len(msg_string) < 2:  # empty message
                continue
            
            opcode = msg_string[0]
            data = json.loads(msg_string[1:])
            if opcode == "A": # Update the timeout time if known node, otherwise add new neighbor
                # receive keepAlive as JSON
                # print(f"Got a keep alive from {client_address[0]}")
                with self.peers_lock:
                    if data["uuid"] in self.peers:
                        self.peers[data["uuid"]]["name"] = data["name"]
                        self.peers[data["uuid"]]["last_alive"] = time.time()
                    else:
                        # NOTE: no need to consider this
                        continue
                        # self.peers[data["uuid"]] = {
                        #     "name": data["name"],
                        #     "host": client_address[0],
                        #     "port": data["port"],
                        #     # "metric": data["metric"],
                        #     "last_alive": time.time()
                        # }
            elif opcode == "L":     # Update the map based on new information, drop if old information
                #If new information, also flood to other neighbors
                print(f"!! Got link state message from {client_address[0]} !!")
                if data["name"] not in self.tables or data["sequence"] > self.tables[data["name"]]["sequence"]:
                    # forward
                    self.flood(msg_string)
                    self.tables[data["name"]] = {"peers": data["peers"], "sequence": data["sequence"]}
                    if self.uuid in data["peers"] and data["uuid"] not in self.peers:
                        # we're in and we need to add the new peer
                        new_metric = data["peers"][self.uuid]["metric"]
                        self.addneighbor(uuid=data["uuid"],
                                         host=client_address[0],
                                         backend_port=data["port"],
                                         metric=new_metric)
                        self.peers[data["uuid"]]["name"] = data["name"]
                        # with self.peers_lock:
                            # add to peers
                            # self.peers[data["uuid"]] = {
                            #     "name": data["name"],
                            #     "host": client_address[0],
                            #     "port": data["port"],
                            #     "metric": new_metric,
                            #     "last_alive": time.time()
                            # }
                            # "name": None,  # will be filled in from the keepAlive messages
                            # "host": host,
                            # "port": backend_port,
                            # "metric": metric,
                            # "last_alive": time.time()
                
            elif opcode == "D": # Delete the node if it sends the message before executing kill.
                print(f"Got death message from {client_address[0]}")
                # forward to all our peers, unless we have already marked the node for death
                alive_peers = self.get_alive_peers()
                if data["uuid"] not in alive_peers:
                    self.flood(msg_string)

                # kill it
                with self.peers_lock:
                    # check if it exists
                    if data["uuid"] in self.peers:
                        self.peers[data["uuid"]]["last_alive"] = 0
            # otherwise the msg is dropped

    def shortest_path(self):
        # derive the shortest path according to the current link state
        rank = {}
        return rank
    
    def get_alive_peers(self):
        out = {}
        with self.peers_lock:
            for uuid in self.peers:
                if self.peers[uuid]["last_alive"] > time.time() - TIMEOUT_INTERVAL:
                    out[uuid] = self.peers[uuid]
        return out
        
    def alive(self):
        keep_alive = threading.Thread(target=self.keep_alive) # A thread that keeps sending keep_alive messages
        listen = threading.Thread(target=self.listen) # A thread that keeps listening to incoming packets
        link_state_adv = threading.Thread(target=self.link_state_adv) # A thread that keeps doing link_state_adv
        keep_alive.start()
        listen.start()
        link_state_adv.start()
        while self.remain_threads:
            time.sleep(ALIVE_SGN_INTERVAL)  # wait for the network to settle
            command_line = input().split(" ")
            command = command_line[0]
            if command == "kill":
                # Send death message
                self.flood(f"D{json.dumps({"uuid": self.uuid})}")
                self.remain_threads = False
            elif command == "uuid":
                print(json.dumps({"uuid":self.uuid}))
            elif command == "neighbors":
                out = {
                    "neighbors": {}
                }
                alive_peers = self.get_alive_peers()
                for uuid in alive_peers:
                    if alive_peers[uuid]["name"]:
                        # only list those that have names
                        out["neighbors"][alive_peers[uuid]["name"]] = {
                            "uuid": uuid,
                            "host": alive_peers[uuid]["host"],
                            "backend_port": alive_peers[uuid]["port"],
                            "metric": alive_peers[uuid]["metric"]
                        }
                print(json.dumps(out))
                # Print Neighbor information
            elif command == "addneighbor":
                # Update Neighbor List with new neighbor
                # parse command parameters
                new_uuid = None
                new_host = None
                new_backend_port = None
                new_metric = None
                for item in command_line[1:]:
                    if len(item) < 5:
                        # invalid
                        continue
                    if item[:5] == "uuid=":
                        new_uuid = item[5:]
                    elif item[:5] == "host=":
                        new_host = item[5:]
                    elif item[:5] == "backe" and item[:13] == "backend_port=":
                        new_backend_port = item[13:]
                    elif item[:5] == "metri" and item[:7] == "metric=":
                        new_metric = item[7:]
                    else:  # invalid
                        continue
                # check arguments
                if new_uuid:
                    # check UUID
                    try:
                        temp = UUID(new_uuid)
                        if not str(temp) == new_uuid: raise Exception()
                    except:
                        # not a UUID, invalid
                        continue
                else:
                    # if there's no UUID, create one randomly
                    new_uuid = str(uuid4())
                
                # check port and metric
                if not new_backend_port.isdecimal() or not new_metric.isdecimal():
                    continue
                new_backend_port = int(new_backend_port)
                new_metric = int(new_metric)

                self.addneighbor(uuid=new_uuid,
                                 host=new_host,
                                 backend_port=new_backend_port,
                                 metric=new_metric)
            elif command == "map":
                # Print Map
                pass
            elif command == "rank": 
                # Compute and print the rank
                pass

if __name__ == "__main__":
    content_sever = Content_server(sys.argv[2])

"""
addneighbor uuid=3d2f4e34-6d21-4dda-aa78-796e3507903c host=10.1.0.3 backend_port=18346 metric=25
addneighbor uuid=3d2f4e34-6d21-4dda-aa78-796e3507903c host=10.1.0.3 backend_port=18346 metric=25
"""
