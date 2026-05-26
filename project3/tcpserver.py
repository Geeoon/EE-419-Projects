import socket, sys
import json
import time
import threading
import struct

BUFSIZE = 10202  # size of receiving buffer
PKTSIZE = 10200  # number of bytes in a packet
WINDOW_SIZE = 16
IDX_LENGTH = 2 # 2 bytes of packet index
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

        self.remain_threads = True
        self.cli()
    
    def find_file(self, file_name):
        #A function to find the peer with the file you want!
        for peer in self.peer_info:
            if file_name in peer['content_info']
                return (peer['hostname'], peer['port'])
    
    def load_file(self, file_name):
        # find which server has the file
        server = find_file(file_name)
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

        while not connect_flag:
            try:
                # handshake
                # send SYN
                self.cl_socket.send(b'S' + file_name.encode('ascii'))
                # receive SYNACK
                received = self.cl_socket.recv(BUFSIZE)
                if received != b'B':
                    # we should receive a '2' in response
                    raise Exception(f"Did not receive proper SYNACK: {received}")
                # send ACK
                self.cl_socket.send(b'A' + struct.pack(">I", our_sequence_number))
                connect_flag = True
            except socket.timeout:
                # handshake failed
                # timeout waiting for SYNACK
                # resend the SYN, so do nothing
                pass
      
        # start receiving file
        data = b''
        while connect_flag:
            try:
                chunk = self.cl_socket.recv(BUFSIZE)
                # check the header
                if chunk[0] == ord('F'):  # check if FIN packet
                    our_sequence_number += 1
                    connect_flag = False
                    continue
                else chunk[0] != ord('D'):
                    continue  # we got junk, toss it
                chunk = chunk[1:]  # strip the header

                seq_num = struct.unpack(">I", chunk[:2])
                if seq_num == our_sequence_number:
                    # valid packet
                    # store and increment our sequence numbers
                    data += chunk[2:]
                    our_sequence_number += 1
                else:
                    # repeated or out of order packet
                    pass  # drop
            except socket.timeout:
                # socket timed out, meaning we did not receive a packet in time, resend an ACK
                pass
            finally:
                # send the ACK
                self.cl_socket.send(b'A' + struct.pack(">I", our_sequence_number))
                
        # transmission complete, close socket
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
        # create a udp socket for transmission
        tx_socket = 
        # divide the file into several parts
        #transmit_file = self.read_file(file_name)
        #packet_num = len(transmit_file)
        # use socket to send packet number to the receiver
        #ack = 0
        #print("sending packet num", packet_num, "to", addr)
        tx_socket.sendto(str(packet_num).encode(), addr)
        try:
            #Receive ACK from the same tx_socket and increment window
            pass
        except socket.timeout:
            pass
        # use a transmit window to determine which file should be transmitted

        # use a time-out array to record which file is time-out and need to be transmitted again
        # -1 indicates received, 0 indicates not transmitted, positive numbers means the time of transmission
        
        def transmit_thread():
            #Takes the transmit window and transmits every packet that is allowed to be transmitted
            return
        
        def ack_thread():
            #Receives acknowledgement and updates the transmit window with sendable packets
            pass
        
        #Create TX and RX threads and start doing it

        #When done transmitting, close the threads.

    def listener(self): # listen to the socket to see if there's any transmission request
        #Do any initializations that you want
        while self.remain_threads:
            file_name = ""
            try:
                file_name, addr = self.server_socket.recvfrom(BUFSIZE)
                #Receive the file name and requesting address from the UDP
            except socket.timeout:
                pass
            
            if file_name == "":
                pass
            else:   # start transmission
                pass#Create a transmit thread (HINT : you can have a large array of transmit threads if you want) and start it
                
        return
    
    def cli(self):  # cli interface for input of the file name
        listen_thread = threading.Thread(target=self.listener)
        listen_thread.start()

        while self.remain_threads:
            command_line = input()
            if command_line == "kill":  # for debugging purpose
                #Do the kill stuff
                return
            #Otherwise it is a file name!
        #Exit stuff if you have some?
        return


if __name__ == "__main__":
    server = Server(sys.argv[1])