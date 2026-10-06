import time
from arduino.app_utils import App, Bridge

print("Starting Biwheel Control Python MPU App with RouterBridge...")

def run_sequence():
    print("=== PART 1 TEST SEQUENCE START (RouterBridge) ===")
    
    # 1. Scan for 10 seconds (turn slowly in circles)
    print("Notifying MCU: scan")
    Bridge.notify("scan")
    time.sleep(10.0)
    
    # 2. Switch to Hunt mode: move forward with delta of 20 deg changing to 0 over 10 seconds
    print("Notifying MCU: hunt (delta 20 -> 0 over 10 seconds)...")
    hunt_duration = 10.0
    steps = 20
    step_duration = hunt_duration / steps
    
    for i in range(steps + 1):
        delta = 20.0 * (1.0 - (i / steps))
        Bridge.notify("hunt", float(delta))
        time.sleep(step_duration)
        
    print("HUNT sequence complete. Notifying MCU: hunt with delta = 0.0")
    Bridge.notify("hunt", 0.0)
    
    print("=== PART 1 TEST SEQUENCE COMPLETE ===")

def loop():
    """This function is called repeatedly by the App framework."""
    run_sequence()
    # Keep app running after test sequence completes
    while True:
        time.sleep(60)

# See: https://docs.arduino.cc/software/app-lab/tutorials/getting-started/#app-run
App.run(user_loop=loop)
