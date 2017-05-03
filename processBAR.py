# Count TIFFs
# First let's check for subdirectories in the BAR/toProcess folder
# Count the number of TIFFs in the folder
# We'll then compare this number to the page count recorded in the Google Sheet

import glob, os

# When testing, set these accordingly
sourcePath = 'C:\\BARtest\\toProcess\\'
destinationPath = 'C:\\BARtest\\toQC\\'

# set up the dict
tifCount = {}

for root, dirs, files in os.walk(sourcePath):
	for dir in dirs:
		issue = os.path.join(root, dir)

		# Count the TIFs (found here: http://stackoverflow.com/questions/1320731/count-number-of-files-with-certain-extension-in-python)
		tifs = len(glob.glob1(issue,"*.tif"))

		# Add the value to the dict
		tifCount[dir] = tifs




# Google Sheet

import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds']

credentials = ServiceAccountCredentials.from_json_keyfile_name('BAR Digitization-fb1d45aa1d32.json', scope)

gc = gspread.authorize(credentials)

# Open spreadsheet and worksheet
sh = gc.open_by_key('1tZjpKZfkGsuUD1iEx_blclJiNQBcfiGhkdXPn9voYGo')
wks = sh.worksheet('itemList')

# set up list of issues to process
processList = []

for issue in tifCount:

	# Find cell with string value
	cell_list = wks.findall(issue)
	
	# Get the row, then find the value of column F (pagecount) in that row
	row_number = cell_list[0].row
	val = wks.acell('F'+str(row_number)).value

	print issue, 'has', val, 'pages'
	print issue, 'has', tifCount[issue], 'TIFFs'

	if int(val) == int(tifCount[issue]):
		processList.append(issue)
		print 'yes!', issue, 'contains correct # of TIFFs'
	else:
		print 'mismatch error! with', issue

print 'OK, lets process', processList




# # Move issues to QC folder
# import shutil

# for issue in processList:
# 	source = sourcePath+issue
# 	destination = destinationPath+issue
# 	shutil.move(source, destination)

# 	print 'Moved', issue, 'to QC'