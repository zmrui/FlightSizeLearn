# First, you need to install the 'psutil' library to measure CPU usage.
# You can do this by running: pip install psutil
import tl2cgen
import numpy as np
import math
import datetime
import time
import psutil
import os

# --- Configuration ---
# Path to the compiled model library
MODEL_PATH = "/home/ubuntu/FlightSize/C_ml_model/libxgb.so"
# Path to the file where the kernel writes socket info
SOCKET_INFO_PATH = "/home/ubuntu/FlightSize/socket_info"
# Path to the file where this script writes the prediction
ML_FLIGHT_SIZE_PATH = "/home/ubuntu/FlightSize/ml_flight_size"
# How often to print summary statistics (in number of predictions)
STATS_INTERVAL = 500

# --- Predictor Initialization ---
# Load the compiled model using tl2cgen
try:
    predictor = tl2cgen.Predictor(MODEL_PATH)
except tl2cgen.TL2cgenError as e:
    print(f"Error loading model from {MODEL_PATH}: {e}")
    print("Please ensure the path is correct and the model file exists.")
    exit(1)


def predict(row):
    """
    Performs prediction on a single row of features and measures inference time.

    Args:
        row (list): A list of numerical features.

    Returns:
        tuple: A tuple containing the prediction (float) and the inference time (float, in seconds).
    """
    row_np = np.array(row, dtype=np.float32).reshape(1, -1)
    dmat = tl2cgen.DMatrix(row_np)
    
    # --- Measure Inference Time ---
    start_time = time.perf_counter()
    y_hat = predictor.predict(dmat)
    end_time = time.perf_counter()
    
    inference_time = end_time - start_time
    # Use .item() to extract the scalar value from the numpy array
    prediction_value = y_hat.item()
    
    return prediction_value, inference_time

def print_summary(stats):
    """Prints summary statistics for the collected metrics."""
    print("\n\n--- Performance Summary ---")
    if not stats['comm_latencies']:
        print("No data collected.")
        return

    count = len(stats['comm_latencies'])
    avg_latency = np.mean(stats['comm_latencies']) * 1000  # ms
    avg_inference = np.mean(stats['inference_times']) * 1000 # ms
    
    if stats['cpu_usages']:
        avg_cpu = np.mean(stats['cpu_usages'])
        max_cpu = np.max(stats['cpu_usages'])
    else:
        avg_cpu = 0.0
        max_cpu = 0.0
    
    max_latency = np.max(stats['comm_latencies']) * 1000
    max_inference = np.max(stats['inference_times']) * 1000

    print(f"Total Predictions: {count}")
    print(f"Communication Latency (ms): Avg={avg_latency:.4f}, Max={max_latency:.4f}")
    print(f"Inference Time (ms):        Avg={avg_inference:.4f}, Max={max_inference:.4f}")
    print(f"CPU Overhead (%):             Avg={avg_cpu:.2f}, Max={max_cpu:.2f}")
    print("---------------------------\n")


def main():
    """
    Main function to monitor the input file, and run prediction on update.
    """
    # --- Performance Monitoring Setup ---
    process = psutil.Process(os.getpid())
    process.cpu_percent(interval=None) # Prime the call

    stats = {
        'inference_times': [],
        'comm_latencies': [],
        'cpu_usages': []
    }
    prediction_count = 0
    cached_line = ""

    print("Starting user-space inference loop. Press Ctrl+C to exit and see summary.")

    try:
        while True:
            try:
                # --- Start Communication Latency Measurement ---
                start_comm_latency = time.perf_counter()
                
                with open(SOCKET_INFO_PATH, 'r') as f:
                    line = f.readline().strip()

                if line and line != cached_line:
                    cached_line = line
                    
                    row = [int(token) for token in line.split(",")]
                    
                    pred, inference_time = predict(row)

                    res = 0
                    if pred > 0:
                        res = math.ceil(pred)
                    
                    with open(ML_FLIGHT_SIZE_PATH, 'w') as f2:
                        f2.write(f"{res}")
                    
                    # --- End Latency Measurement and Collect Metrics ---
                    end_comm_latency = time.perf_counter()
                    comm_latency = end_comm_latency - start_comm_latency
                    cpu_usage = process.cpu_percent(interval=None)

                    stats['inference_times'].append(inference_time)
                    stats['comm_latencies'].append(comm_latency)
                    if cpu_usage > 0.0:
                        stats['cpu_usages'].append(cpu_usage)

                    prediction_count += 1

                    # Update the live status line
                    status_line = (f"Preds: {prediction_count} | "
                                   f"Latency: {comm_latency * 1000:.2f}ms | "
                                   f"Inference: {inference_time * 1000:.2f}ms | "
                                   f"CPU: {cpu_usage:.1f}% | "
                                   f"Pred Val: {pred:.1f}   ")
                    print(status_line, end='\r')

                    if prediction_count % STATS_INTERVAL == 0:
                        print_summary(stats)

                # To avoid busy-waiting, pause briefly before the next check
                time.sleep(0.01)

            except FileNotFoundError:
                print(f"Waiting for input file {SOCKET_INFO_PATH}...", end='\r')
                time.sleep(1)
            except Exception as e:
                # print(f"\nAn error occurred: {e}. Waiting to retry.")
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nCtrl+C detected! Exiting gracefully.")
    
    finally:
        # Print the final performance summary before exiting
        print_summary(stats)


if __name__ == "__main__":
    main()
