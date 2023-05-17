# Module imports
import  pandas                  as pd

import  utils.constants         as constants

from    requests                import get
from    time                    import sleep
from    bs4                     import BeautifulSoup, Comment
from    pandas                  import DataFrame
from    datetime                import datetime, timedelta, date
from    unidecode               import unidecode

from    utils.database_service  import NBADatabase



class Scraper:
    ''' A class to scrape data from the web using BeautifulSoup
    '''
    def __init__(self):
        ''' Initializes the Scraper object with the given URL
        '''
        self.soup = None


    def get_soup(self, url, sleep_time = 3, in_place = False):
        ''' Obtain the BeautifulSoup object for the given URL by making a get
                request for data from the URL, checking for a valid response
                (exiting if there are errors), and setting the soup instance
                variable to the parsed data from that response

            url -- a string representing the URL to ping and parse
            sleep_time -- an integer representing the number of seconds to wait
                between requests
            in_place -- a boolean representing whether to return the soup
                (False) or to set the soup instance variable to the soup
                (True, default)
        '''
        print(url)
        response = get(url)
        if not 200 <= response.status_code < 300:
            exit(f'Error: {response}')
        sleep(sleep_time)
        self.soup = BeautifulSoup(response.content, 'html.parser')
        if in_place:
            return self.soup
    

    def parse_row(self, row):
        ''' Take in a row of an HTML table and return a list of elements from
                the row

            row -- a BeautifulSoup tag representing the row to parse
        '''
        elements = [ x.string if x.find('a') == None else x.find('a').string for x in row.find_all('td') ]
        return elements


    def table_to_df(self, table, overheader = 0, set_index = False, allow_class = False):
        ''' Take in an HTML table and return a DataFrame containing the data in
                that table, accounting for a potential overheader

            table -- a BeautifulSoup tag representing the table to parse
            overheader -- an integer that denotes the row containing the headers
                for each column (effectively counting "overheaders")
            set_index -- a boolean representing whether to set the index of the
                DataFrame to the first column (default False)
            allow_no_class -- a boolean representing whether to allow rows with
                a class to be parsed (default False)
        '''
        # Get the column names from the table headers and parse them
        cols = table.find('thead').find_all('tr')[overheader].find_all('th')
        cols = [ col.string if col.string != None else '' for col in cols ]

        # Parse out the actual rows of the table and their potential labels
        data_table = table.find('tbody')
        rows = data_table.find_all('tr', class_ = None) if not allow_class else data_table.find_all('tr')
        row_labels = [ row.find('th').string for row in rows if row.find('th') != None ]

        # Parse rows and filter out empty rows
        parsed_rows = [ self.parse_row(row) for row in rows ]
        parsed_rows = [ row for row in parsed_rows if row != [] ]

        # Create a DataFrame from these parsed rows, labels, and columns
        df = DataFrame(parsed_rows)

        # Insert row labels as the first column if they exist
        if len(row_labels) != 0:
            df.insert(0, '', row_labels)
        df.columns = cols
        
        # Set the index of the table if desired
        if set_index:
            df = df.set_index(cols[0])

        # Return the newly created DataFrame
        return df
    

    def push_df_to_db(self, df, table_name, if_exists = 'replace'):
        ''' Push the given DataFrame to the database

            df -- a DataFrame to push to the database
            table_name -- a string representing the name of the table to push
                the DataFrame to
            if_exists -- a string representing the behavior to take if the
                table already exists in the database
        '''
        self.database_service.update_table(df, table_name, if_exists)
    


class BRScraper(Scraper):
    ''' A class to scrape data from basketball-reference.com using BeautifulSoup
            inheriting from the base Scraper class
    '''
    def __init__(self, database_service):
        ''' Initializes the BRScraper object with the given URL
        '''
        super().__init__()
        self.database_service = database_service


    def get_boxscores_url_from_date(self, game_date):
        ''' Returns the URL string for the Basketball Reference NBA boxscores page
                on the given date
            
            game_date -- a Python date object including the year, month, and day
        '''
        return f'\n{constants.BR_PREFIX}/boxscores/?month={game_date.month}&day={game_date.day}&year={game_date.year}'


    def get_game_url_from_id(self, game_id):
        ''' Returns the URL string for the Basketball Reference NBA boxscore for
                the given game ID
            
            game_id -- a Basketball Reference game ID of the form YYYYMMDD0HTM
        '''
        return f'{constants.BR_PREFIX}/boxscores/{game_id}.html'


    def get_player_game_stats(self, row):
        ''' Get the player stats for the current game (stored in self.soup) and
                return them as a DataFrame

            row -- a dictionary representing a game from the boxscores DataFrame
                containing the game ID, the home and away teams, and other
                information
        '''
        # List of the different types of statistics tables to parse
        table_types = ['game-basic', 'game-advanced', 'q1-basic', 'q2-basic', 'h1-basic', 'q3-basic', 'q4-basic', 'h2-basic']
        
        # Initialize lists to hold the home and away team's stats in dataframes
        #   for each table
        home_dfs = []
        away_dfs = []

        # Iterate through each table type and parse the data into a DataFrame
        #   for each team
        for table_type in table_types:
            # Find the table for the home and away team, skipping if either
            #  table is not found 
            home = self.soup.find('table', {'id': f'box-{row["Home Team"]}-{table_type}'})
            away = self.soup.find('table', {'id': f'box-{row["Away Team"]}-{table_type}'})
            if home == None or away == None:
                return
            
            # Parse the tables into home and away DataFrames, renaming the
            #   'Starters' column to 'Name' for 'game-basic' tables and removing
            #   the it for the other tables
            home_df = self.table_to_df(home, overheader = 1)
            away_df = self.table_to_df(away, overheader = 1)
            if table_type == 'game-basic':
                home_df = home_df.rename(columns = {'Starters': 'Name'})
                away_df = away_df.rename(columns = {'Starters': 'Name'})
            else:
                home_df = home_df.drop('Starters', axis = 1)
                away_df = away_df.drop('Starters', axis = 1)

            # Add the player IDs to the DataFrames
            if table_type == 'game-basic':
                home_player_ids = [ player['href'].split('/')[-1].split('.')[0] for player in home.find_all('a') ]
                home_df.insert(0, 'Player ID', home_player_ids)
                away_player_ids = [ player['href'].split('/')[-1].split('.')[0] for player in away.find_all('a') ]
                away_df.insert(0, 'Player ID', away_player_ids)

            # Filter out the duplicate MP column for the advanced stats table
            #   and add the table type to the column names for the other stats
            if table_type == 'game-advanced':
                home_df = home_df.drop('MP', axis = 1)
                away_df = away_df.drop('MP', axis = 1)
            elif not 'game' in table_type:
                home_df.columns = [ table_type.split('-')[0].upper() + ' ' + col for col in home_df.columns ]
                away_df.columns = [ table_type.split('-')[0].upper() + ' ' + col for col in away_df.columns ]

            # Add the DataFrames to the lists
            home_dfs.append(home_df)
            away_dfs.append(away_df)
                
        # Concatenate the DataFrames of each statistic type into one DataFrame
        #   for each team
        home_combined_df = pd.concat(home_dfs, axis = 1)
        away_combined_df = pd.concat(away_dfs, axis = 1)
        
        # Combine the home and away DataFrames into one DataFrame and return it
        combined = pd.concat([home_combined_df, away_combined_df])
        combined.insert(0, 'Game ID', row['Game ID'])
        return combined


    def get_game_row(self, game_id, game_date):
        ''' Returns a dictionary of team boxscore data and DataFrame of player
                statistics for the given game_id
            
            game_id -- a Basketball Reference game ID of the form YYYYMMDD0HTM
            game_date -- a Python date object including the year, month, and day
        '''
        # Get the HTML data for the game's boxscore page
        game_url = self.get_game_url_from_id(game_id)
        self.get_soup(game_url)
        
        # Get the line score and four factors tables as DataFrames
        line_score = BeautifulSoup(self.soup.find('div', {'id': 'all_line_score'}).find(string = lambda text: isinstance(text, Comment)), 'html.parser').find('table')
        line_score = self.table_to_df(line_score, 1, True)
        four_factors = BeautifulSoup(self.soup.find('div', {'id': 'all_four_factors'}).find(string = lambda text: isinstance(text, Comment)), 'html.parser').find('table')
        four_factors = self.table_to_df(four_factors, 1, True)
        
        # Concatenate the tables
        df = pd.concat([line_score, four_factors], axis = 1)
        
        # Convert the concatenated DataFrame to a single dictionary "row" with home and away data
        row = {'Game ID': game_id, 'Date': game_date, 'Home Team': df.index[1], 'Away Team': df.index[0]}
        for col in df.columns:
            row[f'Home {col}'] = df[col].iloc[1]
            row[f'Away {col}'] = df[col].iloc[0]

        # Get the player stats for the game as a DataFrame
        player_game_stats = self.get_player_game_stats(row)
        
        # Return a row of game data as a dictionary
        return row, player_game_stats


    def get_games_for_date(self, game_date):
        ''' Returns a DataFrame of team boxscore data and a DataFrame of player
                statistics for all games played on the given date

            game_date -- a Python date object including the year, month, and day
        '''
        # Get the HTML data for the date's boxscore page
        date_url = self.get_boxscores_url_from_date(game_date)
        self.get_soup(date_url)

        # Get the game IDs for each game from the "Box Score" links
        game_links = self.soup.find_all('p', {'class': 'links'})
        game_urls = [ game_link.find('a').get('href') for game_link in game_links ]
        game_ids = [ game_url.split('/')[-1].split('.html')[0] for game_url in game_urls ]
        
        # Create lists of game statistic dictionaries and player statistic
        #   DataFrames
        rows = []
        player_dfs = []
        for game_id in game_ids:
            row, player_df = self.get_game_row(game_id, game_date)
            rows.append(row)
            player_dfs.append(player_df)
        
        # Return a DataFrame of the game statistics and a concatenated DataFrame 
        #   of the player statistics
        game_df = DataFrame(rows)
        player_df = pd.concat(player_dfs) if player_dfs else DataFrame()
        
        return game_df, player_df
    

    def get_season_from_date(self, game_date):
        ''' Returns the NBA season and whether it was a playoff game for the 
                given date by going from the earliest possible season to the
                latest based on the year

            game_date -- a Python date object including the year, month, and day
        '''
        if game_date < constants.SEASON_DATES[f'{game_date.year - 1}-{game_date.year % 100}']['playoffs_start']:
            season = f'{game_date.year - 1}-{game_date.year}'
            playoffs = False
        elif game_date.year == 2023 or game_date < constants.SEASON_DATES[f'{game_date.year}-{(game_date.year + 1) % 100}']['reg_start']:
            season = f'{game_date.year - 1}-{game_date.year}'
            playoffs = True
        elif game_date < constants.SEASON_DATES[f'{game_date.year}-{(game_date.year + 1) % 100}']['playoffs_start']:
            season = f'{game_date.year}-{game_date.year + 1}'
            playoffs = False
        else:
            season = f'{game_date.year}-{game_date.year + 1}'
            playoffs = True

        return season, playoffs
    

    def get_games_for_date_range(self, start_date, end_date):
        ''' Returns a DataFrame including a row of data for each game between 
                the given start and end dates, along with a DataFrame of player
                statistics for each game

            start_date -- a Python date object including the year, month, and 
                day
            end_date -- a Python date object including the year, month, and day
        '''
        # Lists of DataFrames of game rows and Dataframes of player statistics
        #   for each date in the range
        game_date_dfs = []
        player_date_dfs = []
        
        # Add all games to the game_date_dfs list
        date_range = pd.date_range(start_date, end_date)
        for game_date in date_range:
            game_df, player_df = self.get_games_for_date(game_date)

            # Add non-empty game DataFrames to the list
            if not game_df.empty:
                # Insert columns for the season and a boolean for whether it is a playoff game
                season, playoffs = self.get_season_from_date(game_date.date())
                game_df.insert(1, 'Season', season)
                game_df.insert(2, 'Playoffs', playoffs)
                game_date_dfs.append(game_df)
            
            # Add non-empty player DataFrames to the list
            if not player_df.empty:
                player_date_dfs.append(player_df)
        
        # Concatenate all DataFrames in the list and return the result
        game_df = pd.concat(game_date_dfs).set_index('Game ID')
        player_df = pd.concat(player_date_dfs, ignore_index = True).set_index(['Game ID', 'Player ID'])
        return game_df, player_df


    def get_games_for_season(self, season):
        ''' Returns a DataFrame including a row of data for each game in the
                given season, along with a corresponding DataFrame of player
                statistics

            season -- a string representing the NBA season to get games for, in the
                form YYYY-YY
        '''
        return self.get_games_for_date_range(constants.SEASON_DATES[season]['reg_start'], constants.SEASON_DATES[season]['finals_end'])
        

    def get_games_for_seasons(self, seasons):
        ''' Returns a DataFrame including a row of data for each game in any season
                from the given list, along with a corresponding DataFrame of player
                statistics

            seasons -- a list of strings representing the NBA seasons to get games
                for, each in the form YYYY-YY
        '''
        # Create lists of DataFrames of game rows and Dataframes of player
        #   statistics for each season
        season_game_dfs = []
        season_player_dfs = []
        for season in seasons:
            season_game_df, season_player_df = self.get_games_for_season(season)
            season_game_dfs.append(season_game_df)
            season_player_dfs.append(season_player_df)
        
        # Concatenate all DataFrames in the list and return the result
        game_df = pd.concat(season_game_dfs)
        player_df = pd.concat(season_player_dfs)
        return game_df, player_df
    

    def update_db_games(self):
        ''' Updates the database with the latest game data from Basketball Reference
        '''
        # Get the latest date in the database
        latest_date = self.database_service.execute_query('''SELECT MAX("Date") FROM boxscores''').iloc[0, 0].date()

        # If the latest date is yesterday, then there is no new data to add
        if latest_date == datetime.today().date() - timedelta(days = 1):
            return

        # Get all the games from the latest date in the database to yesterday
        new_game_df, new_player_df = self.get_games_for_date_range(latest_date + timedelta(days = 1), datetime.today().date() - timedelta(days = 1))        

        # Update the database with the new DataFrames
        self.database_service.update_table('boxscores', new_game_df, if_exists = 'append')
        self.database_service.update_table('player_games', new_player_df, if_exists = 'append')


    def get_month_urls_from_year(self, year):
        ''' Returns a list of URL strings for each month of the Basketball Reference
                schedule for the given year
            
            year -- a season starting year of the form YYYY
        '''
        # Go to the base schedule page for the given year and get a list of a tags
        #   for each month
        self.get_soup(f'{constants.BR_PREFIX}/leagues/NBA_{year}_games.html')
        a_links = self.soup.find('div', class_ = 'filter').find_all('a')
        
        # Return a list of links extracted from the href property
        month_links = [ constants.BR_PREFIX + a['href'] for a in a_links ]
        return month_links
    

    def get_schedule_df(self, year):
        ''' Return a DataFrame containing the schedule for the given year with
                columns: Game ID, Date, Start (ET), Home Team, Away Team
                by combining the tables for each month of the season
        '''
        # Get a list of tables for each month of the given season and combine them
        #   into a single DataFrame
        month_urls = self.get_month_urls_from_year(year)
        month_tables = [ self.table_to_df(self.get_soup(month_url, in_place = True).find('table')) for month_url in month_urls ]
        year_table = pd.concat(month_tables)
        
        # Reformat the table to match the schema of the schedule table
        year_table['Home Team'] = year_table['Home/Neutral'].apply(lambda x: constants.TEAMS[x])
        year_table['Away Team'] = year_table['Visitor/Neutral'].apply(lambda x: constants.TEAMS[x])
        year_table['Date'] = year_table.apply(lambda row: datetime.strptime(row['Date'], '%a, %b %d, %Y'), axis = 1)
        year_table['Game ID'] = year_table.apply(lambda row: f'{datetime.strftime(row["Date"], "%Y%m%d")}0{constants.TEAMS[row["Home/Neutral"]]}', axis = 1)
        year_table = year_table[['Game ID', 'Date', 'Start (ET)', 'Home Team', 'Away Team']].set_index('Game ID')

        # Return the newly created DataFrame
        return year_table
    

    def get_url_from_player_id(self, player_id):
        ''' Returns the URL for the Basketball Reference page for the given 
                player
        '''
        return f'{constants.BR_PREFIX}/{player_id[0]}/{player_id}.html'
    

    def get_player_name_from_id(self, player_id):
        ''' Returns the name of the player with the given player ID

            player_id -- a string representing the player's Basketball
                Reference ID
        '''
        self.get_soup(self.get_url_from_player_id(player_id))
        name = unidecode(self.soup.find('h1', itemprop = 'name').text.strip())
        return name
    

    def get_player_df(self):
        ''' Returns a DataFrame containing a row of identification data for each
                player in the player_games table
        '''
        # Get a DataFrame of all player IDs in the database and add a column
        #   containing the player's name scraped from Basketball Reference
        players = self.database_service.execute_query('''SELECT DISTINCT player_id FROM player_games''')
        players['name'] = players.apply(self.get_player_name_from_id, axis = 1)

        # TODO: Add additional player identification data

        # Return the player DataFrame
        return players
    

    def get_season_url(self, year):
        ''' Returns the URL for the Basketball Reference page for the given 
                season

            year -- a season ending year of the form YYYY
        '''
        return f'{constants.BR_PREFIX}/leagues/NBA_{year}.html'
    

    def get_team_season(self, year):
        ''' Returns a DataFrame containing team data for each team in the given
                season
            
            year -- a season starting year of the form YYYY
        '''
        # Get the URL for the given season and scrape the page
        season_url = self.get_season_url(year)
        self.get_soup(season_url)

        # Get the tables containing the team data and convert them to
        #   DataFrames, then combine them into a single DataFrame
        TABLE_ID, TABLE_OVERHEADER = 0, 1
        desired_tables = [('advanced-team', 1), ('per_game-team', 0), ('per_game-opponent', 0)]
        dfs = []
        for desired_table in desired_tables:
            table = self.soup.find('table', id = desired_table[TABLE_ID])
            df = self.table_to_df(table, set_index = True, overheader = desired_table[TABLE_OVERHEADER]).set_index('Team')
            dfs.append(df)
        season_df = pd.concat(dfs, axis = 1)

        # Drop empty columns and rename duplicated columns to denote that they
        #   are actually defensive statistics
        season_df.drop(columns = [ col for col in season_df.columns if col.strip() == '' ], inplace = True)
        season_df.columns = [ f'Opp {col}' if dup else col for col, dup in zip(season_df.columns, season_df.columns.duplicated()) ]
        
        # TODO: Consider incorporating additional team data tables,
        #   e.g. "Shooting Stats"

        # Convert the table to a DataFrame and return it
        return season_df
    

    def get_team_seasons(self, years):
        ''' Returns a DataFrame containing team data for each team in the given
                seasons
            
            years -- a list of season starting years of the form YYYY
        '''
        # Get the team data for each season and combine them into a single
        #   DataFrame
        season_dfs = [ self.get_team_season(year) for year in years ]
        seasons_df = pd.concat(season_dfs)

        # Return the DataFrame
        return seasons_df



def main():
    ''' Tests the BRScraper class with a default NBADatabase, executing each
            function and printing the results
    '''
    # Create a database and scraper instance
    database = NBADatabase()
    scraper = BRScraper(database)

    # # Scrape boxscores for a specific date range
    # date_range_game_df, date_range_player_df = scraper.get_games_for_date_range(date(2023, 4, 19), date(2023, 4, 20))
    # print(date_range_game_df)
    # print(date_range_player_df)

    # # Update the database with the most recent games
    scraper.update_db_games()

    # Scrape boxscores for the most recent season
    #season_boxscores_df = scraper.get_games_for_seasons(list(constants.SEASON_DATES.keys())[-2:-1])
    #print(season_boxscores_df)

    # Scrape the schedule for the 2023 season
    schedule_df = scraper.get_schedule_df(2023)
    print(schedule_df)
    database.update_table('schedule', schedule_df)

    # Scrape season data for the most recent season
    # season_df = scraper.get_team_season(2023)
    # print(season_df)



# Run the main function when the module is executed in the top-level code
#   environment, e.g. when executed from the CLI
if __name__ == "__main__":
    main()
