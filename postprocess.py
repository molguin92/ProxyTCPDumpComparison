from typing import Dict

import matplotlib.pyplot as plt
import pandas as pd


def data_to_df(results: Dict) -> pd.DataFrame:
    rows = []
    for cpu_load, l_results in results.items():
        for bench_type, bench_results in l_results.items():
            for i, sample in enumerate(bench_results):
                rows.append((bench_type, cpu_load, i, sample))

    df = pd.DataFrame(rows, columns=['benchmark', 'cpu_load',
                                     'sample_idx', 'rtt'])
    return df.set_index(['benchmark', 'cpu_load', 'sample_idx'])


def plot_results(results: pd.DataFrame) -> None:
    data = results.reset_index()

    fig, ax = plt.subplots()

    base = data[data['benchmark'] == 'base'].groupby(['cpu_load'])['rtt']
    proxy = data[data['benchmark'] == 'proxy'].groupby(['cpu_load'])['rtt']
    tcpdump = data[data['benchmark'] == 'tcpdump'].groupby(['cpu_load'])['rtt']

    cpu_loads = data['cpu_load'].unique() * 100.0

    ax.errorbar(
        cpu_loads,
        base.mean(),
        yerr=base.std(),
        marker='o',
        label='Base',
        capsize=5
    )
    ax.errorbar(
        cpu_loads,
        proxy.mean(),
        yerr=proxy.std(),
        marker='v',
        label='Proxy',
        capsize=10
    )
    ax.errorbar(
        cpu_loads,
        tcpdump.mean(),
        yerr=tcpdump.std(),
        marker='^',
        label='TCPDump',
        capsize=15
    )
    ax.set_xlabel('Additional CPU Load [%]')
    ax.set_ylabel('Total Round-trip Time [ms]')
    ax.set_ylim([20, 35])
    ax.legend()

    fig.savefig('results.png')
    plt.show()


if __name__ == '__main__':
    data = pd.read_csv('./results.csv')
    data = data.set_index(['benchmark', 'cpu_load', 'sample_idx'])
    plot_results(data)
