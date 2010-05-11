#!/usr/bin/env python

from lxml.html import fromstring, tostring
from urllib2 import urlopen
import sys, os, re
import curses
import tempfile, zipfile

if 1 < len(sys.argv):
    cim = ' '.join(sys.argv[1:])
else:
    cim = raw_input('cim: ')

if cim in ('v', 'V'):
    url = 'http://www.hosszupuskasub.com/index.php?serial=v2009'
elif cim == 'supernatral':
    url = 'http://www.hosszupuskasub.com/index.php?serial=supernatural'
else:
    url = 'http://www.hosszupuskasub.com/index.php?cim=%s' % cim

subs = []
row = 0
page = 0

scr = curses.initscr()
curses.noecho()
curses.cbreak()
scr.keypad(1)

c = urlopen(url).read()
html = fromstring(c)

class Win:
    def __init__(self, scr):
        self.scr = scr
        self.scr.clear()
        self.list = []
        self.maxy, self.maxx = self.scr.getmaxyx()
        self.row = 0        # current row
        self.idx = 0        # current sub
        self.page = 0
        self.len = 0
        self.y = 0          # top border
        self.x = 0          # left border

    def printsubs(self):
        lrow = 0
        self.updidx()
        downl = self.page * self.maxy
        upl = (self.page + 1) * self.maxy

        for sub in self.list[downl:upl]:
            self.scr.addstr(self.y + lrow, self.x, sub)
            lrow += 1

        self.scr.addstr(self.y + self.row, self.x,
                self.list[self.idx], curses.A_STANDOUT)
        self.scr.refresh()

    def move(self, i):
        self.updidx()
        maxrow = self.len - self.page * self.maxy - 1

        if i >= 0 and i <= maxrow and i < self.maxy:
            self.scr.addstr(self.y + self.row, self.x, self.list[self.idx])
            self.row = i
            self.updidx()
            self.scr.addstr(self.y + self.row, self.x, self.list[self.idx],
                    curses.A_STANDOUT)
        elif i >= self.maxy:
            self.page += 1
            self.scr.erase()
            self.row = 0
            self.printsubs()
        elif i < 0 and self.page > 0:
            self.page -= 1
            self.scr.erase()
            self.row = self.maxy-1
            self.printsubs()
        self.updidx()

    def updidx(self):
        self.idx = self.page * self.maxy + self.row

class Root(Win):
    def __init__(self, scr):
        self.scr = scr
        self.list = []
        self.dl = []
        self.maxy, self.maxx = self.scr.getmaxyx()
        self.scr.clear()
        self.row = 0
        self.idx = 0
        self.page = 0
        self.len = 0
        self.y = 0
        self.x = 0

class SubWin(Win):
    def __init__(self, scr, list):
        self.scr = scr
        self.list = list
        self.maxy, self.maxx = self.scr.getmaxyx()
        self.maxx -= 1
        self.maxy -= 1
        self.scr.clear()
        self.row = 0
        self.idx = 0
        self.page = 0
        self.len = len(self.list)
        self.y = 1
        self.x = 1
        self.scr.erase()
        self.scr.box()
        self.scr.addstr(0, 3, 'download')

def fetch():
    link = 'http://www.hosszupuskasub.com/' + root.dl[root.idx]
    f = tempfile.NamedTemporaryFile()
    f.write(urlopen(link).read())
    zf = None
    files = []
    isZip = False
    if re.search('\.zip$', root.dl[root.idx]):
        zf = zipfile.ZipFile(f)
        files = zf.namelist()
        isZip = True
    elif re.search('\.rar$', root.dl[root.idx]):
        files = os.popen('unrar v %s | awk \'BEGIN { s=0; f=1; } \
                /^---/ {s++; if(s>1) exit 0; next; } \
                s==1 && f++ %% 2 { sub("^ ", ""); print; }\'' % f.name).read().split('\n')
#         files = os.popen('unrar lb %s' % f.name).read().split('\n')
        files.pop()

    submaxy = submaxy = len(files) + 2
    if len(files)+2 > root.maxy:
        submaxy = root.maxy - 2
    dwin = SubWin(
            root.scr.subwin(submaxy, int(root.maxx * 0.85), 10, 2), files)
    dwin.scr.addstr(0, 3, re.search(r'file=(.*$)', root.dl[root.idx]).group(1))
    dwin.printsubs()

    while True:
        c = dwin.scr.getch()
        if c == ord('q'):
            break
        elif c in (ord('k'), curses.KEY_UP):
            dwin.move(dwin.row-1)
        elif c in (ord('j'), curses.KEY_DOWN):
            dwin.move(dwin.row+1)
        elif c in (ord('g'), curses.KEY_HOME):
            dwin.move(0)
        elif c in (ord('G'), curses.KEY_END):
            if dwin.len - 1 < dwin.maxy:
                dwin.move(dwin.len - 1)
            elif dwin.len - 1 > (dwin.page+1) * dwin.maxy:
                dwin.move(dwin.maxy - 1)
            else:
                dwin.move(dwin.len-1 - dwin.page*dwin.maxy)
        elif c in (ord('e'), ord('s'), curses.KEY_ENTER, 10):
            if isZip:
                zf.extract(files[dwin.maxy*dwin.page + dwin.row])
            else:
                os.system('unrar e -inul %s "%s"' % (f.name, files[dwin.idx]))
        elif c in (ord('a'), ord('A')):
            if isZip:
                zf.extractall()
            else:
                os.system('unrar e -inul %s' % f.name)
        elif c in (ord('r'), ord('R')):
            dwin.scr.refresh()
    dwin.scr.erase()
    root.printsubs()

    if zf is not None:
        zf.close()
    f.close()

def end():
    curses.nocbreak();
    scr.keypad(0);
    curses.echo()
    curses.endwin()

root = Root(scr)

for a in html.cssselect('a#menu'):
    if 'download.php' in a.get('href'):
        root.list.append(' - '.join((
            re.search('<br>(.+?)<\/td>', tostring(a.getparent().getparent().getchildren()[1])).group(1),
            a.getparent().getparent().getchildren()[2].find('img').attrib['alt'])))
        root.dl.append(a.get('href'))
        root.len += 1

if root.list:
    root.printsubs()
else:
    end()
    sys.exit()

while True:
    c = scr.getch()
    if c == ord('q'):
        end()
        break
    elif c in (ord('k'), curses.KEY_UP):
        root.move(root.row-1)
    elif c in (ord('j'), curses.KEY_DOWN):
        root.move(root.row+1)
    elif c in (ord('g'), curses.KEY_HOME):
        root.move(0)
    elif c in (ord('G'), curses.KEY_END):
        if root.len - 1 < root.maxy:    # ha kisebb mint az ablak
            root.move(root.len - 1)     # a vegere ugrunk
        elif root.len - 1 > (root.page+1) * root.maxy:
            root.move(root.maxy - 1)    # ha nagyobb az akkor az ablak aljara
        else:                           # utolso oldal miatt kell
            root.move(root.len-1 - root.page*root.maxy)
    elif c in (ord('f'), curses.KEY_ENTER, 10):
        fetch()
    elif c in (ord('r'), ord('R')):
        scr.refresh()
