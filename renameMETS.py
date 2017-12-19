import os

source_path = 'F:\\Dropbox (GLBTHS)\\Archive\\BAR'

def rename_mets():

	mets_list = []

	for root, dirs, files in os.walk(source_path):
		for file in files:
			if '.xml' in file and len(file) == 16:
				filepath = os.path.join(root,file)
				new_name = filepath.replace('.xml','_mets.xml')

				try:
					os.rename(filepath,new_name)
				except Exception as e:
					print e

	print 'Files have been renamed.'

rename_mets()