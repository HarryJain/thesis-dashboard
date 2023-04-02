# Module Imports
import pandas   as pd

from sys            import exit
from sqlalchemy     import create_engine
from numpy          import sqrt, mean, std
from scipy.stats    import norm
from pandas         import DataFrame


# Global Variables
TEAMS = {'ATL': 'Hawks', 'BOS': 'Celtics', 'BRK': 'Nets', 'CHO': 'Hornets', 'CHI': 'Bulls', 'CLE': 'Cavaliers', 'DAL': 'Mavericks', 'DEN': 'Nuggets', 'DET': 'Pistons', 'GSW': 'Warriors', 'HOU': 'Rockets', 'IND': 'Pacers', 'LAC': 'Clippers', 'LAL': 'Lakers', 'MEM': 'Grizzlies', 'MIA': 'Heat', 'MIL': 'Bucks', 'MIN': 'Timberwolves', 'NOP': 'Pelicans', 'NYK': 'Knicks', 'OKC': 'Thunder', 'ORL': 'Magic', 'PHI': '76ers', 'PHO': 'Suns', 'POR': 'Trail Blazers', 'SAC': 'Kings', 'SAS': 'Spurs', 'TOR': 'Raptors', 'UTA': 'Jazz', 'WAS': 'Wizards'}


def connect_to_db(url = 'postgresql://postgres:admin@localhost/thesis_nba'):
    ''' Returns a SQLAlchemy DB engine for the given URL, defaulting to the
            local host
            
        url -- a string URL for the database to connect to, defaults to
            local postgresql database thesis_nba
    '''
    engine = create_engine(url)
    return engine


def get_team_games(engine, team, season = '2021-22', playoffs = False, date = None):
    ''' Returns a DataFrame of all the games for the given team and season
            with all the columns from the database
            
        engine -- a SQLAlchemy DB engine to connect to a database
        team -- a TLA string representing the team whose data to get
        season -- a string representing the season years as YYYY-YY, defaults
            to 2021-22
        playoffs -- a boolean representing whether to get playoff games or
            regular season games, defaulting to regular season (False)
        date -- a string representing the date to get games up to as YYYY-MM-DD,
            defaulting to None for the whole season
    '''
    date_str = f""" AND "Date" <= '{date}'""" if date else ''
    team_df = pd.read_sql(f"""SELECT * FROM boxscores WHERE ("Home Team" = '{team}' OR "Away Team" = '{team}') AND "Season" = '{season}' AND "Playoffs" = {playoffs}{date_str}""", engine)
    return team_df

    
def team_win(team, row):
    ''' Returns whether the given team was the winner of the game represented
            by the given row, accounting for home and away games
        
        team -- a TLA string representing the team to check
        row -- a DataFrame row representing a single game
    '''
    if team in row['Game ID']:
        return int(row['Home T']) > int(row['Away T'])
    else:
        return int(row['Away T']) > int(row['Home T'])

    
def calculate_team_gap_dict(engine, team):
    ''' Returns a dictionary with team name, win, loss, win streak, and 
            loss streak summary statistics

        engine -- a SQLAlchemy DB engine to connect to a database
        team -- a TLA string representing the team whose statistics to calculate
    '''
    # Set up a dictionary for the team row
    team_dict = {'Team': team}
    
    # Get the team data from the database and create a boolean column for wins
    team_df = get_team_games(engine, team_dict['Team'])
    team_df['Win'] = team_df.apply(lambda row: team_win(team_dict['Team'], row), axis = 1)
    
    # Calculate the difference between the win/loss column, e.g. end of
    #   streaks, and count the non-zero differences, which effectively
    #   labels streaks 1,...,n
    streaks = team_df['Win'].diff().ne(0).cumsum()
    
    # Group the rows by the streak and calculate a length column
    streak_df = team_df[['Game ID', 'Win']].groupby(streaks).agg(list)

    # Create lists of all streaks, the lengths of the win streaks, and the
    #   lengths of the loss streaks
    streaks = list(streak_df['Win'])
    win_streaks = [ len(streak) for streak in streaks if streak[0] ]
    loss_streaks = [ len(streak) for streak in streaks if not streak[0] ]
    
    # Make a list of wins and losses from team_df
    results = list(team_df['Win'])
    
    # Calculate win, loss, win streak, and loss streak summary statistics
    team_dict['W'] = sum(results)
    team_dict['L'] = len(results) - team_dict['W']
    team_dict['Pct'] = team_dict['W'] / len(results)
    team_dict['n_ws'] = len(win_streaks)
    team_dict['u_ws'] = mean(win_streaks)
    team_dict['std_ws'] = std(win_streaks)
    team_dict['n_ls'] = len(loss_streaks)
    team_dict['u_ls'] = mean(loss_streaks)
    team_dict['std_ls'] = std(loss_streaks)
    
    # Calculate the gap for the given team
    gap = sqrt(sum( (sum(results[:i + 1]) - i * team_dict['Pct']) ** 2 for i in range(len(results))) )
    team_dict['Gap'] = gap
    
    # Calculate the mean, variance, Z-score, and p-value for the Runs Test
    u_r = (2 * team_dict['W'] * team_dict['L']) / (team_dict['W'] + team_dict['L']) + 1
    o_r = ((u_r - 1) * (u_r - 2)) / (team_dict['W'] + team_dict['L'] - 1)
    team_dict['z'] = (len(streaks) - u_r) / o_r
    team_dict['p'] = norm.sf(abs(team_dict['z'])) * 2
    
    # Print the resulting dictionary for a given team and return it
    return team_dict


def calculate_gap_measures(engine, type = 'dict', season = '2021-22', playoffs = False, date = None):
    ''' Calcualtes the gap statistics for all teams in the given season and
            returns them as a dictionary or DataFrame

        engine -- a SQLAlchemy DB engine to connect to a database
        type -- a string representing the type of output to return, either a
            dictionary or a DataFrame, defaulting to a dictionary
        season -- a string representing the season years as YYYY-YY, defaults
            to 2021-22
        playoffs -- a boolean representing whether to get playoff games or
            regular season games, defaulting to regular season (False)
        date -- a string representing the date to get games up to as YYYY-MM-DD,
            defaulting to None for the whole season
    '''
    # Loop over the teams, calculate their statistics diciontaries, and add them
    #   to the list
    team_dicts = []
    for team in TEAMS.keys():
        team_dicts.append(calculate_team_gap_dict(engine, team))

    # Convert the list of dictionaries into a DataFrame with a row for each team
    gap_df = DataFrame(team_dicts).set_index('Team')

    # Store the gap statistics as a dictionary
    gap_dict = dict(gap_df['Gap'])
    
    # Return the DataFrame or dictionary based on the type argument
    return gap_dict if type == 'dict' else gap_df


def main():
    ''' Connects to the NBA database, calculates the gap statistics for each
            team, and prints them out as a dictionary
    '''
    # Connect to the PostgreSQL database
    engine = connect_to_db()

    # Get the gap statistics as a dictionary and print them
    gap_df = calculate_gap_measures(engine, type = 'df')
    print(gap_df)


# Run the main function when the module is executed in the top-level code
#   environment, e.g. when executed from the CLI
if __name__ == '__main__':
    exit(main())
