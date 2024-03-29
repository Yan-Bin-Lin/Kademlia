#-*- coding: UTF-8 -*-
'''
Created on 2019年9月1日

@author: danny
'''
import socket
import threading
import sys
import traceback

from ..util.web import GetLocalIP
from ..handler.handler import RespondHandle

from ..util.log import log
logger = log()

from ..util.error import CheckError

# a server socket class
class Server():
    @CheckError()
    def __init__(self, ServePort=0):
        #server local IP
        self.LocalIP = GetLocalIP()#self._get_host_ip()
        # 创建一个socket套接字，该套接字还没有建立连接
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 绑定监听端口，这里必须填本机的IP192.168.27.238，localhost和127.0.0.1是本机之间的进程通信使用的
        self.server.bind((self.LocalIP, ServePort)) 
        # 开始监听，并设置最大连接数
        self.server.listen(5)
        logger.debug(f'serve at {self.GetAddress()}')
        self.KadeNode = None

    @CheckError()
    def start(self):
        #start serving
        threading._start_new_thread(self.WaitConnect, ())                     
        
        
    # get the sever socket bindind address    
    @CheckError()
    def GetAddress(self):
        return self.server.getsockname()

    @CheckError()
    def CallHandle(self, connect, data, KadeNode):
        '''call handler'''
        RespondHandle(connect, data, KadeNode)
        
    @CheckError()
    def communicate(self, connect, host, port):
        while True:
            try:
                # block to wait for receive
                #connect.setblocking(1)
                # 接受客户端的数据
                data = connect.recv(10240)
                if data != b'':
                    # 由main handle決定處理方法
                    self.CallHandle(connect, data, self.KadeNode)
            except Exception as e:
                raise
                return
                
    @CheckError()     
    def WaitConnect(self):
        while True:
            logger.debug(u'waiting for connect...')
            # 等待连接，一旦有客户端连接后，返回一个建立了连接后的套接字和连接的客户端的IP和端口元组
            connect, (host, port) = self.server.accept()
            logger.debug(u'the client %s:%s has connected.' % (host, port))
            threading._start_new_thread(self.communicate, (connect, host, port))        