###
# GLBT Historical Society
# BAR Digitization Project -- Upload to Internet Archive
# This script creates a temporary zipfile of TIFFs for an issue of the BAR,
# gathers metadata from our project Google Sheet to a dictionary, and uploads
# the package to the Internet Archive.
# by Bill Levay
###

import zipfile, os, datetime, gspread, subprocess, sys
from internetarchive import upload
from oauth2client.service_account import ServiceAccountCredentials

###
# Get issue metadata from Google Sheet
###
def get_metadata(issue):
	# Google Sheet setup
	scope = ['https://spreadsheets.google.com/feeds']
	credentials = ServiceAccountCredentials.from_json_keyfile_name('BAR Digitization-fb1d45aa1d32.json', scope)
	gc = gspread.authorize(credentials)

	issue_meta = {}

	# Open spreadsheet and worksheet
	sh = gc.open_by_key('1tZjpKZfkGsuUD1iEx_blclJiNQBcfiGhkdXPn9voYGo')
	wks = sh.worksheet('itemList')
	print 'Getting metadata from Google Sheet...'

	# Find cell by finding issue date in Sheet
	try:
		cell_list = wks.findall(issue)

		# Get the row, then get some values in that row
		row = str(cell_list[0].row)

		vol = wks.acell('C' + row).value
		issue_no = wks.acell('D' + row).value
		page_ct = wks.acell('F' + row).value
		publisher = wks.acell('S' + row).value
		ia_upload = wks.acell('W' + row).value

		date = issue[0:4] + '-' + issue[4:6] + '-' + issue[6:8]
		datetext = datetime.datetime.strptime(issue, '%Y%m%d').strftime('%d %B %Y').lstrip('0')

		ia_id = 'BAR_' + issue
		ia_title = 'Bay Area Reporter, Volume {}, Number {}, {}'.format(vol, issue_no, datetext)

		# Add issue metadata to the issue_meta dict
		issue_meta['vol'] = vol
		issue_meta['issue_no'] = issue_no
		issue_meta['page_ct'] = page_ct
		issue_meta['publisher'] = publisher
		issue_meta['date'] = date
		issue_meta['datetext'] = datetext
		issue_meta['ia_upload'] = ia_upload
		issue_meta['ia_id'] = ia_id
		issue_meta['ia_title'] = ia_title


	except Exception as e:
		print 'Error with metadata for {}: {}'.format(issue, e)

	print issue_meta
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
		wks.update_acell('W' + row, issue_meta['ia_upload'])

	except Exception as e:
		print 'Could not update Google Sheet for {}: {}'.format(issue, e)

###
# Create a list of issues to process
###
def process():

	process_list = []

	if os.path.exists(source_path):

		for issue in os.listdir(source_path):
			if len(issue) == 8:
				process_list.append(issue)
		print process_list
		return process_list

	else:
		print 'Sorry, we cannot find any issues from', year


###
# Create temporary zipfile of TIFFs
###
def zip(issue):

	# open zipfile
	print 'creating archive'
	with zipfile.ZipFile(zip_path, mode='w', allowZip64 = True) as zf:
	
		# loop through files and add TIFFs to ZIP
		for file in os.listdir(issue_path):
			if '.tif' in file:
				file_path = os.path.join(issue_path, file)

				try:
					print 'writing', file
					zf.write(file_path)
				except Exception as e:
					print 'An error occurred with', file
					pass

	# close zipfile
	zf.close()
	print 'Created zipfile for', issue

	#TO DO: confirm zipfile has same number of files as pages in spreadsheet


###
# Upload to IA
###
def upload(issue):

	# create a command-line string to run as a subprocess
	ia_string = 'ia --config-file "config\\ia.ini" upload {} "{}" -m "title:{}" -m "date:{}" -m "publisher:{}" -m "rights:Copyright BAR Media, Inc." -m "contributor:GLBT Historical Society" -m "coverage:San Francisco (Calif.)" -m "mediatype:texts" -m "collection:bayareareporter" -m "language:English"'.format(issue_meta['ia_id'], zip_path, issue_meta['ia_title'], issue_meta['date'], issue_meta['publisher'])

	try:
		print 'Uploading...'
		r = subprocess.check_output(ia_string, stderr=subprocess.STDOUT)
		print r
		issue_meta['ia_upload'] = 'TRUE'
	except Exception as e:
		print e
		pass

	# TO DO: confirm upload before deleting zipfile

	# delete zip
	try:
		os.remove(zip_path)
		print 'Removed', zip_path
	except Exception as e:
		print e
		pass


###
# Yes or No?
###
def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")

###
# Start processing
###

if __name__ == "__main__":

	year = raw_input('Enter the year you want to upload to Internet Archive: ')

	source_path = 'G:\\Dropbox (GLBTHS)\\Archive\\BAR\\{}\\'.format(year)

	process_list = process()

	if process_list is not None:

		if query_yes_no('Upload ' + str(len(process_list)) + ' issues from ' + year + '?', None):

			for issue in process_list:
				issue_path = source_path + issue
				issue_meta = get_metadata(issue)

				# check to make sure we didn't already upload this one
				if issue_meta['ia_upload'] == '':

					zip_path = 'G:\\{}_images.zip'.format(issue_meta['ia_id'])
					zip(issue)
					upload(issue)
					update_sheet(issue)
					print 'Finished with', issue, '- moving on to next issue.'

				else:
					print issue, 'was already uploaded to IA. Moving to next issue.'
		
		else:
			print('No issues uploaded.')
	else:
		print('No issues to upload.')
		
	print 'ALL DONE'