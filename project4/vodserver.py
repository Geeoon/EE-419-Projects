import socket, sys
import datetime
import os
import threading

BUFSIZE = 1024
LARGEST_CONTENT_SIZE = 5242880

class Vod_Server():
    def __init__(self, port_id):
        # create an HTTP port to listen to
        self.http_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.http_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.http_socket.bind(("0.0.0.0", port_id))
        self.http_socket.listen(10000)
        self.remain_threads = True

        # load all contents in the buffer
        self.contents = self.load_contents("./contents")  # this is the only part it should be set
        print(self.contents)
        # listen to the http socket
        self.listen()

    def load_contents(self, dir):
        #Create a list of files and stuff that you have
        out = {}
        for path, subdirs, files in os.walk(dir):
            for name in files:
                full = os.path.join(path, name)
                with open(full, "rb") as f:
                    out[full] = {
                        "protected": full.startswith("./contents/confidential/"),
                        "contents": f.read()
                    }
        return out

    def listen(self):
        while self.remain_threads:
            connection_socket, client_address = self.http_socket.accept()
            # start thread
            threading.Thread(target=self.response, args=(connection_socket,)).start()
            # Do stuff here
        return
    
    def response(self, connection_socket):
        # Do based on the situation if the files exist, do not exist or are unable to respond due to confidentiality
        msg = connection_socket.recv(BUFSIZE).decode()
        lines = msg.split(b'\r\n')
        # decode the METHOD, PATH, and VERSION.  NOTE: method and version can be ignored for this project
        _, path, _ = lines[0].split(b' ')
        # parse headers

    def parse_headers(self, headers):
        pass
    
    def generate_response_404(self, http_version, connection_socket):
        #Generate Response and Send
        
        return response

    def generate_response_403(self, http_version, connection_socket):
        #Generate Response and Send
        
        return response
    
    def generate_response_200(self, http_version, file_idx, file_type, connection_socket):
        #Generate Response and Send
        
        return response

    def generate_response_206(self, http_version, file_idx, file_type, command_parameters, connection_socket):
        #Generate Response and Send
        
        return response

    def generate_content_type(self, file_type):
        #Generate Headers
        return ""

if __name__ == "__main__":
    Vod_Server(int(sys.argv[1]))
