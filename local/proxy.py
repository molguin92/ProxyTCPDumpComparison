import multiprocessing.pool
import signal
import socket
import socketserver
import sys
import time
from typing import Any

import click


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
            data = in_sock.recv(1024)
            ti = time.time()
            times[0] = ti * 1000.0
            out_sock.sendall(data)
        except _ShutDownException as e:
            print('Received shutdown signal...', file=sys.stderr)
            break
        except Exception as e:
            break

    out_sock.shutdown(socket.SHUT_WR)
    in_sock.shutdown(socket.SHUT_RD)
    out_sock.close()
    in_sock.close()


class ProxyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        uplink_proc = multiprocessing.Process(
            target=link_with_load,
            args=(self.request, self.server.client_socket)
        )

        downlink_proc = multiprocessing.Process(
            target=link_with_load,
            args=(self.server.client_socket, self.request)
        )

        uplink_proc.start()
        downlink_proc.start()
        # wait for processes to end...
        uplink_proc.join()
        downlink_proc.join()

        self.request.shutdown(socket.SHUT_RDWR)
        self.server.client_socket.shutdown(socket.SHUT_RDWR)

        # shutdown server
        # needs to be done in "asynchronous" fashion


class Proxy(socketserver.TCPServer):
    def __init__(self, listen_port: int, remote_host: str, remote_port: int):
        # bind
        super().__init__(('0.0.0.0', listen_port), ProxyHandler)

        self.host = remote_host
        self.port = remote_port

        # connect
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.host, self.port))

        print(
            'Proxy listening on 0.0.0.0:{}, forwarding to {}:{}' \
                .format(listen_port, remote_host, remote_port),
            file=sys.stderr
        )

    def handle_request(self):
        def signal_handler(arg0, arg1):
            raise _ShutDownException('Shutdown before receiving a request!')

        signal.signal(signal.SIGINT, signal_handler)
        try:
            super().handle_request()
        except _ShutDownException as e:
            print(e.msg, file=sys.stderr)
            return

    def server_close(self):
        try:
            self.client_socket.close()
        except Exception:
            pass
        super().server_close()


@click.command(help='TCP proxy. Listens on localhost:LOCAL_PORT and resends '
                    'everything it receives there to REMOTE_HOST:REMOTE_PORT.')
@click.argument('local_port', type=int)
@click.argument('remote_host', type=str)
@click.argument('remote_port', type=int)
def main(local_port: int, remote_host: str, remote_port: int) -> None:
    def sig_handler(arg0, arg1):
        pass

    signal.signal(signal.SIGINT, sig_handler)
    with Proxy(local_port, remote_host, remote_port) as proxy:
        proxy.handle_request()


if __name__ == '__main__':
    main()
