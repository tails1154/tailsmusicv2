# tailsmusicv2

Better tailsmusic

## Why?

So I lost my MP3 Player and decided instead of looking for it, I make my own. I make these files in a rpi zero W and connected my bluetooth headphones to it and boom!


## How do I use it?

It's a little complicated, unless you have my exact SIMOLIO headphones lol




First, `git clone https://github.com/tails1154/tailsmusicv2` into /home/pi and rename it to `mp3player` (or just symlink it lol)



Now, go to the `bashrc` file in the root of the repo. then change the bluetoothctl connect command to your bluetooth headphones' mac address. If you don't know what it is, then do `sudo bluetoothctl scan le` and find your headphones then do `sudo bluetoothctl pair <headphones mac address>`.

Next, If you don't already have the pulseaudio support libs, look it up for your distro on google but here is the ones for (raspberry pi os) debian.  `sudo apt install pulseaudio pulseaudio-module-bluetooth -y`

Next, you need `espeak` installed. If you don't have it installed, here is the instructions for debian (raspberry pi os). for other distros, look it up on google or something.    `sudo apt install espeak -y`

We're almost there. Once you have paired and installed espeak and eveything else, we now need `evtest`  and `python3-evdev` installed.




Now run `evtest` with your bluetooth headphones connected. You should see your headphones in the list. Take note of the name because we will need it later.



Edit (`nano`) player.py and change line 31 (and the other print messages if you want to) to the name we noted down earlier from `evtest`




Make sure `pulseaudio` is running (`pulseaudio --kill && pulseaudio --start`) and run `pactl list short sinks`


You should see a `bluez_<random stuff>`. note this down. We need it in a moment

Edit (`nano`) bashrc and change the refrences to the set-default-sink bluez_ thing to yours we noted down earlier.





Almost there! Now run `cp ~/.bashrc ~/.bashrc.bak` in case you need your bashrc back and run `cp bashrc ~/.bashrc` and modify it if you desire.



Finally, `mkdir playlists` and `mkdir songs` and put your mp3's in songs!


If you are having issues with pressing Pause, go to `evtest` again and select the number of your headphones and press pause/play. The event should show up like this:

```
...
Properties:
Testing ... (interrupt to exit)
Event: time 1750784635.024298, type 1 (EV_KEY), code 201 (KEY_PAUSECD), value 1
Event: time 1750784635.024298, -------------- SYN_REPORT ------------
Event: time 1750784635.070529, type 1 (EV_KEY), code 201 (KEY_PAUSECD), value 0
Event: time 1750784635.070529, -------------- SYN_REPORT ------------
```
The part after `code 201` or code whatever in the ()'s is what you need to note down. Press it again and see if it has a PLAY function and note that down too if it does.

Now, edit (`nano`) player.py and replace all instances of "KEY_CDPLAY" and "KEY_CDPAUSE" with the ones we noted down earlier (set "KEY_CDPAUSE" to the same one as you set the first one if you onlyy had one "KEY_whatever".)



## Menus


Usage is simple, you can press back or skip or pause/play and they do what you would expect in NORMAL mode.

If you pause, then press skip you can access some menus.

To navigate (most) menus, the controls are:

Back: Advance selector
Skip: Select

In a few menus there is this control

Play/Pause: Move Selector Backwards
