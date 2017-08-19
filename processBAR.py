###
# GLBT Historical Society
# BAR Digitization Project Image Processing
# by Bill Levay
# This is an attempt at some automated image processing that can be run on a folder of TIFFs, 
# ideally at night or on the weekend, while no one is using the local machine for scanning.
###

import logging, glob, os, re, gspread, shutil, subprocess
from PyPDF2 import PdfFileMerger, PdfFileReader
from oauth2client.service_account import ServiceAccountCredentials

###
# Get issue metadata and create a list of issues to process
###
def get_metadata():
	# Google Sheet setup
	scope = ['https://spreadsheets.google.com/feeds']
	credentials = ServiceAccountCredentials.from_json_keyfile_name('BAR Digitization-fb1d45aa1d32.json', scope)
	gc = gspread.authorize(credentials)

	issue_meta = {}

	# Open spreadsheet and worksheet
	sh = gc.open_by_key('1tZjpKZfkGsuUD1iEx_blclJiNQBcfiGhkdXPn9voYGo')
	wks = sh.worksheet('itemList')

	for root, dirs, files in os.walk(source_path):
		for dir in dirs:
			issue = dir
			issue_path = os.path.join(root, dir)
			an_issue = {}

			# Count the number of TIFFs in the issue folder
			# Later we'll compare this number to the page count recorded in the Google Sheet
			tif_list = glob.glob1(issue_path,'*.tif')
			an_issue['tifs'] = tif_list
			an_issue['tif_count'] = len(tif_list)

			logger.info('Looking up %s in Google Sheet', issue)

			# Find cell by finding issue date in Sheet
			try:
				cell_list = wks.findall(issue)

				# Get the row, then get some values in that row
				row = str(cell_list[0].row)

				vol = wks.acell('B' + row).value
				issue_no = wks.acell('C' + row).value
				page_ct = wks.acell('F' + row).value
				scanned_by = wks.acell('I' + row).value
				publisher = wks.acell('P' + row).value
				pg_match = wks.acell('Q' + row).value
				derivs = wks.acell('R' + row).value
				ocr = wks.acell('S' + row).value

				# Add issue metadata to the issue_meta dict
				an_issue['vol'] = vol
				an_issue['issue_no'] = issue_no
				an_issue['page_count'] = page_ct
				an_issue['scanned_by'] = scanned_by
				an_issue['publisher'] = publisher
				an_issue['pg_match'] = pg_match
				an_issue['derivs'] = derivs
				an_issue['ocr'] = ocr
				an_issue['date'] = issue[0:4] + '-' + issue[4:6] + '-' + issue[6:8]

				issue_meta[issue] = an_issue

			except Exception as e:
				logger.error('Could not find %s in Google Sheet: %s', issue, e)

	return issue_meta

###
# Update Google Sheet after processing
###
def update_sheet(issue):
	# Google Sheet setup
	scope = ['https://spreadsheets.google.com/feeds']
	credentials = ServiceAccountCredentials.from_json_keyfile_name('BAR Digitization-fb1d45aa1d32.json', scope)
	gc = gspread.authorize(credentials)

	try:

		# Open spreadsheet and worksheet
		sh = gc.open_by_key('1tZjpKZfkGsuUD1iEx_blclJiNQBcfiGhkdXPn9voYGo')
		wks = sh.worksheet('itemList')

		# Find cell
		cell_list = wks.findall(issue)

		# Get the row
		row = str(cell_list[0].row)

		# Update cells in that row
		wks.update_acell('Q' + row, issue_meta[issue]['pg_match'])
		wks.update_acell('R' + row, issue_meta[issue]['derivs'])
		wks.update_acell('S' + row, issue_meta[issue]['ocr'])

	except Exception as e:
		logger.error('Could not update Google Sheet for %s: %s', issue, e)


###
# Create a list of issues to process
###
def process():

	process_list = []

	for issue in issue_meta:

		# Check if TIF count matches page number
		if int(issue_meta[issue]['page_count']) == int(issue_meta[issue]['tif_count']):
			process_list.append(issue)
			issue_meta[issue]['pg_match'] = 'TRUE'
			logger.info('Yes, %s contains correct # of TIFFs', issue)

		else:
			issue_meta[issue]['pg_match'] = 'FALSE'
			logger.error('Mismatch. Error with %s. Not processing', issue)

	# Check process list to see if we should proceed
	if len(process_list) > 0:
		logger.info('Going to process the following issues: %s', process_list)
		print 'OK, we have some newspaper issues to process'
	else:
		logger.info('No issues to process right now')
		print 'No issues to process right now'

	return process_list


###
# Deskew TIFFs
###
def deskew(issue):
	# tif_list = issue_meta[issue]['tifs']
	tif_list = glob.glob1(issue_path,'*.tif')

	for tif in tif_list:
		tif_path = issue_path + sep + tif
		rotate_path = tif_path.replace('.tif','_rotate.tif')

		find_angle = 'deskew -l 80 ' + tif_path

		try:
			output = subprocess.check_output(find_angle, stderr=subprocess.STDOUT)
		except Exception as e:
			logger.error('Error running Deskew on %s: %s', tif, e)

		if output is not None:
			m = re.search('Skew angle found: (.*)', output)
			if m is not None:
				skew = float(m.group(1).rstrip())
				rotate_angle = skew * -1

				if abs(rotate_angle) > 0.1 and abs(rotate_angle) < 3:
					rotate_string = 'magick ' + tif_path + ' -background #000000 -rotate ' + str(rotate_angle) + ' +repage ' + rotate_path

					try:
						subprocess.check_output(rotate_string)
					except Exception as e:
						logger.error('Error rotating %s: %s', tif, e)
					else:
						logger.info('Rotating %s at %s degrees', tif, rotate_angle)

					try:
						os.remove(tif_path)
						os.rename(rotate_path, tif_path)
					except Exception as e:
						logger.error('Problem removing or renaming %s: %s', tif, e)

				else:
					logger.info('No need to deskew %s', tif)

	logger.info('Finished deskewing TIFFs for %s', issue)


###
# Add metadata tags to TIFFs via exiftool
###
def tif_meta(issue):
	tif_list = issue_meta[issue]['tifs']

	# get metadata
	date = issue_meta[issue]['date']
	vol = issue_meta[issue]['vol']
	issue_no = issue_meta[issue]['issue_no']
	
	for tif in tif_list:
		tif_path = issue_path + sep + tif
		pg_num = tif[13:16]

		exif_string = 'exiftool -m -Title="Bay Area Reporter. (San Francisco, Calif.), ' + date + ', [p ' + pg_num + ']" -Description="Page from Bay Area Reporter" -Subject= -DocumentName=' + LCCN + ' -ImageUniqueID=' + date + '_1_' + pg_num + ' -FileSource="Digital Camera" -Artist="GLBT Historical Society" -Copyright="Benro Enterprises, Inc." -Make="Image Access" -Model="Bookeye4 V1-A, SN#BE4-SGS-V1A-00073239BCFD" ' + tif_path

		try:
			subprocess.check_output(exif_string)
		except Exception as e:
			logger.error('Error running Exiftool on %s: %s', tif, e)

	logger.info('Finished fixing TIFF tags for %s', issue)

	original_list = glob.glob1(issue_path,'*.tif_original')
	for original in original_list:
		try:
			os.remove(issue_path+sep+original)
		except Exception as e:
			logger.error('Could not remove %s: %s', original, e)



###
# Create derivatives with ImageMagick
###
def derivs(issue):
	tif_list = issue_meta[issue]['tifs']
	for tif in tif_list:
		tif_path = issue_path + sep + tif
		# jpg_path = tif_path.replace('.tif','.jpg')
		jp2_path = tif_path.replace('.tif','.jp2')

		# Run ImageMagick to create JP2s for each page
		magick_string_jp2 = 'magick ' + tif_path + ' -define jp2:tilewidth=1024 -define jp2:tileheight=1024 -define jp2:rate=0.125 -define jp2:lazy -define jp2:ilyrrates="1,0.84,0.7,0.6,0.5,0.4,0.35,0.3,0.25,0.21,0.18,0.15,0.125,0.1,0.088,0.07,0.0625,0.05,0.04419,0.03716,0.03125,0.025,0.0221,0.01858,0.015625" ' + jp2_path
		# magick_string_jpg = 'magick -units PixelsPerInch ' + tif_path + ' -quality 60 -density 300 ' + jpg_path
		
		try:
			subprocess.check_output(magick_string_jp2)
			# subprocess.check_output(magick_string_jpg)
		except Exception as e:
			logger.error('Error running Imagemagick on %s: %s', tif, e)

	jp2_list = glob.glob1(issue_path,'*.jp2')
	# jpg_list = glob.glob1(issue_path,'*.jpg')
	if len(jp2_list) == len(tif_list):
		logger.info('Finished with derivs for %s', issue)
		issue_meta[issue]['derivs'] = 'TRUE'
	else:
		logger.error('Problem with derivs for %s', issue)
		issue_meta[issue]['derivs'] = 'FALSE'


###
# Create JP2 XML box and add to JP2
###
def jp2xml(issue):
	date = issue_meta[issue]['date']
	tif_list = issue_meta[issue]['tifs']
	page_count = len(tif_list)
	page_num = 1

	for a_file in tif_list:

		if page_num <= page_count:

			# write out to new file
			filename = issue_path + sep + a_file.replace('.tif','.jp2.xml')
			xml_string = '<?xml version="1.0" encoding="UTF-8"?>\n<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdfsyntax-ns#">\n\t<rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/" rdf:about="urn:libraryofcongress:ndnp:mets:newspaper:page://sn92019460/' + date + '/1/' + str(page_num) + '">\n\t\t<dc:format>image/jp2</dc:format>\n\t\t<dc:title>\n\t\t\t<rdf:Alt>\n\t\t\t\t<rdf:li xml:lang="en">Bay Area Reporter. (San Francisco, Calif.), ' + date + ', [p ' + str(page_num) + '].</rdf:li>\n\t\t\t</rdf:Alt>\n\t\t</dc:title>\n\t\t<dc:description>\n\t\t\t<rdf:Alt>\n\t\t\t\t<rdf:li xml:lang="en">Page from Bay Area Reporter. [See LCCN: sn92019460 for catalog record.]. Prepared by GLBT Historical Society.</rdf:li>\n\t\t\t</rdf:Alt>\n\t\t</dc:description>\n\t\t<dc:date>\n\t\t\t<rdf:Seq>\n\t\t\t\t<rdf:li xml:lang="x-default">' + date + '</rdf:li>\n\t\t\t</rdf:Seq>\n\t\t</dc:date>\n\t\t<dc:type>\n\t\t\t<rdf:Bag>\n\t\t\t\t<rdf:li xml:lang="en">text</rdf:li>\n\t\t\t\t<rdf:li xml:lang="en">newspaper</rdf:li>\n\t\t\t</rdf:Bag>\n\t\t</dc:type>\n\t</rdf:Description>\n</rdf:RDF>'
			
			try:
				with open(filename, 'wb') as f:
					f.write(xml_string)
			except Exception as e:
				logger.error('Error writing XML for %s: %s', a_file, e)
			
			page_num += 1

	# Add XML box to JP2s
	jp2_list = glob.glob1(issue_path,'*.jp2')

	for a_jp2 in jp2_list:
		jp2_filename = issue_path + sep + a_jp2
		jp2xml_filename = jp2_filename + '.xml'
		exif_string = 'exiftool -m -xml ' + jp2xml_filename + ' ' + jp2_filename

		try:
			subprocess.check_output(exif_string)
		except Exception as e:
			logger.error('Error with file %s: %s', a_jp2, e)

		try:
			os.remove(jp2xml_filename)
		except Exception as e:
			logger.error('Error with file %s: %s', a_jp2, e)

	logger.info('Finished with JP2 XML for %s', a_file)



###
# OCR with Tesseract
###
def ocr(issue):
	tif_list = issue_meta[issue]['tifs']
	for file in tif_list:
		file_path = issue_path + sep + file
		ocr_path = file_path.replace('.tif','')

		# Run OCR -- we're creating HOCR and PDF files for each page, which we'll further process later
		try:
			subprocess.check_output(['tesseract', file_path, ocr_path, 'hocr'])
		except Exception as e:
			logger.error('Error running Tesseract on %s: %s', file, e)
		
		try:
			subprocess.check_output(['tesseract', file_path, ocr_path, 'pdf'])
		except Exception as e:
			logger.error('Error running Tesseract on %s: %s', file, e)

	issue_meta[issue]['ocr'] = 'TRUE'
	logger.info('Finished OCR on %s', issue)


###
# Downsample PDFs with ImageMagick
###
def downsample_pdf(issue):
    pdf_list = glob.glob1(issue_path,'*.pdf')

    for a_pdf in pdf_list:
        hires_pdf_path = issue_path + sep + a_pdf
        lowres_pdf_path = hires_pdf_path.replace('.pdf','_lo.pdf')
        gs_string_pdf = '"C:\\Program Files (x86)\\gs\\gs9.21\\bin\\gswin32c.exe" -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook -dAutoRotatePages=/None -dNOPAUSE -dQUIET -dBATCH -sOutputFile=' + lowres_pdf_path + ' ' + hires_pdf_path

        try:
            subprocess.check_output(gs_string_pdf)
        except Exception as e:
            logger.error('Error with file %s: %s', a_pdf, e)

        try:
            os.remove(hires_pdf_path)
            os.rename(lowres_pdf_path, hires_pdf_path)
        except Exception as e:
            logger.error('Problem trying to remove and rename file %s: %s', a_pdf, e)

    logger.info('Finished downsampling PDFs for %s', issue)


###
# Merge PDFs
###
def pdf_merge(issue):

	issue_pgs = {}

	file_list = [f for f in os.listdir(issue_path) if f.endswith('pdf') and len(f) == 20]
	for afile in file_list:
		# get the page number from the filename with a slice
		pg_num = int(afile[13:16])
		# add to dict
		issue_pgs[pg_num] = afile

	# open merger object
	merger = PdfFileMerger()
	
	# start counter
	pg_count = 1

	# start merging
	for page in issue_pgs:

		# append PDFs
		pdf_filename = issue_path + '\\' + issue_pgs[pg_count]

		pdf = file(pdf_filename, 'rb')
		merger.append(pdf)
		# Advance count
		pg_count += 1

	output = issue_path + '\\BAR_' + issue + '.pdf'
	out = file(output, 'wb')
	merger.write(out)
	merger.close()
	logger.info('Created issue PDF for %s', issue)


###
# Transform HOCR to ALTO using Saxon and XSL
###
def hocr2alto(issue):
	xsl_filename = '..\hOCR-to-ALTO\hocr2alto2.1.xsl'
	hocr_list = glob.glob1(issue_path,'*.hocr')

	# Transform
	for hocr in hocr_list:
		hocr_filename = issue_path + sep + hocr
		xml = hocr.replace('.hocr','.xml')
		xml_filename = issue_path + sep + xml
		
		saxon_string = 'java -cp C:\saxon\saxon9he.jar net.sf.saxon.Transform -t -s:' + hocr_filename + ' -xsl:' + xsl_filename + ' -o:' + xml_filename

		try:
			subprocess.check_output(saxon_string)
		except Exception as e:
			logger.error('Error transforming %s: %s', hocr, e)

	logger.info('Finished creating ALTO XML for %s', issue)


###
# Move issues to QC folder
###
def to_QC(issue):
	source = source_path+issue
	destination = destination_path+issue

	try:
		shutil.move(source, destination)
	except Exception as e:
		logger.error('Error moving %s to QC: %s', issue, e)
	else:
		logger.info('Cleaning up... Moved %s to QC', issue)


###
# Move issues from Complete to network backup
###
def to_network():
	source_path = 'C:\\BAR\\complete\\'
	backup_path = 'Z:\\BAR\\'

	for root, dirs, files in os.walk(source_path):
		for issue in dirs:
			source = source_path+issue
			destination = backup_path+issue

			try:
				shutil.move(source, destination)
			except Exception as e:
				logger.error('Error moving %s to QC: %s', issue, e)
			else:
				logger.info('Cleaning up... Moved %s to Network Drive', issue)



###
# Start processing
###

# Logging
# Set up logging (found here: https://fangpenlin.com/posts/2012/08/26/good-logging-practice-in-python/)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# create a file handler
handler = logging.FileHandler('processBAR.log')
# handler = logging.FileHandler('processBARtest.log')
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)

# Starting the run
logger.info('Script started...')

# Constants
source_path = 'C:\\BAR\\toProcess\\'
# source_path = 'C:\\Users\\BLevay\\Dropbox\\GLBT\\BARtest\\'
destination_path = 'C:\\BAR\\toQC\\'
sep = '\\'

LCCN = 'sn92019460' #Library of Congress Call Number for Bay Area Reporter

issue_meta = get_metadata()
process_list = process()
# process_list = ['20021128']

for issue in process_list:
	issue_path = source_path + issue
	
	logger.info('---------------------------------------------------------')
	logger.info('Starting to process %s', issue)

	deskew(issue)
	tif_meta(issue)
	derivs(issue)
	jp2xml(issue)
	ocr(issue)
	downsample_pdf(issue)
	pdf_merge(issue)
	hocr2alto(issue)
	to_QC(issue)
	update_sheet(issue)

	logger.info('Finished processing %s', issue)
	logger.info('---------------------------------------------------------')

# to_network()

logger.info('ALL DONE')