#!/usr/bin/env python

from subprocess import Popen, PIPE
import os
import tempfile
import math

t = tempfile.TemporaryDirectory()

def execute(command):
    p = Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = p.communicate()
    return p.returncode, stdout, stderr

def checkfile(file_):
    if not os.path.isfile(file_):
        raise NameError("the file don't exist: {}".format(file_))

def Tinst(res, data, start):
    data = data[start:]
    while len(data) >= 2:
        data[1] = int(data[1])
        if "ADD" in data[0]:
            res.append({'name': data[0], 'len': data[1]})
            if len(data) > 2:
                data = data[2:]
            else:
                break      
        if "RUN" in data[0]:
            res.append({'name': data[0], 'len': data[1]})
            if len(data) > 2:
                data = data[2:]
            else:
                break
        if "CPY" in data[0]:
            res.append({'name': data[0], 'len': data[1], 'type': data[2][0], 'pos': int(data[2][2:])})
            if len(data) > 3:
                data = data[3:]
            else:
                break

def readDeltaInsts(idelta):
    k = execute('xdelta3 printdelta "{}"'.format(idelta))
    if k[0] != 0:
        raise Exception("Error reading {} delta file".format(idelta))
    r = k[1].decode("utf-8").split('\n')
    p = 0
    result = []
    while p < len(r):
        res = []
        while p < len(r) and (r[p] == "" or r[p][0] != " " or "Offset" in r[p]):
            p += 1
            if p >= len(r): return result
        while p < len(r) and (r[p] == "" or r[p][0] == " "):
            t = r[p].split(" ")
            while "" in t:
                t.remove("")
            if len(t) != 0: res.append(t)
            p += 1
        if len(res) != 0: result.append(res)
    result2 = []
    for i_ in range(len(result)):
        i = result[i_]
        for j in i:
            Tinst(result2, j, 2)
    return result2

def simplifyDelta(res):
    i = 0
    p = len(res) - 1
    while i < p:
        if res[i]['name'] == res[i+1]['name'] and res[i]['len'] + res[i]['pos'] == res[i+1]['pos']:
            res[i]['len'] += res[i+1]['len']
            del res[i+1]
            p += -1
        else:
            i += 1
    return res

def constructDelta(delta, orig, dest, idelta):
    ll = os.path.getsize(orig)
    pos = 0
    posd = 0
    res = []
    for j in delta:
        if "ADD" in j['name'] or "RUN" in j['name']:
            res.append({'name': idelta, 'pos': pos, 'len': int(j['len']), 'dest': dest, 'pos_dest': posd, 'delta': idelta})
            pos += j['len']
            posd += j['len']
        if "CPY" in j['name']:
            j['pos'] = int(j['pos'])
            j['len'] = int(j['len'])
            if "S" in j['type']:
                if j['len'] + j['pos'] > ll:
                    p1 = ll - j['pos']
                    p2 = j['len'] - (ll - j['pos'])
                    res.append({'name': orig, 'pos': j['pos'], 'len': p1, 'dest': dest, 'pos_dest': posd, 'delta': idelta})
                    res.append({'name': idelta, 'pos': pos, 'len': p2, 'dest': dest, 'pos_dest': posd + p1,'delta': idelta})
                    pos += p2
                else:
                    res.append({'name': orig, 'pos': j['pos'], 'len': j['len'], 'dest': dest, 'pos_dest': posd,'delta': idelta})
            if "T" in j['type']:
                res.append({'name': idelta, 'pos': pos, 'len': j['len'], 'dest': dest, 'pos_dest': posd,'delta': idelta})
                pos += j['len']
            posd += j['len']
    return simplifyDelta(res)

def deltapatch(delta, orig):
    r = open(orig, "wb")
    for i in delta:
        p = open(i['name'], "rb")
        p.seek(i['pos'])
        data = p.read(i['len'])
        if len(data) != i['len']:
            print(i)
            print("error reading {} bytes from {} pos".format(i[2], i[1]))
        r.write(data)
        p.close()
    r.close()

def checkdelta(delta, dest):
    pos = 0
    for i in delta:
        p = open(i['name'], "rb")
        p.seek(i['pos'])
        r.seek(pos)
        pr = p.read(i['len'])
        rr = r.read(i['len'])
        if pr != rr:
            print(i)
        pos += i['len']

def CompleteDelta(delta, dirD, dirF):
    pos = {}
    kk = {}
    fdelta = []
    for i in delta:
        if i['delta'] == i['name'] and i['delta'] not in fdelta:
            fdelta.append(i['delta'])
    for i in fdelta:
        kk[i] = open(os.path.join(dirD, i), "wb")
        pos[i] = 0
    for i in delta:
        if i['name'] in fdelta:
            kk[i['delta']].seek(i['pos'])
            r = open(os.path.join(dirF, i['dest']), "rb")
            r.seek(pos[i['delta']])
            rr = r.read(i['len'])
            r.close()
            kk[i['delta']].write(rr)
        pos[i['delta']] += i['len']
    for i in kk:
        kk[i].close()

def Delta(delta, idelta, orig, dest):
    a=readDeltaInsts(delta)
    return constructDelta(a, orig, dest, idelta)

def chs(delta):
    for i in delta:
        if i[1] + i[2] > os.path.getsize(i[0]):
            print(i)

# final file, [[part, delta]]
def ReconstructFile(old_file, newfiles, idelta):
    r = []
    for i in newfiles:
        if not os.path.isfile(i[1]):
            print("Constructing delta for {}".format(i[0]))
            out = execute('xdelta3 -e -s "{}" "{}" "{}"'.format(i[0], old_file, i[1]))
            if out[0] != 0:
                raise Exception("Error constructing delta file for {} to {} in {} delta file".format(i[0], old_file, i[1]))
        r.append({'delta': Delta(i[1], idelta, i[0], old_file), pos: 0})
    res = []
    pos = 0
    ll = os.path.getsize(old_file)
    if len(newfiles) == 1:
        return r[0]['delta']
    print("phrist phase")
    while pos < ll:
        sol = {'len': 0, 'r': {}}
        # lets get the larger section from some file
        for p in range(len(r)):
            for i_ in range(r[p]['pos'], len(r[p]['delta'])):
                i = r[p]['delta'][i_]
                if i['name'] != i['delta']:
                    if i['pos_dest'] >= pos and pos < i['pos_dest'] + i['len']:
                        if sol['len'] < i['len']:
                            sol['len'] = i['len']
                            sol['r'] = {i['name']: i}
                        elif sol['len'] == i['len']:
                            sol['r'][i['name']] = i
                        r[p]['pos'] = i_
                        break
        # if we don't found any data in files just use the minimum size in a delta file
        if sol['r'] == -1:
            #just a very big number, all must be smaller than this
            sol['len'] = math.inf
            for p in range(len(r)):
                for i_ in range(r[p]['pos'], len(r[p]['delta'])):
                    i = r[p]['delta'][i_]
                    if i['name'] == i['delta']:
                        if i['pos_dest'] >= pos and pos < i['pos_dest'] + i['len']:
                            if sol['len'] > i['len']:
                                sol['len'] = i['len']
                                sol['r'] = {i['name']: i}
                            elif sol['len'] == i['len']:
                                sol['r'][i['name']] = i
                            r[p]['pos'] = i_
                            break
        if len(sol['r']) == 0:
            raise Exception("Error, this should not happen, all deltas contain all the file, so, there must be at least 1 fragment")
        res.append(sol['r'])
        pos += sol['len']
    print("second phase")
    result = []
    sizes = {}
    for i in res:
        if len(i) == 1:
            continue
        for j in i:
            if not j in sizes:
                sizes[j] = i[j]['len']
            else:
                sizes[j] += i[j]['len']
    asizes = sorted(sizes, key=sizes.get, reverse=True)
    for i in res:
        if len(i) == 1:
            result.append(i[0])
        for j in asizes:
            if j in i:
                result.append(i[j]) 
    return res

