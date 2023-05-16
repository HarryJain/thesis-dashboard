# Module imports
from    datetime    import date

# Prefix for Basketball Reference URLs
BR_PREFIX = 'https://www.basketball-reference.com'

# List of three letter acronyms for each team
TLAS = ['ATL', 'BOS', 'BRK', 'CHO', 'CHI', 'CLE', 'DAL', 'DEN', 'DET', 'GSW', 'HOU', 'IND', 'LAC', 'LAL', 'MEM', 'MIA', 'MIL', 'MIN', 'NOP', 'NYK', 'OKC', 'ORL', 'PHI', 'PHO', 'POR', 'SAC', 'SAS', 'TOR', 'UTA', 'WAS']

# Dictionary with keys of team names used in box scores and values of the TLAs used
TEAMS = {'Atlanta': 'ATL', 'Boston': 'BOS', 'Brooklyn': 'BRK', 'Charlotte': 'CHO', 'Chicago': 'CHI', 'Cleveland': 'CLE', 'Dallas': 'DAL', 'Denver': 'DEN', 'Detroit': 'DET', 'Golden State': 'GSW', 'Houston': 'HOU', 'Indiana': 'IND', 'LA': 'LAC', 'L.A. Lakers': 'LAL', 'LA Lakers': 'LAL', 'LA Clippers': 'LAC', 'L.A. Clippers': 'LAC', 'Memphis': 'MEM', 'Miami': 'MIA', 'Milwaukee': 'MIL', 'Minnesota': 'MIN', 'New Orleans': 'NOP', 'New York': 'NYK', 'Oklahoma City': 'OKC', 'Orlando': 'ORL', 'Philadelphia': 'PHI', 'Phoenix': 'PHO', 'Portland': 'POR', 'Sacramento': 'SAC', 'San Antonio': 'SAS', 'Toronto': 'TOR', 'Utah': 'UTA', 'Washington': 'WAS', 'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BRK', 'Charlotte Hornets': 'CHO', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE', 'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET', 'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND', 'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM', 'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC', 'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHO', 'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS', 'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS', 'ATL': 'Hawks', 'BOS': 'Celtics', 'BRK': 'Nets', 'CHO': 'Hornets', 'CHI': 'Bulls', 'CLE': 'Cavaliers', 'DAL': 'Mavericks', 'DEN': 'Nuggets', 'DET': 'Pistons', 'GSW': 'Warriors', 'HOU': 'Rockets', 'IND': 'Pacers', 'LAC': 'Clippers', 'LAL': 'Lakers', 'MEM': 'Grizzlies', 'MIA': 'Heat', 'MIL': 'Bucks', 'MIN': 'Timberwolves', 'NOP': 'Pelicans', 'NYK': 'Knicks', 'OKC': 'Thunder', 'ORL': 'Magic', 'PHI': '76ers', 'PHO': 'Suns', 'POR': 'Trail Blazers', 'SAC': 'Kings', 'SAS': 'Spurs', 'TOR': 'Raptors', 'UTA': 'Jazz', 'WAS': 'Wizards'}

# List of all the different types of streak measures
MEASURES = ['Runs Test', 'Gap Measure', 'Clump Measure (Wins)', 'Second Moment', 'Entropy', 'Log Utility']

# Dictionary of team colors with keys of TLAs and values of hex codes
COLORS = {'ATL': ['#E0393E', '#FBB405'], 'BOS': ['#008247', '#BA9553'], 'BRK': ['#000000', '#A6A9AC'], 'CHO': ['#00788C', '#1D1260'], 'CHI': ['#CE1241', '#000000'], 'CLE': ['#73243D', '#BB945B'], 'DAL': ['#027DC4', '#C4CED3'], 'DEN': ['#0D213E', '#FFC627'], 'DET': ['#013DA6', '#DD0031'], 'GSW': ['#FDB927', '#1C428A'], 'HOU': ['#F0063F', '#333733'], 'IND': ['#FDBB30', '#012D61'], 'LAC': ['#EC164B', '#016AB5'], 'LAL': ['#FDB927', '#552582'], 'MEM': ['#5D76A9', '#12173F'], 'MIA': ['#98002E', '#F8A01A'], 'MIL': ['#00471B', '#00471B'], 'MIN': ['#0D2240', '#236192'], 'NOP': ['#012B5C', '#B39759'], 'NYK': ['#016AB5', '#FF671B'], 'OKC': ['#007AC0', '#F05133'], 'ORL': ['#0B77BD', '#C1CBD0'], 'PHI': ['#EC164B', '#016AB5'], 'PHO': ['#422183', '#E56021'], 'POR': ['#CE092B', '#000000'], 'SAC': ['#5A2D81', '#63727A'], 'SAS': ['#848A8D', '#000000'], 'TOR': ['#BD1A21', '#061A22'], 'UTA': ['#0D2240', '#00471B'], 'WAS': ['#CF082C', '#0D2240']}

# Nested dictionary storing the start dates of the regular season and playoffs
#   and the end date of the finals
SEASON_DATES = {
    '2015-16': {
        'reg_start': date(2015, 10, 27),
        'playoffs_start': date(2016, 4, 16),
        'finals_end': date(2016, 6, 19),
    },
    '2016-17': {
        'reg_start': date(2016, 10, 25),
        'playoffs_start': date(2017, 4, 15),
        'finals_end': date(2017, 6, 12),
    },
    '2017-18': {
        'reg_start': date(2017, 10, 17),
        'playoffs_start': date(2018, 4, 14),
        'finals_end': date(2018, 6, 8),
    },
    '2018-19': {
        'reg_start': date(2018, 10, 16),
        'playoffs_start': date(2019, 4, 13),
        'finals_end': date(2019, 6, 13),
    },
    '2019-20': {
        'reg_start': date(2019, 10, 22),
        'playoffs_start': date(2020, 8, 15),
        'finals_end': date(2020, 10, 11),
    },
    '2020-21': {
        'reg_start': date(2020, 12, 22),
        'playoffs_start': date(2021, 5, 18),
        'finals_end': date(2021, 7, 20),
    },
    '2021-22': {
        'reg_start': date(2021, 10, 19),
        'playoffs_start': date(2022, 4, 12),
        'finals_end': date(2022, 6, 16),
    },
    '2022-23': {
        'reg_start': date(2022, 10, 18),
        'playoffs_start': date(2023, 4, 11),
        'finals_end': date(2023, 6, 20),
    },
}
