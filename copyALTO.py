###
# Copy all ALTO XML files from external drive to local drive so we can resend to CDNC
###

import os, shutil

source = 'G:\\Dropbox (GLBTHS)\\Archive\\BAR\\'

for root, dirs, files in os.walk(source):

	for file in files:
		if file.endswith('xml') and len(file) == 20:
			year = file[4:8]
			issue = file[4:12]
			filepath = source + year + '\\' + issue + '\\' + file
			copydir = 'C:\\BAR\\ALTO\\' + issue
			copypath = os.path.join(copydir,file)
			if os.path.exists(copydir) == False:
				os.mkdir(copydir)
			shutil.copy2(filepath, copypath)
			print 'copied', file

print 'done'