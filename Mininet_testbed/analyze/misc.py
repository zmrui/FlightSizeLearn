import pandas as pd

def calculat_E(csvpath):
    FlightSize_compare_csv = csvpath
    FlightSize_compare_df = pd.read_csv(FlightSize_compare_csv).reset_index(drop=True)
    # if len(FlightSize_compare_df) > 100:
    #     FlightSize_compare_df.drop(FlightSize_compare_df.head(10).index,inplace=True)
    #     FlightSize_compare_df.drop(FlightSize_compare_df.tail(10).index,inplace=True)

    FlightSize_compare_df['FlightSizeTP'] = FlightSize_compare_df['FlightSizeTP'].astype(int)
    FlightSize_compare_df['LinuxFlightSize'] = FlightSize_compare_df['LinuxFlightSize'].astype(int)
    FlightSize_compare_df['FlightSizePrintK'] = FlightSize_compare_df['FlightSizePrintK'].astype(int)

    FlightSize_compare_df = FlightSize_compare_df[FlightSize_compare_df['Time'] <= 17.5]

    for index, row in FlightSize_compare_df.iterrows():
        # curr_time = row['Time']
        # print(curr_time)
        # if float(curr_time) > 17.5:
        #     break
        FlightSize_compare_df.loc[index,'PrintkDiff'] = row['LinuxFlightSize'] - row['FlightSizePrintK']
        FlightSize_compare_df.loc[index,'TPDiff'] = row['LinuxFlightSize'] - row['FlightSizeTP']
    sum_FS_TP = sum(FlightSize_compare_df['FlightSizeTP'].to_list())
    sum_printk_FS = sum(FlightSize_compare_df['FlightSizePrintK'].to_list())
    # sum_FS_Lin = sum(FlightSize_compare_df['LinuxFlightSize'].to_list())

    sum_tp_average_error = sum(FlightSize_compare_df['TPDiff'].to_list())
    sum_pk_average_error = sum(FlightSize_compare_df['PrintkDiff'].to_list())

    average_E_tp = sum_tp_average_error/sum_FS_TP*100
    average_E_pk = sum_pk_average_error/sum_printk_FS*100
    return average_E_tp, average_E_pk

def calculat_E2(csvpath):
    FlightSize_compare_csv = csvpath
    FlightSize_compare_df = pd.read_csv(FlightSize_compare_csv).reset_index(drop=True)
    if len(FlightSize_compare_df) > 100:
        FlightSize_compare_df.drop(FlightSize_compare_df.head(10).index,inplace=True)
        FlightSize_compare_df.drop(FlightSize_compare_df.tail(10).index,inplace=True)

    FlightSize_compare_df['FlightSizeTP'] = FlightSize_compare_df['FlightSizeTP'].astype(int)
    FlightSize_compare_df['LinuxFlightSize'] = FlightSize_compare_df['LinuxFlightSize'].astype(int)

    for index, row in FlightSize_compare_df.iterrows():
        # curr_time = row['Time']
        # if curr_time > 18:
        #     break
        FlightSize_compare_df.loc[index,'TPDiff'] = row['LinuxFlightSize'] - row['FlightSizeTP']
    sum_FS_TP = sum(FlightSize_compare_df['FlightSizeTP'].to_list())
    # sum_FS_Lin = sum(FlightSize_compare_df['LinuxFlightSize'].to_list())

    sum_tp_average_error = sum(FlightSize_compare_df['TPDiff'].to_list())

    average_E_tp = sum_tp_average_error/sum_FS_TP*100

    return average_E_tp