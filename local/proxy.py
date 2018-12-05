import multiprocessing
import socket
import socketserver
import sys
import time

import click


def link_with_load(in_sock: socket.socket, out_sock: socket.socket):
    # links an incoming socket with an outgoing socket
    # additionally adds some light load equivalent to what would be done if
    # using the proxy to measure round-trip-times
    times = [0]
    while True:
        try:
            data = in_sock.recv(1024)
            ti = time.time()
            tf = time.time()
            times[0] = (tf - ti) * 1000.0
            out_sock.sendall(data)
        except Exception:
            out_sock.shutdown(socket.SHUT_WR)
            in_sock.shutdown(socket.SHUT_RD)
            out_sock.close()
            in_sock.close()
            return


class ProxyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        with multiprocessing.Pool(processes=2) as pool:
            pool.starmap(
                link_with_load,
                ((self.request, self.server.client_socket),
                 (self.server.client_socket, self.request))
            )
        self.request.shutdown(socket.SHUT_RDWR)
        self.server.client_socket.shutdown(socket.SHUT_RDWR)


class Proxy(socketserver.TCPServer):
    def __init__(self, listen_port: int, remote_host: str, remote_port: int):
        # bind
        super().__init__(('localhost', listen_port), ProxyHandler)

        self.host = remote_host
        self.port = remote_port

        # connect
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.host, self.port))

        print(
            'Proxy listening on localhost:{}, forwarding to {}:{}' \
                .format(listen_port, remote_host, remote_port),
            file=sys.stderr
        )

    def server_close(self):
        self.client_socket.close()
        super().server_close()


@click.command(help='TCP proxy. Listens on localhost:LOCAL_PORT and resends '
                    'everything it receives there to REMOTE_HOST:REMOTE_PORT.')
@click.argument('local_port', type=int)
@click.argument('remote_host', type=str)
@click.argument('remote_port', type=int)
def main(local_port: int, remote_host: str, remote_port: int) -> None:
    with Proxy(local_port, remote_host, remote_port) as proxy:
        proxy.serve_forever()


if __name__ == '__main__':
    main()
