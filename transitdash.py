#/usr/bin/python

from __future__ import division

# DONE
# Get it showing 3 departures for 3 nearest stops
# Add bearings
# Add geocoding

# TODO
# Gitify
# Refactor
# Webify
# Make it shiny
# Use bounding box for geocoding requests

import sys
import MySQLdb as mdb
import math
import datetime
from decimal import Decimal
from operator import itemgetter
from geopy import geocoders, distance
from urllib import urlencode

# Elmira
#my_lat = Decimal( '43.559558')
#my_lon = Decimal('-80.557766')

## Loft
my_lat_hardcoded = Decimal( '43.467935')
my_lon_hardcoded = Decimal('-80.522060')
my_address_hardcoded = "12 bridgeport rd e, waterloo, on"

my_address_input = raw_input("Enter an address or intersection: ")

# FIXME
my_address = my_address_hardcoded

g = geocoders.Google(domain='maps.google.ca')
place, (my_lat, my_lon) = g.geocode(my_address)

my_lat = Decimal("%.15g" % my_lat)
my_lon = Decimal("%.15g" % my_lon)

#my_lat = Decimal('43.455816')
#my_lon = Decimal('-80.385751')

try:
	c = mdb.connect(
		host = 'localhost',
		user = 'transitdash',
		passwd = 'transitdash',
		db = 'grt_gtfs')
	cursor = c.cursor()


	# stop selection -- factor out ##########################
	cursor.execute("SELECT `stop_id`, `stop_name`, `stop_lat`, `stop_lon` FROM stops")
	stops = cursor.fetchall()

	# FIXME ugly selection algorithm! make this efficient later probably
	nullstop = [1000000000, None]
	nearest_stops = [nullstop, nullstop, nullstop]

	for stop in stops:
		stop_lat = stop[2]
		stop_lon = stop[3]

		dist = distance.distance((my_lat, my_lon), (stop_lat, stop_lon)).meters

		if nearest_stops[0][0] > dist:
			nearest_stops[0] = (dist, stop)
			nearest_stops.sort(key=itemgetter(0), reverse=True)

	nearest_stops.reverse()
	# /FIXME
	# /stop selection #######################################

	for dist_stop in nearest_stops:
		dist = dist_stop[0]
		stop = dist_stop[1]

		stop_id = stop[0]
		stop_name = stop[1]

		# bearing -- factor out #################################
		stop_lat = stop[2]
		stop_lon = stop[3]

		y_bearing = math.sin(stop_lon - my_lon) * math.cos(stop_lat)
		x_bearing = math.cos(my_lat) * math.sin(stop_lat) - math.sin(my_lat) * math.cos(stop_lat) * math.cos(stop_lon - my_lon)
		bearing = math.degrees(math.atan2(y_bearing, x_bearing) % (2*math.pi))

		cardinal_dirs = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")
		cardinal_dir = cardinal_dirs[int(math.floor(bearing / (360 / len(cardinal_dirs)) + 0.5) % len(cardinal_dirs))]
		# /bearing ##############################################

		now = datetime.datetime.now() # deal with time zones!
		now_time = now.strftime('%H:%M:00') # departure time > now_time

		today_yyyymmdd = now.strftime("%Y%m%d")

		# TODO check for trips from next day if there are < 3 trips today
		# Also test what happens around midnight - do post-midnight, pre-morning departures show up?

		#tomorrow = datetime.date.today() + datetime.timedelta(days=1)
		#tomorrow_yyyymmdd = (now + datetime.timedelta(days=1)).strftime("%Y%m%d")
		#tomorrow_weekday = weekdays[tomorrow.weekday()]

		# don't use strftime because weekdays in GTFS are not locale-dependent!
		weekdays = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
		today_weekday = weekdays[now.weekday()]

		# trip fetching -- factor out ###########################
		cursor.execute("SELECT stop_times.`departure_time`, trips.`route_id`, trips.`trip_headsign` \
				FROM stop_times LEFT JOIN trips ON stop_times.`trip_id` = trips.`trip_id` \
				WHERE stop_times.`stop_id` = '%s' AND stop_times.`departure_time` > '%s' AND trips.`service_id` IN \
				(SELECT `service_id` FROM calendar WHERE `start_date` <= '%s' AND `end_date` >= '%s' AND `%s` = 1) \
				ORDER BY `departure_time` ASC LIMIT 5"
				% (stop_id, now_time, today_yyyymmdd, today_yyyymmdd, today_weekday))
		trips = cursor.fetchall()
		# trip fetching #########################################

		if dist < 500:
			print "Stop #%s (%s, %dm %s):" % (stop_id, stop_name, dist, cardinal_dir)
		else:
			print "Stop #%s (%s, %.1fkm %s):" % (stop_id, stop_name, dist / 1000, cardinal_dir)

		print "http://maps.google.com/maps/place?" + urlencode({'q': 'type:transit_station:"%s"' % stop_name})

		if len(trips) == 0:
			print "No more trips departing from this stop today."
		else:
			for trip in trips:
				print "%d %s departing at: %s" % (trip[1], trip[2], trip[0])
		print

	cursor.close()
	c.close()

except mdb.Error, e:
	print "Error %d: %s" % (e.args[0],e.args[1])
	sys.exit(1)
