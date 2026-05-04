import sys
import pickle

def trace(frame, event, arg):
    print(f"{event} {frame.f_code.co_filename}:{frame.f_lineno}")
    return trace

sys.settrace(trace)
print("Starting pickling...")
with open("backend/models/anomaly.pkl", "rb") as f:
    pickle.load(f)
print("Done!")
