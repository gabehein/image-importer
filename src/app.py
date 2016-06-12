#! /usr/bin/env python

import sys
import os

from PyQt4 import QtGui, QtCore

import importer

class ProcessThread(QtCore.QThread):
    def __init__(self, files, destdir, importer):
        QtCore.QThread.__init__(self)
        self.files = files
        self.destdir = destdir
        self.importer = importer
        
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.signal_status_update)
        self.timer.start(250)
        
    def __del__(self):
        self.wait()
    
    def get_status(self):
#         print self.importer.status
        return self.importer.status
        
    def run(self):
        self.importer.process_file_list(self.files, self.destdir)
            
    def signal_status_update(self):
        self.emit(QtCore.SIGNAL('update_progress'))
          
class CameraImporter(QtGui.QWidget):
    def __init__(self):
        super(CameraImporter, self).__init__()
        
    def Init(self):
        self.srcdir = ''
        self.destdir = ''
        
        self.layout = QtGui.QVBoxLayout()
        
        self.src = QtGui.QPushButton('Source: ')
        self.src.clicked.connect(self.SrcCallback)
        self.layout.addWidget(self.src)
        
        self.dest = QtGui.QPushButton('Destination: ')
        self.dest.clicked.connect(self.DestCallback)
        self.layout.addWidget(self.dest)
        
        self.process = QtGui.QPushButton('Start Import')
        self.process.clicked.connect(self.ImportCallback)
        self.layout.addWidget(self.process)
        
        self.textbox = QtGui.QTextEdit()
        self.textbox.setReadOnly(True)
        self.textbox.setLineWrapMode(QtGui.QTextEdit.NoWrap)

        self.layout.addWidget(self.textbox)
        
        self.progress_bar = QtGui.QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)

        self.layout.addWidget(self.progress_bar)
        self.setLayout(self.layout)
        
        self.importer = importer.Importer(self.log)
        
        self.procthread = None
        
    def SrcCallback(self):
        self.srcdir = str(QtGui.QFileDialog.getExistingDirectory(parent=None, caption=QtCore.QString('Source: ')))
        self.src.setText('Source: %s' % self.srcdir)
        self.log('Source: %s' % self.srcdir)
         
    def DestCallback(self):
        self.destdir = str(QtGui.QFileDialog.getExistingDirectory(parent=None, caption=QtCore.QString('Destination: ')))
        self.dest.setText('Destination: %s' % self.destdir)
        self.log('Destination: %s' % self.destdir)
            
    def ImportCallback(self):
        self.log('---------- Processing source directory ----------')
        files = []
        os.path.walk(self.srcdir, self.importer.process_source_directory, files)
        self.log('Found %d files' % len(files))    
        self.procthread = ProcessThread(files, self.destdir, self.importer)
        self.procthread.start()
        self.connect(self.procthread, QtCore.SIGNAL('update_progress'), self.update_progress_bar)
        
    def update_progress_bar(self):
        if (not self.procthread):  
            self.progress_bar.setValue(0)
#             print 'xxx'
        else:
            if not self.procthread.isFinished():
                self.progress_bar.setValue(self.procthread.get_status())
#                 print 'yyy'
            else:
                self.progress_bar.setValue(self.progress_bar.maximum())

    def log(self, text):
        self.textbox.moveCursor(QtGui.QTextCursor.End)
        self.textbox.insertPlainText('%s\n' % text)
        sb = self.textbox.verticalScrollBar()
        sb.setValue(sb.maximum())
        
def main():
    app = QtGui.QApplication(sys.argv)

    w = CameraImporter()
    w.setWindowTitle('Camera Importer')
    w.Init()
    w.show()
                           
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    main()
    
