# adapted from https://github.com/uscresl/piksi_ros/blob/master/src/piksi_driver.py


from socket import *
from sbp.client.drivers.base_driver import BaseDriver
from sbp.client import Handler, Framer
from collections import deque
import threading

# Driver class for handling UDP connections for SBP
class UDPDriver(BaseDriver):
    def __init__(self, host, port):
        self.buf = deque()
        self.handle = socket(AF_INET, SOCK_DGRAM)
        self.handle.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        try:
            #self.handle.connect((host, port))
            self.handle.bind(("", port))
        except socket.error, msg:
            pass
        super(UDPDriver, self).__init__(self.handle)
        self._write_lock = threading.Lock()

    def read(self, size):
        if len(self.buf) < size:
            try:
                data, addr = self.handle.recvfrom(4096)
                if not data:
                    raise IOError
                for d in data:
                    self.buf.append(d)
            except socket.error, msg:
                raise IOError

        res = ''.join([self.buf.popleft() for i in xrange(min(size, len(self.buf)))])
        return res

    def flush(self):
        pass

    def write(self, s):
        return
        """
        Write wrapper.
        Parameters
        ----------
        s : bytes
        Bytes to write
        """
        try:
            self._write_lock.acquire()
            self.handle.sendall(s)
        except socket.error, msg:
            raise IOError
        finally:
            self._write_lock.release()



class UdpMulticaster:

    def __init__(self):
        self.multicast_address = "10.10.50.255"
        self.port = 12345
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

    def sendPacket(self, data):
        self.socket.sendto(data, (self.multicast_address, self.port))



class SbpUdpMulticaster(UdpMulticaster):
    def __init__(self):
        UdpMulticaster.__init__(self)

    def sendSbpPacket(self, sbp_data):
        self.sendPacket(sbp_data.pack())


class SbpUdpMulticastReceiver:
    def __init__(self, ext_callback):
        self._callback = ext_callback
        self.driver = UDPDriver(' ', 12345)
        self.framer = Framer(self.driver.read, None, verbose=False)
        self.piksi = Handler(self.framer)
        self.piksi.add_callback(self.recv_callback)
        self.piksi.start()

    def recv_callback(self, msg, **metadata):
        self._callback(msg, **metadata)