import sys
from typing import Dict

import matplotlib.pyplot as plt


def plot_results(results: Dict) -> None:
    # results structure:
    # {cpuload: {benchmark: {}}}
    cpu_loads = []
    base = []
    proxy = []
    tcpdump = []

    for load, l_results in results.items():
        print(load, file=sys.stderr)
        cpu_loads.append(load)
        base.append(l_results['base'].mean())
        proxy.append(l_results['proxy'].mean())
        tcpdump.append(l_results['tcpdump'].mean())

    fig, ax = plt.subplots()
    ax.plot(cpu_loads, base, label='Base')
    ax.plot(cpu_loads, proxy, label='Proxy')
    ax.plot(cpu_loads, tcpdump, label='TCPDump')
    ax.legend()

    plt.show()
