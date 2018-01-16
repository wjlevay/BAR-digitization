###
# GLBT Historical Society
# BAR Digitization Project File Deletion
# by Bill Levay
# Run this script on a year's worth of scanned issues once we've (1) confirmed those issues are   
# published on the CDNC site, and (2) performed some QC on those CDNC issues.
###

import os, glob, sys

def get_delete_list(year):

	delete_list = []

	for root, dirs, files in os.walk(source_path + str(year)):
		for dir in dirs:
			issue = dir
			issue_path = os.path.join(root, dir)

			jp2_list = glob.glob1(issue_path,'*.jp2')
			pdf_list = glob.glob1(issue_path,'*.pdf')

			for jp2 in jp2_list:
				jp2_path = os.path.join(issue_path,jp2)
				delete_list.append(jp2_path)

			for pdf in pdf_list:
				if len(pdf) == 20:
					pdf_path = os.path.join(issue_path,pdf)
					delete_list.append(pdf_path)
	
	return delete_list

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

def delete_files(a_list):

	for a_file in a_list:
		try:
			os.remove(a_file)
		except:
			print('There was a problem removing ' + 'a_file')
	print('Files have been deleted.')


source_path = 'G:\\Dropbox (GLBTHS)\\Archive\\BAR\\'
year = raw_input('Enter the year from which to delete files: ')

del_list = get_delete_list(year)

if del_list is not None:
	if query_yes_no('Delete ' + str(len(del_list)) + ' files?', None):
		delete_files(del_list)
	else:
		print('No files deleted.')
else:
	print('No files to delete.')

print ('All done!')