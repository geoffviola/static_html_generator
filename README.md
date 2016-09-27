# Static HTML Generator
a script to extend HTML to facilitate repeating HTML and image thumbnails

## Design
The intent was to keep HTML mostly intact. Instead of using a new language, the script replacing certain keywords and creates thumbnails.

## Dependencies
 - Python 3.5.1
 - bs4
 - PIL

## Setup
Setup a directory structure as follows
 - resources: files that may be included in other files, but don't get put into the final structure. For example, a header.html file, which could be the header for every HTML file.
 - skeleton: files that will go to the final structure.
 
## Features
 - Include another file from the resources folder with %filename.html%. For example, %header.html% will replace that string with the contents of the header.html file
 - Automatically generate thumbnails
   - Uses the width and height attributes are set to the img tag
   - Generates when the filename is skeleton\_image\_width\_height. For example, my\_cool\_image\_100\_200.png will turn into a thumbnail of width 100 and height 200.
 - All the HTML files are automatically formatted for readability. 
 
##  Options
 - -w sets the working directory
 - -b sets the a multiplier on the size of the thumbnails when the width and height attributes in the img tag are set
 
## Output
The result is all the files in the skeleton file processed and put into the output directory.
