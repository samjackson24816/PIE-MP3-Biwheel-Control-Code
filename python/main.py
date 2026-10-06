import time
from arduino.app_utils import App, Bridge

print("Starting Biwheel Control Python MPU App with Bridge Library...")

def run_sequence():
    print("=== PART 1 TEST SEQUENCE START (Bridge Library) ===")
    
    # 1. Scan for 10 seconds (turn slowly in circles)
    print("Setting Bridge mode to 'scan' for 10 seconds...")
    Bridge.put("mode", "scan")
    Bridge.put("delta", "0.0")
    time.sleep(10.0)
    
    # 2. Switch to Hunt mode: move forward with delta of 20 deg changing to 0 over 10 seconds
    print("Setting Bridge mode to 'hunt' (delta 20 -> 0 over 10 seconds)...")
    Bridge.put("mode", "hunt")
    
    hunt_duration = 10.0
    steps = 20
    step_duration = hunt_duration / steps
    
    for i in range(steps + 1):
        delta = 20.0 * (1.0 - (i / steps))
        Bridge.put("delta", f"{delta:.1f}")
        print(f"Bridge updated: mode=hunt, delta={delta:.1f}")
        time.sleep(step_duration)
        
    print("HUNT sequence complete. Setting delta = 0.0...")
    Bridge.put("delta", "0.0")
    
    print("=== PART 1 TEST SEQUENCE COMPLETE ===")

def loop():
    """This function is called repeatedly by the App framework."""
    run_sequence()
    # Keep app running after test sequence completes
    while True:
        time.sleep(60)

# See: https://docs.arduino.cc/software/app-lab/tutorials/getting-started/#app-run
App.run(user_loop=loop)
