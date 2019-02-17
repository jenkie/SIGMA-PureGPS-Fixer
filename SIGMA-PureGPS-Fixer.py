"""
This script fixes track records from the Sigma Pure GPS bike computer which are sometimes unusable due to poor GPS signal strength.
Copyright (C) 2019 Jens Kiessling jenskiessling@gmail.com

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import xml.etree.ElementTree as ET
from geopy import distance

# user configuration start
include_breaks = False
repair_speed = True  # repairs speed measurement
smoothing_points = 10  # smoothen speed and distance over n points, minimum: 2, recommended: 10
altitude_start = 1136000  # in mm, start altitude to use
input_filename = 'yourfile.slf'

# calculation start, no changes needed from here
tree = ET.parse(input_filename)
root = tree.getroot()

last_lon = []  # list of last longitudes while iterating through records
last_lat = []  # list of last latitudes while iterating through records
last_alt = []  # list of last altitudes while iterating through records
distance_absolute = 0
speed_max = 0
speed = 0
trainingTimeAbsolute = 0
last_altitude = altitude_start
altitude_min = altitude_start
altitude_max = altitude_start
altitude_difference_uphill_absolute = 0
distance_uphill_absolute = 0
altitude_difference_downhill_absolute = 0
distance_downhill_absolute = 0

if smoothing_points < 2:
    print("Smoothing points needs to be at least 2")
    exit()

if include_breaks:
    for element in root.iter("Marker"):  # first iterate through breaks
        if element.get("type") == "p":
            pause_distance_absolute = element.get("distanceAbsolute")  # find distance at which break occured
            pause_duration = int(element.get("duration"))  # get break duration
            track_element = root.find(".//Entry[@distanceAbsolute='" + pause_distance_absolute + "']")
            trainingtime = int(track_element.get("trainingTime")) + pause_duration  # add break time to training time
            track_element.set("trainingTime", str(trainingtime))

for element in root.iter("Entry"):  # now iterate through records
    trainingtime = int(element.get("trainingTime"))
    element.set("trainingTimeAbsolute", str(trainingTimeAbsolute))
    trainingTimeAbsolute += trainingtime

    # fill history
    last_alt = [int(element.get("altitude"))] + last_alt
    last_lon = [float(element.get("longitude"))] + last_lon
    last_lat = [float(element.get("latitude"))] + last_lat

    if len(last_lon) > smoothing_points:  # clear unneccessary history items
        last_lon = last_lon[:smoothing_points]
        last_lat = last_lat[:smoothing_points]
        last_alt = last_alt[:smoothing_points]

    distance_new = distance.distance([last_lat[0], last_lon[0]], [last_lat[-1], last_lon[-1]]).km * 1e3 / (smoothing_points - 1)  # calculate distance change
    altitude_new = (last_alt[0] - last_alt[-1]) / (smoothing_points - 1)  # calculate altitude change

    # altitude corrections
    if last_alt[0] > altitude_max:
        altitude_max = last_alt[0]  # find max altitude
    if last_alt[0] < altitude_min:
        altitude_min = last_alt[0]  # find min altitude
    if altitude_new > 0:  # calculations for uphill incline and differences
        element.set("altitudeDifferencesUphill", str(altitude_new))
        altitude_difference_uphill_absolute += altitude_new
        distance_uphill_absolute += distance_new
    if altitude_new < 0:  # calculations for downhill incline and differences
        altitude_difference_downhill_absolute += altitude_new
        distance_downhill_absolute += distance_new

    # distance corrections
    distance_absolute += distance_new
    element.set("distance", str(int(distance_new)))
    element.set("distanceAbsolute", str(int(distance_absolute)))

    # incline corrections
    if distance_new > 3:  # only calculate incline if distance difference is larger than 3m
        incline = altitude_new / distance_new / 10
        element.set("incline", str(int(incline)))
    else:
        incline = 0
        element.set("incline", "0")

    # speed corrections
    if repair_speed:
        if trainingtime > 0:
            speed = distance_new / trainingtime * 100
            element.set("speed", str(speed))
    else:
        speed = float(element.get("speed"))

    if speed > speed_max:
        speed_max = speed

# finally set general information
root.find("GeneralInformation/distance").text = str(int(distance_absolute))
root.find("GeneralInformation/minimumAltitude").text = str(int(altitude_min))
root.find("GeneralInformation/maximumAltitude").text = str(int(altitude_max))
root.find("GeneralInformation/altitudeDifferencesUphill").text = str(int(altitude_difference_uphill_absolute))
root.find("GeneralInformation/maximumSpeed").text = str(speed_max)
root.find("GeneralInformation/trainingTime").text = str(trainingTimeAbsolute)
root.find("GeneralInformation/averageSpeed").text = str(distance_absolute / trainingTimeAbsolute * 100)
root.find("GeneralInformation/averageInclineUphill").text = str(altitude_difference_uphill_absolute / distance_uphill_absolute / 10)
root.find("GeneralInformation/averageInclineDownhill").text = str(altitude_difference_downhill_absolute / distance_downhill_absolute / 10)

# print general information
for element in root.iter("GeneralInformation"):
    for subelement in list(element):
        print(subelement.tag, subelement.text)

# write file
tree.write("outfile.slf")
