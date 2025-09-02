import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re
import matplotlib
matplotlib.rcParams['pdf.fonttype'] = 42

def parse_goodput(log_path):
    with open(log_path, "r") as f:
        data = f.read()
        goodputMbps = re.findall(r': (\d+\.\d+) Mbit/s', data)
        return goodputMbps[0]

def parse_receiver_goodput(log_path):
    try:
        goodputMbps = parse_goodput(log_path)
        # print(goodputMbps)
        return float(goodputMbps)
    except:
        return None


def plot_boxplot_mbps_list(boxplots):
    plt.clf()
    plt.figure()
    boxplots_keys = list(boxplots.keys())
    key = boxplots_keys[0].split(",")[1]
    fig, ax = plt.subplots(figsize=(3,3))
    ax.boxplot(boxplots.values(), showfliers=False)
    labels = [key.split(",")[0].replace("MLON","Model-Predicted FlightSize").replace("MLOFF","Original FlightSize") for key in boxplots.keys()]
    ax.set_xticklabels(labels, rotation=10) # Modified line
    plt.title(f'BBR, Reorder Rate=25%\n{key}')
    plt.tick_params(axis='x', pad=1)
    plt.tick_params(axis='y', pad=2)
    plt.ylabel('Goodput (Mbps)')
    plt.tight_layout()
    
    plt.savefig(f"bbr_reorder{key}.png")
    plt.savefig(f"bbr_reorder{key}.pdf")


def format_string(input_str):
    """
    Converts a string from a specific technical format to a more readable format.

    Args:
        input_str: A string in the format like 'MLOFF_bbr_reorder_bw50_rtt10'.

    Returns:
        A formatted string like 'MLOFF, BW=50Mbps RTT=10ms' or an error message
        if the format is incorrect.
    """
    # Use regular expressions to find all the required parts.
    # This is more robust than splitting by '_' in case the middle parts change.
    pattern = r"^(MLON|MLOFF)_.*_bw(\d+)_rtt(\d+)$"
    match = re.search(pattern, input_str)

    if not match:
        return f"Error: Input string '{input_str}' does not match the expected format."

    # Extract the captured groups from the match
    ml_status = match.group(1)
    bandwidth = match.group(2)
    rtt = match.group(3)

    # Construct the final formatted string
    formatted_str = f"{ml_status}, BW={bandwidth}Mbps RTT={rtt}ms"
    
    return formatted_str

if __name__ == "__main__":
    base = "/home/ubuntu/FlightSize/Results/reorder"
    exp_path = os.listdir(base)
    
    # exp_path.sort()
    for exp in exp_path:
        if "MLON_bbr_reorder" in exp:
            boxplots = {}
            MLON_path = exp
            MLOFF_path = exp.replace("MLON_bbr_reorder", "MLOFF_bbr_reorder")
            ML_path_pair = [MLON_path, MLOFF_path]
            for path in ML_path_pair:
                goodput_list = []
                for file in os.listdir(os.path.join(base, path)):
                    log_path = os.path.join(base, path, file)
                    # print(log_path)
                    goodput = parse_receiver_goodput(log_path)
                    if goodput:
                        goodput_list.append(goodput)

                print(path)
                # print(goodput_list)
                print(f"Median: {np.median(goodput_list)}")
                print(f"Mean: {np.mean(goodput_list)}")
                print(f"Std: {np.std(goodput_list)}")
                title = format_string(path)
                boxplots[title] = goodput_list
            plot_boxplot_mbps_list(boxplots)