import socket
import threading
import ssl
import json
from datetime import datetime, timezone
from pathlib import Path
from functools import wraps

from utils import get_env
from db import Database
import models

class Server:
    def __init__(self, max_clients_num: int = 5) -> None:
        if max_clients_num < 1:
            raise ValueError("max_clients_num musi być większe od zera")

        self.clients = []
        self._clients_lock = threading.Lock()
        self.max_clients_num = max_clients_num
        self._closed = False
        self.server = None
        self.database = None

        base_dir = Path(__file__).resolve().parent
        self.context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.context.load_cert_chain(
            certfile=base_dir / "cert.pem",
            keyfile=base_dir / "key.pem",
        )

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind(("0.0.0.0", self._port()))
            self.database = Database()
        except Exception:
            self.server.close()
            self.server = None
            raise

    @staticmethod
    def _port() -> int:
        raw = get_env("PORT")
        if not raw:
            raise ValueError("Brak zmiennej PORT w pliku .env")
        try:
            port = int(raw)
        except ValueError as error:
            raise ValueError(f"PORT musi być liczbą, otrzymano {raw!r}") from error
        if not 1 <= port <= 65535:
            raise ValueError(f"PORT musi być z zakresu 1-65535, otrzymano {port}")
        return port

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True

        if self.server is not None:
            try:
                self.server.close()
            except OSError:
                pass
            self.server = None

        with self._clients_lock:
            clients = list(self.clients)
            self.clients.clear()

        for conn in clients:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            try:
                conn.close()
            except OSError:
                pass

        if self.database is not None:
            self.database.close()
            self.database = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def _auth(self, req: models.Request) -> str | None:
        if req.token is None or self.database is None:
            return None

        db_token = self.database.get_token(req.token)
        if db_token is None:
            return None

        expiry_date = db_token.expiry_date
        if expiry_date.tzinfo is None:
            expiry_date = expiry_date.replace(tzinfo=timezone.utc)

        if expiry_date <= datetime.now(timezone.utc):
            return None
        return db_token.user_id

    def auth(func):  # bez self, wywoływane tylko przy definicji klasy
        @wraps(func)
        def wrapper(self, req, *args, **kwargs):
            user_id = self._auth(req)
            if user_id is None:
                return json.dumps({"error": "Bad authorization"})
            return func(self, req, user_id, *args, **kwargs)
        return wrapper

    @auth
    def client_get_update(self, req: models.Request, user_id: str) -> list | None:
        pass

    @auth
    def client_send_message(self, req: models.Request, user_id: str) -> models.Message | None:
        pass

    @staticmethod
    def parse_request(request: str) -> models.Request:
        parsed = json.loads(request)    

        return models.Request(
            action = parsed.get('action'),    
            token = parsed.get('token'),
            body = parsed.get('body')
        )

    def handle_request(self, req: str) -> str:
        parsed = self.parse_request(req)

        match parsed.action:
            case 'login':
                return self.client_login(parsed)
            case 'logout':
                return self.client_logout(parsed)
            case 'get-update':
                return self.client_get_update(parsed)
            case 'send-message':
                return self.client_send_message(parsed)
            case _:
                return json.dumps({"error": "Invalid action"})

    def handle_client(self, conn, addr):
        print(f'[NEW CONNECTION] {addr}')
        while True:
            try:

                # Odbierz wiadomość od klienta
                request_raw = conn.recv(1024)

                if not request_raw:
                    break
            
                print(f"Otrzymano od {addr}: {request_raw.decode('utf-8')}")

                response = self.handle_request(request_raw.decode('utf-8')).encode('utf-8')
                conn.sendall(response)

            except:
                break

        # Sprzątanie po rozłączeniu klienta
        conn.close()
        with self._clients_lock:
            if conn in self.clients:
                self.clients.remove(conn)
        print(f"[ROZŁĄCZONO] Klient {addr} się rozłączył")

    def start(self) -> None:
        self.server.listen(self.max_clients_num)
        print("[START] Serwer czatu działa i czeka na połączenia...")

        try:
            while True:
                try:
                    conn, addr = self.server.accept()
                except OSError:
                    break

                with self._clients_lock:
                    if len(self.clients) >= self.max_clients_num:
                        conn.close()
                        print(f"[ODRZUCONO] {addr}: limit {self.max_clients_num} klientów")
                        continue

                try:
                    secure_conn = self.context.wrap_socket(conn, server_side=True)
                except ssl.SSLError as error:
                    conn.close()
                    print(f"[TLS] Odrzucono {addr}: {error}")
                    continue

                with self._clients_lock:
                    if len(self.clients) >= self.max_clients_num:
                        secure_conn.close()
                        print(f"[ODRZUCONO] {addr}: limit {self.max_clients_num} klientów")
                        continue
                    self.clients.append(secure_conn)
                    active = len(self.clients)

                thread = threading.Thread(
                    target=self.handle_client,
                    args=(secure_conn, addr),
                    daemon=True,
                )
                thread.start()
                print(f"[AKTYWNE POŁĄCZENIA] {active}")
        except KeyboardInterrupt:
            print("\n[STOP] Zamykanie serwera...")
        finally:
            self.close()
