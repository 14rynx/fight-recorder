# Fight Recorder

A simple utility that reads eve logs and based on them starts / ends OBS recordings and downloads the replay buffer.

## Requirements
- OBS

## Setup
- In OBS start a Replay Buffer of your desired length that should be recorded before the first action. 
(Currently this won't work without one)
- In OBS under Tools open WebSocker Server Settings, and enable the WebSocker Server
- Run Fight Recorder and copy over your Settings from OBS WebSocker Server
- Set the path of your eve gamelogs folder (Typically `C:\Users\your_user\Documents\EVE\logs\Gamelogs`)
- Set a path to where you want the outputed files to land

The script should now show the Status "Ready" which means as soon as you dive into action it will record.

# Options
- Concatenate output Videos: This will automatically merge the replay buffer and recording. Currently they might not be synced perfectly so you can get stutter. Also this can be resource intensive just after an enagegement when you might still be in space.
- Delete original Videos: If Concatenate output Videos is on, this will delete the originals after (If anything goes wrong they won't be deleted so you can manually recover them).
- Run On Startup: Runs the program when you start the PC. Currently there is no mechanism to auto-hide yet, so you will get a window pop up on startum.

# Tray
Just like OBS, this tool will minimize to tray with the Minimize Button and terminate with the X Button.
The tray icon will go green if a recording is active.

# Bugs
This tool is in early development, so expect it to sometimes fail. In that case it will not (yet) do anything to get back to a working state, so you might have to restart it and possibly also stop an OBS recording.
If you happen to find any useful info why it failed, please let me know.
