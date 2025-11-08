import socket
import threading

class ServerTCP:
    def __init__(self, server_port):
          self.server_port = server_port
          self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
          self.server_socket.bind(('0.0.0.0', self.server_port))
          self.server_socket.listen(5)

          self.clients = {}
          self.run_event = threading.Event()
          self.handle_event = threading.Event()
          self.run_event.set()
          self.handle_event.set()

          print(f"Server TCP started on port {self.server_port}")




    def accept_client(self):
        # accepts a new client and adds it if the name is unique

        try:
            client_socket, client_address = self.server_socket.accept()
            print(f"New connection from {client_address}")

            client_name = client_socket.recv(1024).decode('utf-8').strip()

            if client_name in self.clients.values():
                client_socket.sendall("Name already taken. Connection refused.".encode('utf-8'))
                client_socket.close()
                return False
            else:
                self.clients[client_socket] = client_name
                client_socket.sendall("Welcome to the chatroom!".encode('utf-8'))

                self.broadcast(client_socket,'join')
                print(f"Client '{client_name}' connected to chat.")
                return True
        except Exception as e:
            print(f"Error accepting client: {e}")
            return False    
        



    def close_client(self, client_socket):
        if client_socket in self.clients:
            client_name = self.clients[client_socket]
            del self.clients[client_socket]
            client_socket.close()
            self.broadcast(client_socket, 'leave')
            print(f"Client '{client_name}' disconnected from chat.")
            return True
        return False    
    
    def broadcast(self, client_socket_sent, message):
        # send a message to all clients except the sender 
        sender_name = self.clients.get(client_socket_sent, "Unknown")

        if message == 'join':
            broadcast_message = f"User '{sender_name}' has joined the chat."
        elif message == 'exit':
            broadcast_message = f"User '{sender_name}' has left the chat."
        else:
            broadcast_message = f"{sender_name}: {message}"

        for client_socket in list(self.clients.keys()):
            if client_socket != client_socket_sent:
                try:
                    client_socket.sendall(broadcast_message.encode('utf-8'))
                except:
                    self.close_client(client_socket)

    def shutdown(self):
        # gracefully shutdonw the server
        print("Shutting down server...")
        shutdown_message = "Server is shutting down. Disconnecting..."
        for client_socket in list(self.clients.keys()):
            try:
                client_socket.sendall(shutdown_message.encode('utf-8'))
                client_socket.close()
            except:
                pass
        self.clients.clear()
        self.run_event.clear()
        self.handle_event.clear()
        self.server_socket.close()
        print("Server shutdown complete.")

    def get_clients_number(self):
        return len(self.clients)
    
    def handle_client(self, client_socket):
        #continuously listen for broadcasts and messages from a client.

        while self.handle_event.is_set():
            try:
                message = client_socket.recv(1024).decode('utf-8').strip()
                if not message:
                    break
                if message.lower() == 'exit':
                    self.broadcast(client_socket, 'exit')
                    self.close_client(client_socket)
                    break
                else:
                    self.broadcast(client_socket, message)
            except:
                self.close_client(client_socket)
                break

                
    def run(self):
       # start theserver and accept clientsin seperate threads
        print("Server running . Waiting for clients...")

        try:
           while self.run_event.is_set():
               success = self.accept_client() 
               if success:
                   
                   client_socket = list(self.clients.keys())[-1]
                   threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
        except KeyboardInterrupt:
           print("\nKeyboard interrupt detected.")
           self.shutdown()
        except Exception as e:
           print(f"server error: {e}")
           self.shutdown()

class ClientTCP:
    def __init__(self, client_name, server_port):
        self.server_port = server_port
        self.client_name = client_name
        self.server_addr = socket.gethostbyname(socket.gethostname())
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.exit_run = threading.Event()
        self.exit_receive = threading.Event()

    def connect_server(self):
        try:
            self.client_socket.connect((self.server_addr, self.server_port))
            self.client_socket.sendall(self.client_name.encode('utf-8'))
            response = self.client_socket.recv(1024).decode('utf-8')
            if 'Welcome' in response:
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
            self.client_socket.sendall(text.encode('utf-8'))
        except Exception as e:
            print(f"Send error: {e}")
            self.exit_run.set()    
    def receive(self):
        while not self.exit_receive.is_set():
            try:
               ready, _, _ = select.select([self.client_socekt], [], [], 1.0)
               if ready:
                   message = self.client_socket.recv(1024).decode('utf-8')
                   if message == 'server-shutdown':
                       print("[Disconnected] Server is shutting down.")
                       self.exit_run.set()
                       self.exit_receive.set()
                       break
                   print("\r" + message + "\n> ", end="")
                   sys.stdout.flush()
            except Exception as e:
                break
    def run(self):
        if not self.connect_server():
            return
        threading.Thread(target= self.reveive, daemon=True).start()
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
            print("\n[Disconnected] Exiting chatroom.")
            self.send("exit")
            self.exit_run.set()
            self.exit_receive.set()
        finally:
            self.client_socket.close()
            print("disconected")

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
        self.server_socket.sendto("Welcome".encoded('utf-8;'), client_addr)
        self.messages.append((client_addr, f"User '{name}' has joined the chat."))
        self.broadcast()
        print(f"Client '{name}' connected to chat.")
        return True
    
    def close_client(self, client_addr):
        if client_addr in self.clients:
            name = self.clients[client_addr]
            del self.clients[client_addr]
            self.messages.append((client_addr, f"user {name} left"))
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
        shutdown_message = "Server is shutting down. Disconnecting..."
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
                    if message == 'join':
                       self.accept_client(client_addr, client_addr[0])
                    elif message == 'exit':
                        self.close_client(client_addr)
                    elif client_addr in self.clients:
                       self.messages.append((client_addr, f"{self.clients[client_addr]}: {message}"))
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
        self.client_socekt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.exit_run = threading.Event()
        self.exit_reveive = threading.Event()

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
        pass
    def receive(self):
        pass
    def run(self):
        pass