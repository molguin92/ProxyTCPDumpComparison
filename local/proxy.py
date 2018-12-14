import multiprocessing.pool
import signal
import socket
import struct
import sys
import time
from typing import Any

import click

from netutils import recvmsg


class _ShutDownException(Exception):
    def __init__(self, msg: Any):
        super().__init__(msg)
        self.msg = msg


def link_with_load(in_sock: socket.socket, out_sock: socket.socket):
    # links an incoming socket with an outgoing socket
    # additionally adds some light load equivalent to what would be done if
    # using the proxy to measure round-trip-times
    def sig_handler(arg0, arg1):
        raise _ShutDownException('SIGINT')

    signal.signal(signal.SIGINT, sig_handler)
    times = [0]
    while True:
        try:
            data = recvmsg(in_sock)
            d_len = len(data)
            ti = time.time()
            times[0] = ti * 1000.0
            out_sock.sendall(struct.pack(f'>I{d_len}s', d_len, data))
        except _ShutDownException as e:
            print('Received shutdown signal...', file=sys.stderr)
            break
        except Exception as e:
            break

    try:
        out_sock.shutdown(socket.SHUT_WR)
        in_sock.shutdown(socket.SHUT_RD)
        out_sock.close()
        in_sock.close()
    except Exception:
        pass


class Proxy:
    def __init__(self, listen_host: str, listen_port: int,
                 remote_host: str, remote_port: int):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.remote_host = remote_host
        self.remote_port = remote_port

        self.conn = None
        self.running = False

        self.uplink_proc = None
        self.downlink_proc = None

        # prepare sockets
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start(self):
        # start listening
        self.server_socket.bind((self.listen_host, self.listen_port))
        self.server_socket.listen(1)

        # connect to remote
        self.client_socket.connect((self.remote_host, self.remote_port))

        print(f'Proxy connected to {self.remote_host}:{self.remote_port} and '
              f'listening on {self.listen_host}:{self.listen_port}',
              file=sys.stderr)

        # wait for a connection
        (self.conn, addr) = self.server_socket.accept()

        # start relaying
        print(f'Accepted connection from {addr[0]}:{addr[1]}, relaying...',
              file=sys.stderr)

        self.uplink_proc = multiprocessing.Process(
            target=link_with_load,
            args=(self.conn, self.client_socket)
        )

        self.downlink_proc = multiprocessing.Process(
            target=link_with_load,
            args=(self.client_socket, self.conn)
        )

        self.uplink_proc.start()
        self.downlink_proc.start()
        self.running = True

    def stop(self):
        # shutdown by closing all sockets
        if self.running:
            print(f'Shutting down proxy...', file=sys.stderr)

            if self.conn:
                self.conn.shutdown(socket.SHUT_RDWR)
                self.conn.close()

            self.server_socket.shutdown(socket.SHUT_RDWR)
            self.client_socket.shutdown(socket.SHUT_RDWR)
            self.server_socket.close()
            self.client_socket.close()

            # wait for processes
            if self.uplink_proc:
                self.uplink_proc.join()
            if self.downlink_proc:
                self.downlink_proc.join()


@click.command(help='TCP proxy. Listens on localhost:LOCAL_PORT and resends '
                    'everything it receives there to REMOTE_HOST:REMOTE_PORT.')
@click.argument('local_port', type=int)
@click.argument('remote_host', type=str)
@click.argument('remote_port', type=int)
def main(local_port: int, remote_host: str, remote_port: int) -> None:
    proxy = Proxy('0.0.0.0', local_port, remote_host, remote_port)
    proxy.start()

    # set up a signal handler
    def signal_handler(a0, a1):
        proxy.stop()

    signal.signal(signal.SIGINT, signal_handler)


if __name__ == '__main__':
    main()
