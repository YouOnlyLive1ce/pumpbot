import pandas as pd
import os
import glob

def create_performance(df):
    df['amount_trades'] = df['# win'] + df['# lose'] + df['expired']
    df['performance'] = df['profit'] * 50 + df['amount_trades'] / max(df['amount_trades']) + (df['# win'] / (df['# lose'] + df['# win'])) #+ (1 / df['tp_natr_coef'] + 1 / df['sl_natr_coef']) / 4
    df = df.sort_values(by='performance', ascending=False)
    df['performance']=df['performance'].fillna(0)
    return df

def find_statistics(df, param):
    period, limit, tp_natr_coef,sl_natr_coef,cumulative_threshold,change_threshold,tolerance,num_bin,price_index,strategy = param
    limit=500
    
    condition = (
        (df['period'] == period) &
        (df['limit'] == limit) &
        (df['tp_natr_coef'] == tp_natr_coef) &
        (df['sl_natr_coef'] == sl_natr_coef) &
        (df['cumulative_threshold'] == cumulative_threshold) &
        (df['change_threshold'] == change_threshold) &
        (df['tolerance'] == tolerance) &
        (df['num_bin'] == num_bin) &
        (df['price_index'] == price_index) &
        (df['strategy'] == strategy)
    )
    
    row = df[condition]
    statistics = row.iloc[:, 10:]
    return statistics

perfomance_threshold=0.85
bad_performance_threshold=1
file_paths=file_paths = glob.glob(os.path.join('parameters_statistics_new', '*.csv'))

# Load the DataFrame from the CSV file
dfs=[]
for file_path in file_paths:
    df = pd.read_csv(file_path)
    df = create_performance(df)
    print(df['performance'].mean())
    dfs.append(df)

# for df in dfs:
#     print(len(df.dtypes))

# Extract parameters and statistics
df1_parameters = dfs[0].iloc[:, :10]
df1_statistics = dfs[0].iloc[:, 10:]

# # Iterate over the rows
best_params=[] # params which in all dataframes has perfomance > better_than
best_statistics=[]
for i in range(len(df1_parameters)):
    param = tuple(df1_parameters.iloc[i, :])
    statistics1 = df1_statistics.iloc[i, :].values
    
    bad_performance=0
    # if perform bad on first dataframe, skip
    if statistics1[-1]<df1_statistics['performance'].quantile(perfomance_threshold):
        bad_performance+=1
        continue
    
    for df in dfs[1:]:
        statistics_df = find_statistics(df, param)
        statistics = statistics_df.iloc[0, :].values
        if statistics[-1]<df['performance'].quantile(perfomance_threshold):
            bad_performance+=1
    
    if bad_performance>bad_performance_threshold:
        best_params.append(param)
        best_statistic=[statistics1[0]]
        for df in dfs[1:]:
            best_statistic.append(tuple(find_statistics(df,param)['profit']))
        best_statistics.append(best_statistic)

print(len(best_params), len(best_statistics))
for i, param in enumerate(best_params):
    if sum(best_statistics[i])>0.1:
        print(sum(best_statistics[i]))
        print(param,'\n',best_statistics[i])    

# TODO: ansemble
# current best: ('15m', 500, 2.0, 0.25, 0.1, 0.01, 4, 40, 'high', 'poc')