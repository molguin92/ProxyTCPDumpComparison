import os
import signal
import socket
import sys
import time

import click
import numpy as np


def send_recv(conn: socket,
              data_len: int = 512,
              samples: int = 500) -> np.ndarray:
    rtts = np.empty(samples)
    count = 0
    initialized = False
    while count < samples:
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

        # timestamp delta t in milliseconds
        dt = (time.time() - ti) * 1000.0

        # if data is "corrupted" for some weird reason, don't count the stats
        # also, discard the first sample to avoid effects due to connection
        # setup times and such
        if not initialized or incoming != data:
            initialized = True
            continue

        # store stats
        rtts[count] = dt
        count += 1
        time.sleep(0.01)  # sleep 10 ms so as to not overload the network

    return rtts


@click.command(help='RTT benchmarking client. Connects to an echo server '
                    'running on HOST:PORT and measures round trip times.')
@click.argument('host', type=str)
@click.argument('port', type=int)
@click.option('-s', '--samples',
              type=int, default=500,
              help='Number of samples to take',
              show_default=True)
def main(host: str, port: int, samples: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
        def sigint_handler(sig, frame):
            print('Shut down gracefully...', file=sys.stderr, flush=True)
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()
            print('Done!', file=sys.stderr, flush=True)
            exit(0)

        signal.signal(signal.SIGINT, sigint_handler)
        conn.connect((host, port))
        results = send_recv(conn, samples=samples)
        conn.shutdown(socket.SHUT_RDWR)

        for i in results:
            print(i, file=sys.stdout, flush=False)
        sys.stdout.flush()


if __name__ == '__main__':
    main()
