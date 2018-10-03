#!/usr/bin/env python

from Delta import Delta, CompleteDelta, execute
import bencoder
import os

def opentorrent(file):
    a = open(file, "rb")
    b = bencoder.decode(a.read())
    a.close()
    return b

def fileintorr(torrent, ifile):
    if b'files' in torrent[b'info']:
        for i_ in range(len(torrent[b'info'][b'files'])):
            i = torrent[b'info'][b'files'][i_]
            if i[b'path'][0].decode("utf-8") == ifile:
                return i + 1
    else:
        if torrent[b'info'][b'name'].decode("utf-8") == ifile:
            return 1
    return 0

def replaceintorr(torrent, ifile, data):
    if b'files' in torrent[b'info']:
        for i_ in range(len(torrent[b'info'][b'files'])):
            i = torrent[b'info'][b'files'][i_]
            if i[b'path'][0].decode("utf-8") == ifile:
                del torrent[b'info'][b'files'][i_]
                data.reverse()
                for j in data:
                    torrent[b'info'][b'files'].insert(i_, j)
#    else:
#        if torrent[b'info'][b'name'].decode("utf-8") == ifile:
#            torrent[
#            return 1

def sortByFiles(torrent, files):
    res = []
    if b'files' in torrent[b'info']:
        for i in torrent[b'info'][b'files']:
            for k in files:
                if i[b'path'][0].decode("utf-8") == k[1]:
                    res.append(k)
    else:
        return files
    return res

def CDelta(lists, dirD, dirF):
    superD = []
    for i in lists:
        superD += i['delta']
    CompleteDelta(superD)

def Torrent(itorrent, dir1, dir2, idelta, dirD, files):
    torrent = opentorrent(itorrent)
    sfiles = []
    d = 0
    files = sortByFiles(files)
    for i in files:
        S = True
        df1 = os.path.join(dir1, i[0])
        df2 = os.path.join(dir2, i[1])
        if not os.path.isfile(df1):
            print("File not found: {}".format(i[0]))
            S = False
        if not os.path.isfile(df2):
            print("File not found: {}".format(i[1]))
            S = False
        if not fileintorr(torrent, i[0]):
            print("File not found in torrent: {}".format(i[0]))
            S = False
        if S:
            execute('xdelta3 -e -s "{}" "{}" "{}.delta"'.format(df1, df2, d))
            sfiles.append({'file1': i[0], 'file2': i[1], 'delta': Delta("d.delta".format(d), idelta, i[0], i[1])})
            d += 1
    CDelta(sfiles, dirD, dir2)
