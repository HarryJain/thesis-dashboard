# Module imports
import  base64
import  numpy                   as np

import  utils.constants         as constants

from    matplotlib.lines        import Line2D
from    matplotlib.figure       import Figure
from    io                      import BytesIO
from    random                  import random
from    pandas                  import DataFrame

from    utils.database_service  import NBADatabase
from    utils.scraper           import Scraper



def get_elo_table(year = '2022-2023'):
    ''' Returns a DataFrame of FiveThirtyEight's end of season NBA Elo ratings
            for the given year, containing columns for the current rating and
            their full-strength rating and indexed by team name
        
        year -- string year for the ratings, with a default of 2022-2023
    '''
    # Declare a web scraper to get the HTML from FiveThirtyEight
    scraper = Scraper()

    # Get the HTML from FiveThirtyEight
    scraper.get_soup(f'https://projects.fivethirtyeight.com/{year.split("-")[-1]}-nba-predictions/')

    # Create a table with the current and full-strength ratings for each team
    #   and return it
    elo_df = scraper.table_to_df(scraper.soup.find('table'), overheader = 3, allow_class = True)
    elo_df = elo_df[['Current rating', 'Full-strength rating', 'Team']].set_index('Team')
    return elo_df
    
    
def plot_streaks(team, result_df, simulated_avg, fig, ax, win = True):
    ''' Outputs a bar plot using Matplotlib showing the distribution of streak
            lengths, by default win streaks
        
        team -- three letter string for the team whose streaks you want
            to plot
        result_df -- a DataFrame containing game results containing three
            columns: game ID, home total, away total, and a boolean win column
        simulated_avg -- the average streak length from the simulations of the
            given team's season
        win -- a boolean signifying whether to plot win (default) or loss
            streaks
    '''
    # Calculate the difference between the win/loss column, e.g. end of
    #   streaks, and count the non-zero differences, which effectively
    #   labels streaks 1,...,n
    streaks = result_df['Team Win'].diff().ne(0).cumsum()

    # Group the rows by the streak and calculate a length column
    streak_df = result_df[['Game ID', 'Team Win']].groupby(streaks).agg(list)
    streak_df['Length'] = streak_df.apply(lambda row: len(row['Team Win']) if win in row['Team Win'] else None, axis = 1)

    # Calculate the average length of the streaks and distribution of streaks
    #   of each length
    avg_len = streak_df['Length'].mean()
    counts = streak_df.groupby('Length').count()['Team Win']
    
    # Plot the distribution of streak lengths
    ax.bar(counts.index, counts, color = constants.COLORS[team][0], align = 'edge', width = -0.4)
    ax.set_xlabel('Length')
    ax.set_ylabel('Frequency')
    ax.set_title(f'Distribution of {"Win" if win else "Loss"} Streaks for {team}')
    if ax.get_xticks()[-1] < int(max(counts.index)) + 1:
        ax.set_xticks(np.arange(int(max(counts.index)) + 1))
        ax.set_xticklabels(np.arange(int(max(counts.index)) + 1))
    legend_elements = [Line2D([0], [0], marker = 'o', color='w', markerfacecolor = constants.COLORS[team][0], markersize = 5, label = f'AVG Length: {round(avg_len, 3)}'),
                       Line2D([0], [0], marker = 'o', color='w', markerfacecolor = constants.COLORS[team][1], markersize = 5, label = f'Simulated AVG Length: {round(simulated_avg, 3)}')]
    ax.legend(handles = legend_elements)

    # Save the plot to a temporary buffer
    buf = BytesIO()
    fig.savefig(buf, format = 'png')

    # Encode the result to embed in HTML
    plot_data = base64.b64encode(buf.getbuffer()).decode('ascii')
    return plot_data
    

def simulate_season(team, elo_ratings, team_df, win = True):
    ''' Simulate the season in documented in team_df for a given team based
            on the assumption of constant Elo ratings according to elo_ratings,
            plot the distribution of streak lengths, and return the average
            streak length

        team -- three letter string for the team whose streaks you want
            to simulate
        elo_ratings -- a DataFrame containing the 
        team_df -- a DataFrame containing game results containing three
            columns: game ID, home total, away total, and a boolean win column
        simulated_avg -- the average streak length from the simulations of the
            given team's season
        win -- a boolean signifying whether to plot win (default) or loss
            streaks
    '''
    # Simulate sim_count seasons and store the results in the counts_list
    #   list of DataFrames
    sim_count = 100
    counts_list = []
    for i in range(sim_count):
        # Get the end of season Elo rating for the given team
        elo_rating = int(elo_ratings.loc[constants.TEAMS[team], 'Current rating'])
        
        # Loop through each game from the team_df table and simulate it
        #   randomly according to the Elo rating probability
        for ind in team_df.index:
            opponent = team_df.loc[ind, 'Away Team'] if team_df.loc[ind, 'Home Team'] == team else team_df.loc[ind, 'Home Team']
            opponent_rating = int(elo_ratings.loc[constants.TEAMS[opponent], 'Current rating'])
            expected = 1 / (1 + 10 ** ((opponent_rating - elo_rating) / 400))
            team_df.loc[ind, f'Trial {i}'] = True if random() < expected else False
       
        # Calculate the difference between the win/loss column, e.g. end of
        #   streaks, and count the non-zero differences, which effectively
        #   labels streaks 1,...,n
        streaks = team_df[f'Trial {i}'].diff().ne(0).cumsum()

        # Group the rows by the streak and calculate a length column
        streak_df = team_df[['Game ID', f'Trial {i}']].groupby(streaks).agg(list)
        streak_df['Length'] = streak_df.apply(lambda row: len(row[f'Trial {i}']) if win in row[f'Trial {i}'] else None, axis = 1)
        
        counts = streak_df.groupby('Length').count()[f'Trial {i}']
        counts_list.append(counts)
    # Create a composite DataFrame with the rows being each trial of the
    #   simulation and the columns representing 
    counts_df = DataFrame(counts_list).fillna(0)
    print(counts_df)

    # Average the counts of each streak length across the trials
    counts_df = counts_df.mean(axis = 0).sort_index()
    print(counts_df)
    
    # Plot the distribution of these average streak length counts
    fig = Figure()
    ax = fig.subplots()
    ax.bar(counts_df.index, counts_df, color = constants.COLORS[team][1], align = 'edge', width = 0.4)
    ax.set_xticks(np.arange(int(max(counts_df.index)) + 1))
    ax.set_xticklabels(np.arange(int(max(counts_df.index)) + 1))
    
    # Return the average streak length
    return fig, ax, sum([ ind * counts_df[ind] for ind in counts_df.index ]) / sum(counts_df)


def main():
    # Create a database object
    db = NBADatabase('postgresql://pohkbdxjkwmnms:288ae8a77dd3e18169c9fcf455e179425751e1eaf9bc77e95c63b442c48d3bce@ec2-44-214-9-130.compute-1.amazonaws.com:5432/d5imhhjosegjqo')

    # Set the team and year
    team = 'PHO'
    year = '2021-2022'

    # Scrape Elo ratings and store them as a DataFrame
    elo_ratings = get_elo_table(year)
    print(elo_ratings)

    # Get the team data from the database and create a boolean column for wins
    team_df = db.get_team_games(team, win = 'Team Win', season = year)
    print(team_df)

    # Simulate and plot the win streaks
    fig, ax, simulated_avg = simulate_season(team, elo_ratings, team_df[['Game ID', 'Home Team', 'Away Team']])
    plotdata = plot_streaks(team, team_df[['Game ID', 'Home T', 'Away T', 'Team Win']], simulated_avg, fig, ax)
    fig.savefig("test.png")



# Run the main function when the module is executed in the top-level code
#   environment, e.g. when executed from the CLI
if __name__ == "__main__":
    main()
