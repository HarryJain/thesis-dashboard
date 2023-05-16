import base64
from io import BytesIO
import pandas               as pd
import numpy                as np
import os
import utils.constants      as constants

from flask                  import Flask, render_template, request
from requests               import get
from bs4                    import BeautifulSoup, Comment
from pandas                 import DataFrame
from sqlalchemy             import create_engine
from random                 import random
from matplotlib.lines       import Line2D
from matplotlib.figure      import Figure
from datetime               import datetime
from utils.elo              import calculate_elo_ratings, get_season_games, expected_score
from utils.gap_measure      import calculate_gap_measures


# Global Variables
TEAMS = {'ATL': 'Hawks', 'BOS': 'Celtics', 'BRK': 'Nets', 'CHO': 'Hornets', 'CHI': 'Bulls', 'CLE': 'Cavaliers', 'DAL': 'Mavericks', 'DEN': 'Nuggets', 'DET': 'Pistons', 'GSW': 'Warriors', 'HOU': 'Rockets', 'IND': 'Pacers', 'LAC': 'Clippers', 'LAL': 'Lakers', 'MEM': 'Grizzlies', 'MIA': 'Heat', 'MIL': 'Bucks', 'MIN': 'Timberwolves', 'NOP': 'Pelicans', 'NYK': 'Knicks', 'OKC': 'Thunder', 'ORL': 'Magic', 'PHI': '76ers', 'PHO': 'Suns', 'POR': 'Trail Blazers', 'SAC': 'Kings', 'SAS': 'Spurs', 'TOR': 'Raptors', 'UTA': 'Jazz', 'WAS': 'Wizards'}

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
#database_uri = 'postgresql://snaqiuwvjxmcnv:87357d96f1e3322290c07dd3a0ac6b219655a3b9770641fcc7a7ce96694aff3d@ec2-44-199-22-207.compute-1.amazonaws.com:5432/d7npoqqmolsofp'
database_uri = 'postgresql://pohkbdxjkwmnms:288ae8a77dd3e18169c9fcf455e179425751e1eaf9bc77e95c63b442c48d3bce@ec2-44-214-9-130.compute-1.amazonaws.com:5432/d5imhhjosegjqo'
app.config['SQLALCHEMY_DATABASE_URI'] = database_uri

#engine = create_engine('postgresql://postgres:admin@localhost/thesis_nba')
#engine = create_engine('postgres://snaqiuwvjxmcnv:87357d96f1e3322290c07dd3a0ac6b219655a3b9770641fcc7a7ce96694aff3d@ec2-44-199-22-207.compute-1.amazonaws.com:5432/d7npoqqmolsofp')
engine = create_engine(database_uri)
#engine = create_engine(database_uri)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/about/')
def about():
    return render_template('construction.html')


@app.route('/proposal/')
def proposal():
    #return render_template('proposal.html')
    return app.send_static_file('CPSC_490_Project_Proposal_Final_Advisor.pdf')


@app.route('/games/')
def games():
    date_str = datetime.now().strftime('%Y-%m-%d')
    games_df = pd.read_sql(f"""SELECT * FROM schedule WHERE "Date" = '{date_str} 00:00:00'""", engine)
    print(games_df)

    results_df = get_season_games(engine)
    elo_df, elo_ratings = calculate_elo_ratings(engine, results_df)

    games_df['Home Win %'] = games_df.apply(lambda row: expected_score(elo_ratings[row['Home Team']], elo_ratings[row['Away Team']]), axis = 1)

    return render_template('games.html', games = games_df, elo_ratings = elo_ratings, colors = constants.COLORS)


@app.route('/stats/')
def stats():
    df = calculate_gap_measures(engine, type = 'df')
    print(df)
    return render_template('statistics.html', statistics = df)


@app.route('/teams/', methods = ['GET', 'POST'])
def teams():
    ''' Scrapes the end of season Elo ratings from FiveThirtyEight
        and plots the actual streaks compared to simulated streaks for the
        given team
    '''
    if request.method == 'POST':
        team = request.form.get('team')
        print(team)

        # Scrape Elo ratings and store them as a DataFrame
        elo_ratings = get_elo_table()
        print(elo_ratings)

        # Get the team data from the database and create a boolean column for wins
        team_df = get_team_games(engine, team)
        team_df['Win'] = team_df.apply(lambda row: win(team, row), axis = 1)

        # Simulate and plot the win streaks
        fig, ax, simulated_avg = simulate_season(team, elo_ratings, team_df[['Game ID', 'Home Team', 'Away Team']])
        plotdata = plot_streaks(team, team_df[['Game ID', 'Home T', 'Away T', 'Win']], simulated_avg, fig, ax)

        # # Simulate and plot the loss streaks
        # simulated_avg = simulate_season(team, elo_ratings, team_df[['Game ID', 'Home Team', 'Away Team']], False)
        # plot_streaks(team, team_df[['Game ID', 'Home T', 'Away T', 'Win']], simulated_avg, False)
        #return f"<img src='data:image/png;base64,{plotdata}'/>"
        return render_template('teams.html', teams = TEAMS, selected = team, plotdata = plotdata)
    else:
        return render_template('teams.html', teams = TEAMS, selected = None)


# @app.route('/teams/')
# @app.route('/teams/<team>')
# def teams(team = None):
#     if team:
#         ''' Scrapes the end of season Elo ratings from FiveThirtyEight
#             and plots the actual streaks compared to simulated streaks for the
#             given team
#         '''
#         print(team)

#         # Scrape Elo ratings and store them as a DataFrame
#         elo_ratings = get_elo_table()
#         print(elo_ratings)

#         # Get the team data from the database and create a boolean column for wins
#         team_df = get_team_games(engine, team)
#         team_df['Win'] = team_df.apply(lambda row: win(team, row), axis = 1)

#         # Simulate and plot the win streaks
#         fig, ax, simulated_avg = simulate_season(team, elo_ratings, team_df[['Game ID', 'Home Team', 'Away Team']])
#         plotdata = plot_streaks(team, team_df[['Game ID', 'Home T', 'Away T', 'Win']], simulated_avg, fig, ax)

#         # # Simulate and plot the loss streaks
#         # simulated_avg = simulate_season(team, elo_ratings, team_df[['Game ID', 'Home Team', 'Away Team']], False)
#         # plot_streaks(team, team_df[['Game ID', 'Home T', 'Away T', 'Win']], simulated_avg, False)
#         #return f"<img src='data:image/png;base64,{plotdata}'/>"
#         return render_template('team.html', plotdata = plotdata)
#     else:
#         return render_template('construction.html')

def get_soup(url):
    ''' Return the BeautifulSoup object for the given URL by making a get
            request for data from the URL, checking for a valid response
            (exiting if there are errors), and returning parsed data from
            that response

        url -- a string representing the URL to ping and parse
    '''
    print(url)
    response = get(url)
    if not 200 <= response.status_code < 300:
        exit('Invalid URL')
    return BeautifulSoup(response.content, 'html.parser')


def parse_row(row):
    ''' Take in a row of an HTML table and return a list of elements from
            the row

        row -- a BeautifulSoup tag representing the row to parse
    '''
    elements = [ x.string if x.find('a') == None else x.find('a').string for x in row.find_all('td') ]
    return elements


def table_to_df(table, overheader = 0, set_index = False):
    ''' Take in an HTML table and return a DataFrame containing the data in
            that table, accounting for a potential overheader

        table -- a BeautifulSoup tag representing the table to parse
        overheader -- an integer that denotes the row containing the headers
            for each column (effectively counting "overheaders")
    '''
    # Get the column names from the table headers and parse them
    cols = table.find('thead').find_all('tr')[overheader].find_all('th')
    cols = [ col.string if col.string != None else '' for col in cols ]

    # Parse out the actual rows of the table and their potential labels
    data_table = table.find('tbody')
    rows = data_table.find_all('tr')
    row_labels = [ row.find('th').string for row in rows if row.find('th') != None ]

    # Parse rows and filter out empty rows
    parsed_rows = [ parse_row(row) for row in rows ]
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


def get_elo_table(year = 2022):
    ''' Returns a DataFrame of FiveThirtyEight's end of season NBA Elo ratings
            for the given year, containing columns for the current rating and
            their full-strength rating and indexed by team name
        
        year -- integer year for the ratings, with a default of 2022
    '''
    # Get the HTML from FiveThirtyEight
    soup = get_soup(f'https://projects.fivethirtyeight.com/{year}-nba-predictions/')

    # Create a table with the current and full-strength ratings for each team
    #   and return it
    elo_df = table_to_df(soup.find('table'), overheader = 3)
    elo_df = elo_df[['Current rating', 'Full-strength rating', 'Team']].set_index('Team')
    return elo_df


def connect_to_db(url = 'postgresql://postgres:admin@localhost/thesis_nba'):
    ''' Returns a SQLAlchemy DB engine for the given URL, defaulting to the
            local host
    '''
    engine = create_engine(url)
    return engine


def get_team_games(engine, team, season = '2021-22'):
    ''' Returns a DataFrame of all the games for the given team and season
            with all the columns from the database
    '''
    team_df = pd.read_sql(f"""SELECT * FROM boxscores WHERE ("Home Team" = '{team}' OR "Away Team" = '{team}') AND "Season" = '{season}'""", engine)
    return team_df
    
    
def win(team, row):
    ''' Returns whether the given team was the winner of the game represented
            by the given row, accounting for home and away games
    '''
    if team in row['Game ID']:
        return int(row['Home T']) > int(row['Away T'])
    else:
        return int(row['Away T']) > int(row['Home T'])
    
    
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
    streaks = result_df['Win'].diff().ne(0).cumsum()

    # Group the rows by the streak and calculate a length column
    streak_df = result_df[['Game ID', 'Win']].groupby(streaks).agg(list)
    streak_df['Length'] = streak_df.apply(lambda row: len(row['Win']) if win in row['Win'] else None, axis = 1)

    # Calculate the average length of the streaks and distribution of streaks
    #   of each length
    avg_len = streak_df['Length'].mean()
    counts = streak_df.groupby('Length').count()['Win']
    
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
        elo_rating = int(elo_ratings.loc[TEAMS[team], 'Current rating'])
        
        # Loop through each game from the team_df table and simulate it
        #   randomly according to the Elo rating probability
        for ind in team_df.index:
            opponent = team_df.loc[ind, 'Away Team'] if team_df.loc[ind, 'Home Team'] == team else team_df.loc[ind, 'Home Team']
            opponent_rating = int(elo_ratings.loc[TEAMS[opponent], 'Current rating'])
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

