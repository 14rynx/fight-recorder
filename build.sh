pyinstaller --onefile  --noconsole --icon data/orange.ico --name "Fight Recorder" --add-data "data/*;data" main.py
cp settings.json dist/
cp "dist/Fight Recorder.exe" debug/
