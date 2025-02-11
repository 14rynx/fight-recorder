# Fight Recorder

A simple utility that reads eve logs and based on them starts / ends OBS recordings and downloads the replay buffer.

![Main Window](https://i.imgur.com/a5xwEej.png)

## Requirements
- [Open Broadcaster Software (OBS)](https://obsproject.com)

## Setup
### Written Guide
#### Set up OBS:
1. Enable the WebSocker Server:
   - **Go to** Tools -> WebSocket Server Settings
   - **Check** Enable WebSocket server
   - **Note down** Server Port and Server Password
2. Start a Replay Buffer of your desired length:
   - **Go to** Settings -> Output -> Replay Buffer
   - **Set** Maximum Replay Time
   - **Go to** Main Window
   - **Click** Start Replay Buffer
3. (Optional) Automatically start the replay buffer by adding a Flag to the OBS Startup Symlink
   - **Press_ Win + R
   - **Enter** `shell:startup`
   - **Open** OBS Symlink -> Properties -> Shortcut
   - **Add** ` --startreplaybuffer` at the end of the Target field
   - **Click** Apply

#### Set up Fight Recorder
1. Configure Fight_Recorder: 
   - **Enter** Server Port and Server Password from the OBS WebSocket Server
   - **Set** Log Directory to your eve gamelogs folder (Typically `C:\Users\your_user\Documents\EVE\logs\Gamelogs`)
   - **Set** a path to where you want the outputed files to land

If you did everything right, you should see a green "Ready" Status in Fight Recorder.
Otherwise it will tell you what is currently the problem in a red error message.

### Video Guide

[![Video Guide](https://img.youtube.com/vi/nKUF6oge0og/0.jpg)](https://www.youtube.com/watch?v=nKUF6oge0og)

# Behaviour Options
#### Concatenate output Videos
This will automatically merge the replay buffer and recording. Currently they might not be synced perfectly so you can get stutter. Also this can be resource intensive just after an enagegement when you might still be in space.
#### Delete original Videos
If Concatenate output Videos is on, this will delete the originals after (If anything goes wrong they won't be deleted so you can manually recover them). 
#### Run On Startup
Runs the program when you start the PC. Currently there is no mechanism to auto-hide yet, so you will get a window pop up on startum.

# Tray Behaviour
Just like OBS, this tool will minimize to tray with the Minimize Button and terminate with the X Button.
The tray icon will go green if a recording is active.

# Bug Reporting
This tool is in early development, so expect it to sometimes fail. In that case it will not (yet) do anything to get back to a working state, so you might have to restart it and possibly also stop an OBS recording.
If you happen to find any useful info why it failed, please let me know.
