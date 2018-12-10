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

    ax.errorbar(
        data['cpu_load'].unique(),
        base.mean(),
        yerr=base.std(),
        label='Base',
        capsize=5
    )
    ax.errorbar(
        data['cpu_load'].unique(),
        proxy.mean(),
        yerr=proxy.std(),
        label='Proxy',
        capsize=5
    )
    ax.errorbar(
        data['cpu_load'].unique(),
        tcpdump.mean(),
        yerr=tcpdump.std(),
        label='TCPDump',
        capsize=5
    )
    ax.set_xlabel('Additional CPU Load [%]')
    ax.set_ylabel('Total Round-trip Time [ms]')
    ax.legend()

    plt.show()


if __name__ == '__main__':
    data = pd.read_csv('./results.csv')
    data = data.set_index(['benchmark', 'cpu_load', 'sample_idx'])
    plot_results(data)
