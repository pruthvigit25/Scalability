import base64
import enum
import os
import socket
import threading
import sys
import time
import asyncio
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.application import get_app
from prompt_toolkit.application import run_in_terminal
from math import ceil

Dictionary = {
              'SHORTNAME': 'tiliu3', #send your device name
              'NO_USER': 'This connection is not found. Please check the route table.',
              'USER_EXISTED': 'User has existed on socket.',
              'BROADCAST': 'BROADCAST',
              'GROUP': 'GROUP17',
             }

IP_table = {
    
}

class SendType():
    #The values of these variables must be as same as the end of private function
    CHAT = 'CHAT'
    INTEREST = 'INTEREST'
    DATA = 'DATA'

    def __init__(self, shortname):
        self.__shortname = shortname

    def __sendCHAT(self, param):
        package = {
            1: True,
            2: f"CHAT://{self.__shortname}:{param}",
        }
        return package

    def __sendINTEREST(self, param):
        package = {
            1: True,
            2: f"INTEREST://{param}",
        }
        return package

    def __sendDATA(self, param):
        package = {
            1: True,
            2: f"DATA://{param}",
        }
        return package

    def __Default(self, param):
        package = {
            1: False,
            2: f"Can't send this type of packag: {param}",
        }
        return package

    def send_(self, type_, param):
        sendtype = "_SendType__send" + type_
        fun = getattr(self, sendtype, self.__Default)
        return fun(param)

class Command():
    OPEN_NET = 'open-net'
    HELP = 'help'
    SHOW_MSG = 'show-msg'
    SHUT_SHOW_MSG = 'shut-show-msg'
    SEND_TO = 'send'
    CONNECT = 'connect'
    SEARCH_CONN = 'search-conn'

    @staticmethod
    def not_found(input):
        print(f'Command "{input}" not found.')

    @staticmethod
    def send_success(target_name, text):
        print(f'You have sent to {target_name} - {text}')

    @staticmethod
    def send_failed(target_name, text):
        print(f'There has something wrong to send to {target_name} - {text}')
    
    @staticmethod
    def connect_failed(target_name):
        print(f'There has something wrong to connect to {target_name}.')

class _Prompt():
    __cli_header = f'ndn-cli:{Dictionary["SHORTNAME"]}'
    @staticmethod
    def begining():
        return _Prompt.__cli_header + ' >'
    
    @staticmethod
    def running_bind():
        return _Prompt.__cli_header + '-running >'

class Demo():

    def __init__(self):
        self.__host = self.__get_host_ip()
        self.__host_broadcast = None
        self.__shortname = Dictionary['SHORTNAME']
        self.__group = Dictionary['GROUP']
        self.__port_LAN = 33000
        self.__port_WAN = 33001
        self.__port_BROADCAST = 33002
        self.__recv_size = 2048#1024/2048/3072
        self.__isWAN_occupied = False
        self.__Sem_conn_change = threading.Semaphore(1)
        self.__Sem_conns = threading.Semaphore(2) # the maximum number of connections is 2/最大连接数量为2
        self.__Sem_IPT_change = threading.Semaphore(1)
        self.__socket_pool = {}
        self.__isShow_msg = True
        self.__isShow_bd = True
        self.__isRun_net = False

    def __get_host_ip(self):
        """
        Inquire IP address:
        :return: ip
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        finally:
            s.close()

        return ip
    
    def __addConnection(self, shortname, sock):
        if shortname not in self.__socket_pool:
            with self.__Sem_conn_change:
                self.__socket_pool[shortname] = sock
        else:
            self.__echo(Dictionary['USER_EXISTED'])
            return False
        return True

    def __deleteConnection(self, shortname):
        if shortname in self.__socket_pool:
            sock = self.__socket_pool[shortname]
            if sock:
                sock.close()
                with self.__Sem_conn_change:
                    del self.__socket_pool[shortname]

    def __isRight_group(self, group):
        if group == self.__group:
            return True
        else: return False

    def __echo(self, text):
        with patch_stdout():
            if self.__isShow_msg:
                print(text)
            else: return

    def __echo_bc(self, text):
        with patch_stdout():
            if self.__isShow_bd:
                print(text)
            else: return

    def __broadcast(self):
        try:
            broad = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            broad.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            broad.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            host_broadcast = self.__host[::-1]
            host_broadcast = host_broadcast.replace(host_broadcast.split('.')[0], '552', 1)[::-1]
            # self.__host_broadcast = host_broadcast
            self.__host_broadcast = '255.255.255.255'
            broad.bind(("", self.__port_BROADCAST))
            self.__echo_bc(f'broadcast_ip: {host_broadcast}')
            isDie = [False]
            isLoop = False
            if self.__addConnection(Dictionary['BROADCAST'], broad) == True:
                t = threading.Thread(target = self.__broadcast_recv, args = (broad, isDie))
                t.setDaemon(True)
                t.start()
                isLoop = True

            while isLoop:
                time.sleep(3)
                if(isDie[0] == True):
                    self.__echo_bc(f'Socket of broadcast is closed <{self.__host_broadcast} - {self.__port_BROADCAST}>.')
                    break

        finally:
            broad.close()
            self.__deleteConnection(Dictionary['BROADCAST'])
        
    def __broadcast_ip(self):
        try:
            label = Dictionary['BROADCAST']
            if label in self.__socket_pool:
                broad = self.__socket_pool[label]
                message = base64.b64encode(f'{self.__group}/SHORTNAME:{self.__shortname}'.encode())
                broad.sendto(message, (self.__host_broadcast, self.__port_BROADCAST))
                self.__echo_bc('IP has been broadcasted.')
            else:
                self.__echo_bc('There is no socket for socket.')
        except Exception as e:
            self.__echo_bc(e)

    def __broadcast_recv(self, broad, isDie):
        try:
            while True:
                data, addr = broad.recvfrom(self.__recv_size)
                data = base64.b64decode(data).decode()
                self.__echo_bc(str(data) + ' ' + str(addr))
                t = threading.Thread(target=self.__process_bc, args=(data, addr))
                t.daemon = True
                t.start()
        except Exception as e:
            self.__echo_bc(e)
        finally:
            isDie[0] = True
            return

    def __process_bc(self, data, addr):
        conn_ip = addr[0]
        if(conn_ip != self.__host):
            header = data.split('/')[0]
            if self.__isRight_group(header):
                conn_name = data.split('/')[1].split(':')[1]
                if conn_name not in IP_table:
                    with self.__Sem_IPT_change:
                        IP_table[conn_name] = conn_ip
            else:
                self.__echo_bc(f"The connection - {conn_ip} is illegal.")

    def __search_conn(self):
        t = threading.Thread(target=self.__broadcast_ip)
        t.daemon = True
        t.start()
        print('Searching connection.....')
        time.sleep(2)
        if len(IP_table) != 0:
            print('Connections are shown as below:')
            for name, ip in IP_table.items():
                print(name)
                self.__echo_bc(f'debug: {name} - {ip}')
        else:
            print('No connection has been found.')

    def __WAN_slot(self, target_name):
        socket_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        src_addr = ("", self.__port_WAN)
        #Use a specific port to connect
        socket_.bind(src_addr)
        socket_.settimeout(3)

        try:
            isLoop = False
            isDie = [False]
            target = (IP_table[target_name], self.__port_LAN)
            socket_.connect(target)
            
            print(f'Trying to connect to {target_name}......')
            message = base64.b64encode(f'SHORTNAME:{self.__shortname}'.encode())
            socket_.sendall(message)
            data = socket_.recv(self.__recv_size)
            data = base64.b64decode(data).decode()

            if data.split(':')[0] == 'SHORTNAME':
                sendername = data.split(':')[1]
                if sendername == target_name:
                    self.__echo(f'Success to connect to {sendername}.')
                    #append the connection in socket pool
                    if self.__addConnection(target_name, socket_) == True:
                        isLoop = True
                        self.__isWAN_occupied = True
                        socket_.settimeout(None)
                        print(f"You have successfully connected to {target_name}")
                        t = threading.Thread(target = self.__receive, args = (socket_, sendername, isDie))
                        t.setDaemon(True)
                        t.start()
                    else:
                        isLoop = False
                        self.__isWAN_occupied = False
                else:
                    isLoop = False
                    self.__isWAN_occupied = False
                    self.__echo('The name of connection does not match, please check the IP_table!!!')
            else:
                isLoop = False
                self.__isWAN_occupied = False
                self.__echo(f'Device: <{target_name}>, is illegal. It cannot be connected')

            while isLoop:
                time.sleep(3)
                if(isDie[0] == True):
                    self.__echo('Connection terminate: source: ' + self.__shortname + ' --- %s:%s' %src_addr + ' --- destination: %s:%s' %target)
                    break
            
        except socket.timeout:
            print("connection timed out.")
        except ConnectionRefusedError:
            print(f'Failed to connect to {target_name}')
        finally:
            socket_.close()
            print("WAN slot is released now.")
            self.__isWAN_occupied = False
            if isDie[0]:
                self.__deleteConnection(target_name)
            else:
                socket_.close()

    def __LAN_slot(self, sock, addr, src_addr):
        with self.__Sem_conns:
            try:
                self.__echo('set connection: source address %s:%s' %addr + ' --- destination address %s:%s'  %src_addr )
                #when first accept the connection, we need save the shortname of the device
                isLoop = False
                isDie = [False]

                data = sock.recv(self.__recv_size)
                data = base64.b64decode(data).decode()
                
                if data.split(':')[0] == 'SHORTNAME':
                    sendername = data.split(':')[1]
                    #append the connection in socket pool
                    if self.__addConnection(sendername, sock) == True:
                        self.__echo(sendername + " has connected to this device.")
                        message = base64.b64encode(f'SHORTNAME:{self.__shortname}'.encode())
                        sock.send(message)
                        isLoop = True
                        t = threading.Thread(target = self.__receive, args =(sock, sendername, isDie))
                        t.setDaemon(True)
                        t.start()
                    else:
                        isLoop = False
                        return
                else:
                    isLoop = False
                    self.__echo(f"illegal connection! ==> {data}")
                    return
                
                while isLoop:
                    time.sleep(3)
                    if(isDie[0] == True):
                        self.__echo('Connection terminate: source: ' + sendername + ' --- destination: ' + self.__)
                        break
                return
            except ConnectionResetError:
                self.__echo('A peer client suddenly disconnected')
                return
            finally:
                #this token means whether the socket is added into socket pool.
                if isDie[0] == True:
                    self.__deleteConnection(sendername)
                    text = '++++++++++++++++++++++++++++++++++++++++++++++++++\n'
                    text += f'        connection: {sendername} closed\n'
                    text += '++++++++++++++++++++++++++++++++++++++++++++++++++'
                    print(text)
                else:
                    sock.close()

    def __send(self, targetname, text, type_):
        send_filter = SendType(self.__shortname)
        if targetname in self.__socket_pool:
            sock = self.__socket_pool[targetname]
            pack = send_filter.send_(type_, text)
            if pack[1] == True:
                msg = pack[2]
                self.__echo(msg)
                msg = base64.b64encode(msg.encode())
                sock.sendall(msg)
            else:
                print(pack[2])
                return False
            return True
        else:
            print(Dictionary['NO_USER'])
            return False

    def __receive(self, sock, sendername, isDie):
        try:
            while True:
                data = sock.recv(self.__recv_size)
                data = base64.b64decode(data).decode()
                if not data:
                    isDie[0] = True
                    break
                self.__echo("previous node: " + sendername + ', data: ' + data)
                

        except ConnectionResetError:
            isDie[0] = True
            return

        except BrokenPipeError:
            isDie[0] = True
            return
        finally:
            isDie[0] = True
            return
    
    def __maintain_listen(self, socket_, src_addr):
        while True:
            try:
                sock_,addr_ = socket_.accept()
                self.__echo(f'new connection: {addr_}')
                t = threading.Thread(target = self.__LAN_slot, args = (sock_,addr_,src_addr))
                t.setDaemon(True)
                t.start()
            except:
                print ("Error: Failed to create a new thread")
    
    def __listen_host(self):
        if not self.__isRun_net:
            socket_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print("IP address of current device: " + self.__host)
            src_addr = (self.__host, self.__port_LAN)
            socket_.bind(src_addr)
            #set the num of wating connection application
            socket_.listen(0)
            print('======================start=======================')
            print('                service is running...')
            print('=======================end========================')

            # to maintain listening the host
            maintain_listen = threading.Thread(target = self.__maintain_listen, args = (socket_, src_addr))
            maintain_listen.setDaemon(True)
            maintain_listen.start()
            self.__isRun_net = True
        else:
            print("You have already started the net.")

    def __connect_to(self, target_name):
        if self.__isWAN_occupied == False:
            t = threading.Thread(target = self.__WAN_slot, args = (target_name,))
            t.setDaemon(True)
            t.start()
            return True
        else:
            print("You have already connected to another device. No more slot are available")
            return False

    def __do_showMsg(self):
        self.__isShow_msg = True

    def __do_shut_showMsg(self):
        self.__isShow_msg = False

    async def __cli_input(self):
        #add a key binding to quit the cli
        isLoop = True
        kb = KeyBindings()
        @kb.add('escape')
        async def _(event):
            nonlocal isLoop
            isLoop = False
            event.app.exit()

        @kb.add('c-b')#
        async def _(event):
            self.__isShow_bd = not self.__isShow_bd

        #welcom text
        welcom_text = "Welcom to use ndn cli.\nYou can press 'escape' or 'Control + c' to quit.\n"
        print(welcom_text)
        #Create Prompt
        session = PromptSession()
        prompt = _Prompt.begining
        #Run echo loop.
        while isLoop:
            try:
                commandline = await session.prompt_async(prompt, key_bindings = kb)
                if commandline != None and commandline != '':
                    command = commandline.split(" ")

                    if command[0] == Command.OPEN_NET:
                        self.__listen_host()
                        prompt = _Prompt.running_bind

                    elif command[0] == Command.SHOW_MSG:
                        self.__do_showMsg()
                    
                    elif command[0] == Command.SHUT_SHOW_MSG:
                        self.__do_shut_showMsg()

                    elif command[0] == Command.SEARCH_CONN:
                        self.__search_conn()

                    elif command[0] == Command.SEND_TO:
                        if len(command) != 3:
                            print(f"The expression is wrong. please check it. {command[0]} -name -text")
                        else:
                            target_name = commandline.split(" ")[1]
                            text = commandline.split(" ")[2]
                            if self.__send(target_name, text, SendType.CHAT) == True:
                                Command.send_success(target_name, text)
                            else:
                                Command.send_failed(target_name, text)

                    elif command[0] == Command.CONNECT:
                        if len(command) != 2:
                            print(f'f"The expression is wrong. please check it. {command[0]} -name')
                        else:
                            target_name = commandline.split(' ')[1]
                            if self.__connect_to(target_name) != True:
                                Command.connect_failed(target_name)
                        pass
                        
                    elif command != None:
                        Command.not_found(command)

            except (EOFError, KeyboardInterrupt):
                return

    async def __main(self):
        with patch_stdout():
            t = threading.Thread(target = self.__broadcast)
            t.setDaemon(True)
            t.start()
            try:
                await self.__cli_input()
            finally:
                #cancell background tasks
                # bct.cancel()
                pass
            print("\nQuitting CLI. Bye.\n")

    def run(self):
        try:
            from asyncio import run
        except ImportError:
            asyncio.run_until_complete(self.__main())
        else:
            asyncio.run(self.__main())

if __name__ == '__main__':
    os.system('clear')
    demo = Demo()
    demo.run()
