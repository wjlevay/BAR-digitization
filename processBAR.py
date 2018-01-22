###
# GLBT Historical Society
# BAR Digitization Project Image Processing
# by Bill Levay
# This is an attempt at some automated image processing that can be run on a folder of TIFFs, 
# ideally at night or on the weekend, while no one is using the local machine for scanning.
###

import logging, glob, os, re, gspread, shutil, subprocess, datetime, zipfile, math, cv2
import numpy as np
from lxml import etree
from xml.sax.saxutils import escape
from PyPDF2 import PdfFileMerger, PdfFileReader
from oauth2client.service_account import ServiceAccountCredentials

###
# Get issue metadata from Google Sheet
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

		# first, let's clean up the csv files created by Opus Freeflow
		for file in files:
			if file.endswith('csv'):
				csv = os.path.join(root,file)
				logger.info('Removing CSV...')
				os.remove(csv)

		# Now let's get down to business
		for dir in dirs:
			issue = dir
			issue_path = os.path.join(root, dir)
			an_issue = {}

			# Count the number of TIFFs in the issue folder
			# Later we'll compare this number to the page count recorded in the Google Sheet
			tif_list = []
			for file in os.listdir(issue_path):
				if '.tif' in file and len(file) == 20:
					tif_list.append(file)
			an_issue['tifs'] = tif_list
			an_issue['tif_count'] = len(tif_list)

			logger.info('Looking up %s in Google Sheet', issue)

			# Find cell by finding issue date in Sheet
			try:
				cell_list = wks.findall(issue)

				# Get the row, then get some values in that row
				row = str(cell_list[0].row)

				vol = wks.acell('C' + row).value
				issue_no = wks.acell('D' + row).value
				page_ct = wks.acell('F' + row).value
				sec1_page_ct = wks.acell('K' + row).value
				sec2_page_ct = wks.acell('L' + row).value
				sec3_page_ct = wks.acell('M' + row).value
				sec4_page_ct = wks.acell('N' + row).value
				sec1_label = wks.acell('O' + row).value
				sec2_label = wks.acell('P' + row).value
				sec3_label = wks.acell('Q' + row).value
				sec4_label = wks.acell('R' + row).value
				scanned_by = wks.acell('I' + row).value
				publisher = wks.acell('S' + row).value
				pg_match = wks.acell('T' + row).value
				derivs = wks.acell('U' + row).value
				ocr = wks.acell('V' + row).value
				no_rotate = wks.acell('Z' + row).value

				# Add issue metadata to the issue_meta dict
				an_issue['vol'] = vol
				an_issue['issue_no'] = issue_no
				an_issue['page_count'] = page_ct
				an_issue['sec1_page_ct'] = sec1_page_ct
				an_issue['sec2_page_ct'] = sec2_page_ct
				an_issue['sec3_page_ct'] = sec3_page_ct
				an_issue['sec4_page_ct'] = sec4_page_ct
				an_issue['sec1_label'] = sec1_label
				an_issue['sec2_label'] = sec2_label
				an_issue['sec3_label'] = sec3_label
				an_issue['sec4_label'] = sec4_label
				an_issue['scanned_by'] = scanned_by
				an_issue['publisher'] = publisher
				an_issue['pg_match'] = pg_match
				an_issue['derivs'] = derivs
				an_issue['ocr'] = ocr
				an_issue['no_rotate'] = no_rotate.split(',')
				an_issue['date'] = issue[0:4] + '-' + issue[4:6] + '-' + issue[6:8]

				issue_meta[issue] = an_issue

			except Exception as e:
				logger.error('Could not find issue in Google Sheet: %s', e)

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
		wks.update_acell('T' + row, issue_meta[issue]['pg_match'])
		wks.update_acell('U' + row, issue_meta[issue]['derivs'])
		wks.update_acell('V' + row, issue_meta[issue]['ocr'])

	except Exception as e:
		logger.error('Could not update Google Sheet: %s', e)


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
			logger.info('Yes, contains correct # of TIFFs')

		else:
			issue_meta[issue]['pg_match'] = 'FALSE'
			logger.error('Mismatch error. Not processing.')

	# Check process list to see if we should proceed
	if len(process_list) > 0:
		logger.info('Going to process the following issues: %s', process_list)
		print 'OK, we have some newspaper issues to process'
	else:
		logger.info('No issues to process right now')
		print 'No issues to process right now'

	return process_list

###
# Compute largest rectangle after rotating
# From: https://stackoverflow.com/questions/16702966/rotate-image-and-crop-out-black-borders/16778797
###
def rotatedRectWithMaxArea(w, h, angle):
  """
  Given a rectangle of size wxh that has been rotated by 'angle' (in
  radians), computes the width and height of the largest possible
  axis-aligned rectangle (maximal area) within the rotated rectangle.
  """
  if w <= 0 or h <= 0:
    return 0,0

  width_is_longer = w >= h
  side_long, side_short = (w,h) if width_is_longer else (h,w)

  # since the solutions for angle, -angle and 180-angle are all the same,
  # if suffices to look at the first quadrant and the absolute values of sin,cos:
  sin_a, cos_a = abs(math.sin(angle)), abs(math.cos(angle))
  if side_short <= 2.*sin_a*cos_a*side_long or abs(sin_a-cos_a) < 1e-10:
    # half constrained case: two crop corners touch the longer side,
    #   the other two corners are on the mid-line parallel to the longer line
    x = 0.5*side_short
    wr,hr = (x/sin_a,x/cos_a) if width_is_longer else (x/cos_a,x/sin_a)
  else:
    # fully constrained case: crop touches all 4 sides
    cos_2a = cos_a*cos_a - sin_a*sin_a
    wr,hr = (w*cos_a - h*sin_a)/cos_2a, (h*cos_a - w*sin_a)/cos_2a

  return wr,hr

###
# Deskew TIFFs
###
def deskew(issue):
	tif_list = [f for f in os.listdir(issue_path) if f.endswith('tif') and len(f) == 20]
	
	# did the scanner operator flag some pages as potentially confusing to deskew?
	if issue_meta[issue]['no_rotate'] is not None:
		no_rotate_list = issue_meta[issue]['no_rotate']
	else:
		no_rotate_list = []

	# grab the page number from the file name and see whether it's on the no-rotate list
	for tif in tif_list:
		pg_num = tif[13:16]

		# not on the list? let's find the angle
		if pg_num not in no_rotate_list:

			tif_path = issue_path + sep + tif
			rotate_path = tif_path.replace('.tif','_rotate.tif')
			crop_path = tif_path.replace('.tif', '_crop.tif')

			find_angle = 'deskew -l 80 ' + tif_path

			try:
				output = subprocess.check_output(find_angle, stderr=subprocess.STDOUT)
			except Exception as e:
				logger.error('Error running Deskew on %s: %s', tif, e)

			# get the angle from the output
			if output is not None:
				m = re.search('Skew angle found: (.*)', output)
				if m is not None:
					skew = float(m.group(1).rstrip())
					rotate_angle = skew * -1

					# set our min and max rotation angles
					if abs(rotate_angle) > 0.1 and abs(rotate_angle) < 1.25:

						# make a copy of the original tif just in case
						backup_tif = issue_path + sep + tif.replace('.tif','_orig.tif')
						shutil.copy2(tif_path, backup_tif)

						# get width and height of image before rotating
						img = cv2.imread(tif_path)
						height = img.shape[0]
						width = img.shape[1]

						# rotate
						rotate_string = 'magick {} -background #000000 -rotate {} +repage {}'.format(tif_path, str(rotate_angle), rotate_path)

						try:
							subprocess.check_output(rotate_string)
						except Exception as e:
							logger.error('Error rotating %s: %s', tif, e)
						else:
							logger.info('Rotating %s at %s', tif, rotate_angle)

						# now let's compute largest rectangle in rotated TIFF and crop
						crop_width, crop_height = rotatedRectWithMaxArea(width, height, math.radians(rotate_angle))

						# and crop using imagemagick
						crop_string = 'magick {} -gravity Center -crop {}x{}+0+0 +repage {}'.format(rotate_path, str(int(crop_width)), str(int(crop_height)), crop_path)

						try:
							subprocess.check_output(crop_string)
						except Exception as e:
							logger.error('Error cropping %s: %s', tif, e)

						# file cleanup
						try:
							os.remove(tif_path)
							os.remove(rotate_path)
							os.rename(crop_path, tif_path)
						except Exception as e:
							logger.error('Problem removing or renaming %s: %s', tif, e)

					else:
						logger.info('No need to deskew %s', tif)

		else:
			logger.info('Skipping %s as per spreadsheet', tif)

	logger.info('Finished deskewing TIFFs')


###
# Add metadata tags to TIFFs via exiftool
###
def tif_meta(issue):
	tif_list = issue_meta[issue]['tifs']

	# get metadata
	date = issue_meta[issue]['date']
	vol = issue_meta[issue]['vol']
	issue_no = issue_meta[issue]['issue_no']

	# # some tifs were rotated and lost exif data, including x and y resolution -- let's fix that
	# # get the list of original tifs
	# rotate_list = glob.glob1(issue_path,'*_orig.tif')

	# # for each, copy exif data from original to rotated tif
	# for orig in rotate_list:
	# 	o_path = issue_path+sep+orig
	# 	r_path = o_path.replace('_orig','')

	# 	# use exif command found here: http://u88.n24.queensu.ca/exiftool/forum/index.php?topic=3440.0
	# 	exif_string = 'exiftool -tagsfromfile {} "-all:all>all:all" {} -overwrite_original'.format(o_path, r_path)

	# 	try:
	# 		subprocess.check_output(exif_string)
	# 	except Exception as e:
	# 		logger.error('Error copying Exif data from %s', f)
	
	# let's add standard metadata to all production tifs
	for tif in tif_list:
		tif_path = issue_path + sep + tif
		pg_num = tif[13:16]

		exif_string = 'exiftool -m -Title="Bay Area Reporter. (San Francisco, Calif.), {}, [p {}]" -Description="Page from Bay Area Reporter" -Subject= -DocumentName={} -ImageUniqueID={}_1_{} -FileSource="Digital Camera" -Artist="GLBT Historical Society" -Copyright="Benro Enterprises, Inc." -Make="Image Access" -Model="Bookeye4 V1-A, SN#BE4-SGS-V1A-00073239BCFD" {} -overwrite_original'.format(date, pg_num, LCCN, date, pg_num, tif_path)
		try:
			subprocess.check_output(exif_string)
		except Exception as e:
			logger.error('Error running Exiftool on %s: %s', tif, e)

	logger.info('Finished fixing TIFF tags')



###
# Create derivatives with ImageMagick
###
def derivs(issue):
	tif_list = issue_meta[issue]['tifs']
	jp2_list = glob.glob1(issue_path,'*.jp2')

	logger.info('Starting on JP2s...')
	for tif in tif_list:
		tif_path = issue_path + sep + tif
		jp2 = tif.replace('.tif','.jp2')
		jp2_path = tif_path.replace('.tif','.jp2')

		# Run ImageMagick to create JP2s for each page
		magick_string_jp2 = 'magick ' + tif_path + ' -define jp2:tilewidth=1024 -define jp2:tileheight=1024 -define jp2:rate=0.125 -define jp2:lazy -define jp2:ilyrrates="1,0.84,0.7,0.6,0.5,0.4,0.35,0.3,0.25,0.21,0.18,0.15,0.125,0.1,0.088,0.07,0.0625,0.05,0.04419,0.03716,0.03125,0.025,0.0221,0.01858,0.015625" ' + jp2_path
		
		#if jp2 not in jp2_list:
		try:
			subprocess.check_output(magick_string_jp2)
		except Exception as e:
			logger.error('Error running Imagemagick on %s: %s', tif, e)

	jp2_list = glob.glob1(issue_path,'*.jp2')
	if len(jp2_list) == len(tif_list):
		logger.info('Finished with derivs')
		issue_meta[issue]['derivs'] = 'TRUE'
	else:
		logger.error('Problem with derivs')
		issue_meta[issue]['derivs'] = 'FALSE'


###
# Create JP2 XML box and add to JP2
###
def jp2xml(issue):
	date = issue_meta[issue]['date']
	tif_list = issue_meta[issue]['tifs']
	page_count = len(tif_list)
	page_num = 1

	logger.info('Starting to add XML to JP2s...')

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

	logger.info('Finished with JP2 XML')



###
# OCR with Tesseract
###
def ocr(issue):
	tif_list = issue_meta[issue]['tifs']
	hocr_list = glob.glob1(issue_path,'*.hocr')
	pdf_list = glob.glob1(issue_path,'*.pdf')

	logger.info('Starting OCR...')

	for file in tif_list:
		file_path = os.path.join(issue_path, file)
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
	logger.info('Finished OCR')


###
# Downsample PDFs with ImageMagick
###
def downsample_pdf(issue):
    pdf_list = glob.glob1(issue_path,'*.pdf')

    logger.info('Downsampling PDFs...')

    for a_pdf in pdf_list:
        hires_pdf_path = issue_path + sep + a_pdf
        lowres_pdf_path = hires_pdf_path.replace('.pdf','_lo.pdf')
        gs_string_pdf = '"C:\\Program Files\\gs\\gs9.22\\bin\\gswin64c.exe" -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook -dAutoRotatePages=/None -dNOPAUSE -dQUIET -dBATCH -sOutputFile=' + lowres_pdf_path + ' ' + hires_pdf_path

        try:
            subprocess.check_output(gs_string_pdf)
        except Exception as e:
            logger.error('Error with file %s: %s', a_pdf, e)

        try:
            os.remove(hires_pdf_path)
            os.rename(lowres_pdf_path, hires_pdf_path)
        except Exception as e:
            logger.error('Problem trying to remove and rename file %s: %s', a_pdf, e)

    logger.info('Downsampled PDFs')


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
		# advance the count
		pg_count += 1

	output = issue_path + '\\BAR_' + issue + '.pdf'
	out = file(output, 'wb')
	merger.write(out)
	merger.close()
	logger.info('Created issue PDF')


###
# Transform HOCR to ALTO using Saxon and XSL
###
def hocr2alto(issue):
	xsl_filename = 'hocr2alto2.1.xsl'
	hocr_list = glob.glob1(issue_path,'*.hocr')
	xml_list = glob.glob1(issue_path,'*.xml')

	# Transform
	for hocr in hocr_list:
		hocr_filename = issue_path + sep + hocr
		xml = hocr.replace('.hocr','.xml')
		xml_filename = issue_path + sep + xml
		
		saxon_string = 'java -cp C:\saxon\saxon9he.jar net.sf.saxon.Transform -t -s:{} -xsl:{} -o:{}'.format(hocr_filename, xsl_filename, xml_filename)

		try:
			subprocess.check_output(saxon_string)
		except Exception as e:
			logger.error('Error transforming %s: %s', hocr, e)

		# remove HOCR
		try:
			os.remove(hocr_filename)
		except Exception as e:
			logger.error('Problem trying to remove file %s: %s', hocr, e)

	logger.info('Created ALTO XML')


###
# Move issues to QC folder
###
def to_QC(issue):
	source = source_path+issue
	destination = destination_path+issue

	try:
		shutil.move(source, destination)
		logger.info('Moved to QC')
	except Exception as e:
		logger.error('Error moving %s to QC: %s', issue, e)


###
# Create METS XML
###
def create_METS(issue):
	
	xml = 'BAR_' + issue + '_mets.xml'
	output_path = issue_path + sep + xml
	xml_list = glob.glob1(issue_path,'*.xml')

	if xml not in xml_list:

		try:

			vol = issue_meta[issue]['vol']
			issue_no = issue_meta[issue]['issue_no']
			page_ct = issue_meta[issue]['page_count']
			date = issue_meta[issue]['date']
			timestamp = '{:%Y-%m-%dT%H:%M:%S}'.format(datetime.datetime.now())
			JP2list = glob.glob1(issue_path,'*.jp2')

			sec1_label = escape(issue_meta[issue]['sec1_label'])
			sec2_label = escape(issue_meta[issue]['sec2_label'])
			sec3_label = escape(issue_meta[issue]['sec3_label'])
			sec4_label = escape(issue_meta[issue]['sec4_label'])

			sec1_page_range = issue_meta[issue]['sec1_page_ct'].split('-')
			sec2_page_range = issue_meta[issue]['sec2_page_ct'].split('-')
			sec3_page_range = issue_meta[issue]['sec3_page_ct'].split('-')
			sec4_page_range = issue_meta[issue]['sec4_page_ct'].split('-')

			#parse sections
			sec1_start = sec1_page_range[0]
			sec1_end = sec1_page_range[1]

			if sec2_page_range != ['']:
				sec2_start = sec2_page_range[0]
				sec2_end = sec2_page_range[1]

			if sec3_page_range != ['']:
				sec3_start = sec3_page_range[0]
				sec3_end = sec3_page_range[1]
			else:
				sec3_start = None

			if sec4_page_range != ['']:
				sec4_start = sec4_page_range[0]
				sec4_end = sec4_page_range[1]
			else:
				sec4_start = None

			count = 1
			pages = {}
			sections = {}
			while count <= int(page_ct):
				page = {}
				if count >= int(sec1_start) and count <= int(sec1_end):
					sections['1'] = sec1_label
					page['sec_num'] = '1'
					page['sec_label'] = sec1_label
				elif sec2_start is not None and count >= int(sec2_start) and count <= int(sec2_end):
					sections['2'] = sec2_label
					page['sec_num'] = '2'
					page['sec_label'] = sec2_label
				elif sec3_start is not None and count >= int(sec3_start) and count <= int(sec3_end):
					sections['3'] = sec3_label
					page['sec_num'] = '3'
					page['sec_label'] = sec3_label
				elif sec4_start is not None and count >= int(sec4_start) and count <= int(sec4_end):
					sections['4'] = sec4_label
					page['sec_num'] = '4'
					page['sec_label'] = sec4_label

				pages[str(count)] = page
				count += 1

			mets_open = '<mets TYPE="urn:library-of-congress:ndnp:mets:newspaper:issue" PROFILE="urn:library-of-congress:mets:profiles:ndnp:issue:v1.5" LABEL="Bay area reporter (San Francisco, Calif. : 1971), ' + date + '" xmlns:mix="http://www.loc.gov/mix/" xmlns:ndnp="http://www.loc.gov/ndnp" xmlns:premis="http://www.loc.gov/standards/premis" xmlns:mods="http://www.loc.gov/mods/v3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:dsig="http://www.w3.org/2000/09/xmldsig#" xmlns="http://www.loc.gov/METS/">'
			metsHdr = '<metsHdr CREATEDATE="' + timestamp + '"><agent ROLE="CREATOR" TYPE="ORGANIZATION"><name>GLBT Historical Society</name></agent></metsHdr>'
			issueMODS = '<dmdSec ID="issueModsBib"><mdWrap MDTYPE="MODS" LABEL="Issue metadata"><xmlData><mods:mods><mods:relatedItem type="host"><mods:identifier type="lccn">sn92019460</mods:identifier><mods:part><mods:detail type="volume"><mods:number>' + vol + '</mods:number></mods:detail><mods:detail type="issue"><mods:number>' + issue_no + '</mods:number></mods:detail><mods:detail type="edition"><mods:number>1</mods:number></mods:detail></mods:part></mods:relatedItem><mods:originInfo><mods:dateIssued encoding="iso8601">' + date + '</mods:dateIssued></mods:originInfo><mods:note type="noteAboutReproduction">Present</mods:note></mods:mods></xmlData></mdWrap></dmdSec>'
			xml_string = mets_open + metsHdr + issueMODS

			count = 1
			for section in sections:
				sec_num = str(count)
				if count > 1:
					separator = ': '
				else:
					separator = ''

				sectionMODS = '<dmdSec ID="sectionModsBib' + sec_num + '"><mdWrap MDTYPE="MODS" LABEL="Section metadata"><xmlData><mods:mods><mods:part><mods:detail type="section label"><mods:number>Section ' + sec_num + ' of ' + str(len(sections)) + separator + sections[sec_num] + '</mods:number></mods:detail></mods:part></mods:mods></xmlData></mdWrap></dmdSec>'
				xml_string += sectionMODS
				count += 1

			count = 1
			for page in pages:
				pg_num = str(count)
				page_MODS = '<dmdSec ID="pageModsBib' + pg_num + '"><mdWrap MDTYPE="MODS" LABEL="Page metadata"><xmlData><mods:mods><mods:part><mods:extent unit="pages"><mods:start>' + pg_num + '</mods:start></mods:extent><mods:detail type="page number"><mods:number>' + pg_num + '</mods:number></mods:detail></mods:part><mods:relatedItem type="original"><mods:physicalDescription><mods:form type="print" /></mods:physicalDescription><mods:location><mods:physicalLocation authority="marcorg" displayLabel="GLBT Historical Society">casfglbt</mods:physicalLocation></mods:location></mods:relatedItem><mods:note type="agencyResponsibleForReproduction" displayLabel="GLBT Historical Society">casfglbt</mods:note><mods:note type="noteAboutReproduction">Present</mods:note></mods:mods></xmlData></mdWrap></dmdSec>'
				xml_string += page_MODS
				count += 1

			amdSec = '<amdSec><!--TECHNICAL METADATA.--><!--All technical metadata is added by trusted validator--></amdSec>'
			xml_string += amdSec

			fileSec_open = '<fileSec>'
			xml_string += fileSec_open

			count = 1
			for page in pages:
				pg_num = str(count)
				pg_dig = str("%03d" % (count,))
				JP2path = 'BAR_' + issue + '_' + pg_dig + '.jp2'
				PDFpath = JP2path.replace('.jp2','.pdf')
				XMLpath = JP2path.replace('.jp2','.xml')

				fileSec_page = '<fileGrp ID="pageFileGrp' + pg_num + '"><file ID="serviceFile' + pg_num + '" USE="service" ADMID="primaryServicePremis' + pg_num + ' primaryServiceMix' + pg_num + '"><FLocat LOCTYPE="OTHER" OTHERLOCTYPE="file" xlink:href="' + JP2path + '" /></file><file ID="otherDerivativeFile' + pg_num + '" USE="derivative" ADMID="otherDerivativePremis' + pg_num + '"><FLocat LOCTYPE="OTHER" OTHERLOCTYPE="file" xlink:href="' + PDFpath + '" /></file><file ID="ocrFile' + pg_num + '" USE="ocr" ADMID="ocrTextPremis' + pg_num + '"><FLocat LOCTYPE="OTHER" OTHERLOCTYPE="file" xlink:href="' + XMLpath + '" /></file></fileGrp>'
				xml_string += fileSec_page
				count += 1
			
			fileSec_close = '</fileSec>'
			xml_string += fileSec_close

			structMap_open = '<structMap xmlns:np="urn:library-of-congress:ndnp:mets:newspaper"><div TYPE="np:issue" DMDID="issueModsBib">'
			xml_string += structMap_open

			count = 1
			for page in pages:
				pg_num = str(count)
				next_page = str(count+1)
				prev_page = str(count-1)
				if count > 1 and pages[pg_num]['sec_label'] == pages[prev_page]['sec_label']:
					structMap_sect = ''
				else:
					structMap_sect = '<div TYPE="np:section" DMDID="sectionModsBib' + pages[pg_num]['sec_num'] + '">'

				structMap_page = '<div TYPE="np:page" DMDID="pageModsBib' + pg_num + '"><fptr FILEID="serviceFile' + pg_num + '" /><fptr FILEID="otherDerivativeFile' + pg_num + '" /><fptr FILEID="ocrFile' + pg_num + '" /></div>'
				
				if count < len(pages) and pages[pg_num]['sec_label'] == pages[next_page]['sec_label']:
					structMap_sect_close = ''
				else:
					structMap_sect_close = '</div>'

				xml_string += structMap_sect + structMap_page + structMap_sect_close
				count += 1

			structMap_close = '</div></structMap>'
			mets_close = '</mets>'
			xml_string += structMap_close + mets_close

			# serialize the string to XML
			tree = etree.fromstring(xml_string)

			# write out to METS XML file
			with open(output_path, 'wb') as f:
				f.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
				f.write(etree.tostring(tree, pretty_print = True))
			logger.info('Created METS XML')

		except Exception as e:
			logger.error('Could not create METS XML for %s', issue)

	else:
		logger.info('METS XML already exists!')

###
# Move QC'd issues to backup
###
def to_archive():
	source_path = 'C:\\BAR\\toArchive\\'
	backup_path = 'G:\\Dropbox (GLBTHS)\\Archive\\BAR\\'

	logger.info('Let\'s move completed issues to Archive')
	for root, dirs, files in os.walk(source_path):

		if dirs:

			for issue in dirs:
				issue_path = os.path.join(root, issue)

				logger.info('Cleaning up any non-rotated TIFFs...')
				# since we've QCed this issue by now, let's clean up any remaning non-rotated tiffs
				for file in os.listdir(issue_path):
					if '_orig' in file:
						file_path = os.path.join(issue_path,file)
						os.remove(file_path)

				year = issue[0:4]
				destination = backup_path + year + sep + issue

				try:
					logger.info('Trying to move %s to Archive...', issue)
					shutil.move(issue_path, destination)
					logger.info('Moved %s to Archive', issue)
				except Exception as e:
					logger.error('Error moving %s to Archive: %s', issue, e)

			logger.info('Moved issues to Archive')

		else:
			logger.info('Nothing to archive right now.')

###
# Start processing
###

# Logging
# Set up logging (found here: https://fangpenlin.com/posts/2012/08/26/good-logging-practice-in-python/)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# create a file handler
now = datetime.datetime.now()
logfile = now.strftime("%Y-%m-%d-%H-%M") + '.log'
handler = logging.FileHandler('logs\\' + now.strftime("%Y-%m-%d-%H-%M") + '.log')
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)

# Starting the run
logger.info('=======================')
logger.info('Script started...')

# Constants
source_path = 'C:\\BAR\\toProcess\\'
destination_path = 'C:\\BAR\\toQC\\'

sep = '\\'

LCCN = 'sn92019460' #Library of Congress Call Number for Bay Area Reporter

os.startfile('logs\\' + logfile)
issue_meta = get_metadata()
process_list = process()

for issue in process_list:
	issue_path = source_path + issue
	
	logger.info('========== %s =========', issue)

	create_METS(issue)
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

	logger.info('Finished processing %s \n', issue)

to_archive()

logger.info('ALL DONE')
logger.info('=======================')