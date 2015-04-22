Python script to control torrents from a Transmission server. Deals with ratio sites, hit and runs, and off-peak hours.

You'll need Python 2 or greater. Server details are in the script. Run this from crontab if you want.

During off-peak, it pauses the torrents rather than setting turtle mode. This avoids problems with routers and connections.

There are 5 directories that the script uses:

**nopause**
Putting torrents in this directory stops the script from pausing the torrent

**completed**
This is where torrents end up once they've been downloaded and finished their ratio/seeding

**ratio**
This is the minimum ratio that the torrent must seed for until being moved to the completed directory

**rationopause**
Same as ratio and nopause combined

**seed**
This is the holding directory for ratio torrents

Then there are 5 parameters to change the scripts behaviour

**keepseconds**
Number of seconds to keep the torrent seeding

**minratio**
The minimum ratio to seed the torrent for

**concurrent**
The number of torrents to keep running simultaneously

**offpeakstart**
Starting hour of the off peak time (24 hour clock)

**offpeakend**
Ending hour of the off peak time (24 hour clock)
