import os 
import re
from threading import Thread
import time
import operator
import json

import fitz # from installed PyMuPDF package
pattern=r"(anti-phase| synchronization| electromagnetic induction)" # String to be searched
Fpath=r"C:\Users\AMSTRONG\Desktop\Research ideas" # Folder to be searched
count_total=[]
#load previous file paths and texts
try:
    with open('history.json', 'r') as f:
        search_history=json.load(f)
except FileNotFoundError:
    search_history=[]

def parse_pdf(filename,folderName):
    if not search_pdf_history(filename,folderName):
        curr_file=os.path.join(folderName,filename)# holds current file path str
        with fitz.open(curr_file) as f:
            P_text=''.join([ p.get_text() for p in f])
            search_history.append((filename,folderName,P_text))

def search_pdf_text(pattern,text):
     return re.findall(pattern,text,flags=re.IGNORECASE)

def search_pdf_history(filename,folderName):
    for searched in search_history:
        if (filename,folderName)==(searched[0],searched[1]):
            match=search_pdf_text(pattern,searched[2])
            if match:
                count_total.append((filename,len(match),match))
            return True
    return False

def search_files(dir_path):
    for folderName, subfolders, filenames in os.walk(dir_path):
        for filename in filenames:
            if filename.endswith('.pdf'):
                #t = Thread(target=search_pdf, args=(filename,folderName))
                #t.start()
                #t.join()
                parse_pdf(filename,folderName)


start = time.time()
search_files(Fpath)
end = time.time()
print(end - start)
#store current session file paths and texts
with open('history.json', 'w') as f:
    json.dump(search_history,f)

sorted_results=sorted(count_total,key=operator.itemgetter(1), reverse=True)

for result in sorted_results:
    print(result[0],"\t",result[1],"\n")
