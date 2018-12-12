from typing import Dict

import matplotlib.pyplot as plt
import numpy as np
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

    bench_types = ['base', 'proxy', 'tcpdump']
    init_capsize = 5
    markers = ['o', '^', 'v']

    sample_sz = 1000
    z = 1.96

    cpu_loads = data['cpu_load'].unique()

    # add extra legend
    ax.plot([], [], ' ', label='Errorbars indicate 95% confidence interval.')

    for i, (btype, mrkr) in enumerate(zip(bench_types, markers)):
        rtt_means = np.empty(len(cpu_loads))
        rtt_stds = np.empty(len(cpu_loads))
        conf_intervals = np.empty(len(cpu_loads))
        for j, load in enumerate(cpu_loads):
            sample = np.random.choice(
                data[(data['benchmark'] == btype) &
                     (data['cpu_load'] == load)]['rtt'],
                size=sample_sz, replace=False)
            rtt_means[j] = sample.mean()
            rtt_stds[j] = sample.std()
            conf_intervals[j] = z * (rtt_stds[j] / np.sqrt(sample_sz))

        ax.errorbar(
            cpu_loads * 100.0,
            rtt_means,
            yerr=conf_intervals,
            marker=mrkr,
            label=btype.upper(),
            capsize=5 + (i * init_capsize)
        )

    ax.set_xlabel('Additional CPU Load [%]')
    ax.set_ylabel('Total Round-trip Time [ms]')
    ax.set_ylim([23, 27.5])
    ax.legend()

    fig.savefig('results.png')
    plt.show()


if __name__ == '__main__':
    data = pd.read_csv('./results.csv')
    data = data.set_index(['benchmark', 'cpu_load', 'sample_idx'])
    plot_results(data)
