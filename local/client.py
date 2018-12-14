import os
import signal
import socket
import struct
import sys
import time

import click
import numpy as np

from netutils import recvmsg

WARMUP_COUNT = 25


def send_recv(conn: socket,
              data_len: int = 512,
              samples: int = 500) -> np.ndarray:
    rtts = np.empty(samples)
    count = 0
    init_count = 0
    while count < samples:
        # generate an array of random bytes
        data = os.urandom(data_len)
        conn.sendall(struct.pack(f'>I{data_len}s', data_len, data))
        # timestamp
        ti = time.time()

        # get the echo
        echo = recvmsg(conn)

        # timestamp delta t in milliseconds
        dt = (time.time() - ti) * 1000.0

        # discard the first WARMUP_COUNT samples to avoid effects due
        # to connection setup times and such
        if init_count < WARMUP_COUNT:
            init_count += 1
            time.sleep(0.01)
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
