import time
import sys

print("Background test script started.")
with open("test.log", "w") as f:
    f.write("Test script was here.\n")
time.sleep(10)
print("Background test script finished.")
