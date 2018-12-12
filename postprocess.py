from typing import Dict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def random_sample_means(data: np.array,
                        sample_size: int,
                        num_sample_means: int) -> np.array:
    means = np.empty(num_sample_means)
    for i in range(num_sample_means):
        means[i] = np.random.choice(data, sample_size, replace=False).mean()
    return means


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

    bench_types = ['base', 'proxy', 'tcpdump']
    init_capsize = 5
    markers = ['o', '^', 'v']

    cpu_loads = data['cpu_load'].unique()

    for i, (btype, mrkr) in enumerate(zip(bench_types, markers)):
        rtt_means = np.empty(len(cpu_loads))
        for j, load in enumerate(cpu_loads):
            rtts = data[(data['benchmark'] == btype) &
                        (data['cpu_load'] == load)]['rtt']
            means = random_sample_means(rtts, sample_size=50,
                                        num_sample_means=100)
            rtt_means[j] = np.random.choice(means)

        ax.errorbar(
            cpu_loads * 100.0,
            rtt_means,
            # yerr=rtts.std(),
            marker=mrkr,
            label=btype.upper(),
            capsize=5 + (i * init_capsize)
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
