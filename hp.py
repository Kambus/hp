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

c = urlopen(url).read()
html = fromstring(c)

rarr = re.compile(r"""(?P<date>\d{4}-\d{2}-\d{2})    # date
                   \s+                               # seperator
                   (?P<time>\d{2}:\d{2}:\d{2})       # time
                   \s+                               # seperator
                   (?P<attr>.{5})                    # attributes
                   \s+                               # seperator
                   (?P<size>\d+)                     # size
                   \s+                               # seperator
                   (?P<csize>\d+)                    # compressed size
                   \s+                               # seperator
                   (?P<name>.*)                      # name
                   """, re.X)


class Win:  #{{{
    def __init__(self, scr):
        self.scr = scr
        self.scr.clear()
        self.list = []
        self.maxy, self.maxx = self.scr.getmaxyx()
        self.row  = 0           # current row
        self.idx  = 0           # current sub
        self.page = 0
        self.len  = 0
        self.y    = 0           # top border
        self.x    = 0           # left border

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
            self.updscr()
            self.row = 0
            self.printsubs()
        elif i < 0 and self.page > 0:
            self.page -= 1
            self.updscr()
            self.row = self.maxy-1
            self.printsubs()
        self.updidx()

    def updidx(self):
        self.idx = self.page * self.maxy + self.row

    def updscr(self):
        self.scr.clear()

    def otherkey(self, c):
        pass

    def actions(self):
        while True:
            c = self.scr.getch()
            if c == ord('q'):
                self.end()
                break
            elif c in (ord('k'), curses.KEY_UP):
                self.move(self.row-1)
            elif c in (ord('j'), curses.KEY_DOWN):
                self.move(self.row+1)
            elif c in (ord('g'), curses.KEY_HOME, curses.KEY_PPAGE):
                self.move(0)
            elif c in (ord('G'), curses.KEY_END, curses.KEY_NPAGE):
                if self.len - 1 < self.maxy:    # ha kisebb mint az ablak
                    self.move(self.len - 1)     # a vegere ugrunk
                elif self.len - 1 > (self.page+1) * self.maxy:
                    self.move(self.maxy - 1)    # ha nagyobb akkor az ablak aljara
                else:                           # utolso oldal miatt kell
                    self.move(self.len-1 - self.page*self.maxy)
            elif c in (ord('r'), ord('R')):
                self.scr.refresh()
            else:
                self.otherkey(c)
#}}}

class Root(Win):    #{{{
    def __init__(self, scr):
        self.scr  = scr
        self.list = []
        self.dl   = []
        self.maxy, self.maxx = self.scr.getmaxyx()
        self.scr.clear()
        self.row  = 0
        self.idx  = 0
        self.page = 0
        self.len  = 0
        self.y    = 0
        self.x    = 0

        curses.noecho()
        curses.cbreak()
        self.scr.keypad(1)

    def otherkey(self, c):
        if c in (ord('f'), curses.KEY_ENTER, 10):
            self.fetch()
        elif c in(ord('d'), ord('D')):
            link = 'http://www.hosszupuskasub.com/' + self.dl[self.idx]
            dfile = open(re.search(r'file=(.*$)', link).group(1), 'w')
            dfile.write(urlopen(link).read())
            dfile.close()

    def fetch(self):
        link      = 'http://www.hosszupuskasub.com/' + self.dl[self.idx]

        if re.search('\.zip$', link):
            self.arch = ZipArch(link)
        elif re.search('\.rar$', link):
            self.arch = RarArch(link)

        substarty = int(self.maxy * 0.3)
        substartx = 2

        submaxy = self.arch.lenght + 2
        if (substarty + submaxy) >= self.maxy:
            submaxy = self.maxy - substarty - 2
        dwin = SubWin(
                self.scr.subwin(submaxy, int(self.maxx * 0.85),
                    substarty, substartx), self.arch, self.printsubs)

        if dwin.list is []:
            dwin.scr.addstr(1, 1, 'Corrupt archive')
            self.src.getch()
            dwin.end()
        else:
            dwin.printsubs()
            dwin.actions()

    def end(self):
        curses.nocbreak();
        self.scr.keypad(0);
        curses.echo()
        curses.endwin()
        sys.exit()
#}}}

class SubWin(Win):  #{{{
    def __init__(self, scr, arch, ppsubs):
        self.scr   = scr
        self.arch  = arch
        self.list  = arch.files
        self.maxy, self.maxx = self.scr.getmaxyx()
        self.maxx -= 1
        self.maxy -= 1
        self.scr.clear()
        self.row   = 0
        self.idx   = 0
        self.page  = 0
        self.len   = len(self.list)
        self.y     = 1
        self.x     = 1
        self.title = re.search(r'file=(.*$)', root.dl[root.idx]).group(1)
        self.scr.erase()
        self.scr.box()
        self.scr.addstr(0, 3, self.title)
        self.parent_printsubs = ppsubs
        self.scr.keypad(1)

    def updscr(self):
        self.scr.clear()
        self.scr.box()
        self.scr.addstr(0, 3, self.title)

    def otherkey(self, c):
        if c in (ord('e'), ord('s'), curses.KEY_ENTER, 10):
            self.arch.extract(self.maxy*self.page + self.row)
        elif c in (ord('a'), ord('A')):
            self.arch.extractall()

    def end(self):
        self.arch.close()
        self.scr.erase()
        self.parent_printsubs()
#}}}

class ZipArch:  #{{{
    def __init__(self, url):
        self.f      = tempfile.NamedTemporaryFile()
        self.f.write(urlopen(url).read())
        self.zf     = zipfile.ZipFile(self.f)
        self.files  = self.zf.namelist()
        self.lenght = len(self.files)

    def extract(self, idx):
        self.zf.extract(self.files[idx])

    def extractall(self):
        self.zf.extractall()

    def close(self):
        self.zf.close()
        self.f.close()
#}}}

class RarArch:  #{{{
    def __init__(self, url):
        self.f      = tempfile.NamedTemporaryFile()
        self.f.write(urlopen(url).read())
        self.files  = [rarr.search(i).group('name') for i in filter(rarr.match, os.popen('7z l %s' % self.f.name))]
        self.lenght = len(self.files)

    def extract(self, idx):
        os.system('7z x %s "%s" > /dev/null' % (self.f.name, self.files[idx]))

    def extractall(self):
        os.system('7z x %s > /dev/null' % self.f.name)

    def close(self):
        self.f.close()
#}}}

root = Root(curses.initscr())

for a in html.cssselect('td > a'):
    if 'download.php' in a.get('href'):
        root.list.append(' - '.join((
            re.search('<br>(.+?)<\/td>',
                tostring(a.getparent().getparent().getchildren()[1])).group(1),
            a.getparent().getparent().getchildren()[2].find('img').attrib['alt'])))
        root.dl.append(a.get('href'))
        root.len += 1

if root.list:
    root.printsubs()
else:
    root.end()

root.actions()
