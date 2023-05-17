# Module imports
import pandas                   as pd
import utils.constants          as constants

from flask                      import Flask, render_template, request, redirect
from utils.elo                  import expected_score
from utils.measure              import GapMeasure, ClumpMeasure, SecondMoment, Entropy, LogUtility, ClumpMeasure, WWRunsMeasure, combined_measure_df
from utils.database_service     import NBADatabase
from utils.streak_simulation    import get_elo_table, simulate_season, plot_streaks
from utils.model                import EloModel
from utils.selection_bias       import plot_expectation, paper_expectation_plot



# Global Variables
app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Set up database
database_uri = 'postgresql://postgres:admin@localhost/thesis_nba'
database_uri = 'postgresql://pohkbdxjkwmnms:288ae8a77dd3e18169c9fcf455e179425751e1eaf9bc77e95c63b442c48d3bce@ec2-44-214-9-130.compute-1.amazonaws.com:5432/d5imhhjosegjqo'
app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
db = NBADatabase(url = database_uri)



# Routes
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/about/')
def about():
    return render_template('construction.html')


@app.route('/proposal/')
def proposal():
    return app.send_static_file('CPSC_490_Project_Proposal_Final_Advisor.pdf')


@app.route('/midterm/')
def midterm():
    return app.send_static_file('CPSC 490 Midterm Presentation.pdf')


@app.route('/math/')
def math():
    return app.send_static_file('Streaky Good Models Math Presentation.pdf')


@app.route('/repository/')
def repository():
    return redirect('https://github.com/HarryJain/thesis')


@app.route('/background/')
def background():
    return render_template('construction.html')


@app.route('/hot-hand/', methods = ['GET', 'POST'])
def hot_hand():
    if request.method == 'POST':
        paper_plot_data = paper_expectation_plot()

        k = int(request.form.get('k_num'))
        p = float(request.form.get('p_num'))
        user_plot_data = plot_expectation(k = k, p = p, return_fig = True)
        
        return render_template('hot_hand.html', k_value = k, p_value = p, paper_plot_data = paper_plot_data, user_plot_data = user_plot_data)
    else:
        paper_plot_data = paper_expectation_plot()
        return render_template('hot_hand.html', k_value = 1, p_value = 0.5, paper_plot_data = paper_plot_data)


@app.route('/streak-measures/')
def streak_measures():
    measure_df = combined_measure_df()
    return render_template('streak_measures.html', measure_df = measure_df)


@app.route('/simulations/')
def simulations():
    return render_template('construction.html')


@app.route('/measure-simulations/', methods = ['GET', 'POST'])
def measure_simulations():
    if request.method == 'POST':
        season_df = db.get_season_games(season = '2021-2022')
        print(season_df)

        team = request.form.get('team')
        print(team)

        measure = request.form.get('measure')
        print(measure)

        measure = WWRunsMeasure(season_df, name = 'Runs Test') if measure == 'Runs Test' else GapMeasure(season_df, name = 'Gap Measure') if measure == 'Gap Measure' else ClumpMeasure(season_df, name = 'Clump Measure (Wins)') if measure == 'Clump Measure (Wins)' else SecondMoment(season_df, name = 'Second Moment') if measure == 'Second Moment' else Entropy(season_df, name = 'Entropy') if measure == 'Entropy' else LogUtility(season_df, name = 'Log Utility') if measure == 'Log Utility' else None
        
        simulated_measure_dfs, p_value, plot_data = measure.monte_carlo_plot(team)
        print(p_value)

        return render_template('simulate_measure.html', teams = constants.TLAS, measures = constants.MEASURES, selected_team = team, selected_measure = measure, plotdata = plot_data)
    else:
        return render_template('simulate_measure.html', teams = constants.TLAS, measures = constants.MEASURES, selected_team = None, selected_measure = None)


@app.route('/streak-simulations/')
def streak_simulations():
    return render_template('construction.html')


@app.route('/predictions/')
def predictions():
    return render_template('construction.html')


@app.route('/game_predictions/')
def game_predictions():
    return render_template('construction.html')


@app.route('/conclusions/')
def conclusions():
    return render_template('conclusions.html')


@app.route('/games/')
def games():
    games_df = db.get_today_games()
    print(games_df)

    elo_model = EloModel()
    elo_model.execute_model()

    games_df['Home Win %'] = games_df.apply(lambda row: expected_score(elo_model.ratings[row['Home Team']], elo_model.ratings[row['Away Team']]), axis = 1)

    return render_template('games.html', games = games_df, elo_ratings = elo_model.ratings, colors = constants.COLORS)


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
        team_df = db.get_team_games(team, win = 'Team Win')

        # Simulate and plot the win streaks
        fig, ax, simulated_avg = simulate_season(team, elo_ratings, team_df[['Game ID', 'Home Team', 'Away Team']])
        plotdata = plot_streaks(team, team_df[['Game ID', 'Home T', 'Away T', 'Team Win']], simulated_avg, fig, ax)

        return render_template('teams.html', teams = constants.TLAS, selected = team, plotdata = plotdata)
    else:
        return render_template('teams.html', teams = constants.TLAS, selected = None)
