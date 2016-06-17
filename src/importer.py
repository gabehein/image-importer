#! /usr/bin/env python

import os
# import sys
import time

from PyQt4 import QtGui, QtCore

from PIL import Image
import exifread
import shutil
import hashlib 

TYPE_IMG = 1
TYPE_RAW = 2
TYPE_VID = 3
TYPE_OTHER = 4

EXT_IMG = ['.jpg', '.jpeg', '.tif', '.tiff', '.png', '.bmp', '.svg']
EXT_VID = ['.mp4', '.mov', '.mts', '.avchd', '.avi', '.wmv', ',.ogv', '.m4v']
EXT_RAW = ['.3fr', '.ari', '.arw', '.bay', '.crw', '.cr2', '.cap', '.data', '.dcs', '.dcr', '.dng', '.drf', '.eip', '.erf', '.fff', '.iiq', '.k25', '.kdc', '.mdc', '.mef', '.mos', '.mrw', '.nef', '.nrw', '.obm', '.orf', '.pef', '.ptx', '.pxn', '.r3d', '.raf', '.raw', '.rwl', '.rw2', '.rwz', '.sr2', '.srf', '.srw', '.tif', '.x3f']

# what tags use to redate file (use first found)
DT_TAGS = ["Image DateTime", "EXIF DateTimeOriginal", "DateTime"]
        
class FileInfo(object):
    def __init__(self):
        self.time = None
        self.path = None
        self.name = None
        self.type = None
        
        self.pathfull = None
        self.year = None
        self.month = None
        self.day = None
        self.timestr = None

class ReportSource(object):
    def __init__(self):
        self.files_total = 0
        self.files_img = 0
        self.files_raw = 0
        self.files_vid = 0
        self.files_other = 0
        self.files_with_exif_time = 0
        self.files_without_exif_time = 0
    
    def str(self):
        out = '\n'
        out += 'Total                  : %d\n' % self.files_total
        out += 'Images                 : %d\n' % self.files_img
        out += 'Raw                    : %d\n' % self.files_raw
        out += 'Videos                 : %d\n' % self.files_vid
        out += 'Other                  : %d\n' % self.files_other
        out += 'Files with exif time   : %d\n' % self.files_with_exif_time
        out += 'Files without exif time: %d\n' % self.files_without_exif_time
        out += 'Will attempt to import : %d\n' % (self.files_total - self.files_other)
        out += 'Which should equal     : %d\n' % (self.files_img + self.files_raw + self.files_vid)
        return out

class ReportDest(object):
    def __init__(self):
        self.all = []
        self.skipped_unrecognized = []
        self.skipped_duplicate = []
        self.renamed = []
        self.imported = []
            
    def str(self):
        out = '\n'
        out += 'Unrecognized      : %d\n' % len(self.skipped_unrecognized)
        out += 'Duplicate         : %d\n' % len(self.skipped_duplicate)
#         out += str(self.skipped_duplicate) + '\n'
        out += 'Renamed           : %d\n' % len(self.renamed)
        out += 'Imported          : %d\n' % len(self.imported)
        out += 'Which should equal: %d' % (len(self.all) - len(self.skipped_duplicate) - len(self.skipped_unrecognized))
        return out
                   
class Importer(QtGui.QWidget):
    def __init__(self):
        super(Importer, self).__init__()
#         self.log = log
        self.progress = 0.0
        
        self.report_source = ReportSource()
        self.report_dest = ReportDest()
    
    def log(self, text):
        self.emit(QtCore.SIGNAL('log_entry'), text)
    
    def hashfile(self, path, blocksize=65536):
        afile = open(path, 'rb')
        hasher = hashlib.md5()
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
        afile.close()
        return hasher.hexdigest()
    
    def insert_suffix(self, filename, suffix):
        bits = filename.split('.')
        out = ''
        for i in range(len(bits) - 1):
            out += bits[i]
        out += '_' + suffix
        out += '.' + bits[-1]
        return out
    
    def insert_prefix(self, filename, prefix):
        out = prefix + '_' + filename
        return out
                
    def exif_info_to_time(self, ts):
        """changes EXIF date ('2005:10:20 23:22:28') to number of seconds since 1970-01-01"""
        tpl = time.strptime(ts + 'UTC', '%Y:%m:%d %H:%M:%S%Z')
        return time.mktime(tpl)
    
    def get_exif_date_exifread(self, filepath):
        """return EXIF datetime using exifread (formerly EXIF)"""
        dt_value = None   
        f = open(filepath, 'rb')
        try:
            tags = exifread.process_file(f)
            for dt_tag in DT_TAGS:
                try:
                    dt_value = '%s' % tags[dt_tag]
                    break
                except:
                    continue
            if dt_value:
                exif_time = self.exif_info_to_time(dt_value)
                return exif_time
        finally:
            f.close()
        return None
    
    def get_exif_date_pil(self, jpegfn):
        """return EXIF datetime using PIL"""
        im = Image.open(jpegfn)
        if hasattr(im, '_getexif'):
            exifdata = im._getexif()
            dt_value = exifdata[0x9003]
            exif_time = self.exif_info_to_time(dt_value)
            return exif_time
        return None
    
    def process_file_list(self, filelist, destination_root, copy=True):
        self.report_dest.all = filelist
        self.progress = 0.0
        cnt = 0
        n = len(filelist)
        for f in filelist:
            self.progress = 100.0 * float(cnt) / float(n)
            cnt += 1
            path = os.path.join(destination_root, f.year + '-' + f.month)
            
            if f.type == TYPE_RAW:
                path = os.path.join(path, 'raw')  # '+= '/raw'
            elif f.type == TYPE_VID:
                path = os.path.join(path, 'vid')  # += '/vid'
            elif f.type == TYPE_IMG:
                pass
            else:
                self.log('Skipping unrecognized file type found: %s' % f.pathfull)
                self.report_dest.skipped_unrecognized.append(f.pathfull)
                continue
    
            pathfull = os.path.join(path, f.year + '_' + f.month + '_' + f.day + '_' + f.timestr + '_' + f.name)
#             pathfull = os.path.join(path, f.name)
            if not os.path.exists(path):
                os.makedirs(path)
                    
            count = 0
            move = True
            # TODO(Gabe) - Make this behavior for duplicates more customizable
            if (os.path.exists(pathfull)):
                # Check if hash is equal
                src_hash = self.hashfile(f.pathfull)
                dst_hash = self.hashfile(pathfull)
                if (src_hash != dst_hash):
                    while (os.path.exists(pathfull)):  
                        self.log('Same file name found for multiple files who are not identical. Renaming and keeping both: ' + str(count) + 'dest, ' + pathfull + ' src, ' + f.pathfull)            
                        count += 1
                        pathfull = self.insert_suffix(pathfull, 'copy')
                    self.report_dest.renamed.append([f.pathfull, pathfull])
                else:
                    self.log('Skipping duplicate file (same filename and identical file contents): ' + pathfull)
                    self.report_dest.skipped_duplicate.append([f.pathfull, pathfull])
                    move = False
    
            if move: 
                self.report_dest.imported.append([f.pathfull, pathfull])     
                if copy:
                    shutil.copy2(f.pathfull, pathfull)
                else:
                    shutil.move(f.pathfull, pathfull)
                                               
#         self.emit(QtCore.SIGNAL('process_file_list'))
    
    def count_files(self, root):
        self.file_count = 0
        os.path.walk(root, self._count_files, self.file_count)
    
    def _count_files(self, filelist, destination_root):
        pass
        
        
    def process_source_directory(self, filelist, dirname, names):
        n = len(names)
        self.progress = 0.0
        cnt = 0.0
        for filename in names:
            self.progress = cnt / n
            cnt += 1
            fullname = os.path.join(dirname, filename)
            if not os.path.isdir(fullname):
                self.report_source.files_total += 1
                info = FileInfo()
                for ext in EXT_IMG:
                    if (filename.lower().endswith(ext)):
                        info.type = TYPE_IMG
                        self.report_source.files_img += 1
                        break     
                
                if (not info.type):
                    for ext in EXT_RAW:
                        if (filename.lower().endswith(ext)):
                            info.type = TYPE_RAW
                            self.report_source.files_raw += 1
                            break
                
                if (not info.type):
                    for ext in EXT_VID:
                        if (filename.lower().endswith(ext)):
                            info.type = TYPE_VID
                            self.report_source.files_vid += 1
                            break
                        
                if (not info.type): 
                    self.log('Skipping unrecognized file type: %s' % fullname)
                    self.report_source.files_other += 1
                    continue
    
                info.path = dirname 
                info.name = filename
                info.pathfull = fullname
                info.time = None
                s = os.stat(info.pathfull)
                file_time = s[8]           
                try:
                    info.time = self.get_exif_date_pil(info.pathfull)
                except:
                    try:
                        info.time = self.get_exif_date_exifread(info.pathfull)
                    except:
                        self.log('PIL and exifread raises exceptions for %s' % filename)
            
                if (not info.time):
                    self.log('Timestamp from metadata was blank for %s. Using file timestamp instead.' % (info.pathfull))
                    info.time = file_time
                    self.report_source.files_without_exif_time += 1
                else:
                    self.report_source.files_with_exif_time += 1
                        
                if info.time:
                    info.year = time.strftime("%Y", time.gmtime(info.time))
                    info.month = time.strftime("%m", time.gmtime(info.time))
                    info.day = time.strftime("%d", time.gmtime(info.time))
                    info.timestr = time.strftime("%H%M%S", time.gmtime(info.time))
                    filelist.append(info)

