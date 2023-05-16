# Module imports
import  pandas      as pd

from    sqlalchemy  import create_engine



class DatabaseService:
    ''' A class to connect to a database and run queries, used primarily as a
            parent class for more specific database services
    '''
    def __init__(self, url):
        ''' Initializes the DatabaseService object with the given URL
            and creates a SQLAlchemy DB engine for the given URL
        '''
        self.engine = create_engine(url)


    def execute_query(self, query):
        ''' Executes the given query and returns the result as a DataFrame
                using pd.read_sql
        '''
        return pd.read_sql(query, self.engine)
    

    def get_table(self, table_name, columns = None):
        ''' Returns the table with the given name as a DataFrame using
                pd.read_sql_table

            table_name -- a string representing the name of the table to get
            columns -- a list of strings representing the columns to get,
                defaulting to None (all columns)
        '''
        return pd.read_sql_table(table_name, self.engine, columns = columns)
    

    def update_table(self, table_name, df, if_exists = 'replace'):
        ''' Updates the table with the given name with the given DataFrame
                using pd.to_sql

            table_name -- a string representing the name of the table to update
            df -- a DataFrame representing the data to update the table with
            if_exists -- a string representing the behavior to take if the table
                already exists, defaulting to 'replace' (replace the table)
        '''
        df.to_sql(table_name, self.engine, if_exists = if_exists)



class NBADatabase(DatabaseService):
    ''' A class to connect to the NBA database and run queries with convenient
            methods
    '''
    def __init__(self, url = 'postgresql://postgres:admin@localhost/thesis_nba'):
        ''' Initializes the NBADatabase object, calling the
                parent class's __init__ method with the given URL
        '''
        super().__init__(url)
    

    def team_win(self, team, row):
        ''' Returns whether the given team was the winner of the game represented
                by the given row, accounting for home and away games
            
            team -- a TLA string representing the team to check
            row -- a DataFrame row representing a single game
        '''
        if team in row['Game ID']:
            return int(row['Home T']) > int(row['Away T'])
        else:
            return int(row['Away T']) > int(row['Home T'])


    # def get_team_games(self, team, season = '2021-22', playoffs = False):
    #     ''' Returns a DataFrame of all the games for the given team and season
    #             with all the columns from the database
                
    #         team -- a TLA string representing the team whose data to get
    #         season -- a string representing the season years as YYYY-YY, defaults
    #             to 2021-22
    #         playoffs -- a boolean representing whether to get playoff games or
    #             regular season games, defaulting to regular season (False)
    #     '''
    #     team_df = self.execute_query(f"""SELECT * FROM boxscores WHERE ("Home Team" = '{team}' OR "Away Team" = '{team}') AND "Season" = '{season}' AND "Playoffs" = {playoffs}""")
    #     print(team_df)
    #     team_df['Team Win'] = team_df.apply(lambda row: self.team_win(team, row), axis = 1)
    #     return team_df

    
    def get_team_games(self, team, season = '2021-22', playoffs = False, date = None, win = 'Home Win'):
        ''' Returns a DataFrame of all the games for the given team and season
                with all the columns from the database, marking whether the
                given team won the game
                
            team -- a TLA string representing the team whose data to get
            season -- a string representing the season years as YYYY-YY, defaults
                to 2021-22
            playoffs -- a boolean representing whether to get playoff games or
                regular season games, defaulting to regular season (False)
            date -- a string representing the date to get games up to as YYYY-MM-DD,
                defaulting to None for the whole season
        '''
        date_str = f""" AND "Date" <= '{date}'""" if date else ''
        team_df = self.execute_query(f"""SELECT * FROM boxscores WHERE ("Home Team" = '{team}' OR "Away Team" = '{team}') AND "Season" = '{season}' AND "Playoffs" = {playoffs}{date_str}""")
        if win == 'Home Win':
            team_df['Home Win'] = team_df.apply(lambda row: self.home_win(row), axis = 1)
        elif win == 'Team Win':
            team_df['Team Win'] = team_df.apply(lambda row: self.team_win(team, row), axis = 1)
        return team_df
    

    def home_win(self, row):
        ''' Returns whether the home team was the winner of the game represented
                by the given row
                
            row -- a DataFrame row representing a single game
        '''
        return int(row['Home T']) > int(row['Away T'])


    def get_season_games(self, season = '2021-22', playoffs = False, date = None):
        ''' Returns a DataFrame of all the games for the given season
                with all the columns from the database
            
            season -- a string representing the season years as YYYY-YY, defaults
                to 2021-22
            playoffs -- a boolean representing whether to get playoff games or
                regular season games, defaulting to regular season (False)
            date -- a string representing the date to get games up to as YYYY-MM-DD,
                defaulting to None for the whole season
        '''
        date_str = f""" AND "Date" <= '{date}'""" if date else ''
        season_df = self.execute_query(f"""SELECT * FROM boxscores WHERE "Season" = '{season}' and "Playoffs" = {playoffs}{date_str}""")
        season_df['Home Win'] = season_df.apply(lambda row: self.home_win(row), axis = 1)
        return season_df



def main():
    ''' Creates a DataFrame containing all the boxscore data from the given
            seasons, connects to the database, and writes it to the boxscores
            table
    '''
    database = NBADatabase()
    season_df = database.get_season_games('2021-22')
    print(season_df)

    #database.update_table('boxscores', df)



# Run the main function when the module is executed in the top-level code
#   environment, e.g. when executed from the CLI
if __name__ == "__main__":
    main()
