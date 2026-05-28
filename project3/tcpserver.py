import socket, sys
import json
import time
import threading
import struct
import subprocess

BUFSIZE = 10202  # size of receiving buffer
PKTSIZE = 10200  # number of bytes in a packet
WINDOW_SIZE = 16
IDX_LENGTH = 2 # 2 bytes of packet index.  Not used
TIMEOUT = 0.5   # timeout time

class Server():
    def __init__(self, config_file):
        #Read the config file and initialize the port, peer_num, peer_info, content_info from the config file

        # read the config file supplied
        with open(config_file, "r") as file:
            configs = json.load(file)
        self.hostname = configs['hostname']
        self.port = configs['port']
        self.content = configs['content_info']
        self.peers = configs['peer_info']

        # establish a socket according to the information
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #NOTE THAT THE SOCK_DGRAM will ensure your socket is UDP
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # allow connections from all
        self.server_socket.bind(("0.0.0.0", self.port)) # This is the only port you can use to receive
        self.server_socket.settimeout(TIMEOUT)   # timeout value

        self._incoming_packets = {}
        self._incoming_lock = threading.Lock()

        self.remain_threads = True
        self.cli()

    def _recv_addr(self, addr):
        start = time.time()
        while self.remain_threads:
            with self._incoming_lock:
                if (addr in self._incoming_packets) and len(self._incoming_packets[addr]):
                    return self._incoming_packets[addr].pop(0)
            time.sleep(.01)  # to spamming
            if (time.time() - start) > TIMEOUT:
                raise socket.timeout

    
    def find_file(self, file_name):
        #A function to find the peer with the file you want!
        for peer in self.peers:
            if file_name in peer['content_info']:
                return (peer['hostname'], peer['port'])
    
    def load_file(self, file_name):
        # find which server has the file
        server = self.find_file(file_name)
        if not server:
            raise Exception("Could not find the server which has the requested file.")
        # establish a client socket for downloading file
        self.cl_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
        self.cl_socket.settimeout(TIMEOUT)
        # connect socket to server
        self.cl_socket.connect(server)
        # use a connect flag to determine if the file name is sent correctly
        connect_flag = False

        #Initiate three-way handshake and use a connect flag
        our_sequence_number = 0
        final_sequence_number = -1

        while not connect_flag:
            try:
                # handshake
                # send SYN
                self.cl_socket.send(b'S' + file_name.encode('ascii'))
                # receive SYNACK
                received = self.cl_socket.recv(BUFSIZE)
                if received[0] != ord('B'):
                    # we should receive a 'B' (SYNACK) in response
                    raise Exception(f"Did not receive proper SYNACK: {received}")
                # strip the header
                received = received[1:]
                # serialize the final sequence number
                final_sequence_number = struct.unpack(">I", received)[0]
                print(f"Final sequence number is {final_sequence_number}")
                # send ACK
                our_sequence_number += 1
                self.cl_socket.send(b'A' + struct.pack(">I", our_sequence_number))
                connect_flag = True
            except socket.timeout:
                # handshake failed
                # timeout waiting for SYNACK
                # resend the SYN, so do nothing
                # print("Timed out waiting for the SYNACK")
                pass
      
        # start receiving file
        data = b''
        while connect_flag:
            try:
                chunk = self.cl_socket.recv(BUFSIZE)
                if chunk[0] != ord('D'):
                    # print(f"Improper DATA packet: {chunk}")  # we got junk, toss it
                    continue
                seq_num = struct.unpack(">I", chunk[1:5])[0]
                chunk = chunk[5:]  # strip the header
                print(f"Got the following sequence number: {seq_num}")
                if seq_num == our_sequence_number:
                    print("Valid packet")
                    # valid packet
                    # store and increment our sequence numbers
                    data += chunk
                    our_sequence_number += 1
                    connect_flag = our_sequence_number != final_sequence_number + 1
                else:
                    print("Invalid packet, dropped")
                    # repeated or out of order packet
                    pass  # drop
            except socket.timeout:
                # socket timed out, meaning we did not receive a packet in time, resend an ACK
                pass
            finally:
                # send the ACK
                print(f"Sending ACK with seq num: {our_sequence_number}")
                self.cl_socket.send(b'A' + struct.pack(">I", our_sequence_number))
                
        # transmission complete, wait a little bit in-case our last ACK was dropped
        for _ in range(3):
            try:
                chunk = self.cl_socket.recv(BUFSIZE)
                self.cl_socket.send(b'A' + struct.pack(">I", our_sequence_number))
            except socket.timeout:
                pass
                
        self.cl_socket.close()

        # write the file
        with open(file_name, "wb") as file:
            file.write(data)
        
    def read_file(self, file_name):
        #You can write a function that takes the file to be transmitted and converts into chunks of packet_size
        transmit_file = []
        with open(file_name, "rb") as file:
            while not file.closed:
                chunk = file.read(PKTSIZE)
                if not chunk:
                    break
                transmit_file.append(chunk)
        return transmit_file

    def transmit(self, file_name, addr):
        # divide the file into several parts
        transmit_file = self.read_file(file_name)
        final_sequence_number = len(transmit_file)
        # finish handshake
        # send SYNACK
        self.server_socket.sendto(b'B' + struct.pack(">I", final_sequence_number), addr)
        last_recv_ack = 0
        # wait for first ACK
        while last_recv_ack != 1:
            try:
                data = self._recv_addr(addr)
                # check header
                if data[0] != ord('A'):
                    raise Exception(f"Malformed ACK packet in handshake: {data}")
                # strip header
                data = data[1:]
                # get sequence number
                last_recv_ack = struct.unpack(">I", data)[0]
                if last_recv_ack != 1:
                    raise Exception(f"Did not receive the expected first ACK sequence number: {last_recv_ack}")
            except socket.timeout:
                # did not receive ACK, try sending the SYNACK again
                # print("Timed out waiting for ACK, sending another SYNACK")
                self.server_socket.sendto(b'B' + struct.pack(">I", final_sequence_number), addr)
        # handshake done, start sending DATA packets
        last_sent_seq = 1
        tries = 0
        while last_recv_ack != final_sequence_number + 1 and tries < 3:
            try:
                # send DATA packets in window
                while last_sent_seq < min(last_recv_ack + WINDOW_SIZE, final_sequence_number + 1):
                    # send DATA packet
                    self.server_socket.sendto(b'D' + struct.pack(">I", last_sent_seq) + transmit_file[last_sent_seq - 1], addr)
                    last_sent_seq += 1
                data = self._recv_addr(addr)
                tries = 0
                if data[0] != ord('A'):
                    raise Exception(f"Malformed ACK packet in DATA portion: {data}")
                # strip header
                data = data[1:]
                seq_num = struct.unpack(">I", data)[0]
                print(f"Got the following sequence number: {seq_num}")
                if seq_num > last_recv_ack:
                    print("Got normal ACK")
                    # normal behavior
                    # advance received sequence number
                    last_recv_ack = seq_num
                elif seq_num == last_recv_ack:
                    # ACK sequence number indicates issue
                    # reset window
                    print("ACK indicates issue")
                    last_recv_ack = seq_num
                    last_sent_seq = last_recv_ack
                # in the case where we get an old ACK (i.e., out of order ACKs) we can just ignore it
            except socket.timeout:
                # reset window
                last_sent_seq = last_recv_ack
                tries += 1
                print(f"Tries: {tries}")
        # remove connection
        with self._incoming_lock:
            self._incoming_packets.pop(addr, None)
        
    def listener(self): # listen to the socket to see if there's any transmission request
        while self.remain_threads:
            try:
                data, addr = self.server_socket.recvfrom(BUFSIZE)  # blocking
                # print(f"Got message: {data} from {addr}")
                if data[0] != ord('S'):
                    # add to queue, it's not a new connection
                    with self._incoming_lock:
                        if not addr in self._incoming_packets:
                            # doesn't have a connection yet, we can just ignore this source
                            # print(f"Ignoring {data} from {addr}")
                            continue
                        self._incoming_packets[addr].append(data)
                else:
                    with self._incoming_lock:
                        if addr in self._incoming_packets:
                            continue
                    # new connection, destroy previous message queue
                    with self._incoming_lock:
                        self._incoming_packets[addr] = []
                    # strip header
                    file_name = data[1:].decode('ascii')
                    # process the rest of the handshake
                    tx_thread = threading.Thread(target=lambda fn=file_name, a=addr: self.transmit(fn, a))
                    tx_thread.start()
            except socket.timeout:
                pass

    def cli(self):  # cli interface for input of the file name
        listen_thread = threading.Thread(target=self.listener)
        listen_thread.start()

        while self.remain_threads:
            command_line = input()
            if command_line == "kill":  # for debugging purpose
                # kill
                self.remain_threads = False
            else:
                self.load_file(command_line)

if __name__ == "__main__":
    server = Server(sys.argv[1])
