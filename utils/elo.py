# Module imports
import pandas       as pd

from sqlalchemy     import create_engine
from numpy          import mean

from utils.gap_measure    import calculate_gap_measures


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


def expected_score(R_A, R_B):
    ''' Returns the expected score for a player of rating R_A vs a player of
            rating R_B, using the classic Elo formula with a logistic curve with
            base 10
        R_A -- the previous rating of Player A
        R_B -- the previous rating of Player B
    '''
    return 1 / (1 + 10**((R_B - R_A) / 400))


def update_ratings(R_A, R_B, S_A, S_B, K = 20):
    ''' Updates ratings of players A and B, with ratings R_A and R_B,
            respectively, given scores S_A and S_B and K-factor K
            
        R_A -- the previous rating of Player A
        R_B -- the previous rating of Player B
        S_A -- the actual points scored by Player A (1 for win, 0 otherwise)
        S_B -- the actual points scored by Player B (1 for win, 0 otherwise)
        K -- the K-factor, defaulting to FiveThirtyEight's 20
    '''
    # Calculate the expected scores of players A and B
    E_A = expected_score(R_A, R_B)
    E_B = expected_score(R_B, R_A)

    # Update the scores of players A and B according to expected scores vs. the
    #   actual scores
    R_A += K * (S_A - E_A)
    R_B += K * (S_B - E_B)

    # Return the updated scores
    return R_A, R_B


def get_season_games(engine, season = '2021-22', playoffs = False, date = None):
    ''' Returns a DataFrame of all the games for the given season
            with all the columns from the database
        
        engine -- a SQLAlchemy DB engine to connect to a database
        season -- a string representing the season years as YYYY-YY, defaults
            to 2021-22
        playoffs -- a boolean representing whether to get playoff games or
            regular season games, defaulting to regular season (False)
        date -- a string representing the date to get games up to as YYYY-MM-DD,
            defaulting to None for the whole season
    '''
    date_str = f""" AND "Date" <= '{date}'""" if date else ''
    season_df = pd.read_sql(f"""SELECT * FROM boxscores WHERE "Season" = '{season}' and "Playoffs" = {playoffs}{date_str}""", engine)
    season_df.set_index('Game ID')
    season_df['Winner'] = season_df.apply(lambda row: home_win(row), axis = 1)
    return season_df

    
def home_win(row):
    ''' Returns whether the home team was the winner of the game represented
            by the given row
            
        row -- a DataFrame row representing a single game
    '''
    return int(row['Home T']) > int(row['Away T'])


def update_ratings_for_game(row, ratings, method = 'vanilla', k_factors = None):
    ''' Calculates the new ratings for the home and away teams in the given
            row and returns the updated ratings (which are also changed in the
            ratings dictionary)

        row -- a DataFrame row representing a single game
        ratings -- a dictionary of ratings with (TLA, Elo) (key, value) pairs
            for each team, to be updated with the new ratings
        method -- a string representing the method to use for calculating the
            ratings, defaulting to 'vanilla' for the classic Elo method
        k_factors -- a dictionary of ratings with (TLA, K) (key, value) pairs
            for each team based on the gap measure
    '''
    # Get the updated ratings for the home and away teams
    if method == 'vanilla':
        home_rating, away_rating = update_ratings(ratings[row['Home Team']], ratings[row['Away Team']], row['Winner'], 1 - row['Winner'])
    elif method == 'gap':
        home_rating, away_rating = update_ratings(ratings[row['Home Team']], ratings[row['Away Team']], row['Winner'], 1 - row['Winner'], mean([k_factors[row['Home Team']], k_factors[row['Away Team']]]))
    else:
        raise ValueError('Invalid method')
    
    # Update the ratings dictionary
    ratings[row['Home Team']] = home_rating
    ratings[row['Away Team']] = away_rating
    
    # Return the updated home and away ratings
    return home_rating, away_rating


def calculate_elo_ratings(engine, games_df, method = 'vanilla', return_df = False):
    ''' Returns a dictionary of ratings with (TLA, Elo) (key, value) pairs for
            each team for the given season
        
        engine -- a SQLAlchemy DB engine to connect to a database
        games_df -- a DataFrame of all the games for the period over which
            to calculate the ratings
        method -- a string representing the method to use for calculating the
            ratings, defaulting to 'vanilla' for the classic Elo method
        return_df -- a boolean representing whether to also return the DataFrame
            with the ratings for each game, defaulting to False
    '''
    # Create a dictionary of "current" Elo ratings that starts at 1500 for all
    ratings = { team: 1500 for team in TEAMS.keys() }
    
    # Create a table of Elo ratings for home and away teams for each game/row,
        #   expanding list-like results to columns of a DataFrame, according to
        #   the given method
    if method == 'vanilla':
        games_ratings_df = games_df.apply(lambda row: update_ratings_for_game(row, ratings), axis = 1, result_type ='expand')
    elif method == 'gap':
        # Calculate the gap measures for the 2021-22 season
        gap_dict = calculate_gap_measures(engine)
        games_ratings_df = games_df.apply(lambda row: update_ratings_for_game(row, ratings, method = 'gap', k_factors = gap_dict), axis = 1, result_type ='expand')
    else:
        raise ValueError('Invalid method')

    # Relabel the Elo ratings columns and add them to the games_df
    games_ratings_df.columns = ['Home Elo', 'Away Elo']
    games_df = pd.concat([games_df, games_ratings_df], axis = 1)
    
    # Return the ratings dictionary
    return ratings, games_df if return_df else ratings


def main():
    ''' Connects to the NBA database, gets a DataFrame of games for the
            2021-22 season, and calculates updated Elo ratings after each game
            using the classic Elo method and the k-factors based on the gap,
            storing results for each in the DataFrame and a dictionary, both of
            which are printed out at the end
    '''
    # Connect to the PostgreSQL database
    engine = connect_to_db()

    # Get the games for the 2021-22 season in a DataFrame
    games_df = get_season_games(engine)

    # Calculate the Elo ratings for the 2021-22 season using the classic Elo
    vanilla_ratings, vanilla_df = calculate_elo_ratings(engine, games_df, return_df = True)
    print(vanilla_df)
    print(vanilla_ratings)

    # Calculate the Elo ratings for the 2021-22 season using the k-factors based
    #   on the gap measure
    gap_ratings, gap_df = calculate_elo_ratings(engine, games_df, method = 'gap', return_df = True)
    print(gap_df)
    print(gap_ratings)


# Run the main function when the module is executed in the top-level code
#   environment, e.g. when executed from the CLI
if __name__ == '__main__':
    exit(main())