import os
import re
import sys
import operator  # for sorting results
from collections import Counter  # for bar chart plot

from PyQt5 import QtWidgets as qtw
from PyQt5 import QtGui as qtg
from PyQt5 import QtCore as qtc
from PyQt5 import QtChart as qtch

import fitz  # from installed PyMuPDF package

Found_total = []
# previous file paths and texts in current folder
search_history = []
#styling elements
WIDTH = 1600
HEIGHT = 850
# settings
settings = qtc.QSettings('LMS', 'PdfRe-search')

styl = """
QMainWindow{
 background-color:#abbed4;  
}
QLineEdit{
font-size: 10pt;
margin:30px;
border-radius: 10px;
}
QLabel{
font-size: 10pt;
}
QListwidget{
background-color: #f5f5f5;
border: 1px solid #dcdcdc;
border-radius: 10px;
}
QListWidget::item {
background-color: #ffffff;
padding: 5px;
margin-bottom: 5px;
}
QListWidget::item:selected {
background-color: #0078d7;
color: #ffffff;
}
QPushButton {
background-color: #0078d7;
border: none;
color: white;
padding: 10px 20px;
text-align: center;
text-decoration: none;
font-size: 16px;
margin: 4px 2px;
border-radius: 50%;
}
QPushButton:hover {
background-color: #005cbf;
}
QPushButton:pressed {
background-color: #004eaa;
}
"""


class MainWidget(qtw.QWidget):
    def __init__(self):
        super().__init__()
        layout = qtw.QVBoxLayout()
        self.setLayout(layout)
        # search area
        search_layout = qtw.QHBoxLayout()
        self.search_btn = qtw.QPushButton("Search", self)
        self.input_text = qtw.QLineEdit(
            "",
            self,
            placeholderText="Type text to search here. Use | separator for multiple keywords",
        )
        search_layout.addWidget(self.input_text)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)
        # List label
        label_layout = qtw.QHBoxLayout()
        Files = qtw.QLabel("All Files", self)
        heading_font = qtg.QFont('SansSerif', 12,qtg.QFont.Bold)
        heading_font.setStretch(qtg.QFont.ExtraExpanded)
        Files.setFont(heading_font)
        Files.setAlignment(qtc.Qt.AlignCenter)
        Found = qtw.QLabel("Files Found", self)
        Found.setAlignment(qtc.Qt.AlignCenter)
        Found.setFont(heading_font)
        Distribution=qtw.QLabel("Results Distribution", self)
        Distribution.setAlignment(qtc.Qt.AlignCenter)
        Distribution.setFont(heading_font)
        label_layout.addWidget(Files)
        label_layout.addWidget(Found)
        label_layout.addWidget(Distribution)
        layout.addLayout(label_layout)
        # List area
        list_layout = qtw.QHBoxLayout()
        self.left_list = qtw.QListWidget(self)
        self.right_list = qtw.QListWidget(self)
        self.rv = ResultsView()  # new
        list_layout.addWidget(self.left_list)
        list_layout.addWidget(self.right_list)
        list_layout.addWidget(self.rv)
        layout.addLayout(list_layout)
        # ProgressBar area
        prog_layout = qtw.QHBoxLayout()
        self.prog = qtw.QProgressBar()
        self.prog.setRange(0, 100)
        # self.prog.setFixedSize(qtc.QSize(WIDTH,20))
        self.label_prog = qtw.QLabel(self)
        prog_layout.addWidget(self.label_prog)
        prog_layout.addWidget(self.prog)
        layout.addLayout(prog_layout)
        # text search thread
        self.ts = TextSearch()
        self.text_search_thread = qtc.QThread()
        self.ts.moveToThread(self.text_search_thread)
        self.ts.finished.connect(self.text_search_thread.quit)
        self.text_search_thread.start()
        # signals and slots for text_search thread
        self.search_btn.clicked.connect(self.text_search_thread.start)
        self.search_btn.clicked.connect(self.set_search_params)
        self.ts.searchStarted.connect(self.ts.search_pdf_text)
        self.ts.searchStarted.connect(lambda: self.label_prog.setText("Searching... "))
        self.ts.indexChanged.connect(lambda i: self.ts.compute_percentage(i))
        self.ts.PercentageChanged.connect(lambda i: self.prog.setValue(i))
        self.ts.resultsAvailable.connect(
            lambda x: self.right_list.addItems([item[0] for item in x])
        )

        # create thread object
        self.te = TextEtract()
        self.text_extract_thread = qtc.QThread()
        self.te.moveToThread(self.text_extract_thread)
        self.te.finished.connect(self.text_extract_thread.quit)
        self.text_extract_thread.start()

        # signals and slots for pdf search thread
        self.te.fileChanged.connect(lambda f, g: self.left_list.addItem(f))
        self.te.FolderSelected.connect(self.text_extract_thread.start)
        self.te.FolderSelected.connect(self.te.search_files)
        self.te.FolderSelected.connect(lambda: self.label_prog.setText("Scanning... "))
        self.te.fileChanged.connect(self.te.compute_percentage)
        self.te.PercentageChanged.connect(lambda i: self.prog.setValue(i))

        self.show()

    def set_search_params(self):
        pattern = self.input_text.text()
        if pattern != "":
            # clear prev search, sets search parameters for ts object, and starts search
            self.clear_prev_search()
            self.ts.pattern = pattern
            self.ts.search_history = search_history
            self.ts.searchStarted.emit()
        else:
            self.ts.emptyField.emit()

    def clear_prev_search(self, newFold=False):
        global Found_total
        global search_history
        self.right_list.clear()
        Found_total = []
        if newFold:
            self.left_list.clear()
            self.te.file_count = 0
            self.te.file_done = 0
            self.prog.setValue(0)
            self.te.file_roster = []
            # search_history = []


class TextSearch(qtc.QObject):
    finished = qtc.pyqtSignal()
    PercentageChanged = qtc.pyqtSignal(int)
    searchStarted = qtc.pyqtSignal()
    resultsAvailable = qtc.pyqtSignal(list)
    indexChanged = qtc.pyqtSignal(int)
    emptyField = qtc.pyqtSignal()
    pattern = ""
    search_history = []
    found_count = 0
    sorted_results = []

    def __init__(self):
        super().__init__()

    qtc.pyqtSlot()

    def search_pdf_text(self):
        index = 1  # starting index of search in search history
        for searched in self.search_history:
            if settings.value("IGNORECASE", True, type=bool):
                match = re.findall(self.pattern, searched[2], flags=re.IGNORECASE)
            else:
                match = re.findall(self.pattern, searched[2])
            if match:
                Found_total.append((searched[0], searched[1], len(match), match))
            self.indexChanged.emit(index)
            index += 1
        # sort in descending order of  len(match)
        self.sorted_results = sorted(
            Found_total, key=operator.itemgetter(2), reverse=True
        )
        self.found_count = len(self.sorted_results)
        self.resultsAvailable.emit(self.sorted_results)
        self.finished.emit()

    qtc.pyqtSlot(int)

    def compute_percentage(self, index):
        int_perc = round((index / len(self.search_history)) * 100)
        self.PercentageChanged.emit(int_perc)


class TextEtract(qtc.QObject):
    finished = qtc.pyqtSignal()
    fileChanged = qtc.pyqtSignal(str, str)
    FolderSelected = qtc.pyqtSignal()
    PercentageChanged = qtc.pyqtSignal(int)
    file_roster = []
    file_count = 0
    file_done = 0
    error_count = 0

    def __init__(self):
        super().__init__()

    qtc.pyqtSlot(str)

    def search_files(self):
        for pair in self.file_roster:
            self.parse_pdf(*pair)
        self.finished.emit()

    qtc.pyqtSlot(str, str)

    def parse_pdf(self, filename, folderName):
        if not self.search_pdf_history(filename, folderName):
            curr_file = os.path.join(
                folderName, filename
            )  # holds current file path str
            try:
                if filename.endswith(".pdf"):
                    with fitz.open(curr_file) as f:
                        P_text = "".join([p.get_text() for p in f])
                search_history.append((filename, folderName, P_text))
                self.file_done += 1
                self.fileChanged.emit(filename, folderName)
            except RuntimeError as e:
                print(e, filename)
                # update error count but don't include it in left list
                self.file_done += 1
                self.error_count += 1

    qtc.pyqtSlot(str, str)

    def search_pdf_history(self, filename, folderName):
        for searched in search_history:
            if (filename, folderName) == (searched[0], searched[1]):
                self.file_done += 1
                self.fileChanged.emit(filename, folderName)
                return True
        return False

    qtc.pyqtSlot(str, str)

    def compute_percentage(self):
        int_perc = round((self.file_done / self.file_count) * 100)
        self.PercentageChanged.emit(int_perc)


class ResultsView(qtch.QChartView):

    def __init__(self):
        super().__init__()
        self.chart = qtch.QChart()
        self.setChart(self.chart)
        self.series = qtch.QBarSeries()
        self.chart.addSeries(self.series)
        self.bar_set = qtch.QBarSet("Search results distribution")
        self.series.append(self.bar_set)
        #self.series.setLabelsVisible(True)
        self.show()
    def set_results(self,data):
        self.results=data

    def plot_data(self,row):
        #values to be plotted
        data=Counter(self.results[row][3]) # 3 is a reference to key words used in search
        data_counts=self.results[row][2]# 2 is reference to count from findall results
        self.bar_set.append(data.values())
        # axes
        x_axis = qtch.QBarCategoryAxis()
        x_axis.append(data.keys())
        self.chart.setAxisX(x_axis)
        self.series.attachAxis(x_axis)

        y_axis = qtch.QValueAxis()
        y_axis.setRange(0, max(data.values()))
        self.chart.setAxisY(y_axis)
        self.series.attachAxis(y_axis)
        #title
        self.chart.setTitle(self.results[row][0])# 0 is a reference for filename 

class SettingsWidget(qtw.QWidget):
    def __init__(self):
        super().__init__()
        self.resize(qtc.QSize(400,300))
        self.setStyleSheet(styl)
        self.setWindowIcon(qtg.QIcon('Icons/logo.png'))
        self.setWindowTitle("Settings")
        layout=qtw.QVBoxLayout()
        self.setLayout(layout)
        tab_widget = qtw.QTabWidget()
        layout.addWidget(tab_widget)
        # file input tab
        container_types=qtw.QWidget(self)
        tab_widget.addTab(container_types, 'File Type')
        sub_layout1=qtw.QVBoxLayout()
        container_types.setLayout(sub_layout1)
        self.pdf_type=qtw.QCheckBox("pdf",self,checked=settings.value("ALLOWPDF", True, type=bool))
        self.doc_type=qtw.QCheckBox("docx",self,checked=settings.value("ALLOWDOC", False, type=bool))
        self.txt_type=qtw.QCheckBox("txt",self,checked=settings.value("ALLOWTXT", False, type=bool))
        sub_layout1.addWidget(self.pdf_type)
        sub_layout1.addWidget(self.doc_type)
        sub_layout1.addWidget(self.txt_type)
        ###Search parameters tab
        container_search=qtw.QWidget(self)
        sub_layout2=qtw.QVBoxLayout()
        container_search.setLayout(sub_layout2)
        tab_widget.addTab(container_search, 'Search parameters')
        self.case_type=qtw.QCheckBox("Ingnore case",self,checked=settings.value("IGNORECASE", True, type=bool))
        sub_layout2.addWidget(self.case_type)
        #apply settings button
        apply_button=qtw.QPushButton("Apply settings",self)#(Requires restart!)
        apply_button.setFixedSize(150,50)
        layoutH_bottom=qtw.QHBoxLayout()
        layoutH_bottom.addWidget(apply_button)
        layout.addLayout(layoutH_bottom)
        layout.addWidget(qtw.QLabel("(Requires restart to be effective!)",self))
        #signals and slots
        apply_button.clicked.connect(self.validate_settings)

    def validate_settings(self):
        settings.setValue("ALLOWPDF",self.pdf_type.isChecked())
        settings.setValue("ALLOWDOC",self.doc_type.isChecked())
        settings.setValue("ALLOWTXT",self.txt_type.isChecked())
        settings.setValue("IGNORECASE",self.case_type.isChecked())
        self.close()



class MainWindow(qtw.QMainWindow):
    def __init__(self, mainwidget):
        super().__init__()
        self.setCentralWidget(mainwidget)
        self.resize(qtc.QSize(WIDTH, HEIGHT))
        self.setStyleSheet(styl)
        self.setWindowIcon(qtg.QIcon('Icons/logo.png'))
        self.setWindowTitle("PdfRe-search")
        #menu bar
        menubar = self.menuBar()
        Folder_menu = menubar.addMenu("Folder")
        Folder_menu.addAction("Open Folder", self.get_folder)
        self.sett=SettingsWidget()
        settings_menu = menubar.addMenu("Settings")
        settings_menu.addAction("Show settings",self.sett.show)
        help_menu = menubar.addMenu("Help")
        about_action=help_menu.addAction('About')
        #add file types
        file_types_list=[]
        if settings.value("ALLOWPDF",True, type=bool):
            file_types_list.append(".pdf")
        if settings.value("ALLOWDOC",False, type=bool):
            file_types_list.append(".docx")
        if settings.value("ALLOWTXT",False, type=bool):
            file_types_list.append(".txt")
        self.File_types=tuple(file_types_list)
        # signals and slots
        #os.normpath to covert all slahses to \
        mainwidget.te.fileChanged.connect(
            lambda f, g: self.statusBar().showMessage(
                os.path.normpath(os.path.join(g, f))
            )
        )
        # display message when scan finished
        mainwidget.te.finished.connect(
            lambda: self.update_status(
                "Scanned",
                mainwidget.te.file_count - mainwidget.te.error_count,
                mainwidget.te.file_count,
                "Done!",
            )
        )
        # dispay message when search finished
        mainwidget.ts.finished.connect(
            lambda: self.update_status(
                "Found", mainwidget.ts.found_count, mainwidget.te.file_count, "Done!"
            )
        )

        mainwidget.ts.emptyField.connect(
            lambda: self.statusBar().showMessage("Empty search field!")
        )
        # signal to plot
        mainwidget.ts.resultsAvailable.connect(mainwidget.rv.set_results)
        mainwidget.right_list.currentRowChanged.connect(mainwidget.rv.plot_data)
        self.show()

    def get_folder(self):
        Fpath = qtw.QFileDialog.getExistingDirectory(
            self, "Select Directory", "/home", qtw.QFileDialog.ShowDirsOnly
        )
        if Fpath:
            self.statusBar().showMessage(Fpath)
            mainwidget = self.centralWidget()
            mainwidget.clear_prev_search(True)  # True for left list clear()
            mainwidget.te.roster = self.get_roster(Fpath, mainwidget)
            mainwidget.te.FolderSelected.emit()

    def get_roster(self, Fpath, mainwidget):
        # gets list of file names
        for folderName, subfolders, filenames in os.walk(Fpath):
            for filename in filenames:
                if filename.endswith(self.File_types):
                    mainwidget.te.file_roster.append((filename, folderName))
                    mainwidget.te.file_count += 1

    def update_status(self, messge1, message2, message3, message4):
        self.statusBar().showMessage(
            "{} {} of {} files".format(messge1, message2, message3)
        )
        # Done, Scanning... or searching...
        self.centralWidget().label_prog.setText(message4)


####

def main():
    app = qtw.QApplication(sys.argv)
    Central_w = MainWidget()
    MW = MainWindow(Central_w)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
### discarded radio section
 #       # radio button area
  #      radio_layout = qtw.QHBoxLayout()
   #     self.pdf_radio = qtw.QRadioButton("pdf", self)
    #    self.word_radio = qtw.QRadioButton("Word", self)
     #   self.both_radio = qtw.QRadioButton("Both", self)
      #  radio_layout.addWidget(self.pdf_radio)
       # radio_layout.addWidget(self.word_radio)
        #radio_layout.addWidget(self.both_radio)
        #layout.addLayout(radio_layout)