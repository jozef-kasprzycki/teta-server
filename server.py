import socket
import threading
import ssl
from utils import get_env

class Server:
    def __init__(self, max_clients_num=5):
        # Lista przechowująca połączenia z klientami
        self.clients = []
        self.max_clients_num = max_clients_num
        
        self.context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self.context.load_cert_chain(certfile='./cert.pem', keyfile='./key.pem')

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Nasłuchuj na wszystkich interfejsach na porcie PORT
        self.server.bind(('0.0.0.0', int(get_env('PORT'))))

    def handle_client(self, conn, addr):
        print(f'[NEW CONNECTION] {addr}')
        while True:
            try:

                # Odbierz wiadomość od klienta
                message = conn.recv(1024)
                if not message:
                    break
            
                print(f"Otrzymano od {addr}: {message.decode('utf-8')}")
                # zapisywanie do bazy danych 
                # Przekaż wiadomość wszystkim *innym* podłączonym klientom
                for client in self.clients:
                    if client != conn:
                        try:
                            client.sendall(message)
                        except:
                            # Jeśli wysyłanie się nie powiodło, usuń klienta
                            self.clients.remove(client)
            except:
                break

        # Sprzątanie po rozłączeniu klienta
        conn.close()
        if conn in self.clients:
            self.clients.remove(conn)
        print(f"[ROZŁĄCZONO] Klient {addr} się rozłączył")

    def start(self):
        self.server.listen(self.max_clients_num)
        print("[START] Serwer czatu działa i czeka na połączenia...")

        while True:
            conn, addr = self.server.accept()
            
            secure_conn = self.context.wrap_socket(conn, server_side=True)
            self.clients.append(secure_conn)
            # Uruchom osobny wątek dla każdego nowego klienta
            thread = threading.Thread(target=self.handle_client, args=(secure_conn, addr))
            thread.start()

            print(f"[AKTYWNE POŁĄCZENIA] {threading.active_count() - 1}")

if __name__ == "__main__":
    server = Server()
    server.start()

