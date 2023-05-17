# Module imports
import  pandas              as pd
import  matplotlib.pyplot   as plt
import  seaborn             as sns
import  base64

import  utils.constants     as constants

from    abc                     import ABC, abstractmethod
from    numpy                   import mean, std, sqrt
from    scipy.stats             import norm
from    pandas                  import DataFrame
from    matplotlib.lines        import Line2D
from    matplotlib.figure       import Figure
from    math                    import log
from    io                      import BytesIO

from    utils.database_service  import NBADatabase



class StreakMeasure(ABC):
    # TODO: Add docstrings, comments, and more methods???
    def __init__(self, df, stat_column = 'Home Win', team = None, name = ''):
        self.df = df
        self.stat_column = stat_column
        self.team = team
        self.measure_df = DataFrame()
        self.name = name


    @abstractmethod
    def calculate_measure(self, df = None, update_dfs = False, team = None):
        pass


    def permute_results(self, df = None, stat_column = None):
        ''' Returns a permutation of the statistical results in the given
                column of the given DataFrame as a DataFrame, defaulting to
                the entire df instance variable

            df -- a DataFrame representing the subset of the data to
                permute, defaulting to None (the entire df instance variable)
            stat_column -- a string representing the column of the given df
                to permute, defaulting to None, which uses the stat_column
                instance variable instead
        '''
        # Default to the df and stat_column instance variables
        if df is None:
            df = self.df
        if not stat_column:
            stat_column = self.stat_column

        # Return a permutation of the given column
        permuted_df = df[[stat_column]].sample(frac = 1).reset_index(drop = True)
        return permuted_df
    


    def simulate_measure(self, iterations = 200, df = None):
        ''' Returns a list of DataFrames of simulated measures for the given
                number of iterations, each time permuting the given column of
                the given DataFrame and calculating the measure for the 
                permuted data

            iterations -- an integer representing the number of iterations to
                simulate the measure for, defaulting to 200
            df -- a DataFrame representing the subset of the data to simulate,
                defaulting to None (the entire df instance variable)
        '''
        # Initialize the list of simulated measures
        measures = []

        # Simulate the measure for the given number of iterations
        for _ in range(iterations):
            # Permute the relevant data depending on the df argument
            permutation_df = self.permute_results(df = df)
            # Calculate the measure for the permuted data and add it to the list
            measures.append(self.calculate_measure(permutation_df, team = 'Simulated Team'))

        # Return the list of simulated measures
        return measures


    def calculate_p_value(self, team = None, iterations = 200):
        ''' Returns the p-value for the given team, determined by simulating
                the measure for the given number of iterations and calculating
                the proportion of simulated measures that are greater than or
                equal to the actual measure

            team -- a TLA string representing the team to simulate the measure
                for, defaulting to None which uses the team instance variable
            iterations -- an integer representing the number of iterations to`
                simulate the measure for, defaulting to 200
        '''
        # Default to the df instance variable if no team is given and filter
        #   the df to only include games for the given team if one is given
        if not team:
            if not self.team:
                raise ValueError("No team given")
            team = self.team
            df = self.df
        elif team in constants.TLAS:
            df = self.df.loc[(self.df['Home Team'] == team) | (self.df['Away Team'] == team)]
        else:
            df = self.df

        # Calculate the measure for the actual data, saving the result in the
        #   measure_df instance variable
        self.calculate_measure(df = df, update_dfs = True, team = team)

        # Calculate the measures for the simulated data
        simulated_measure_dfs = self.simulate_measure(iterations, df)

        # Calculate the p-value
        p_value = sum([ 1 for measure_df in simulated_measure_dfs if measure_df.loc['Simulated Team', 'Measure'] >= self.measure_df.loc[team, 'Measure'] ]) / iterations

        # Return the list of simulated measures and the p-value
        return simulated_measure_dfs, p_value
    

    def monte_carlo_plot(self, team = None, iterations = 200):
        ''' Plots the distribution of simulated measures for the given team
                with the given number of iterations, along with the actual
                measure, and returns the list of simulated measures and the
                p-value

            team -- a TLA string representing the team to simulate the measure,
                defaulting to None which uses the team instance variable
            iterations -- an integer representing the number of iterations to
                simulate the measure for, defaulting to 200
        '''
        # Default to the df instance variable if no team is given
        if not team:
            if not self.team:
                raise ValueError("No team given")
            team = self.team

        # Simulate the measure for the given number of iterations, storing
        #   the list of simulated measures and the p-value
        simulated_measure_dfs, p_value = self.calculate_p_value(team, iterations)
        
        # Plot the distribution of measure values, along with the actual measure
        fig = Figure()
        ax = fig.subplots()
        ax.hist([ simulated_measure_df.loc['Simulated Team', 'Measure'] for simulated_measure_df in simulated_measure_dfs ], color = constants.COLORS[team][0] if team in constants.TLAS else 'b', density = True)
        ax.axvline(x = self.measure_df.loc[team, 'Measure'], color = constants.COLORS[team][1] if team in constants.TLAS else 'r')
        ax.set_xlabel(f'{self.name} Value')
        ax.set_ylabel('Relative Frequency')
        ax.set_title(f'Distribution of Simulated {self.name} for {team} ({iterations} Iterations)')
        legend_elements = [Line2D([0], [0], marker = 'o', color='w', markerfacecolor = constants.COLORS[team][1] if team in constants.TLAS else 'r', markersize = 5, label = f'{team} {self.name}: {round(self.measure_df.loc[team, "Measure"], 3)}'),
                        Line2D([0], [0], marker = 'o', color='w', markerfacecolor = constants.COLORS[team][0] if team in constants.TLAS else 'b', markersize = 5, label = f'Simulated p-value: {round(p_value, 3)}')]
        ax.legend(handles = legend_elements)

        # Save the plot to a temporary buffer
        buf = BytesIO()
        fig.savefig(buf, format = 'png')

        # Encode the result to embed in HTML
        plot_data = base64.b64encode(buf.getbuffer()).decode('ascii')

        # Return the list of simulated measures, the p-value, and the plot data
        return simulated_measure_dfs, p_value, plot_data



class GapMeasure(StreakMeasure):
    def calculate_measure(self, df = None, update_dfs = False, team = None):
        ''' Calculates the gap statistic for all the teams in the given 
                DataFrame and return them as a DataFrame, updating the df 
                instance variable and keeping running 'Home Gap' and 'Away Gap' 
                columns if the update_dfs argument is True

            df -- a DataFrame representing the subset of the data to analyze,
                defaulting to None (the entire df instance variable)
            update_dfs -- a boolean representing whether to update the df
                instance variable and keep running 'Home Gap' and 'Away Gap'
                columns, defaulting to False and ignored if simulation is True
            team -- a TLA string representing the team to calculate the gap
                statistic for, defaulting to None which calculates the gap
                statistic for all teams in the given DataFrame
        '''
        # Default to the df instance variable
        if df is None:
            df = self.df

        # Create a list of unique teams in the given DataFrame
        if not team:
            teams = pd.unique(df[['Home Team', 'Away Team']].values.ravel('K'))
        else:
            teams = [team]

        # Create a DataFrame to store the measure for each team
        measure_df = DataFrame([ {'Team': team, 'Results': []} for team in teams ]).set_index('Team')
        
        # Loop over the rows of the DataFrame
        for ind in df.index:
            # Get the relevant row and team
            row = df.loc[ind]

            # If no team is specified, keep track of all teams
            if not team:
                # Store the home and away teams
                home_team = row['Home Team']
                away_team = row['Away Team']
                
                # Store the game result for the home and away teams
                measure_df.loc[home_team, 'Results'].append(row[self.stat_column])
                measure_df.loc[away_team, 'Results'].append(not row[self.stat_column])
                
                # Calculate the gap for the home and away teams
                home_gap = sqrt(sum( (sum(measure_df.loc[home_team, 'Results'][:i + 1]) - i * mean(measure_df.loc[home_team, 'Results'])) ** 2 for i in range(len(measure_df.loc[home_team, 'Results']))) )
                away_gap = sqrt(sum( (sum(measure_df.loc[away_team, 'Results'][:i + 1]) - i * mean(measure_df.loc[away_team, 'Results'])) ** 2 for i in range(len(measure_df.loc[away_team, 'Results']))) )

                # Store the gap for the home and away teams
                measure_df.loc[home_team, 'Measure'] = home_gap
                measure_df.loc[away_team, 'Measure'] = away_gap

                # Update the df row if the update_dfs argument is True
                if update_dfs:
                    self.df.loc[ind, 'Home Gap'] = home_gap
                    self.df.loc[ind, 'Away Gap'] = away_gap
            # Otherwise, only keep track of the given team
            else:
                # Store the game result for the given team
                measure_df.loc[team, 'Results'].append(not row[self.stat_column]) if 'Home Team' in row and row['Home Team'] != team else measure_df.loc[team, 'Results'].append(row[self.stat_column])

                # Calculate the gap for the given team
                gap = sqrt(sum( ( sum(measure_df.loc[team, 'Results'][:i + 1]) - i * mean(measure_df.loc[team, 'Results'])) ** 2 for i in range(len(measure_df.loc[team, 'Results']) ) ) )

                # Store the gap for the given team
                measure_df.loc[team, 'Measure'] = gap

                # Update the df row if the update_dfs argument is True
                if update_dfs:
                    self.df.loc[ind, f'{team} Gap'] = gap
        
        # Update the measure_df instance variable if the update_dfs argument is
        #   True
        if update_dfs:
            self.measure_df = measure_df

        # Return the measure_df DataFrame
        return measure_df
    


class IETMeasure(StreakMeasure):
    def __init__(self, df, stat_column = 'Home Win', team = None, win = True, name = ''):
        super().__init__(df, stat_column, team, name)
        self.win = win


    @abstractmethod
    def measure_equation(self, index = None):
        pass
            

    def calculate_measure(self, df = None, update_dfs = False, team = None):
        ''' Calculates the clump statistic for all the teams in the given 
                DataFrame and return them as a DataFrame, updating the df 
                instance variable and keeping running 'Home Clump' and 
                'Away Clump' columns if the update_dfs argument is True

            df -- a DataFrame representing the subset of the data to analyze,
                defaulting to None (the entire df instance variable)
            update_dfs -- a boolean representing whether to update the df
                instance variable and keep running 'Home Clump' and 'Away Clump'
                columns, defaulting to False and ignored if simulation is True
            team -- a TLA string representing the team to calculate the clump
                statistic for, defaulting to None which calculates the clump
                statistic for all teams in the given DataFrame
        '''
        # Default to the df instance variable
        if df is None:
            df = self.df

        # Create a list of unique teams in the given DataFrame
        if not team:
            teams = pd.unique(df[['Home Team', 'Away Team']].values.ravel('K'))
        else:
            teams = [team]

        # Create a DataFrame to store the measure for each team
        measure_df = DataFrame([ {'Team': team, 'gaps': [], 'current_gap': 0, 'Measure': None} for team in teams ]).set_index('Team')

        # Update the measure_df instance variable if the update_dfs argument is
        #  True
        if update_dfs:
            self.measure_df = measure_df
        
        # Loop over the rows of the DataFrame
        for ind in df.index:
            # Get the relevant row and team
            row = df.loc[ind]

            # If no team is specified, keep track of all teams
            if not team:
                # Store the home and away teams
                home_team = row['Home Team']
                away_team = row['Away Team']
                
                # Determine the winning and losing team
                end_gap_team, gap_team = (home_team, away_team) if row[self.stat_column] == self.win else (away_team, home_team)

                # Add the current gap of the winning team to the list of gaps 
                #   and reset the current gap
                measure_df.loc[end_gap_team, 'gaps'].append(measure_df.loc[end_gap_team, 'current_gap'])
                measure_df.loc[end_gap_team, 'current_gap'] = 0

                # Add to the current gap of the losing team
                measure_df.loc[gap_team, 'current_gap'] += 1

                # Update the clump for the winning and losing teams
                measure_df.loc[end_gap_team, 'Measure'] = self.measure_equation(end_gap_team)
                measure_df.loc[gap_team, 'Measure'] = self.measure_equation(gap_team)

                # Update the df row if the update_dfs argument is True
                if update_dfs:
                    self.df.loc[ind, f'Home {self.name}'] = measure_df.loc[home_team, 'Measure']
                    self.df.loc[ind, f'Away {self.name}'] = measure_df.loc[away_team, 'Measure']
            # Otherwise, only keep track of the given team
            else:
                # Either add the current gap to the list of gaps and reset 
                #   the current gap or add to the current gap, depending on
                #   the result of the game and the win argument
                win = not row[self.stat_column] if 'Home Team' in row and row['Home Team'] != team else row[self.stat_column]

                if win == self.win:
                    measure_df.loc[team, 'gaps'].append(measure_df.loc[team, 'current_gap'])
                    measure_df.loc[team, 'current_gap'] = 0
                else:
                    # Add to the current gap of the losing team
                    measure_df.loc[team, 'current_gap'] += 1

                # Calculate the clump for the simulated team
                measure = self.measure_equation(team, measure_df)

                # Store the clump for the simulated team
                measure_df.loc[team, 'Measure'] = measure

                # Update the df row if the update_dfs argument is True
                if update_dfs:
                    self.df.loc[ind, self.name] = measure

        # Return the measure_df DataFrame
        return measure_df
    


class SecondMoment(IETMeasure):
    def measure_equation(self, index, measure_df = None):
        if measure_df is None:
            measure_df = self.measure_df
        return sum(gap ** 2 for gap in measure_df.loc[index, 'gaps'])
    


class Entropy(IETMeasure):
    def measure_equation(self, index, measure_df = None):
        if measure_df is None:
            measure_df = self.measure_df
        return sum(gap * log(gap) for gap in measure_df.loc[index, 'gaps'] if gap > 0)
    


class LogUtility(IETMeasure):
    def measure_equation(self, index, measure_df = None):
        if measure_df is None:
            measure_df = self.measure_df
        return -sum(log(gap) for gap in measure_df.loc[index, 'gaps'] if gap > 0)
    


class Sum3Largest(IETMeasure):
    def measure_equation(self, index, measure_df = None):
        return sum(gap for gap in self.measure_df.loc[index, 'gaps'].sorted()[-3:])



class ClumpMeasure(StreakMeasure):
    def __init__(self, df, stat_column = 'Home Win', team = None, win = True, name = ''):
        super().__init__(df, stat_column, team, name)
        self.win = win
            

    def calculate_measure(self, df = None, update_dfs = False, team = None):
        ''' Calculates the clump statistic for all the teams in the given 
                DataFrame and return them as a DataFrame, updating the df 
                instance variable and keeping running 'Home Clump' and 
                'Away Clump' columns if the update_dfs argument is True

            df -- a DataFrame representing the subset of the data to analyze,
                defaulting to None (the entire df instance variable)
            update_dfs -- a boolean representing whether to update the df
                instance variable and keep running 'Home Clump' and 'Away Clump'
                columns, defaulting to False and ignored if simulation is True
            team -- a TLA string representing the team to calculate the clump
                statistic for, defaulting to None which calculates the clump
                statistic for all teams in the given DataFrame
        '''
        # Default to the df instance variable
        if df is None:
            df = self.df

        # Create a list of unique teams in the given DataFrame
        if not team:
            teams = pd.unique(df[['Home Team', 'Away Team']].values.ravel('K'))
        else:
            teams = [team]

        # Create a DataFrame to store the measure for each team
        measure_df = DataFrame([ {'Team': team, 'gaps': [], 'current_gap': 0, 'Measure': None} for team in teams ]).set_index('Team')
        

        # Loop over the rows of the DataFrame
        for ind in df.index:
            # Get the relevant row and team
            row = df.loc[ind]

            # If no team is specified, keep track of all teams
            if not team:
                # Store the home and away teams
                home_team = row['Home Team']
                away_team = row['Away Team']
                
                # Determine the winning and losing team
                end_gap_team, gap_team = (home_team, away_team) if row[self.stat_column] == self.win else (away_team, home_team)

                # Add the current gap of the winning team to the list of gaps 
                #   and reset the current gap
                measure_df.loc[end_gap_team, 'gaps'].append(measure_df.loc[end_gap_team, 'current_gap'])
                measure_df.loc[end_gap_team, 'current_gap'] = 0

                # Add to the current gap of the losing team
                measure_df.loc[gap_team, 'current_gap'] += 1

                # Update the clump for the winning and losing teams
                measure_df.loc[end_gap_team, 'Measure'] = sum(gap ** 2 for gap in measure_df.loc[end_gap_team, 'gaps'])
                measure_df.loc[gap_team, 'Measure'] = sum(gap ** 2 for gap in measure_df.loc[gap_team, 'gaps'])

                # Update the df row if the update_dfs argument is True
                if update_dfs:
                    self.df.loc[ind, 'Home Clump'] = measure_df.loc[home_team, 'Measure']
                    self.df.loc[ind, 'Away Clump'] = measure_df.loc[away_team, 'Measure']
            # Otherwise, only keep track of the given team
            else:
                # Either add the current gap to the list of gaps and reset 
                #   the current gap or add to the current gap, depending on
                #   the result of the game and the win argument
                win = not row[self.stat_column] if 'Home Team' in row and row['Home Team'] != team else row[self.stat_column]

                if win == self.win:
                    measure_df.loc[team, 'gaps'].append(measure_df.loc[team, 'current_gap'])
                    measure_df.loc[team, 'current_gap'] = 0
                else:
                    # Add to the current gap of the losing team
                    measure_df.loc[team, 'current_gap'] += 1

                # Calculate the clump for the simulated team
                clump = sum(gap ** 2 for gap in measure_df.loc[team, 'gaps'])

                # Store the clump for the simulated team
                measure_df.loc[team, 'Measure'] = clump

                # Update the df row if the update_dfs argument is True
                if update_dfs:
                    self.df.loc[ind, 'Clump'] = clump

        # Update the measure_df instance variable if the update_dfs argument is
        #  True
        if update_dfs:
            self.measure_df = measure_df

        # Return the measure_df DataFrame
        return measure_df
    


class WWRunsMeasure(StreakMeasure):
    def calculate_measure(self, df = None, update_dfs = False, team = None):
        ''' Calculates the clump statistic for all the teams in the given DataFrame
                and return them as a DataFrame, updating the df instance 
                variable and keeping running 'Home Clump' and 'Away Clump'
                columns if the update_dfs argument is True

            df -- a DataFrame representing the subset of the data to analyze,
                defaulting to None (the entire df instance variable)
            update_dfs -- a boolean representing whether to update the df
                instance variable and keep running 'Home Clump' and 'Away Clump'
                columns, defaulting to False and ignored if simulation is True
            team -- a TLA string representing the team to calculate the clump
                statistic for, defaulting to None which calculates the clump
                statistic for all teams in the given DataFrame
        '''
        # Default to the df instance variable
        if df is None:
            df = self.df

        # Create a list of unique teams in the given DataFrame
        if not team:
            teams = pd.unique(df[['Home Team', 'Away Team']].values.ravel('K'))
        else:
            teams = [team]

        # Create a DataFrame to store the measure for each team
        measure_df = DataFrame([ {'Team': team, 'W': 0, 'L': 0, 'ws': [], 'ls': [], 'last': None, 'Measure': 0} for team in teams ]).set_index('Team')
        
        # Loop over the rows of the DataFrame
        for ind in df.index:
            # Get the relevant row and team
            row = df.loc[ind]

            # If no team is specified, keep track of all teams
            if not team:
                # Store the home and away teams
                home_team = row['Home Team']
                away_team = row['Away Team']
                
                # Determine the winning and losing team
                win_team = home_team if row[self.stat_column] else away_team
                loss_team = away_team if row[self.stat_column] else home_team

                # Update the win and loss columns
                measure_df.loc[win_team, 'W'] += 1
                measure_df.loc[loss_team, 'L'] += 1

                # Update the win and loss streaks
                if measure_df.loc[win_team, 'last'] == True:
                    measure_df.loc[win_team, 'ws'][-1] += 1
                else:
                    measure_df.loc[win_team, 'ws'].append(1)
                    measure_df.loc[win_team, 'Measure'] += 1
                if measure_df.loc[loss_team, 'last'] == False:
                    measure_df.loc[loss_team, 'ls'][-1] += 1
                else:
                    measure_df.loc[loss_team, 'ls'].append(1)
                    measure_df.loc[loss_team, 'Measure'] += 1

                # Update the last result
                measure_df.loc[win_team, 'last'] = True
                measure_df.loc[loss_team, 'last'] = False

                # Update the df row if the update_dfs argument is True
                if update_dfs:
                    self.df.loc[ind, 'Home WWRuns'] = measure_df.loc[home_team, 'Measure']
                    self.df.loc[ind, 'Away WWRuns'] = measure_df.loc[away_team, 'Measure']
            # Otherwise, only keep track of the given team
            else:
                # Store the game result for the given team
                win = not row[self.stat_column] if 'Home Team' in row and row['Home Team'] != team else row[self.stat_column]
                
                # Update the win and loss streaks
                if win:
                    # Update the win column
                    measure_df.loc[team, 'W'] += 1

                    # Continue a win streak or start a new one
                    if measure_df.loc[team, 'last'] == True:
                        measure_df.loc[team, 'ws'][-1] += 1
                    else:
                        measure_df.loc[team, 'ws'].append(1)
                        measure_df.loc[team, 'Measure'] += 1
                else:
                    # Update the loss column
                    measure_df.loc[team, 'L'] += 1

                    # Continue a loss streak or start a new one
                    if measure_df.loc[team, 'last'] == False:
                        measure_df.loc[team, 'ls'][-1] += 1
                    else:
                        measure_df.loc[team, 'ls'].append(1)
                        measure_df.loc[team, 'Measure'] += 1                        

                # Update the last result
                measure_df.loc[team, 'last'] = win
            
                # Update the df row if the update_dfs argument is True
                if update_dfs:
                    self.df.loc[ind, 'WWRuns'] = measure_df.loc[team, 'Measure']

            
        # Calculate win, loss, win streak, and loss streak summary statistics
        measure_df['Pct'] = measure_df['W'] / (measure_df['W'] + measure_df['L'])
        measure_df['n_ws'] = measure_df['ws'].apply(len)
        measure_df['u_ws'] = measure_df['ws'].apply(mean)
        measure_df['std_ws'] = measure_df['ws'].apply(std)
        measure_df['n_ls'] = measure_df['ls'].apply(len)
        measure_df['u_ls'] = measure_df['ls'].apply(mean)
        measure_df['std_ls'] = measure_df['ls'].apply(std)

        # Calculate the mean, variance, Z-score, and p-value for the Runs Test
        measure_df['u_r'] = measure_df.apply(lambda row: (2 * row['W'] * row['L']) / (row['W'] + row['L']) + 1, axis = 1)
        measure_df['o_r'] = measure_df.apply(lambda row: ((row['u_r'] - 1) * (row['u_r'] - 2)) / (row['W'] + row['L'] - 1), axis = 1)
        measure_df['z'] = measure_df.apply(lambda row: (row['Measure'] - row['u_r']) / row['o_r'], axis = 1)
        measure_df['p'] = measure_df.apply(lambda row: norm.sf(abs(row['z'])) * 2, axis = 1)

        # Update the measure_df instance variable if the update_dfs argument is
        #   True
        if update_dfs:
            self.measure_df = measure_df        

        # Return the measure_df DataFrame
        return measure_df



def plot_correlation(df, x, y):
    ''' Plots the correlation between the given columns of the given DataFrame

        df -- a DataFrame representing the data to plot
        x -- a string representing the column of the given DataFrame to plot
            on the x-axis
        y -- a string representing the column of the given DataFrame to plot
            on the y-axis
    '''
    # Calculate the correlation between the given columns (as floats)
    correlation = df[x].astype(float).corr(df[y].astype(float))

    # Plot the correlation between the given columns
    sns.scatterplot(data = df, x = x, y = y)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.title(f'Correlation Between {x} and {y}')
    legend_elements = [Line2D([0], [0], marker = 'o', color='w', markerfacecolor = 'b', markersize = 5, label = f'{x} and {y} Correlation: {round(correlation, 3)}')]
    plt.legend(handles = legend_elements)
    plt.show()

    # Return the correlation
    return correlation


def plot_histogram(df, column, x_label = None, y_label = None, title = None):
    ''' Plots the histogram of the given column of the given DataFrame

        df -- a DataFrame representing the data to plot
        column -- a string representing the column of the given DataFrame to
            plot the histogram of
    '''
    # Plot the histogram of the given column
    sns.histplot(data = df, x = column, stat = 'density', kde = True, alpha = 0.6, edgecolor = None)
    plt.xlabel(x_label if x_label else column)
    plt.ylabel(y_label if y_label else 'Relative Frequency')
    plt.title(title if title else f'Distribution of {column}')
    plt.show()


def combined_measure_df(season = '2022-2023'):
    db = NBADatabase()
    season_df = db.get_season_games(season = season)

    gap_measure = GapMeasure(season_df, name = 'Gap Measure')
    gap_df = gap_measure.calculate_measure(season_df, update_dfs = True).rename(columns = {'Measure': 'Gap Measure'})

    second_moment = SecondMoment(season_df, name = 'Second Moment')
    second_moment_df = second_moment.calculate_measure(season_df, update_dfs = True).rename(columns = {'Measure': 'Second Moment'})

    entropy = Entropy(season_df, name = 'Entropy')
    entropy_df = entropy.calculate_measure(season_df, update_dfs = True).rename(columns = {'Measure': 'Entropy'})

    log_utility = LogUtility(season_df, name = 'Log Utility')
    log_utility_df = log_utility.calculate_measure(season_df, update_dfs = True).rename(columns = {'Measure': 'Log Utility'})

    wwruns_measure = WWRunsMeasure(season_df, name = 'WWRuns Measure')
    wwruns_df = wwruns_measure.calculate_measure(season_df, update_dfs = True).rename(columns = {'Measure': 'Runs Test', 'z': 'Runs Test z', 'p': 'Runs Test p'})

    measure_df = pd.concat([gap_df, second_moment_df, entropy_df, log_utility_df, wwruns_df], axis = 1)[['W', 'L', 'Pct', 'n_ws', 'u_ws', 'std_ws', 'n_ls', 'u_ls', 'std_ls', 'Runs Test', 'Runs Test z', 'Runs Test p', 'Gap Measure', 'Second Moment', 'Entropy', 'Log Utility']]
    measure_df = measure_df.rename(columns = {'Pct': 'Win Pct', 'n_ws': 'W Streak Count', 'u_ws': 'W Streak Mean Length', 'std_ws': 'W Streak Length Std', 'n_ls': 'L Streak Count', 'u_ls': 'L Streak Mean Length', 'std_ls': 'L Streak Length Std'})
    return measure_df


def main():
    team = 'BOS'
    db = NBADatabase()
    season_df = db.get_season_games(season = '2022-2023')

    gap_measure = GapMeasure(season_df, name = 'Gap Measure')
    gap_df = gap_measure.calculate_measure(season_df, update_dfs = True).rename(columns = {'Measure': 'Gap Measure'})
    gap_measure.monte_carlo_plot(team)

    clump_measure = ClumpMeasure(season_df, name = 'Clump Measure (Wins)')
    clump_w_df = clump_measure.calculate_measure(season_df, update_dfs = True).rename(columns = {'Measure': 'Clump Measure (Wins)'})
    clump_measure.monte_carlo_plot(team)

    second_moment = SecondMoment(season_df, name = 'Second Moment')
    second_moment_df = second_moment.calculate_measure(season_df, update_dfs = True).rename(columns = {'Measure': 'Second Moment'})
    second_moment.monte_carlo_plot(team)

    entropy = Entropy(season_df, name = 'Entropy')
    entropy_df = entropy.calculate_measure(season_df, update_dfs = True).rename(columns = {'Measure': 'Entropy'})
    entropy.monte_carlo_plot(team)

    log_utility = LogUtility(season_df, name = 'Log Utility')
    log_utility_df = log_utility.calculate_measure(season_df, update_dfs = True).rename(columns = {'Measure': 'Log Utility'})
    log_utility.monte_carlo_plot(team)

    clump_measure_loss = ClumpMeasure(season_df, win = False, name = 'Clump Measure (Losses)')
    clump_l_df = clump_measure_loss.calculate_measure(season_df, update_dfs = True).rename(columns = {'Measure': 'Clump Measure (Losses)'})
    clump_measure_loss.monte_carlo_plot(team)

    wwruns_measure = WWRunsMeasure(season_df, name = 'Runs Test')
    wwruns_df = wwruns_measure.calculate_measure(season_df, update_dfs = True).rename(columns = {'Measure': 'Runs Test', 'z': 'Runs Test z', 'p': 'Runs Test p'})
    wwruns_measure.monte_carlo_plot(team)

    print(season_df)

    measure_df = pd.concat([gap_df, clump_w_df, second_moment_df, entropy_df, log_utility_df, clump_l_df, wwruns_df], axis = 1)[['W', 'L', 'Pct', 'n_ws', 'u_ws', 'std_ws', 'n_ls', 'u_ls', 'std_ls', 'Runs Test', 'Runs Test z', 'Runs Test p', 'Gap Measure', 'Clump Measure (Wins)', 'Second Moment', 'Entropy', 'Log Utility', 'Clump Measure (Losses)']]

    for TLA in constants.TLAS:
        _, measure_df.loc[TLA, 'Gap p'] = gap_measure.calculate_p_value(TLA, iterations = 10)
        _, measure_df.loc[TLA, 'Clump W p'] = clump_measure.calculate_p_value(TLA, iterations = 10)
        _, measure_df.loc[TLA, 'Second Moment p'] = second_moment.calculate_p_value(TLA, iterations = 10)
        _, measure_df.loc[TLA, 'Entropy p'] = entropy.calculate_p_value(TLA, iterations = 10)
        _, measure_df.loc[TLA, 'Log Utility p'] = log_utility.calculate_p_value(TLA, iterations = 10)
        _, measure_df.loc[TLA, 'Clump L p'] = clump_measure_loss.calculate_p_value(TLA, iterations = 10)
        _, measure_df.loc[TLA, 'WWRuns p'] = wwruns_measure.calculate_p_value(TLA, iterations = 10)

    print(measure_df)
    
    plot_correlation(measure_df, 'Pct', 'Runs Test')
    plot_correlation(measure_df, 'Pct', 'Runs Test p')
    plot_correlation(measure_df, 'Pct', 'Gap Measure')
    plot_correlation(measure_df, 'Pct', 'Gap p')
    plot_correlation(measure_df, 'Pct', 'Clump Measure (Wins)')
    plot_correlation(measure_df, 'Pct', 'Clump W p')
    plot_correlation(measure_df, 'Pct', 'Second Moment')
    plot_correlation(measure_df, 'Pct', 'Second Moment p')
    plot_correlation(measure_df, 'Pct', 'Entropy')
    plot_correlation(measure_df, 'Pct', 'Entropy p')
    plot_correlation(measure_df, 'Pct', 'Log Utility')
    plot_correlation(measure_df, 'Pct', 'Log Utility p')
    plot_correlation(measure_df, 'Pct', 'Clump Measure (Losses)')
    plot_correlation(measure_df, 'Pct', 'Clump L p')
    plot_correlation(measure_df, 'Clump Measure (Wins)', 'Clump Measure (Losses)')
    plot_correlation(measure_df, 'Clump W p', 'Clump L p')

    plot_histogram(measure_df, 'Runs Test p')
    plot_histogram(measure_df, 'Gap p')
    plot_histogram(measure_df, 'Clump W p')
    plot_histogram(measure_df, 'Second Moment p')
    plot_histogram(measure_df, 'Entropy p')
    plot_histogram(measure_df, 'Log Utility p')
    plot_histogram(measure_df, 'Clump L p')



# Run the main function when the module is executed in the top-level code
#   environment, e.g. when executed from the CLI
if __name__ == '__main__':
    exit(main())
