import sys
import time

import click
import docker
import docker.errors
import numpy as np

# this script deploys the experiments
DOCKER_CPULOAD = 'molguin/cpuload'
DOCKER_PYTHON = 'molguin/python'
CPU_LOADS = [0.0, 0.25, 0.5, 0.75, 1.0]
TARGET_CORE = 0

BENCHMARK_TYPES = ['base', 'tcpdump', 'proxy']


class Benchmark:
    def __init__(self, host: str, port: int, cpu_load: float):
        self.host = host
        self.port = port
        self.cpu_load = cpu_load
        self.docker = docker.from_env()
        self.cpu_load_container = None
        self.results = {t: None for t in BENCHMARK_TYPES}

    def run(self):
        # TODO finish
        self._base('base')

    def _base(self, bench_type: str):
        if bench_type not in BENCHMARK_TYPES:
            raise RuntimeError(bench_type)

        print(f'Performing <{bench_type}> benchmark.', file=sys.stderr)
        print(f'Target CPU load: {self.cpu_load}', file=sys.stderr)

        # perform measurement
        if self.cpu_load > 0.1:
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
            command=f'python -m local.client {self.host} {self.port}',
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
    for cpu_load in CPU_LOADS:
        benchmark = Benchmark(host, port, cpu_load)
        benchmark.run()

        print(benchmark.results)


if __name__ == '__main__':
    main()
