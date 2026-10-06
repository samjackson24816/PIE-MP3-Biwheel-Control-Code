# PIE-MP3-Biwheel-Control-Code

## Part 1 Plan

Send a "Scan" and "Hunt" command to the stm32 from the linux computer

- Scan means turn slowly in circles
- Hunt means move forward and adjust angle based on delta which is provided from linux

Right now, I want to have dummy script on the linux computer that scans for 10 seconds and then switches to move forward with a delta of 20 deg changing to 0 over 10 seconds, just to test everything
