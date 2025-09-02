import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def parse_receiver_bps(iperf_json_log):
    try:
        # Load the JSON string into a Python dictionary
        data = json.loads(iperf_json_log)

        # Navigate through the nested dictionary to find the target value.
        # The path is: data -> 'end' -> 'sum_received' -> 'bits_per_second'
        bits_per_second = data['end']['sum_received']['bits_per_second']
        
        return bits_per_second
    except json.JSONDecodeError:
        # print("Error: Invalid JSON data provided.")
        return None
    except KeyError as e:
        # print(f"Error: Could not find the expected key {e} in the JSON log.")
        # print("Please ensure the log is a valid iperf3 server-side or receiver log.")
        return None

def plot_boxplot_mbps_list(mbps_list):
    plt.boxplot(mbps_list)
    plt.show()

if __name__ == "__main__":
    base = "/home/ubuntu/FlightSize/Results/"
    base_path = os.listdir(base)
    for path in base_path:
        mbps_list = []
        for sub_path in os.listdir(os.path.join(base, path)):
            sub_path = os.path.join(base, path, sub_path)
            if os.path.isdir(sub_path):
                for file in os.listdir(sub_path):
                    if file.endswith("iperf_receiver.txt"):
                        # print(file)
                        with open(os.path.join(sub_path, file), "r") as f:
                            data = f.read()
                        bps = parse_receiver_bps(data)
                        if bps:
                            mbpd = bps / 1000000.0
                            mbps_list.append(mbpd)
        # print(mbps_list)
        # plot_boxplot_mbps_list(mbps_list)
        print(path)
        print(f"Median: {np.median(mbps_list)}")
        print(f"Mean: {np.mean(mbps_list)}")
        print(f"Std: {np.std(mbps_list)}")