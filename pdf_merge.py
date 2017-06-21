###
# Merge (append) PDFs
###
import os, re
from PyPDF2 import PdfFileMerger, PdfFileReader

def pdf_merge(issue):

	pdf_dict = {}
	issue_pgs = {}

	file_list = [f for f in os.listdir(issue_path) if f.endswith('pdf') and len(f) == 20]
	for afile in file_list:
		# get the page number from the filename with a slice
		pg_num = int(afile[13:16])
		# add to dict
		issue_pgs[pg_num] = afile

	pdf_dict[issue] = issue_pgs

	# start merging
	for issue in pdf_dict:
		merger = PdfFileMerger()

		# start counter
		pg_count = 1

		# append PDFs
		for apage in pdf_dict[issue]:
			pdf_filename = issue_path + '\\' + pdf_dict[issue][pg_count]

			pdf = file(pdf_filename, 'rb')
			merger.append(pdf)
			# Advance count
			pg_count += 1

		output = issue_path+'\\BAR_'+issue+'.pdf'
		out = file(output, 'wb')
		merger.write(out)
		merger.close()
		print 'Created PDF for', issue

	print 'All done'



source_path = 'C:\\BAR\\toQC\\'
for root, dirs, files in os.walk(source_path):
	for dir in dirs:
		issue = dir
		issue_path = os.path.join(root, dir)
	
		pdf_merge(issue)