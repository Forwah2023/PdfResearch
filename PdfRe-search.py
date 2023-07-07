import os
import re
import sys
import time
import operator  # for sorting results

from PyQt5 import QtWidgets as qtw
from PyQt5 import QtGui as qtg
from PyQt5 import QtCore as qtc

import fitz  # from installed PyMuPDF package

Found_total = []
# previous file paths and texts in current folder
search_history = []
WIDTH = 800
HEIGHT = 800


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
        # radio button area
        radio_layout = qtw.QHBoxLayout()
        self.pdf_radio = qtw.QRadioButton("pdf", self)
        self.word_radio = qtw.QRadioButton("Word", self)
        self.both_radio = qtw.QRadioButton("Both", self)
        radio_layout.addWidget(self.pdf_radio)
        radio_layout.addWidget(self.word_radio)
        radio_layout.addWidget(self.both_radio)
        layout.addLayout(radio_layout)
        # List label
        label_layout = qtw.QHBoxLayout()
        Files = qtw.QLabel("File(s)", self)
        Files.setAlignment(qtc.Qt.AlignCenter)
        Found = qtw.QLabel("Found", self)
        Found.setAlignment(qtc.Qt.AlignCenter)
        label_layout.addWidget(Files)
        label_layout.addWidget(Found)
        layout.addLayout(label_layout)
        # List area
        list_layout = qtw.QHBoxLayout()
        self.left_list = qtw.QListWidget(self)
        self.right_list = qtw.QListWidget(self)
        list_layout.addWidget(self.left_list)
        list_layout.addWidget(self.right_list)
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
        # signals and slots
        self.search_btn.clicked.connect(
            lambda: self.search_pdf_text(self.input_text.text())
        )
        # create thread object
        self.te = TextEtract()
        self.text_extract_thread = qtc.QThread()
        self.te.moveToThread(self.text_extract_thread)
        self.te.finished.connect(self.text_extract_thread.quit)
        self.text_extract_thread.start()
        # signals and slots
        self.te.fileChanged.connect(lambda f, g: self.left_list.addItem(f))
        self.te.FolderSelected.connect(self.text_extract_thread.start)
        self.te.FolderSelected.connect(self.te.search_files)
        self.te.FolderSelected.connect(lambda: self.label_prog.setText("Scanning... "))
        self.te.finished.connect(lambda: self.label_prog.setText("Done!"))
        self.te.fileChanged.connect(self.te.compute_percentage)
        self.te.PercentageChanged.connect(lambda i: self.prog.setValue(i))
        self.show()

    def search_pdf_text(self, pattern):
        self.clear_prev_search()
        if pattern != "":
            for searched in search_history:
                match = re.findall(pattern, searched[2], flags=re.IGNORECASE)
                if match:
                    Found_total.append((searched[0], searched[1], len(match), match))
            # sort in descending order of  len(match)
            sorted_results = sorted(
                Found_total, key=operator.itemgetter(2), reverse=True
            )
            self.right_list.addItems([item[0] for item in sorted_results])

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
            search_history = []


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

    qtc.pyqtSlot(str)

    def compute_percentage(self):
        int_perc = round((self.file_done / self.file_count) * 100)
        self.PercentageChanged.emit(int_perc)


class MainWindow(qtw.QMainWindow):
    def __init__(self, mainwidget):
        super().__init__()
        self.setCentralWidget(mainwidget)
        self.resize(qtc.QSize(WIDTH, HEIGHT))
        # self.setWindowIcon(qtg.QIcon('Icons/'))
        self.setWindowTitle("PdfRe-search")
        # menu bar
        menubar = self.menuBar()
        Folder_menu = menubar.addMenu("Folder")
        Folder_menu.addAction("Open Folder", self.get_folder)
        help_menu = menubar.addMenu("Help")
        # about_action=help_menu.addAction('About',)
        # signals and slots
        # os.normpath to covert all slahses to \
        mainwidget.te.fileChanged.connect(
            lambda f, g: self.statusBar().showMessage(
                os.path.normpath(os.path.join(g, f))
            )
        )
        mainwidget.te.finished.connect(
            lambda: self.statusBar().showMessage(
                "Scanned {} of {} files".format(
                    mainwidget.te.file_count - mainwidget.te.error_count,
                    mainwidget.te.file_count,
                )
            )
        )
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
        # mainwidget = self.centralWidget()
        for folderName, subfolders, filenames in os.walk(Fpath):
            for filename in filenames:
                if filename.endswith(".pdf"):
                    mainwidget.te.file_roster.append((filename, folderName))
                    mainwidget.te.file_count += 1


# start = time.time()
# search_files(Fpath)
# end = time.time()
# print(end - start)


# for result in sorted_results:
# print(result[0],"\t",result[1],"\n")
def main():
    app = qtw.QApplication(sys.argv)
    Central_w = MainWidget()
    MW = MainWindow(Central_w)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
