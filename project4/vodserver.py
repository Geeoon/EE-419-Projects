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
        self.root = "./contents"
        self.max_content = 5000000
        self.contents = self.load_contents(self.root)  # this is the only part it should be set
        # listen to the http socket
        self.listen()

    def load_contents(self, dir):
        #Create a list of files and stuff that you have
        out = {}
        for path, subdirs, files in os.walk(dir):
            for name in files:
                full = os.path.join(path, name)
                with open(full, "rb") as f:
                    contents = f.read()
                    out[full] = {
                        "protected": full.startswith(f"{self.root}/confidential/"),
                        "contents": contents,
                        "length": len(contents),
                        "last_modified": self.convert_to_gmt(os.path.getmtime(full))
                    }
        return out

    def convert_to_gmt(self, timestamp):
        return datetime.datetime.fromtimestamp(
                    timestamp,
                    tz=datetime.timezone.utc
                ).strftime("%a, %d %b %Y %H:%M:%S GMT")

    def listen(self):
        while self.remain_threads:
            connection_socket, client_address = self.http_socket.accept()
            # start thread for each connection
            threading.Thread(target=self.response_thread, args=(connection_socket,)).start()
        return
    
    def response(self, msg):
        if not msg:
            return None, False
        # Do based on the situation if the files exist, do not exist or are unable to respond due to confidentiality
        lines = msg.split(b'\r\n')
        # decode the METHOD, PATH, and VERSION.  NOTE: method and version can be ignored for this project
        _, path, _ = lines[0].decode().split(' ')
        full_path = f"{self.root}{path}"
        # check if file exists
        close, range = self.parse_headers(lines[1:-2])

        if full_path not in self.contents:
            return self.generate_response_404("1.1"), close
        # determine if protected
        if self.contents[full_path]["protected"]:
            return self.generate_response_403("1.1"), close

        # determine if too large
        if self.contents[full_path]["length"] > self.max_content:  # if larger than 5MB
            return self.generate_response_206("1.1", self.contents[full_path]["contents"], self.contents[full_path]["length"], full_path.split('.')[-1], self.contents[full_path]["last_modified"], range), close
        # send normal file
        return self.generate_response_200("1.1", self.contents[full_path]["contents"], self.contents[full_path]["length"], full_path.split('.')[-1], self.contents[full_path]["last_modified"]), close

    def response_thread(self, connection_socket):
        close = False
        while not close:
            try:
                msg = connection_socket.recv(BUFSIZE)  # keep in bytes format
                res, close = self.response(msg)
                if res:
                    connection_socket.sendall(res)
                pass
            except ConnectionResetError:
                pass

    def parse_headers(self, headers):
        close = False
        range = None
        for header in headers:
            key, value = header.split(b': ')
            if key == b'Connection':
                if value == b'close':
                    close = True
            elif key == b'Range':
                start = None
                end = None
                value = value[6:]  # cut off "bytes="
                # NOTE: we don't support multiple ranges
                s_val, e_val = value.split(b'-')
                if s_val:
                    start = int(s_val.decode())
                if e_val:
                    end = int(e_val.decode())
                range = (start, end)
        return close, range
    
    def generate_headers(self, content_len=None, content_range=None, total_size=None, content_type=None, last_modified=None):
        headers =   (
                        b"Accept-Ranges: bytes\r\n"
                        b"Connection: keep-alive\r\n"
                    )
        headers += f"Date: {self.convert_to_gmt(datetime.datetime.now().timestamp())}\r\n".encode('ascii')
        if content_len is not None:
            headers += f"Content-Length: {content_len}\r\n".encode('ascii')
        if content_range is not None and total_size is not None:
            headers += f"Content-Range: bytes {content_range[0] if (content_range[0] is not None) else ''}-{content_range[1] if (content_range[1] is not None) else ''}/{total_size}\r\n".encode('ascii')
        if content_type is not None:
            headers += f"Content-Type: {content_type}\r\n".encode('ascii')
        if last_modified is not None:
            headers += f"Last-Modified: {last_modified}\r\n".encode('ascii')
        
        headers += b'\r\n'  # indicate end of headers
        return headers
    
    def _convert_to_mime(self, extention):
        if extention == "txt":
            return "text/plain"
        elif extention == "css":
            return "text/css"
        elif extention == "htm" or extention == "html":
            return "text/html"
        elif extention == "gif":
            return "image/gif"
        elif extention == "jpg" or extention == "jpeg":
            return "image/jpeg"
        elif extention == "png":
            return "image/png"
        elif extention == "mp4":
            return "video/mp4"
        elif extention == "webm" or extention == "ogg":
            return "video/webm"
        elif extention == "js":
            return "application/javascript"
        else:
            return "application/octet-stream"
    
    def generate_response_404(self, http_version):
        #Generate Response and Send
        res = f'HTTP/{http_version} 404 Not Found\r\n'.encode('ascii')
        res += self.generate_headers()
        return res

    def generate_response_403(self, http_version):
        #Generate Response and Send
        res = f'HTTP/{http_version} 403 Forbidden\r\n'.encode('ascii')
        res += self.generate_headers()
        return res
    
    def generate_response_200(self, http_version, contents, length, file_type, modified):
        #Generate Response and Send
        res = f'HTTP/{http_version} 200 OK\r\n'.encode('ascii')
        res += self.generate_headers(content_len=length, content_type=self._convert_to_mime(file_type), last_modified=modified)
        res += contents
        return res

    def generate_response_206(self, http_version, contents, length, file_type, modified, range):
        #Generate Response and Send
        res = f'HTTP/{http_version} 206 Partial Content\r\n'.encode('ascii')
        start = 0
        end = self.max_content - 1
        if range is not None:
            start = 0 if (range[0] is None) else range[0]
            end = min(start + self.max_content - 1, length - 1) if (range[1] is None) else range[1]
        end = min(end, length - 1)  # prevent going over
        body = contents[start:end+1]
        
        res += self.generate_headers(content_len=len(body), content_type=self._convert_to_mime(file_type), last_modified=modified, total_size=length, content_range=(start, end))
        res += body        
        return res

if __name__ == "__main__":
    Vod_Server(int(sys.argv[1]))
