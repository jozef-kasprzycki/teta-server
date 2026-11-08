# 🦫 Teta server

## To install

Prepare python environment

```sh
python -m venv ./.venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create ssl certificate and key
```sh
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

Create `.env` file
```env
PORT=<listening_port>
```

## Run

```py
python3 server.py
```
