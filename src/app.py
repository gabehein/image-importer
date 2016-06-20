#! /usr/bin/env python

import sys
# import os

from PyQt4 import QtGui, QtCore

import importer

class ProcessDestDirectory(QtCore.QThread):
    def __init__(self, files, destdir, importer):
        QtCore.QThread.__init__(self)
        self.files = files
        self.destdir = destdir
        self.importer = importer
         
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.StatusUpdate)
        self.timer.start(150)
         
    def __del__(self):
        self.wait()
     
    def run(self):
        self.importer.ImportFiles(self.files, self.destdir)
        self.emit(QtCore.SIGNAL('ImportDoneCallback'))
        
    def StatusUpdate(self):
        self.emit(QtCore.SIGNAL('UpdateProgressBarCallback'), self.importer.progress)
 
class ProcessSourceDirectory(QtCore.QThread):
    def __init__(self, files, srcdir, importer):
        QtCore.QThread.__init__(self)
        self.files = files
        self.srcdir = srcdir
        self.importer = importer
         
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.StatusUpdate)
        self.timer.start(150)
         
    def __del__(self):
        self.wait()
     
    def run(self):
        self.importer.ProcessSourceDirectory(self.files, self.srcdir)
        # print 'xxxxxx Done processing source'
        self.emit(QtCore.SIGNAL('ProcessSourceDoneCallback'))
            
    def StatusUpdate(self):
        self.emit(QtCore.SIGNAL('UpdateProgressBarCallback'), self.importer.progress)
         
    
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
        
        # TODO(Gabe) - Need to add way of stopping processing midway through
#         self.stop = QtGui.QPushButton('Stop Import')
#         self.stop.clicked.connect(self.StopImportCallback)
#         self.layout.addWidget(self.stop)
        
        self.textbox = QtGui.QTextEdit()
        self.textbox.setReadOnly(True)
        self.textbox.setLineWrapMode(QtGui.QTextEdit.NoWrap)

        self.layout.addWidget(self.textbox)
        
        self.status_label = QtGui.QLabel('')
        self.layout.addWidget(self.status_label)
        
        self.progress_bar = QtGui.QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        
        self.layout.addWidget(self.progress_bar)
        self.setLayout(self.layout)
        
        # TODO(Gabe) - Add combobox for selecting between move files and copy files
        self.importer = importer.Importer()
        self.connect(self.importer, QtCore.SIGNAL('log_entry'), self.log)
        
        self.procthread = None
        self.files = []
        
    def SrcCallback(self):
        self.srcdir = str(QtGui.QFileDialog.getExistingDirectory(parent=None, caption=QtCore.QString('Source: ')))
        self.src.setText('Source: %s' % self.srcdir)
        self.log('Source: %s' % self.srcdir)
         
    def DestCallback(self):
        self.destdir = str(QtGui.QFileDialog.getExistingDirectory(parent=None, caption=QtCore.QString('Destination: ')))
        self.dest.setText('Destination: %s' % self.destdir)
        self.log('Destination: %s' % self.destdir)
            
    def ImportCallback(self):
        self.status_label.setText('Processing Source Directory')
        self.log('---------- Processing source directory ----------')
        # TODO(Gabe) - This should happen in its own thread and update the progress bar just like the process thread
        self.files = []
        self.procthread = ProcessSourceDirectory(self.files, self.srcdir, self.importer)
        self.connect(self.procthread, QtCore.SIGNAL('UpdateProgressBarCallback'), self.UpdateProgressBarCallback)
        self.connect(self.procthread, QtCore.SIGNAL('ProcessSourceDoneCallback'), self.ProcessSourceDoneCallback)
        self.procthread.start()
        
    def ProcessSourceDoneCallback(self):
        self.status_label.setText('Processing Source Complete')
#         self.log('Found %d files' % len(self.files))
        self.log(self.importer.report_source.str())
        
        self.status_label.setText('Performing Import')
        self.log('---------- Performing Import --------------------')
        self.procthread = ProcessDestDirectory(self.files, self.destdir, self.importer)
        self.connect(self.procthread, QtCore.SIGNAL('UpdateProgressBarCallback'), self.UpdateProgressBarCallback)
        self.connect(self.procthread, QtCore.SIGNAL('ImportDoneCallback'), self.ImportDoneCallback)
        self.procthread.start()
        
    
    def ImportDoneCallback(self):
        self.status_label.setText('Import Complete')
        self.log(self.importer.report_dest.str())
        
    def UpdateProgressBarCallback(self, progress):
        if (not self.procthread):  
            self.progress_bar.setValue(0)
        else:
            if not self.procthread.isFinished():
                self.progress_bar.setValue(progress)
            else:
                self.progress_bar.setValue(self.progress_bar.maximum())

    def log(self, text):
        t = '[LOG]: ' + text
        print t
        self.textbox.moveCursor(QtGui.QTextCursor.End)
        self.textbox.insertPlainText('%s\n' % t)
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
    
