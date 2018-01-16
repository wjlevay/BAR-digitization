import os, lxml.etree as ET

source = "G:\\Dropbox (GLBTHS)\\Archive\\BAR\\"
# source = 'test\\'

for root, dirs, files in os.walk(source):
	for file in files:
		if '.xml' in file and 'mets' not in file and len(file) == 20:

			# parse source.xml with lxml
			filepath = os.path.join(root,file)
			tree = ET.parse(filepath)

			for element in tree.xpath('.//*[@CONTENT=""]'):
				element.getparent().remove(element)

			for element in tree.xpath('.//*[count(child::*) = 0]'):
				if 'TextLine' in element.tag:
					element.getparent().remove(element)

			for element in tree.xpath('.//*[count(child::*) = 0]'):
				if 'TextBlock' in element.tag:
					element.getparent().remove(element)

			for element in tree.xpath('.//*[count(child::*) = 0]'):
				if 'ComposedBlock' in element.tag:
					element.getparent().remove(element)

			# write out to new file
			newfile = filepath.replace('.xml','_new.xml')
			with open(newfile, 'wb') as f:
				f.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
				f.write(ET.tostring(tree, pretty_print = True))
			print 'Writing', newfile
		
			os.remove(filepath)
			os.rename(newfile, filepath)

	print 'Done'