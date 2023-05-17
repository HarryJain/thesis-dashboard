# Module imports
import  base64
import  matplotlib.pyplot   as plt

from    matplotlib.figure   import Figure
from    io                  import BytesIO



# Global variables
COLORS = ['red', 'blue', 'orange', 'gray']



def dict_exponent(d, m_, p_):
    d_ = {}

    for key in d:
        new_key = (key[0] + m_[0], key[1] + m_[1])
        d_[new_key] = d[key] * p_

    return d_



def dict_union(d_1, d_2):
    d_ = {**d_1, **d_2}
    for key, _ in d_.items():
        if key in d_1 and key in d_2:
            d_[key] = d_1[key] + d_2[key]
    return d_



def count_distribution(N, k, p):
    D = {}

    q = 1 - p
    for n in range(N + 1):
        L = min(n, k)
        for l in range(L, -1, -1):
            r = n - l
            if r == 0:
                D[(l, r)] = {(0, 0): 1}
            elif r > 0:
                if l < k:
                    left_D = dict_exponent(D[(0, r - 1)], (0, 0), q)
                    right_D = dict_exponent(D[(l + 1, r - 1)], (0, 0), p)
                elif l == k:
                    left_D = dict_exponent(D[(0, r - 1)], (1, 0), q)
                    right_D = dict_exponent(D[(k, r - 1)], (0, 1), p)
                D[(l, r)] = dict_union(left_D, right_D)
    return D



def expected_success_proportion(distribution):
    D_c = { key: value for key, value in distribution.items() if key != (0, 0) and value > 0 }
    prob_sum = sum(D_c.values())
    D_c = { key: value / prob_sum for key, value in D_c.items() }

    return sum([ (key[1] / (key[0] + key[1])) * value for key, value in D_c.items() ])



def plot_expectation(N = 82, k = 1, p = 0.5, fig = None, ax = None, return_fig = False):
    if return_fig:
        fig = Figure()
        ax = fig.subplots()
        ax.set_xlabel('Number of Games')
        ax.set_ylabel('Expected Proportion')
        ax.set_title(f'Expected Winning Percentage after a Win Streak of Length {k}')
        # ax.text(x = N / 2, y = p - 0.01, s = f'p = {p}', ha = 'center', va = 'center')
        ax.hlines(y = p, xmin = 0, xmax = N, color = 'black', linestyles = "dashed")
    print(p, k)
    distributions = count_distribution(N, k, p)
    ax.plot([ n for n in range(k + 1, N + 1) ], [ expected_success_proportion(distributions[(0, n)]) for n in range(k + 1, N + 1) ], c = COLORS[(k - 1) % len(COLORS)])
    if return_fig:
        # Save the plot to a temporary buffer
        buf = BytesIO()
        fig.savefig(buf, format = 'png')

        # Encode the result to embed in HTML
        plot_data = base64.b64encode(buf.getbuffer()).decode('ascii')
        return plot_data



def paper_expectation_plot():
    fig = Figure()
    ax = fig.subplots()
    N = 82
    for p in [ 0.25, 0.5, 0.75 ]:
        ax.text(x = N / 2, y = p + 0.025, s = f'p = {p}', ha = 'center', va = 'center')
        ax.hlines(y = p, xmin = 0, xmax = N, color = 'black', linestyles = "dashed")
        for k in range(1, 5):
            plot_expectation(N, k, p, fig, ax)
    ax.set_xlabel('Number of Games')
    ax.set_ylabel('Expected Proportion')
    ax.set_title('Expected Winning Percentage after a Win Streak of Length k')
    ax.legend([ f'k = {k}' for k in range(1, 5) ], loc = 'upper right', bbox_to_anchor = (0.95, 0.9))
    ax.set_xlim(0, N)
    ax.set_ylim(0.1, 0.8)

    # Save the plot to a temporary buffer
    buf = BytesIO()
    fig.savefig(buf, format = 'png')

    # Encode the result to embed in HTML
    plot_data = base64.b64encode(buf.getbuffer()).decode('ascii')
    return plot_data



def main():
    paper_expectation_plot()
    


# Run the main function when the module is executed in the top-level code
#   environment, e.g. when executed from the CLI
if __name__ == '__main__':
    exit(main())
