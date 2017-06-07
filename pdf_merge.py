###
# Merge (append) PDFs
###
import os, re
from PyPDF2 import PdfFileMerger, PdfFileReader

# get dirs and pdfs
source_path = 'C:\\BAR\\toQC\\'
pdf_dict = {}

for root, dirs, files in os.walk(source_path):
	for dir in dirs:
		issue = os.path.join(root, dir)
		issue_pgs = {}

		file_list = [f for f in os.listdir(issue) if f.endswith('pdf')]
		for afile in file_list:
			file_path = issue+'\\'+afile

			# get the page number from the filename with some regex
			m = re.search('_(\d{3}).pdf', file_path)

			if m is not None:
				pg_num = str(int(m.group(1)))
				# add to dict
				issue_pgs[pg_num] = file_path.replace(source_path, '')

		pdf_dict[dir] = issue_pgs

# start merging
for issue in pdf_dict:
	merger = PdfFileMerger()

	# start counter
	pg_count = 1

	# append PDFs
	for apage in pdf_dict[issue]:
		pdf_filename = source_path+pdf_dict[issue][str(pg_count)]

		pdf = file(pdf_filename, 'rb')
		merger.append(pdf)
		# Advance count
		pg_count += 1

	output = source_path+'\\BAR_'+issue+'.pdf'
	out = file(output, 'wb')
	merger.write(out)
	merger.close()
	print 'Created PDF for', issue

print 'All done'