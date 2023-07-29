# PdfResearch
PdfResearch is free software to extract and search text from multiple files in a folder. This software currently supports .pdf, .docx, and .txt 
files. It allows for the search of keyword combinations. When done, it ranks the search results according to the highest count and distribution 
of keywords found.

## IMPORTANT FEATURES
1. Searches a folder of .pdf, .docx, and .txt files for keywords within. 
2. Supports searches using multiple keywords using pipe key (|)
3. Built on Python's Re module but does not support group search
4. Display search results based on search counts and Keyword distribution.

## INSTALLATION
###### Python-based installation

1. From the command line:
    ```
     python setup.py install
   ```
   and 
2. Run the package from command line as
   ```
   pdfre
   ```
3. Or simply run __main__.py after completing step 1:
  ```
     python __main__.py
   ```
###### Desktop installation
1. Download the *.exe* setup from [SourceForge](https://pdfresearch.sourceforge.io)
2. Install and run.

# Developing
1. Add functionality to extract text from more files.

## Built With
* Python 3.9
* PyQtChart
* QtChart
* docx2txt 
* PyMuPDF

# IMPORTANT NOTES
This version does not support the group search feature of the *Re* module.

###### AUTHOR
Forwah Amstrong Tah, Ph.D. <lmsoftware2023@gmail.com>

