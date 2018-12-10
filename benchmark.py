import os
import shlex
import signal
import subprocess
import sys
import time
from threading import Thread

import click
import docker
import docker.errors
import numpy as np

from local.proxy import Proxy
from postprocess import plot_results

# this script deploys the experiments
DOCKER_CPULOAD = 'molguin/cpuload'
DOCKER_PYTHON = 'molguin/python'
CPU_LOADS = [0.0, 0.25, 0.5, 0.75, 1.0]
TARGET_CORE = 0
BENCHMARK_TYPES = ['base', 'tcpdump', 'proxy']
TCPDUMP_PCAP = '/tmp/dump.pcap'
TCPDUMP_CMD_PRE = ['tcpdump', '-s 0']
TCPDUMP_CMD_POST = [f'-w {TCPDUMP_PCAP}']
SAMPLES = 5000


class Benchmark:
    def __init__(self, host: str, port: int, cpu_load: float):
        self.host = host
        self.port = port
        self.cpu_load = cpu_load
        self.docker = docker.from_env()
        self.cpu_load_container = None
        self.results = {t: None for t in BENCHMARK_TYPES}

    def run(self):
        self.base_benchmark()
        self.proxy_benchmark()
        self.tcpdump_benchmark()

    def base_benchmark(self):
        self._base('base')

    def tcpdump_benchmark(self):
        # start tcpdump, run _base() and then shutdown tcpdump
        # only capture packets to and from the echo server

        # remove pcap?
        if os.path.exists(TCPDUMP_PCAP):
            os.remove(TCPDUMP_PCAP)

        filter_cmds = f'(src {self.host} or dst {self.host}) and port' \
            f' {self.port}'
        dump_cmd = shlex.split(' '.join(TCPDUMP_CMD_PRE
                                        + [filter_cmds]
                                        + TCPDUMP_CMD_POST))

        tcpdump_proc = subprocess.Popen(dump_cmd)
        # warmup time?
        time.sleep(0.1)
        if tcpdump_proc.poll():
            raise RuntimeError('Could not start TCPDump?')

        # run benchmark
        self._base('tcpdump')

        # benchmark done, stop TCPDump
        tcpdump_proc.send_signal(signal.SIGINT)
        tcpdump_proc.wait()  # wait for tcpdump shutdown

        # remove pcap?
        if os.path.exists(TCPDUMP_PCAP):
            os.remove(TCPDUMP_PCAP)
        # done

    def proxy_benchmark(self):
        # start the proxy -> run experiment -> stop the proxy
        proxy_port = self.port + 1
        proxy_host = '172.17.0.1'  # proxy runs on the host machine in the
        # docker bridge network, see
        # https://docs.docker.com/v17.09/engine/userguide/networking/#the
        # -default-bridge-network
        proxy = Proxy('0.0.0.0', proxy_port, self.host, self.port)
        # start listening needs to be done asynchronously, but a thread is
        # enough
        t = Thread(target=proxy.start)
        t.start()
        time.sleep(0.1)  # give proxy time to connect and bind

        # proxy running, run benchmark
        self._base('proxy',
                   host_override=proxy_host,
                   port_override=proxy_port)

        # shut down proxy after benchmark finishes
        t.join()
        proxy.stop()

    def _base(self, bench_type: str,
              host_override: str = None,
              port_override: int = None):
        if bench_type not in BENCHMARK_TYPES:
            raise RuntimeError(bench_type)

        print(f'Performing <{bench_type}> benchmark.', file=sys.stderr)
        print(f'Target CPU load: {self.cpu_load}', file=sys.stderr)
        sys.stderr.flush()

        # port/host override for use with the proxy
        if host_override:
            host = host_override
        else:
            host = self.host

        if port_override:
            port = port_override
        else:
            port = self.port

        # perform measurement
        if self.cpu_load > 0.1:
            print('Starting CPU load controller.', file=sys.stderr)
            self.cpu_load_container = self.docker.containers.run(
                DOCKER_CPULOAD,
                command=f'-c {TARGET_CORE} -l {self.cpu_load} -d -1',
                detach=True, auto_remove=True
            )
            # wait for core to ramp up
            time.sleep(1)

        # run client
        results = self.docker.containers.run(
            DOCKER_PYTHON,
            stdout=True,
            command=f'python -m local.client --samples {SAMPLES} {host} {port}',
            detach=False, auto_remove=True, cpuset_cpus=str(TARGET_CORE)
        )

        # stop cpu load
        if self.cpu_load_container:
            self.cpu_load_container.kill()

        parsed_results = []
        for sample in results.splitlines():
            try:
                parsed_results.append(float(sample))
            except ValueError:
                continue

        self.results[bench_type] = np.array(parsed_results)


@click.command(help='Benchmark runner. Executes all benchmarks in one run and '
                    'outputs plots of the collected metrics. '
                    'Connects to an echo server running on HOST:PORT.')
@click.argument('host', type=str)
@click.argument('port', type=int)
def main(host: str, port: int):
    results = {}
    for cpu_load in CPU_LOADS:
        benchmark = Benchmark(host, port, cpu_load)
        benchmark.run()
        print('Benchmarking done.', file=sys.stderr)

        results[cpu_load] = benchmark.results

    print('Plotting...', file=sys.stderr)
    plot_results(results)


if __name__ == '__main__':
    main()
