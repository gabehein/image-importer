#! /usr/bin/env python

import os
# import sys
import time

from PIL import Image
import exifread
import shutil
import hashlib 

TYPE_IMG = 1
TYPE_RAW = 2
TYPE_VID = 3

EXT_IMG = ['.jpg', '.jpeg', '.tif', '.tiff']
EXT_VID = ['.mp4', '.mov', '.mts', '.avchd']
EXT_RAW = ['.raw', '.arw']

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
        self.timestr = None
        
class Importer(object):
    def __init__(self, log):
        self.log = log
        self.status = 0.0
    
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
        self.status = 0.0
        cnt = 0
        n = len(filelist)
        for f in filelist:
            self.status = 100.0 * float(cnt) / float(n)
            cnt += 1
            path = destination_root + '/' + f.year + '-' + f.month
            
            if f.type == TYPE_RAW:
                path += '/raw'
            if f.type == TYPE_VID:
                path += '/vid'
    
            pathfull = path + '/' + f.year + '_' + f.month + '_' + f.timestr + '_' + f.name
            if not os.path.exists(path):
                os.makedirs(path)
                    
            count = 0
            move = True
            if (os.path.exists(pathfull)):
                # Check if hash is equal
                src_hash = self.hashfile(f.pathfull)
                dst_hash = self.hashfile(pathfull)
                if (src_hash != dst_hash):
                    while (os.path.exists(pathfull)):  
                        self.log('Duplicate file found: ' + str(count) + 'dest, ' + pathfull, ' src, ' + f.pathfull)            
                        count += 1
                        pathfull = self.insert_suffix(pathfull, 'copy')                    
                else:
                    self.log('Skipping duplicate file: ' + pathfull)
                    move = False
    
            if move:      
                if copy:
                    shutil.copy(f.pathfull, pathfull)
                else:
                    shutil.move(f.pathfull, pathfull)
                                               
    
    
    def process_source_directory(self, filelist, dirname, files):
        for filename in files:
            info = FileInfo()
            for ext in EXT_IMG:
                if (filename.lower().endswith(ext)):
                    info.type = EXT_IMG
                    break
                
            if (not info.type):
                for ext in EXT_RAW:
                    if (filename.lower().endswith(ext)):
                        info.type = TYPE_RAW
                        break
    
            if (not info.type):
                for ext in EXT_VID:
                    if (filename.lower().endswith(ext)):
                        info.type = TYPE_VID
                        break
                
            if (info.type):
                info.path = dirname 
                info.name = filename
                info.pathfull = info.path + '/' + info.name
                info.time = None
                s = os.stat(info.pathfull)
                file_time = s[8]           
                try:
                    info.time = self.get_exif_date_pil(info.pathfull)
                except:
                    try:
                        info.time = self.get_exif_date_exifread(info.pathfull)
                    except:
                        self.log('Something is terribly wrong! Both PIL and exifread raises exception')
            
                if (not info.time):
                    self.log('Timestamp from metadata was blank for %s. Using file timestamp instead.' % (info.pathfull))
                    info.time = file_time
                        
                if info.time:
                    info.year = time.strftime("%Y", time.gmtime(info.time))
                    info.month = time.strftime("%m", time.gmtime(info.time))
                    info.timestr = time.strftime("%H%M%S", time.gmtime(info.time))
                    filelist.append(info)
                else:
                    self.log('xxxxxxxxxxxxxxxxxxxxxxxxxxxx error!')
    
