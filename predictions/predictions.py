# -*- coding: utf-8 -*-
"""
Created on Sun Jun 28 11:45:42 2020

@author: mhayt
"""

print('\n\n')
print(' ---------------- START ---------------- \n')

#-------------------------------- API-FOOTBALL --------------------------------

#!/usr/bin/python
from os.path import dirname, realpath, sep, pardir
import sys
sys.path.append(dirname(realpath(__file__)) + sep + pardir + sep)


import pandas as pd
import pickle
import numpy as np
import math
from ml_functions.feature_engineering_functions import average_stats_df, mod_df, running_mean

#----------------------------- FEATURE ENGINEERING ----------------------------

with open('../2019_prem_generated_clean/2019_prem_all_stats_dict.txt', 'rb') as myFile:
    game_stats = pickle.load(myFile)
    
    
#creating a list with the team id in
team_list = []
for key in game_stats.keys():
    team_list.append(key)
team_list.sort()

#creating a dictionary with the team id as key and fixture id's as values
team_fixture_id_dict = {}
for team in team_list:
    fix_id_list = []
    for key in game_stats[team].keys():
        fix_id_list.append(key)
    fix_id_list.sort()
    sub_dict = {team:fix_id_list}
    team_fixture_id_dict.update(sub_dict)
    
#creating the same dictionary as above but only with the previous 10 games ready for predictions.
team_fixture_id_dict_reduced = {}
for team in team_fixture_id_dict:
    team_fixture_list_reduced = team_fixture_id_dict[team][-10:]
    sub_dict = {team:team_fixture_list_reduced}
    team_fixture_id_dict_reduced.update(sub_dict)



df_10_upcom_fix_e = average_stats_df(10, team_list, team_fixture_id_dict_reduced, game_stats, making_predictions=True)
df_10_upcom_fix = mod_df(df_10_upcom_fix_e, making_predictions=True)



#loading fixtures dataframe, we will work with the clean version but it is good to be aware of what is available in the raw version.
fixtures = pd.read_json('../2019_prem_generated_clean/2019_premier_league_fixtures.json', orient='records')
fixtures_clean = pd.read_csv('../2019_prem_generated_clean/2019_premier_league_fixtures_df.csv')


#creating a df with unplayed games only
played_games = []
for i in range(0, len(fixtures)):
    if math.isnan(fixtures_clean['Home Team Goals'].iloc[i]) == False:
        played_games.append(i)
  
unplayed_games = fixtures_clean.drop(fixtures_clean.index[played_games])
unplayed_games = unplayed_games.reset_index()
unplayed_games = unplayed_games.drop(['Home Team Goals', 'Away Team Goals'], axis=1)


#loading df for the labels 
with open('../2019_prem_generated_clean/2019_prem_df_for_ml_10_v2.txt', 'rb') as myFile:
    df_ml_10 = pickle.load(myFile)

column_list = df_ml_10.columns.tolist()

#instatiating the df for predictions with zeros
df_for_predictions = pd.DataFrame(np.zeros((68, 14)))
df_for_predictions.columns = column_list[:14]


#adding the home and away team id
df_for_predictions = pd.DataFrame(np.zeros((len(unplayed_games), 14)))
df_for_predictions.columns = column_list[:14]
df_for_predictions['Home Team ID'] = unplayed_games['Home Team ID']
df_for_predictions['Away Team ID'] = unplayed_games['Away Team ID']
df_for_predictions['Home Team'] = unplayed_games['Home Team']
df_for_predictions['Away Team'] = unplayed_games['Away Team']
df_for_predictions['Game Date'] = unplayed_games['Game Date']


#populating the df_for_predictions with stats

for i in range(0, len(unplayed_games)):
    #getting home team id and index
    home_team = unplayed_games['Home Team ID'].iloc[i]
    home_team_index = df_10_upcom_fix[df_10_upcom_fix['Team ID']==home_team].index.values
    
    #getting away team id and index
    away_team = unplayed_games['Away Team ID'].iloc[i]
    away_team_index = df_10_upcom_fix[df_10_upcom_fix['Team ID']==away_team].index.values    
    
    #getting the home and away team stats given the index of the teams. This still a df. To replace in the df_for_predictions we need this to be a list. This turns out to be quite complex (steps 2 through to 5)
    h1 = df_10_upcom_fix.iloc[home_team_index]
    a1 = df_10_upcom_fix.iloc[away_team_index]
    
    h2 = h1.T
    a2 = a1.T
    
    h3 = h2.values.tolist()
    a3 = a2.values.tolist()
    
    h4 = []
    for j in range(0, len(h3)):
        h4.append(h3[j][0])

    a4 = []
    for k in range(0, len(a3)):
        a4.append(a3[k][0])
        
    h5 = h4[0:7]
    a5 = a4[0:7]
    
    df_for_predictions.iloc[i, 0:7] = h5
    df_for_predictions.iloc[i, 7:14] = a5


#--------------------------- MAKING THE PREDICTIONS ---------------------------

clf = pickle.load(open('../ml_model_build_random_forest/ml_models/random_forest_model_10.pk1', 'rb'))

df_for_predictions_r = df_for_predictions.drop(['Home Team ID', 'Away Team ID', 'Home Team', 'Away Team', 'Game Date'], axis=1)

predictions_raw = clf.predict_proba(df_for_predictions_r)

predictions_df = pd.DataFrame(data=predictions_raw, index=range(0, len(predictions_raw)), columns=['Away Win', 'Draw', 'Home Win'])

predictions_df[predictions_df.select_dtypes(include=['number']).columns] *= 100
predictions_df = predictions_df.round(1)

predictions = pd.concat([unplayed_games, predictions_df], axis=1, join='inner')

re_order_cols = ['Home Team', 'Away Team', 'Home Win', 'Draw', 'Away Win', 'Game Date', 'Venue', 'Home Team Logo', 'Away Team Logo', 'Home Team ID', 'Away Team ID', 'Fixture ID', 'index']
    
predictions = predictions.loc[:, re_order_cols]

with open('pl_predictions.csv', 'wb') as myFile:
    pickle.dump(predictions, myFile)  


# ----------------------------------- END -------------------------------------

print(' ----------------- END ----------------- ')
print('\n')