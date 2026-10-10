# Witcher sign lamp sync

Fades a Yeelight to match the sign Geralt has equipped in The Witcher 3.

The game stores the sign as Aard, Yrden, Igni, Quen, Axii. A script mod writes that value into the game settings file. Python reads it and fades the lamp. Tested with the Mi Bedside Lamp 2 (`yeelink.light.bslamp2`) on the next-gen game.

## Setup

1. Copy `mod/lampSync.ws` to:

   `<Witcher 3>/mods/modLampSync/content/scripts/local/lampSync.ws`

2. Copy `mod/lampSync.xml` to:

   `<Witcher 3>/bin/config/r4game/user_config_matrix/pc/lampSync.xml`

3. Install the dependency:

   ```
   pip install -r requirements.txt
   ```

4. Copy `lamp_config.example.json` to `lamp_config.json`. Set the lamp's LAN IP and its 32-character miIO token. `python-miio` uses that same token. Leave `lamp_config.json` uncommitted.

5. In Steam, open Witcher 3 Properties and set Launch Options to the full path of the wrapper, with `%command%` after it:

   ```
   "C:\path\to\witcher-lamp-sync\launch_with_game.bat" %command%
   ```

6. Restart the game so the script compiles, then load a save. The wrapper starts the sync with the game and stops it when you quit.

`python witcher_lamp_sync.py` runs the sync on its own. Colors, Igni's brightness, the fade, and the keepalive are at the top of that file.

The mod needs the script annotations added in the June 2024 patch. Quick Cast can fire a sign without changing the equipped one. The lamp follows the equipped sign.
