import logging, glob, os, gspread, shutil, subprocess, time
from oauth2client.service_account import ServiceAccountCredentials

# When testing, set these accordingly
source_path = 'C:\\BARtest\\toProcess\\'
destination_path = 'C:\\BARtest\\toQC\\'

# Set up the dicts
tif_count = {}
tif_files = {}
rows = {}

# Set up logging (found here: https://fangpenlin.com/posts/2012/08/26/good-logging-practice-in-python/)
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

# Starting the run
logger.info('Script started...')

# Count TIFFs
# First let's check for subdirectories in the BAR/toProcess folder and count the number of TIFFs in the folder
# Later we'll compare this number to the page count recorded in the Google Sheet

for root, dirs, files in os.walk(source_path):
	for dir in dirs:
		issue = os.path.join(root, dir)

		# Count the TIFs (found here: http://stackoverflow.com/questions/1320731/count-number-of-files-with-certain-extension-in-python)
		tifs = len(glob.glob1(issue,'*.tif'))

		# Add the value to the dict
		tif_count[dir] = tifs

		# write a list of TIFs to the tif_files dict
		tif_files[dir] = glob.glob1(issue,'*.tif')
		print tifs
		print tif_files

# Google Sheet setup
scope = ['https://spreadsheets.google.com/feeds']
credentials = ServiceAccountCredentials.from_json_keyfile_name('BAR Digitization-fb1d45aa1d32.json', scope)
gc = gspread.authorize(credentials)

# Open spreadsheet and worksheet
sh = gc.open_by_key('1tZjpKZfkGsuUD1iEx_blclJiNQBcfiGhkdXPn9voYGo')
wks = sh.worksheet('itemList')

# List of issues to process
process_list = []



# Confirm we haven't already processed these images 
for issue in tif_count:

	print 'Looking up', issue
	logger.info('Looking up %s in Google Sheet.', issue)

	# Find cell by finding issue date in Sheet
	try:
		cell_list = wks.findall(issue)

		# Get the row, then get some values in that row
		row = str(cell_list[0].row)
		rows[issue] = row

		JP2_cell = 'R'+row
		OCR_cell = 'S'+row

		JP2_val = wks.acell(JP2_cell).value
		OCR_val = wks.acell(OCR_cell).value

		# Check if we've created JP2s or OCRed this issue
		if JP2_val == '' or JP2_val == 'FALSE':
			if OCR_val == '' or OCR_val == 'FALSE':
				# if we haven't, add them to the process_list
				logger.info('OK, we haven\'t processed these images yet.')
				process_list.append(issue)

		# If we've created JP2s and/or OCRed, log this info 
		if JP2_val == 'TRUE':
			logger.info('We already created derivates for %s.', issue)

		if OCR_val == 'TRUE':
			logger.info('We already ran OCR for %s.', issue)

	except:
		logger.error('Could not find %s in Google Sheet. Something is wrong here.', issue)



# If we have issues in the list, check if the TIFs match the page count in the spreadsheet
if len(process_list) > 0:
	for issue in process_list:
		
		row = rows[issue]
		pg_match_cell = 'Q'+row
		pg_val = wks.acell('F'+row).value
		logger.info('%s has %s pages.', issue, pg_val)
		logger.info('%s has %s TIFFs.', issue, tif_count[issue])

		# If we have a match, keep issue in the list
		if int(pg_val) == int(tif_count[issue]):
			# Write back to the sheet
			wks.update_acell(pg_match_cell, 'TRUE')
			logger.info('Yes, %s contains correct # of TIFFs.', issue)

		# If there's a mismatch, remove issue from list
		else:
			wks.update_acell(pg_match_cell, 'FALSE')
			logger.error('Mismatch. Error with %s. Removing from the processing list.', issue)
			process_list.remove(issue)

# Check list again to see if we should proceed
if len(process_list) > 0:
	logger.info('Going to process the following issues: %s', process_list)
	print 'OK, we have some newspaper issues to process.'
else:
	logger.info('No issues to process right now.')
	print 'No issues to process right now.'


###
# Create derivatives with ImageMagick
for issue in process_list:
	file_list = tif_files[issue]
	for file in file_list:
		file_path = source_path+issue+'\\'+file
		jp2_path = source_path+issue+'\\'+file.replace('.tif','.jp2')

		# Run ImageMagick to create JP2s for each page
		logger.info('Running ImageMagick on %s...', file)
		subprocess.check_output(['magick', file_path, jp2_path])
		logger.info('Complete.')

	logger.info('Finished creating JP2s for %s.', issue)

	# Update the spreadsheet
	row = rows[issue]
	JP2_cell = 'R'+row
	try:
		wks.update_acell(JP2_cell, 'TRUE')
	except RequestError:
		logger.error('RequestError. Couldn\'t write to Google Sheet for issue %s.', issue)


###
#OCR with Tesseract
for issue in process_list:
	file_list = tif_files[issue]
	for file in file_list:
		file_path = source_path+issue+'\\'+file
		hocr_path = source_path+issue+'\\'+file.replace('.tif','')

		# Run OCR -- we're creating HOCR and PDF files for each page, which we'll further process later
		logger.info('Running OCR on %s...', file)
		subprocess.call(['tesseract', file_path, hocr_path, 'hocr'])
		subprocess.call(['tesseract', file_path, hocr_path, 'pdf'])
		logger.info('Complete')

	logger.info('Finished OCR on %s.', issue)

	# Update the spreadsheet
	row = rows[issue]
	OCR_cell = 'S'+row
	try:
		wks.update_acell(OCR_cell, 'TRUE')
	except RequestError:
		logger.error('RequestError. Couldn\'t write to Google Sheet for issue %s', issue)

# Move issues to QC folder

# for issue in processList:
# 	source = sourcePath+issue
# 	destination = destination_path+issue
# 	shutil.move(source, destination)

# 	logger.info('Moved %s to QC', issue)

logger.info('All done.')