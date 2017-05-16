# Set up logging (found here: https://fangpenlin.com/posts/2012/08/26/good-logging-practice-in-python/)
import logging, glob, os, gspread, shutil, subprocess
from oauth2client.service_account import ServiceAccountCredentials

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# create a file handler
handler = logging.FileHandler('processBAR.log')
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)



# Count TIFFs
# First let's check for subdirectories in the BAR/toProcess folder
# Count the number of TIFFs in the folder
# We'll then compare this number to the page count recorded in the Google Sheet

# When testing, set these accordingly
source_path = 'C:\\BARtest\\toProcess\\'
destination_path = 'C:\\BARtest\\toQC\\'

# Set up the dicts
tif_count = {}
tif_files = {}

for root, dirs, files in os.walk(source_path):
	for dir in dirs:
		issue = os.path.join(root, dir)

		# Count the TIFs (found here: http://stackoverflow.com/questions/1320731/count-number-of-files-with-certain-extension-in-python)
		tifs = len(glob.glob1(issue,'*.tif'))

		# Add the value to the dict
		tif_count[dir] = tifs

		# write a list of TIFs to the tif_files dict
		tif_files[dir] = glob.glob1(issue,'*.tif')

# Google Sheet

scope = ['https://spreadsheets.google.com/feeds']

credentials = ServiceAccountCredentials.from_json_keyfile_name('BAR Digitization-fb1d45aa1d32.json', scope)

gc = gspread.authorize(credentials)

# Open spreadsheet and worksheet
sh = gc.open_by_key('1tZjpKZfkGsuUD1iEx_blclJiNQBcfiGhkdXPn9voYGo')
wks = sh.worksheet('itemList')

# Set up list of issues to process
process_list = []

for issue in tif_count:

	# Find cell with string value
	cell_list = wks.findall(issue)
	
	# Get the row, then find the value of column F (pagecount) in that row
	row = str(cell_list[0].row)
	val = wks.acell('F'+row).value

	logger.info('%s has %s pages', issue, val)
	logger.info('%s has %s TIFFs', issue, tif_count[issue])

	# If we have a match, add issue to list, and add info to spreadsheet
	match_cell = 'Q'+row
	JP2_cell = 'R'+row
	OCR_cell = 'S'+row

	if int(val) == int(tif_count[issue]):
		wks.update_acell(match_cell, 'TRUE')
		logger.info('Yes! %s contains correct # of TIFFs', issue)

		# Confirm we haven't already processed these images 
		if wks.acell(JP2_cell).value == '' or wks.acell(JP2_cell).value == 'FALSE':
			wks.update_acell(JP2_cell, 'FALSE')
			if wks.acell(OCR_cell).value == '' or wks.acell(OCR_cell).value == 'FALSE':
				wks.update_acell(OCR_cell, 'FALSE')
				logger.info('OK, we haven\'t processed these images yet')
				process_list.append(issue)

		elif wks.acell(JP2_cell).value == 'TRUE':
			logger.info('We already processed images for %s!', issue)

	else:
		wks.update_acell(match_cell, 'FALSE')
		logger.error('Mismatch! Error with %s', issue)

logger.info('Going to process the following issues: %s', process_list)
print 'OK, we have some newspaper issues to process.'



# Create derivatives with ImageMagick



# OCR with Tesseract

for issue in process_list:
	file_list = tif_files[issue]
	for file in file_list:
		file_path = source_path+issue+'\\'+file
		hocr_path = source_path+issue+'\\'+file.replace('.tif','')

		# Run OCR!
		subprocess.call(['tesseract', file_path, hocr_path, 'hocr'])
		logger.info('Ran OCR on %s', file)

	# Update the spreadsheet
	# Find cell with string value
	cell_list = wks.findall(issue)
	
	# Get the row, then update the OCR cell from FALSE to TRUE
	row = str(cell_list[0].row)
	OCR_cell = 'S'+row
	wks.update_acell(OCR_cell, 'TRUE')

	logger.info('Finished OCR on %s', issue)

# # Move issues to QC folder

# for issue in processList:
# 	source = sourcePath+issue
# 	destination = destination_path+issue
# 	shutil.move(source, destination)

# 	logger.info('Moved %s to QC', issue)

logger.info('OK, all done for now.')