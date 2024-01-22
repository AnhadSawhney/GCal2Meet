from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
#import pytz
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from datetime import datetime,timezone,timedelta
import requests
import mydate
import sys
import argparse

def parse_args():
	parser = argparse.ArgumentParser(description='Get calendar events with exclusion options')
	parser.add_argument('url', help='URL of when2meet')
	parser.add_argument('-n', '--name', default='Anhad', help='Name to put in when2meet')
	parser.add_argument('-ec', '--exclude-calendars', nargs='+', default=['MITOC', 'bike', 'Camelot', 'MAD'],
						help='List of keywords to exclude from calendar names (default: exclude_keyword1, exclude_keyword2)')
	parser.add_argument('-ee', '--exclude-events', nargs='+', default=['W1MX', 'Chaus'],
						help='List of keywords to exclude from event names (default: exclude_event_keyword1, exclude_event_keyword2)')
	return parser.parse_args()

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

#returns true if a string contains a digit
def isDate(pDate):
	for ch in pDate:
		if ch.isdigit():
			return True
	return False

#Returns the current year
def getYear(date, time):
	year = datetime.now().year
	return year
	#if datetime.now() > datetime.strptime((date + ' ' + str(year) + '  ' + time), '%b %d %Y %I:%M %p'):
	#	year += 1
	#return year

#gets list of events for date range in calendar
def getEvents(dates,times, exclude_calendars_keywords, exclude_events_keywords):
	"""Shows basic usage of the Google Calendar API.
	Prints the start and name of the next 10 events on the user's calendar.
	"""
	creds = None
	# The file token.pickle stores the user's access and refresh tokens, and is
	# created automatically when the authorization flow completes for the first
	# time.
	if os.path.exists('token.pickle'):
		with open('token.pickle', 'rb') as token:
			creds = pickle.load(token)
	# If there are no (valid) credentials available, let the user log in.
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				'credentials.json', SCOPES)
			creds = flow.run_local_server(port=0)
		# Save the credentials for the next run
		with open('token.pickle', 'wb') as token:
			pickle.dump(creds, token)

	service = build('calendar', 'v3', credentials=creds)


	#creates datetime objects from string dates given
	start_time = (datetime.strptime((dates[0] + ' ' + str(getYear(dates[0],times[0])) + ' ' + times[0]), '%b %d %Y %I:%M %p')).isoformat('T')+ "Z"
	# print(times)
	# print(((dates[len(dates)-1] + ' ' + str(getYear(dates[len(dates)-1],times[len(dates)-1])) + '  ' + times[len(times)-1])))
	# exit(1)
	end_time = None
	if times[len(times)-1] != "M":
		end_time = (datetime.strptime((dates[len(dates)-1] + ' ' + str(getYear(dates[len(dates)-1],times[len(dates)-1])) + '  ' + times[len(times)-1]), '%b %d %Y %I:%M %p')+timedelta(days=1)).isoformat('T')+ "Z"
	else:
		end_time = (datetime.strptime((dates[len(dates)-1] + ' ' + str(getYear(dates[len(dates)-1],times[len(dates)-1])) + '  ' + "12 AM"), '%b %d %Y %I:%M %p')+timedelta(days=1)).isoformat('T')+ "Z"

	#end_time = (datetime.strptime((dates[len(dates)-1] + ' ' + str(getYear(dates[len(dates)-1],times[len(dates)-1])) + '  11 PM'), '%b %d %Y %I %p')).isoformat('T')+ "Z"


	# Call the Calendar API

	# Get events from all calendars
	calendar_list = service.calendarList().list().execute().get('items', [])
	events = []
	for calendar in calendar_list:
		shared_calendar_id = calendar['id']
		
		# Check if the calendar should be excluded based on keywords
		exclude_calendar = any(keyword.lower() in calendar['summary'].lower() for keyword in exclude_calendars_keywords)
		if not exclude_calendar:
			events_result = service.events().list(
				calendarId=shared_calendar_id,
				timeMin=start_time,
				timeMax=end_time,
				singleEvents=True,
				orderBy='startTime'
			).execute().get('items', [])
		
			events.extend(events_result)

	#color filter	
	event = [event for event in events if 'colorId' not in event or int(event['colorId']) != 8]
	
	#keyword filter
	event = [event for event in events if not any(keyword.lower() in event['summary'].lower() for keyword in exclude_events_keywords)]

	if not events:
		print('No upcoming events found.')
	rlist = []
	for event in events:
		start = event['start'].get('dateTime', event['start'].get('date'))
		end = event['end'].get('dateTime', event['end'].get('date'))
		print(start, end, event['summary'], event['colorId'] if 'colorId' in event else "Undefined")
		#if it's an all day event, add it to the list of items to be removed from the list of dates
		#this was done assuming all-day events are used as more of a reminder than an actual all-day event
		if len(start) < 11:
			rlist.append(event)
	#remove all day events from events list
	for event in rlist:
		events.remove(event)
	return events

def main():
	args = parse_args()
	driver = webdriver.Firefox()
	name = args.name
	url = args.url
	if url == None:
		print("No URL Given")
		exit(1)

	driver.get(url)

	moreDates = True
	i = 1
	dates = []

	#this gets dates polled for by when2meet
	while moreDates:
		try:
			element = driver.find_element_by_xpath(('//*[@id="GroupGrid"]/div[3]/div[' + str(i) +']'))
			block = element.text
			date = (block.split("\n"))[0]
			i+=1
			if isDate(date):
				dates.append(date)
		except:
			moreDates = False

	#gets times polled for by when2meet
	moreTimes = True
	i = 4
	times = []
	while moreTimes:
		try:
			element = driver.find_element_by_xpath(('//*[@id="GroupGrid"]/div[2]/div['+str(i)+']/div/div'))
			block = element.text
			time = (block.split("M"))[0]+"M"
			if "Noon" in time:
				time = "12 PM"
			i+=4
			times.append(time)
		except:
			moreTimes = False

	events = getEvents(dates,times, args.exclude_calendars, args.exclude_events)
	myEvents = []
	for event in events:
		startstr = event['start'].get('dateTime', event['start'].get('date'))
		#print(startstr)
		endstr = event['end'].get('dateTime', event['end'].get('date'))
		start = datetime.strptime(startstr, '%Y-%m-%dT%H:%M:%f%z').replace(tzinfo=None)
		end = datetime.strptime(endstr, '%Y-%m-%dT%H:%M:%f%z').replace(tzinfo=None)
		myEvents.append(mydate.myDate(start,end))

	
	element = driver.find_element_by_xpath(('//*[@id="name"]'))
	element.send_keys(name)
	element = driver.find_element_by_xpath('//*[@id="SignIn"]/div/div/input')
	element.click()


	r = requests.get(url)
	bsObj = BeautifulSoup(r.text, "html.parser")
	#gets the ids of all the clickable time divs in order
	cells = [x.get("id") for x in bsObj.findAll("div", id=lambda x: x and x.startswith('YouTime'))]

	grid = [[] for date in dates]
	print(grid)

	#makes a 2-D array resembling the grid of the when2meet site
	for idx,cell in enumerate(cells):
		grid[idx%len(dates)].append(cell)
	
	dic = {}

	#marks which id's are associated with times i'm free
	for rIdx, row in enumerate(grid):
		for cIdx, num in enumerate(row):
			starttime = (datetime.strptime((dates[rIdx] + ' ' + str(getYear(dates[rIdx],times[0])) + '  ' + times[0]), '%b %d %Y %I:%M %p') + timedelta(minutes=15*cIdx))
			endtime = (starttime + timedelta(minutes=15))	#add 15 minute cushion to start and end of each event
			dic[num] = True
			for myEvent in myEvents:
				if myEvent.inDate(starttime,endtime) == True:
					dic[num] = False

	#clicks divs where I'm free
	for element in dic.keys():
		if dic[element] == True:
			el = driver.find_element_by_xpath(('//*[@id="' + element + '"]'))
			try:
				el.click()
			except:
				print("UH OH")
				pass
	#keeps website open for review until process ended
	while True:
		# check if the site has been closed by the user
		try:
			driver.find_element_by_xpath('//*[@id="SignIn"]/div/div/input')
		except:
			break
			
	driver.close()

if __name__ == "__main__":
	main()
