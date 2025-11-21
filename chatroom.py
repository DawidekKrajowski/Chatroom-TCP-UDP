import socket
import threading
import sys
import select
import time

LOCAL_ADDR = "127.0.0.1"
class ServerTCP:
    def __init__(self, server_port):
          self.server_port = server_port
          self.server_socket = None
          self.clients = {}

        
          self.run_event = threading.Event()
          self.handle_event = threading.Event()
          
          self.LOCAL_ADDR = "0.0.0.0"
          print(f"Server TCP started on port {self.server_port}")




    def accept_client(self):
        # accepts a new client and adds it if the name is unique

        try:
            ready, _, _ = select.select([self.server_socket], [], [], 0.5)
            if not ready:
                return False
            
            client_socket, client_address = self.server_socket.accept()
            client_socket.setblocking(False)
            print(f"New connection from {client_address}")

            ready, _, _ = select.select([client_socket], [], [], 2.0)
            if not ready:
                client_socket.close()
                return False
            
            # Get client name
            data = client_socket.recv(4096)

            if not data:
                client_socket.close()
                return False
            client_name = data.decode('utf-8').strip()

            if client_name in self.clients.values():
                try:
                    client_socket.sendall('Name already taken'.encode('utf-8'))
                except Exception:
                    pass
                client_socket.close()
                return False
            try:
                client_socket.sendall('Welcome'.encode('utf-8'))
            except Exception:
                client_socket.close()
                return False
            self.clients[client_socket] = client_name
            self.broadcast(client_socket, 'join')
            print(f"Client '{client_name}' connected to chat.")

            t = threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True)
            t.start()
            return True
            
        except Exception as e:
            try:
                client_socket.close()
            except Exception:
                pass
            print(f"Error accepting client: {e}")
            return False    
        



    def close_client(self, client_socket):
        if client_socket in self.clients:
            client_name = self.clients[client_socket]
            self.broadcast(client_socket, 'exit')
            del self.clients[client_socket]
            client_socket.close()
            
            print(f"Client '{client_name}' disconnected from chat.")
            return True
        return False    
    
    def broadcast(self, client_socket_sent, message):
        # send a message to all clients except the sender 
        

        if client_socket_sent not in self.clients and message not in ('server-shutdown',):
            sender_name = None
        else:
            sender_name = self.clients.get(client_socket_sent, None)

        if message == 'join' and sender_name:
            broadcast_message = f"User {sender_name} joined"
        elif message == 'exit' and sender_name:
            broadcast_message = f"User {sender_name} left"
        elif message == 'server-shutdown':
            broadcast_message = 'server-shutdown'
        else:
            broadcast_message = f"{sender_name}: {message}" if sender_name else str(message)

        
        for client_socket in list(self.clients.keys()):
            if message != 'server-shutdown' and client_socket == client_socket_sent:
                continue
            try:
                client_socket.sendall(broadcast_message.encode('utf-8'))
            except Exception:

                try:
                    client_socket.close()
                except Exception:
                    pass
                if client_socket in self.clients:
                    self.clients.pop(client_socket,None)
            
                

    def shutdown(self):
        # gracefully shutdonw the server
        print("Shutting down server...")
        self.broadcast(None, 'server-shutdown')

        for client_socket in list(self.clients.keys()):
            try:
                client_socket.close()
            except Exception:
                pass
        self.clients.clear()
        self.run_event.set()
        self.handle_event.set() 

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None
       
        
        print("Server shutdown complete.")

    def get_clients_number(self):
        return len(self.clients)
    
    def handle_client(self, client_socket):
        #continuously listen for broadcasts and messages from a client.

        while self.handle_event.is_set():
            try:
                ready, _, _ = select.select([client_socket], [], [], 0.5)
                if not ready:
                    continue

                message = client_socket.recv(4096)
                if not message:
                    self.close_client(client_socket)
                    break
                msg = message.decode('utf-8').strip()
                if msg.lower() == 'exit':
                    
                    self.close_client(client_socket)
                    break
                
                self.broadcast(client_socket, msg)
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                self.close_client(client_socket)
                break
              
            except Exception:

                self.close_client(client_socket)
                break
                

                
    def run(self):
       # start theserver and accept clientsin seperate threads
        print("Server running . Waiting for clients...")
        self.run_event.clear()
        self.handle_event.set()

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((LOCAL_ADDR, self.server_port))
            self.server_socket.listen(5)
            self.server_socket.setblocking(False)
               
            while not self.run_event.is_set():
                try:
                   self.accept_client()
                   time.sleep(0.1)
                except KeyboardInterrupt:
                    break
                except Exception:
                    time.sleep(0.1)
        finally:
              self.shutdown()                               
                   
class ClientTCP:
    def __init__(self, client_name, server_port):
        self.server_port = server_port
        self.client_name = client_name
        self.server_addr = LOCAL_ADDR
        self.client_socket = None
        self.exit_run = threading.Event()
        self.exit_receive = threading.Event()

    def connect_server(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(4.0)
            self.client_socket.connect((self.server_addr, self.server_port))
            self.client_socket.sendall(self.client_name.encode('utf-8'))
            response = self.client_socket.recv(4096)

            if not response:
                return False
            response = response.decode('utf-8')
            
            if 'Welcome' in response:
                print(f"[Connected] joined the chatroom as '{self.client_name}'")
                self.client_socket.setblocking(False)
                return True
            else:
                print("[Connection Failed]")
                return False
        except Exception:
            try:
                if self.client_socket:
                    self.client_socket.close()
            except Exception:
                pass
            return False 
          
    def send(self, text):
        if not self.client_socket:
            return False
        try:  
            self.client_socket.sendall(text.encode('utf-8'))
            return True
        except Exception:
            return False   



    def receive(self):
        while not self.exit_receive.is_set():
            try:
                ready, _, _ = select.select([self.client_socket], [], [], 1.0)
                if not ready:
                   continue
                data = self.client_socket.recv(1024)
                if not data:
                   self.exit_run.set()
                   self.exit_receive.set()
                   break
                message = data.decode('utf-8')

                if message.lower() == 'server-shutdown':
                       print("[Disconnected] Server is shutting down.")
                       self.exit_run.set()
                       self.exit_receive.set()
                       break
                sys.stdout.write("\r" + message + "\n> ")
                sys.stdout.flush()
            except Exception:
                self.exit_run.set()
                self.exit_receive.set()
                break

    def run(self):
        if not self.connect_server():
            print('Failed to connect to server.')
            return
        recv_thread = threading.Thread(target=self.receive, daemon=True)
        recv_thread.start()
        
        try:
            while not self.exit_run.is_set():
                try:
                    text = input()
                except EOFError:
                    text = "exit"
                if text.strip().lower() == 'exit':
                    try:
                        self.send('exit')
                    except Exception:
                        pass
                    self.exit_run.set()
                    self.exit_receive.set()
                    break
                else:
                    self.send(text)
        except KeyboardInterrupt:
                try:
                    self.send('exit')
                except Exception:
                    pass
                self.exit_run.set()
                self.exit_receive.set()
        finally:
            try:        
                if self.client_socket:
                    self.client_socket.close()
            except Exception:
                pass

class ServerUDP:
    def __init__(self, server_port):
        self.server_port = server_port
        addr = socket.gethostbyname(socket.gethostname())
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((addr,self.server_port))
        self.clients = {}
        self.messages = []
        print(f"Server UDP started on port {self.server_port}")

    def accept_client(self, client_addr, message):
        name = message.strip()
        if name in self.clients.values():
            self.server_socket.sendto("Name already taken".encode('utf-8'), client_addr)
            return False
        self.clients[client_addr] = name
        self.server_socket.sendto("Welcome".encode('utf-8'), client_addr)
        self.messages.append((client_addr, f"User '{name}' has joined the chat."))
        self.broadcast()
        print(f"Client '{name}' connected to chat.")
        return True
    
    def close_client(self, client_addr):
        if client_addr in self.clients:
            name = self.clients[client_addr]
            del self.clients[client_addr]
            self.messages.append((client_addr, f"User {name} left"))
            self.broadcast()
            print(f"Client '{name}' disconnected from chat.")
            return True
        return False
    
    def broadcast(self):
        if not self.messages:
            return
        sender_addr, message = self.messages[-1]
        for addr in self.clients.keys():
            if addr != sender_addr:
                self.server_socket.sendto(message.encode('utf-8'), addr)

    def shutdown(self):
        print("Shutting down server...")
        shutdown_message = "server-shutdown"
        for addr in self.clients.keys():
            self.server_socket.sendto(shutdown_message.encode('utf-8'), addr)
        self.clients.clear()
        self.server_socket.close()
        print("ServerUDP shutdown complete.")

    def get_clients_number(self):
        return len(self.clients)
    def run(self):
        print("Server running. Waiting for clients...")
        try:
            while True:
                ready, _, _ = select.select([self.server_socket], [], [], 1.0)
                if ready:
                    message, client_addr = self.server_socket.recvfrom(1024)
                    message = message.decode('utf-8').strip()

                    if ":" in message:
                        client_name, text = message.split(':',1)
                    else:
                        client_name, text = None, message

                    if text == 'join':
                       self.accept_client(client_addr, client_name)
                    elif text == 'exit':
                        self.close_client(client_addr)
                    elif client_addr in self.clients:
                       self.messages.append((client_addr, f"{self.clients[client_addr]}: {text}"))
                       self.broadcast()
                    
        except KeyboardInterrupt:
            print("\nKeyboard interrupt detected.")
            self.shutdown()
        except Exception as e:
            print(f"Server error: {e}")
            self.shutdown()


class ClientUDP:
    def __init__(self, client_name, server_port):
        self.client_name = client_name
        self.server_port = server_port
        self.server_addr = socket.gethostbyname(socket.gethostname())
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.exit_run = threading.Event()
        self.exit_receive = threading.Event()

    def connect_server(self):
        try:
            self.send('join')
            ready, _, _ = select.select([self.client_socket], [], [], 2.0)
            if ready:
                message, _ = self.client_socket.recvfrom(1024)
                message = message.decode('utf-8')
                if 'Welcome' in message:
                    print(f"[Connected] joined the chatroom as '{self.client_name}'")
                    return True
                else:
                    print("[Connection Failed]")
                    return False
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    def send(self, text):
        try:
            message = f"{self.client_name}:{text}"
            self.client_socket.sendto(message.encode('utf-8'), (self.server_addr, self.server_port))
        except Exception as e:
            print(f"Send error: {e}")
            self.exit_run.set()
    def receive(self):
        try:
            while not self.exit_receive.is_set():
                ready, _, _ = select.select([self.client_socket], [], [], 1.0)
                if ready:
                    data, _ = self.client_socket.recvfrom(1024)
                    message = data.decode('utf-8')
                    if message.lower() == 'server-shutdown':
                        print("[Disconnected] Server is shutting down.")
                        self.exit_run.set()
                        self.exit_receive.set()
                        break
                    print("\r" + message + "\n> ", end="")
                    sys.stdout.flush()
        except:
            print("Receive error")


                
    def run(self):
        if not self.connect_server():
            return
        threading.Thread(target=self.receive, daemon=True).start()
        try:
            while not self.exit_run.is_set():
                message = input("> ")
                if message.lower() == "exit":
                    self.send("exit")
                    self.exit_run.set()
                    self.exit_receive.set()
                    break
                self.send(message)
        except KeyboardInterrupt:
            self.send("exit")
            self.exit_run.set()
            self.exit_receive.set()
        finally:
            self.client_socket.close()
            print("disconected")

