# Module imports
import  pandas                  as pd

import  utils.constants         as constants

from    utils.database_service  import NBADatabase
from    numpy                   import mean

from    utils.selection_bias    import count_distribution, expected_success_proportion



def autocorrelation_dataframe(k = 2):
    db = NBADatabase()
    mean_df = pd.DataFrame(columns = ['Win Streak Mean', 'Overall Mean', 'Difference', 'Expected Streak Mean', 'Difference to Expectation'])

    for TLA in constants.TLAS:
        df = db.get_team_games(TLA, win = 'Team Win')

        candidates = []

        for i in range(k, len(df)):
            if sum(df.iloc[i - k:i]['Team Win']) == k:
                candidates.append(df.iloc[i]['Team Win'])

        # print(f'{TLA}: Win Streak Mean: {mean(candidates)}, Overall Mean: {mean(df["Team Win"])}')

        distributions = count_distribution(len(df['Team Win']), k, mean(df['Team Win']))
        expected_success = expected_success_proportion(distributions[(0, len(df['Team Win']))])

        mean_df.loc[TLA] = [mean(candidates), mean(df['Team Win']), mean(candidates) - mean(df['Team Win']), expected_success, mean(candidates) - expected_success]
    
    mean_df.loc['mean', 'Difference'] = mean(mean_df['Difference'])
    mean_df.loc['mean', 'Difference to Expectation'] = mean(mean_df['Difference to Expectation'])
    return mean_df


def main():
    mean_df = autocorrelation_dataframe(4)
    print(mean_df)



# Run the main function when the module is executed in the top-level code
#   environment, e.g. when executed from the CLI
if __name__ == "__main__":
    main()
