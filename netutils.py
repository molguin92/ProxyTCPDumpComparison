import struct
from socket import socket


def recvall(sock: socket, data_len: int) -> bytes:
    incoming = []
    total_recv = 0
    while total_recv < data_len:
        d = sock.recv(data_len)
        if d == b'':
            raise RuntimeError('socket connection broken')
        incoming.append(d)
        total_recv += len(d)
    return b''.join(incoming)


def recvmsg(sock: socket) -> bytes:
    # receive message length
    data_len_b = recvall(sock, 4)
    (data_len,) = struct.unpack('>I', data_len_b)

    return recvall(sock, data_len)
