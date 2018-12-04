import socket
import os
import time
import signal


def send_recv(conn: socket, data_len: int = 512) -> None:
    while True:
        # generate an array of random bytes
        data = os.urandom(data_len)
        conn.sendall(data)
        # timestamp
        ti = time.time()

        # get the echo
        incoming = []
        total_recv = 0
        while total_recv < data_len:
            d = conn.recv(data_len)
            if d == b'':
                raise RuntimeError('socket connection broken')
            incoming.append(d)
            total_recv += len(d)
        incoming = b''.join(incoming)
        assert incoming == data

        dt = (time.time() - ti) * 1000.0
        print('RTT: {} milliseconds'.format(dt))


if __name__ == '__main__':
    port = 1337
    host = '0.0.0.0'

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
        def sigint_handler(sig, frame):
            print('Shut down gracefully...')
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()
            print('Done!')
            exit(0)


        signal.signal(signal.SIGINT, sigint_handler)
        conn.connect((host, port))
        send_recv(conn)
