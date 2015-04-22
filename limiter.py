#!/usr/bin/python
import urllib2
import json
import re
import datetime
import sys
import os
import string
import pprint
import shutil

reload(sys)
sys.setdefaultencoding("UTF-8")

print "Limiter running"

xsessionid = ""

# Trasmission server details
url = 'http://localhost:8080/transmission/rpc'
username = 'username'
password = 'password'

# Storage directories
# nopause, don't pause these torrents
nopause = "/media/Downloads/NoPause"
# completed, this is where torrents end up
completed = "/media/Downloads/Completed"
# ratio, use keephours and minratio for ratio sensitive private trackers, obeys pause hours
ratio = "/media/Downloads/Ratio"
# rationopause, as above, no pause
rationopause = "/media/Downloads/RatioNoPause"
# seed, directory to seed the torrent from for ratio sites
seed = "/media/Downloads/Seed"

# Number of hours to keep the torrent going
keephours = 144 * 3600
# Minimum ratio to keep the torrent
minratio = 10.05
# Number of torrents to keep going at the same time
concurrent = 4
# Start/end hours for off peak (24 hour clock)
offpeakstart = 1
offpeakend = 8

def dorequest(method,arguments):
	global xsessionid, url, username, password

	passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
	passman.add_password(None, url, username, password)
	authhandler = urllib2.HTTPBasicAuthHandler(passman)
	opener = urllib2.build_opener(authhandler)
	urllib2.install_opener(opener)

	request = urllib2.Request(url, json.dumps({"method":method,"arguments":arguments}))

	if xsessionid == "":
		deadresponse = ""
		try:
			urllib2.urlopen(request)
		except urllib2.HTTPError, error:
			deadresponse = error.read()

		xsessionid = re.search("<code>X-Transmission-Session-Id: (.*?)</code>",deadresponse).group(1)

	request.add_header("X-Transmission-Session-Id",xsessionid)
	return urllib2.urlopen(request)

print "Retrieving current torrentlist"
response = dorequest("torrent-get",{"fields":["id","percentDone","downloadDir","uploadRatio","doneDate","files","name"]})
torrents = json.loads(response.read())
response.close()

now = datetime.datetime.now()

torrents["arguments"]["torrents"].sort(key=lambda k: -k["percentDone"])

# Step through all current torrents on the server
print "Traversing..."
for torrent in torrents["arguments"]["torrents"]:
#	pprint.pprint(torrent)
	torrentid = torrent["id"]
	# Torrent is complete:
	# Normal - Move and remove on complete
	# NoPause - Move and remove on complete
	# Ratio - Copy and keep on complete, remove when 1.05 seeded or > 48 hours old
	# RatioNoPause - Copy and keep on complete, remove when 1.05 seeded or > 48 hours old
	# Normal -> Completed (OK)
	# Ratio -> Seed -> Completed ()

	print "Torrent found: " + torrent["name"]

	if torrent["percentDone"] == 1: # Are we done?
		print "Torrent complete, handling..."
		if torrent["downloadDir"] == ratio or torrent["downloadDir"] == rationopause or torrent["downloadDir"] == seed: # Is this a ratio torrent?
			print "....Ratio torrent"
			doneDate = datetime.datetime.fromtimestamp(torrent["doneDate"])
			nowDate = datetime.datetime.now()
			firstfile = torrent["files"][0]["name"]
			slashindex = firstfile.find("/")

			# Fix some dumb torrents
			if doneDate.year == 1970:
				print "....Found 1970 'done' year: " + torrent["name"] + ", compensating."
				doneDate = nowDate

			# Have we exceeded the minimum ratio or hit the keep time?
			if torrent["uploadRatio"] > minratio or (nowDate - doneDate).total_seconds() > keephours:
				print "....Hit ratio or keephours"
				# Yes, does the file exist in the completed folder?
				# Ratio is completed or hours exceeded and the file is already in the completed folder
				if os.path.exists(completed + '/' + firstfile): # Completed file already exists
					# File exists in the completed folder, remove it from the seed
					print "....Removing torrent"
					dorequest("torrent-remove",{"ids":[torrentid]}).close() # Remove torrent and file
				else:
					# File doesn't exist
					print "....Moving torrent to complete"
					dorequest("torrent-set-location",{"move":"true","location":completed,"ids":[torrentid]}).close()
			else:
				print "....Ratio not hit"
				if torrent["downloadDir"] != seed: # Move it to seed
					print "....Moving to seed directory"
					dorequest("torrent-set-location",{"move":"true","location":seed,"ids":[torrentid]}).close()

					# And copy to the completed folder
					print "....Copying to completed"
					if slashindex > -1:
						if not os.path.exists(seed + '/' + firstfile[:slashindex]):
							shutil.copytree(torrent["downloadDir"] + '/' + firstfile[:slashindex],seed + '/' + firstfile[:slashindex])
					else:
						for file in torrent["files"]:
							src = torrent["downloadDir"] + '/' + file["name"]
							dst = seed + '/' + file["name"]
							if not os.path.exists(dst):
								shutil.copy2(src,dst)

		else: # Non-ratio directory, move and remove
			print "....Hit-and-run torrent, move to completed and remove"
			dorequest("torrent-set-location",{"move":"true","location":completed,"ids":[torrentid]}).close()
			dorequest("torrent-remove",{"ids":[torrentid]}).close()
	else:
		print "....Incomplete torrent"
		# Only deal with pauses for non-ratio torrents
		# Stop and start torrents according to offpeak hours (Technically, Telstra don't have offpeak, but schedule when we're not using it)
		if now.hour >= offpeakstart and now.hour < offpeakend and concurrent > 0:
			print "....Off-peak, resuming torrent"
			dorequest("torrent-start",{"ids":[torrentid]}).close()
			concurrent -= 1
		else:
			print "....On-peak, pausing torrent"
			if torrent["downloadDir"] != nopause and torrent["downloadDir"] != rationopause: # Pause the torrents with exemptions
				dorequest("torrent-stop",{"ids":[torrentid]}).close()

print "Torrent management complete"
