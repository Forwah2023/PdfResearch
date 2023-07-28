from setuptools import setup
setup(
name='PdfResearch',
version='1.0',
author='Forwah Amstrong Tah',
author_email='lmsoftware2023@gmail.com',
description=open('README.md', 'r').read(),
url="",
license='GPL-3.0 license',
keywords='Pdf docx txt search Python Re',
package_dir={'PdfResearch': ''},
packages=['PdfResearch'],
install_requires=['PyQt5','docx2txt==0.8','PyMuPDF==1.22.5','PyQtChart'],
python_requires='>=3.9',
include_package_data=True,
entry_points={
'console_scripts': [
'pdfre=PdfResearch.__main__ : main']
},
)