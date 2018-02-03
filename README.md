# BAR Digitization Project

Scripts and resources for the Bay Area Reporter digitization project at GLBT Historical Society.

Mostly Python scripts written for Python 2.7 in a Windows 10 environment, plus some extra stuff.

## processBAR.py

### Processes TIFFs of scanned newspaper pages to conform with the CDNC's specs on digitized newspapers

This is an attempt at some automated image processing that can be run on a folder of TIFFs, ideally at night or on the weekend, while no one is using the local machine for scanning. 

It aims to produce from the TIFF masters all derivative files required by the California Digital Newspaper Collection. Since CDNC specifications are similar to those of the National Digital Newspaper Program, this script could be adapted to create files for that program as well.

### What it does

For each newspaper issue in the toProcess directory:

* grabs metadata from Google Sheet
* checks if # of pages in Sheet matches # of TIFFs; if so, adds to the queue
* uses [Marek Mauder's Deskew](http://galfar.vevb.net/wp/projects/deskew/) to determine an angle of rotation so text is close to 180 degrees
* invokes ImageMagick to rotate at this angle
* uses coproc's function rotatedRectWithMaxArea, [found here](https://stackoverflow.com/questions/16702966/rotate-image-and-crop-out-black-borders/16778797), to calculate the maximal area within the rotated image
* invokes ImageMagick to crop to this rectangle
* invokes Exiftool to add standard metadata to TIFFs
* invokes ImageMagick to create JPEG-2000 derivatives
* creates an XML metadata "box" and uses Exiftool to add this to the JP2s
* invokes Tesseract OCR twice: first to create an HOCR file, then a PDF
* invokes Ghostscript to "downsample" the hi-res PDFs
* uses PyPDF2's PDFFileMerger to append each PDF to the one before, creating a single PDF for the entire issue
* transforms HOCR to ALTO XML using Saxon and a version of filak's [HOCR-to-ALTO stylesheet](https://github.com/filak/hOCR-to-ALTO), edited to avoid creating empty content boxes
* creates a METS XML document for the issue
* moves the issue to the QC queue
* updates the Google Sheet to indicate the issue was processed

### How we're using it in-house

You could start the script manually by opening a command prompt, navigating to its directory, and typing 

`python processBAR.py`

But we've created a Windows batch file that runs every night via Windows Task Scheduler, so you shouldn't need to kick it off manually unless there's a problem with the scheduler.

## reprocessBAR.py

### Reprocesses a newspaper issue after user fixes problem pages

This is a version of the processBAR.py script that's used for fixing issues that had problem pages. It does not deskew pages because we assume pages have already been deskewed and/or fixed manually. It regenerates all TIFF tags and only produces derivatives for those TIFFs which do not have them.

The idea here is, you QC an issue and find, for example, a page that was badly rotated. You would first move this issue to the toFix folder, go into the issue directory, delete all files for that page EXCEPT for the original, unrotated and not-cropped, TIFF, then kick off this script, which will fix the embedded TIFF tags, generate new derivatives for the fixed page only, regenerate the issue PDF, and move the issue back into the QC queue.

Start this script by opening a command prompt, navigating to the script directory, and typing 

`python reprocessBAR.py`

## archiveBAR.py

### Moves QC'd issues to an external drive

You shouldn't have to mess with this script. There's a .bat file that runs every night via Windows Task Scheduler to shuttle issues that have passed QC to the external drive.

## uploadBAR.py

### Uploads a year's worth of issues to the Internet Archive

For each newspaper issue for the year selected by the user, the script:

* grabs metadata from the Google Sheet
* creates a temporary .zip archive comprising all TIFFs
* invokes the `ia` command-line interface to upload the .zip and create a new object with certain metadata
* updates the Google Sheet to indicate issue was uploaded to IA

To run this script:

Open a command prompt and navigate to the script's directory. Type `python uploadBAR.py`. The system will ask which year you want to upload; enter the 4-digit year. It may take as many as 24 hours to upload a year's worth of issues to IA.

### Additional step after upload completes

Internet Archive does some fancy stuff to try to determine which page of a book is the title page; then it sets that page as the thumbnail and as the default start page when you open the Book Reader.

But for most newspapers and other periodicals, technical manuals, etc., this behavior is not ideal because page 1 should always be the title page. 

The after-the-fact fix/workaround is to run frontpage.sh, courtesy of Jason Scott at Internet Archive, which, given a collection ID (in our case "bayareareporter") or a text file with object IDs on each line, will update each object and designate page 1 as the title page.

After the year's worth of BAR issues has been uploaded, and the last issue has had a few minutes to process, you should run this shell script.

To run the script, you need to run the program Bash on Ubuntu on Windows. This will bring up a Linux-like command line.

`blevay@BOOK-ARCH:~$ sh frontpage.sh bayareareporter`

Let this run and it will fix every object in the collection. Thanks, Jason!

## One-off scripts

### fix_xml.py

Regenerates ALTO XML to ensure there are no empty content boxes.

You shouldn't have to run this again, since we edited the HOCR-to-ALTO stylesheet to accomplish the same thing. But it's here for posterity. If you need to use this, open the script in a text editor and edit the `source` value to the directory you want to target.

### copyALTO.py

Copies ALTO XML files from the external drive to the internal drive.

Another one-off script written to solve a specific problem: After running fix_xml.py we needed to send just the updated ALTO files back to the CDNC.

### renameMETS.py

Yet another one-off script that simply renamed our METS XML files to conform to CDNC standards.