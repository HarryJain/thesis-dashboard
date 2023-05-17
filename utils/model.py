# Module imports
import  pandas                  as pd

import  utils.constants         as constants

from    abc                     import ABC, abstractmethod
from    numpy                   import mean

from    utils.database_service  import NBADatabase



class NBAModel(ABC):
    ''' An abstract class to represent a model for predicting the outcome of 
            NBA games
    '''
    def __init__(self):
        ''' Initializes the NBAModel object by creating a NBADatabase object
                and getting the season games as a DataFrame
        '''
        self.db = NBADatabase()
        self.team_games_df = self.db.get_season_games()


    @abstractmethod
    def win_probability(self):
        ''' Abstract method for calculating the desired win probability, e.g.
                home team or a passed team name
        '''
        pass


    def execute_model(self):
        ''' Executes the model by calculating the win probabilities for each
                game
        '''
        self.team_games_df['Predicted Prob'] = self.team_games_df.apply(self.win_probability, axis = 1)


    def evaluate_model(self, execute = False):
        ''' Evaluates the model by calculating the mean difference between the
                predicted probabilities and the actual outcomes, printing the
                result

            execute -- a boolean representing whether to execute the model
                before evaluating it, defaulting to False
        '''
        # Execute the model to get win probabilities if desired
        if execute:
            self.execute_model()

        # Calculate the mean difference between the probabilities and
        #   the actual outcomes, printing the result
        mean_diff = self.team_games_df.apply(lambda row: abs(row['Predicted Prob'] - row['Home Win']), axis = 1).mean()
        print(f'Mean Difference: {mean_diff:.3f}')
    


class EloModel(NBAModel):
    ''' A class to represent an Elo model for predicting the outcome of NBA 
            games, inheriting from NBAModel
    '''
    def __init__(self, method = 'vanilla', starting_rating = 1500, starting_k = 20):
        ''' Initializes the EloModel object by calling the NBAModel constructor
                and setting the Elo method, ratings, and K-factors

            method -- a string representing the Elo method to use, defaulting
                to 'vanilla'
            starting_rating -- an integer representing the starting Elo rating
                for all teams, defaulting to 1500
            starting_k -- an integer representing the starting K-factor for
                all teams, defaulting to 20
        '''
        super().__init__()
        self.method = method
        self.ratings = { team: starting_rating for team in constants.TLAS }
        self.k_factors = { team: starting_k for team in constants.TLAS}


    def expected_score(self, R_A, R_B):
        ''' Returns the expected score for a player of rating R_A vs a player of
                rating R_B, using the classic Elo formula with a logistic curve with
                base 10
            R_A -- the previous rating of Player A
            R_B -- the previous rating of Player B
        '''
        return 1 / (1 + 10**((R_B - R_A) / 400))
    

    def update_ratings(self, R_A, R_B, S_A, S_B, K = 20):
        ''' Updates ratings of players A and B, with ratings R_A and R_B,
                respectively, given scores S_A and S_B and K-factor K
                
            R_A -- the previous rating of Player A
            R_B -- the previous rating of Player B
            S_A -- the actual points scored by Player A (1 for win, 0 otherwise)
            S_B -- the actual points scored by Player B (1 for win, 0 otherwise)
            K -- the K-factor, defaulting to FiveThirtyEight's 20
        '''
        # Calculate the expected scores of players A and B
        E_A = self.expected_score(R_A, R_B)
        E_B = self.expected_score(R_B, R_A)

        # Update the scores of players A and B according to expected scores vs. the
        #   actual scores
        R_A += K * (S_A - E_A)
        R_B += K * (S_B - E_B)

        # Return the updated scores
        return R_A, R_B
    

    def win_probability(self, row):
        ''' Returns the probability of the home team winning the given game
        '''
        # Get the ratings for the home and away teams
        home_rating = self.ratings[row['Home Team']]
        away_rating = self.ratings[row['Away Team']]

        # Return the probability of the home team winning
        return self.expected_score(home_rating, away_rating)
    

    def update_ratings_for_game(self, row):
        ''' Calculates the new ratings for the home and away teams in the given
                row and returns the updated ratings (which are also changed in 
                the ratings dictionary)

            row -- a DataFrame row representing a single game
            ratings -- a dictionary of ratings with (TLA, Elo) (key, value)
                pairs for each team, to be updated with the new ratings
        '''
        # Get the updated ratings for the home and away teams
        if self.method == 'vanilla':
            home_rating, away_rating = self.update_ratings(self.ratings[row['Home Team']], self.ratings[row['Away Team']], row['Home Win'], 1 - row['Home Win'])
        elif self.method == 'gap':
            home_rating, away_rating = self.update_ratings(self.ratings[row['Home Team']], self.ratings[row['Away Team']], row['Home Win'], 1 - row['Home Win'], mean([self.k_factors[row['Home Team']], self.k_factors[row['Away Team']]]))
        else:
            raise ValueError('Invalid method')
        
        # Update the ratings dictionary
        self.ratings[row['Home Team']] = home_rating
        self.ratings[row['Away Team']] = away_rating
        
        # Return the updated home and away ratings
        return home_rating, away_rating
    

    def calculate_elo_ratings(self):
        ''' Updates the Elo ratings for each game in the DataFrame and sets
                the final updated ratings dictionary
        '''
        # Create a table of Elo ratings for home and away teams for each game/row,
            #   expanding list-like results to columns of a DataFrame, according to
            #   the given method
        if self.method == 'vanilla':
            team_games_ratings_df = self.team_games_df.apply(lambda row: self.update_ratings_for_game(row), axis = 1, result_type ='expand')
        # TODO: Implement gap method
        # elif self.method == 'gap':
            # # Calculate the gap measures for the 2021-22 season
            # gap_dict = calculate_gap_measures(engine)
            # games_ratings_df = games_df.apply(lambda row: update_ratings_for_game(row, ratings, method = 'gap', k_factors = gap_dict), axis = 1, result_type ='expand')
        else:
            raise ValueError('Invalid method')

        # Relabel the Elo ratings columns and add them to the games_df
        team_games_ratings_df.columns = ['Home Elo', 'Away Elo']
        self.team_games_df = pd.concat([self.team_games_df, team_games_ratings_df], axis = 1)

    
    def execute_model(self):
        ''' Executes the Elo model by calculating the Elo ratings and then
                executing the NBAModel execute_model method to fill in win
                probabilities
        '''
        self.calculate_elo_ratings()
        super().execute_model()



def main():
    ''' Tests the EloModel class by creating an EloModel object, executing the
            model, and evaluating the model
    '''
    # Create an EloModel object
    elo_model = EloModel()

    # Calculate the Elo ratings
    elo_model.execute_model()
    print(elo_model.team_games_df)
    print(elo_model.ratings)

    # Evaluate the Elo model
    elo_model.evaluate_model()



# Run the main function when the module is executed in the top-level code
#   environment, e.g. when executed from the CLI
if __name__ == '__main__':
    main()