from socketserver import ThreadingTCPServer, BaseRequestHandler
from socket import SOL_SOCKET, SO_KEEPALIVE, IPPROTO_TCP, TCP_KEEPIDLE, \
    TCP_KEEPCNT, TCP_KEEPINTVL
import click


def set_keepalive_linux(sock, after_idle_sec=1, interval_sec=3, max_fails=5):
    '''Set TCP keepalive on an open socket.
    It activates after 1 second (after_idle_sec) of idleness,
    then sends a keepalive ping once every 3 seconds (interval_sec),
    and closes the connection after 5 failed ping (max_fails), or 15 seconds
    '''
    sock.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
    sock.setsockopt(IPPROTO_TCP, TCP_KEEPIDLE, after_idle_sec)
    sock.setsockopt(IPPROTO_TCP, TCP_KEEPINTVL, interval_sec)
    sock.setsockopt(IPPROTO_TCP, TCP_KEEPCNT, max_fails)


class EchoHandler(BaseRequestHandler):
    # handler for the server which simply echoes the incoming data

    def setup(self):
        set_keepalive_linux(self.request)

    def handle(self):
        # echo up to a kB of data
        print('Client connected:', self.client_address[0])
        while True:
            try:
                self.request.sendall(self.request.recv(1024))
            except Exception:
                print('Client disconnected:', self.client_address[0])
                return


@click.command(help='Echo listen server')
@click.argument('host', type=str, default='0.0.0.0')
@click.argument('port', type=int, default=1337)
def main(host: str, port: int):
    with ThreadingTCPServer((host, port), EchoHandler) as server:
        server.serve_forever()


if __name__ == '__main__':
    main()
