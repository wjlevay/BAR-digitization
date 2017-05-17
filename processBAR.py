import logging, glob, os, gspread, shutil, subprocess, glymur
from oauth2client.service_account import ServiceAccountCredentials
from PyPDF2 import PdfFileMerger, PdfFileReader

# When testing, set these accordingly
source_path = 'C:\\BARtest\\toProcess\\'
destination_path = 'C:\\BARtest\\toQC\\'

# Set up the dicts
tif_count = {}
tif_files = {}
rows = {}
issue_meta = {}

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
		# print tifs
		# print tif_files

# Google Sheet setup
scope = ['https://spreadsheets.google.com/feeds']
credentials = ServiceAccountCredentials.from_json_keyfile_name('BAR Digitization-fb1d45aa1d32.json', scope)
gc = gspread.authorize(credentials)

# Open spreadsheet and worksheet
sh = gc.open_by_key('1tZjpKZfkGsuUD1iEx_blclJiNQBcfiGhkdXPn9voYGo')
wks = sh.worksheet('itemList')

# List of issues to process
process_list = []



# Confirm we haven't already processed these images and get some issue metadata
for issue in tif_count:

	print 'Looking up', issue
	logger.info('Looking up %s in Google Sheet', issue)

	# Find cell by finding issue date in Sheet
	try:
		cell_list = wks.findall(issue)

		# Get the row, then get some values in that row
		row = str(cell_list[0].row)
		rows[issue] = row

		vol_cell = 'B'+row
		issue_no_cell = 'C'+row
		JP2_cell = 'R'+row
		OCR_cell = 'S'+row

		vol = wks.acell(vol_cell).value
		issue_no = wks.acell(issue_no_cell).value
		JP2_val = wks.acell(JP2_cell).value
		OCR_val = wks.acell(OCR_cell).value

		# Check if we've created JP2s or OCRed this issue
		if JP2_val == '' or JP2_val == 'FALSE':
			if OCR_val == '' or OCR_val == 'FALSE':
				# if we haven't, add them to the process_list
				logger.info('OK, we haven\'t processed these images yet')
				process_list.append(issue)

		# If we've created JP2s and/or OCRed, log this info 
		if JP2_val == 'TRUE':
			logger.info('We already created derivates for %s', issue)

		if OCR_val == 'TRUE':
			logger.info('We already ran OCR for %s', issue)


		# Add issue metadata to the issue_meta dict
		single_issue_meta = {}
		single_issue_meta['vol'] = vol
		single_issue_meta['issue_no'] = issue_no
		issue = str(issue)
		single_issue_meta['date'] = issue[0]+issue[1]+issue[2]+issue[3]+'-'+issue[4]+issue[5]+'-'+issue[6]+issue[7]

		issue_meta[issue] = single_issue_meta

	except:
		logger.error('Could not find %s in Google Sheet. Something is wrong here', issue)



# If we have issues in the list, check if the TIFs match the page count in the spreadsheet
if len(process_list) > 0:
	for issue in process_list:
		
		row = rows[issue]
		pg_match_cell = 'Q'+row
		pg_val = wks.acell('F'+row).value
		logger.info('%s has %s pages', issue, pg_val)
		logger.info('%s has %s TIFFs', issue, tif_count[issue])

		# If we have a match, keep issue in the list
		if int(pg_val) == int(tif_count[issue]):
			# Write back to the sheet
			wks.update_acell(pg_match_cell, 'TRUE')
			logger.info('Yes, %s contains correct # of TIFFs', issue)

		# If there's a mismatch, remove issue from list
		else:
			wks.update_acell(pg_match_cell, 'FALSE')
			logger.error('Mismatch. Error with %s. Removing from the processing list', issue)
			process_list.remove(issue)

# Check list again to see if we should proceed
if len(process_list) > 0:
	logger.info('Going to process the following issues: %s', process_list)
	print 'OK, we have some newspaper issues to process'
else:
	logger.info('No issues to process right now')
	print 'No issues to process right now'


###
# Create derivatives with ImageMagick
# for issue in process_list:
# 	file_list = tif_files[issue]
# 	for file in file_list:
# 		file_path = source_path+issue+'\\'+file
# 		jp2_path = source_path+issue+'\\'+file.replace('.tif','.jp2')

# 		# Run ImageMagick to create JP2s for each page
# 		magick_string = 'magick '+file_path+' -define jp2:tilewidth=1024 -define jp2:tileheight=1024 -define jp2:ilyrrates=1,0.84,0.7,0.6,0.5,0.4,0.35,0.3,0.25,0.21,0.18,0.15,0.125,0.1,0.088,0.07,0.0625,0.05,0.04419,0.03716,0.03125,0.025,0.0221,0.01858,0.015625 '+jp2_path
# 		logger.info('Running ImageMagick on %s...', file)
# 		subprocess.check_output(magick_string)
# 		logger.info('Complete')

# 	logger.info('Finished creating JP2s for %s', issue)

# 	# Update the spreadsheet
# 	row = rows[issue]
# 	JP2_cell = 'R'+row
# 	try:
# 		wks.update_acell(JP2_cell, 'TRUE')
# 	except RequestError:
# 		logger.error('RequestError. Couldn\'t write to Google Sheet for issue %s', issue)


###
# Create JP2 XML box
for issue in process_list:
	date = issue_meta[issue]['date']
	vol = issue_meta[issue]['vol']
	issue_no = issue_meta[issue]['issue_no']

	file_list = tif_files[issue]
	page_count = len(file_list)
	page_num = 1

	for a_file in file_list:

		if page_num <= page_count:

			# write out to new file
			filename = source_path+issue+'\\'+a_file.replace('.tif','.jp2.xml')
			xml_string = '<?xml version="1.0" encoding="UTF-8"?>\n<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdfsyntax-ns#">\n\t<rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/" rdf:about="urn:libraryofcongress:ndnp:mets:newspaper:page://sn92019460/'+date+'/1/'+str(page_num)+'">\n\t\t<dc:format>image/jp2</dc:format>\n\t\t<dc:title>\n\t\t\t<rdf:Alt>\n\t\t\t\t<rdf:li xml:lang="en">Bay area reporter. (San Francisco, Calif.), '+date+', [p '+str(page_num)+'].</rdf:li>\n\t\t\t</rdf:Alt>\n\t\t</dc:title>\n\t\t<dc:description>\n\t\t\t<rdf:Alt>\n\t\t\t\t<rdf:li xml:lang="en">Page from Bay area reporter. [See LCCN: sn92019460 for catalog record.]. Prepared by GLBT Historical Society.</rdf:li>\n\t\t\t</rdf:Alt>\n\t\t</dc:description>\n\t\t<dc:date>\n\t\t\t<rdf:Seq>\n\t\t\t\t<rdf:li xml:lang="x-default">'+date+'</rdf:li>\n\t\t\t</rdf:Seq>\n\t\t</dc:date>\n\t\t<dc:type>\n\t\t\t<rdf:Bag>\n\t\t\t\t<rdf:li xml:lang="en">text</rdf:li>\n\t\t\t\t<rdf:li xml:lang="en">newspaper</rdf:li>\n\t\t\t</rdf:Bag>\n\t\t</dc:type>\n\t<rdf:Description>\n</rdf:RDF>'
			with open(filename, 'wb') as f:
				f.write(xml_string)
			
			logger.info('Created JP2 XML for %s', a_file)
			page_num += 1


###
# Add XML box to JP2s
for issue in process_list:
	jp2_list = glob.glob1(issue,'*.jp2')

	for a_jp2 in jp2_list:
		jp2_filename = source_path+issue+'\\'+a_jp2
		jp2xml_filename = jp2_filename+'.xml'

		shutil.copyfile(glymur.data.nemo(), jp2_filename)
		jp2 = glymur.Jp2k(jp2_filename)
		xmlbox = glymur.jp2box.XMLBox(filename=jp2xml_filename)
		jp2.append(xmlbox)
		print(jp2)

# ###
# #OCR with Tesseract
# for issue in process_list:
# 	file_list = tif_files[issue]
# 	for file in file_list:
# 		file_path = source_path+issue+'\\'+file
# 		hocr_path = source_path+issue+'\\'+file.replace('.tif','')

# 		# Run OCR -- we're creating HOCR and PDF files for each page, which we'll further process later
# 		logger.info('Creating HOCR for %s...', file)
# 		subprocess.check_output(['tesseract', file_path, hocr_path, 'hocr'])
# 		logger.info('Complete')

# 		logger.info('Creating PDF for %s...', file)
# 		subprocess.check_output(['tesseract', file_path, hocr_path, 'pdf'])
# 		logger.info('Complete')

# 	logger.info('Finished OCR on %s', issue)

# 	# Update the spreadsheet
# 	row = rows[issue]
# 	OCR_cell = 'S'+row
# 	try:
# 		wks.update_acell(OCR_cell, 'TRUE')
# 	except RequestError:
# 		logger.error('RequestError. Couldn\'t write to Google Sheet for issue %s', issue)


###
# Merge (append) PDFs

# merger = PdfFileMerger()

# for issue in process_list:
# 	file_list = os.listdir(source_path+issue)
# 	page_num = 001

# 	# Append PDFs
# 	for a_file in file_list:
# 		if str(page_num)+'.pdf' in a_file:
# 			pdf_filename = source_path+issue+'\\'+a_file
# 			merger.append(PdfFileReader(file(pdf_filename, 'rb')))
# 			logger.info('Appended %s to the PDF', a_file)
# 			# Advance page_num
# 			page_num += 1

# 	merger.write(source_path+issue+'\\'+issue+'.pdf')
# 	logger.info('Finished creating the issue PDF for %s', issue)


###
# Transform HOCR to ALTO

# xsl_filename = '..\hOCR-to-ALTO\hocr2alto2.1.xsl'

# for issue in process_list:
# 	file_list = os.listdir(source_path+issue)
# 	page_num = 001

# 	# Transform
# 	for file in file_list:
# 		if str(page_num)+'.hocr' in file:
# 			hocr_filename = source_path+issue+'\\'+file
# 			xml = file.replace('.hocr','.xml')
# 			xml_filename = source_path+issue+'\\'+xml
			
# 			saxon_string = 'java -cp C:\saxon\saxon9he.jar net.sf.saxon.Transform -t -s:'+hocr_filename+' -xsl:'+xsl_filename+' -o:'+xml_filename
# 			subprocess.check_output(saxon_string)

# 			logger.info('Transformed %s to %s', file, xml)
# 			# Advance page_num
# 			page_num += 1


# 	logger.info('Finished creating ALTO XML for %s', issue)


# Move issues to QC folder

# for issue in processList:
# 	source = sourcePath+issue
# 	destination = destination_path+issue
# 	shutil.move(source, destination)

# 	logger.info('Moved %s to QC', issue)

print 'All done'
logger.info('All done')