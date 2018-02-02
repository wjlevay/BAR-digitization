import logging, os, shutil, datetime

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
				destination = backup_path + year + '\\' + issue

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

to_archive()

logger.info('ALL DONE')
logger.info('=======================')