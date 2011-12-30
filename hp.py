#!/usr/bin/env python2

from lxml.html import fromstring, tostring
from urllib2 import urlopen
import sys, os, re
import curses, getopt
import tempfile, zipfile

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

    def addline(self, **kwargs):
        y = kwargs.get('y', self.y + self.row)
        x = kwargs.get('x', self.x)
        title = kwargs.get('title', self.list[self.idx])
        attr = kwargs.get('attr', curses.A_NORMAL)

        self.scr.addstr(y, x, title[:self.maxx], attr)

    def printsubs(self):
        downl = self.page * self.maxy
        upl = (self.page + 1) * self.maxy

        for i, sub in enumerate(self.list[downl:upl]):
            self.addline(y=self.y + i, title=sub)

        self.addline(attr=curses.A_STANDOUT)
        self.scr.refresh()

    def lastrow(self):
        if self.maxy * (self.page+1) < self.len:
            return self.maxy - 1
        return self.len - self.page * self.maxy - 1

    def move(self, i):
        isnextpage = self.maxy * (self.page+1) < self.len
        if 0 <= i <= self.lastrow():
            self.addline()
            self.setrow(i)
            self.addline(attr=curses.A_STANDOUT)
        elif i >= self.maxy and isnextpage:
            self.page += 1
            self.updscr()
            self.setrow(0)
            self.printsubs()
        elif i < 0 and self.page > 0:
            self.page -= 1
            self.updscr()
            self.setrow(self.maxy-1)
            self.printsubs()

    def setrow(self, n):
        self.row = n
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
                self.move(self.lastrow())
            elif c in (ord('r'), ord('R')):
                self.scr.refresh()
            else:
                self.otherkey(c)
#}}}

class Root(Win):    #{{{
    def __init__(self, scr):
        self.scr  = scr
        self.arch = None
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

    def getlink(self):
        path = re.sub(r'.*file=(.*$)', r'!!feliratok/\1', self.dl[self.idx])
        return 'http://www.hosszupuskasub.com/' + path

    def otherkey(self, c):
        if c in (ord('f'), curses.KEY_ENTER, 10):
            self.fetch()
        elif c in(ord('d'), ord('D')):
            link = self.getlink()
            dfile = open(link.rsplit('/', 1)[1], 'w')
            dfile.write(urlopen(link).read())
            dfile.close()

    def fetch(self):
        link      = self.getlink()

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
        sys.exit(0)
#}}}

class SubWin(Win):  #{{{
    def __init__(self, scr, arch, ppsubs):
        self.scr   = scr
        self.arch  = arch
        self.list  = arch.files
        self.maxy, self.maxx = self.scr.getmaxyx()
        self.maxx -= 2
        self.maxy -= 2
        self.scr.clear()
        self.row   = 0
        self.idx   = 0
        self.page  = 0
        self.len   = len(self.list)
        self.y     = 1
        self.x     = 1
        self.title = root.getlink().rsplit('/', 1)[1]
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
        self.f.flush()
        self.files  = [rarr.search(i).group('name') for i in filter(rarr.match, os.popen('7z l %s' % self.f.name))]
        self.lenght = len(self.files)

    def extract(self, idx):
        os.system('7z x %s "%s" > /dev/null' % (self.f.name, self.files[idx]))

    def extractall(self):
        os.system('7z x %s > /dev/null' % self.f.name)

    def close(self):
        self.f.close()
#}}}

def getlang(a):
    src = a.getparent().getparent().getchildren()[2].find('img').attrib['src']
    if src == 'flags/1.gif':
        return 'magyar'
    elif src == 'flags/2.gif':
        return 'angol'

def gettitle(a):
    src = tostring(a.getparent().getparent().getchildren()[1]).decode('utf-8')
    return re.search('<br>(.+?)<\/td>', src).group(1)

def getpage(url):
    c = urlopen(url).read()
    return fromstring(c)

def hpsearch(q, s):
    """hpsearch(q, s) --> bool

    Return True if words in q are found in s, False otherwise."""
    words = q.lower().split()
    twords = s.lower().split()
    hits = {}
    for tw in twords:
        for w in words:
            if w in tw:
                hits[w] = True
    if 'and' in words and '&' in twords:    # check for '&' as and
        hits['and'] = True
    return len(words) <= len(hits)


try:
    opts, args = getopt.getopt(sys.argv[1:], "de")
except:
    print str(err)
    sys.exit(2)

debug = None
exact = None
for o, a in opts:
    if o == '-d':
        debug = True
    elif o == '-e':
        exact = True

if args:
    cim = ' '.join(args)
else:
    cim = raw_input('cim: ')

baseurl = 'http://hosszupuskasub.com/'
html    = getpage(baseurl)

sorozatok = [{'id': o.get('value'), 'title': o.text} for o in html.cssselect('select[name=sorozatid] > option')[1:]]

if exact:
    hits = filter(lambda x: cim.lower() == x['title'].lower(), sorozatok)
else:
    hits = filter(lambda x: hpsearch(cim, x['title']), sorozatok)

if debug:
    for hit in hits:
        print "%s --> %s" % (hit['title'], hit['id'])
    sys.exit(0)

if not hits:
    print "Nincs talalat a kovetkezo kifejezesre:", cim
    sys.exit(0)

root = Root(curses.initscr())

for hit in hits:
    html = getpage(baseurl + '/kereso.php?sorozatid=' + hit['id'])
    for a in html.cssselect('td > a[href^=download]'):
        root.list.append(' - '.join((gettitle(a), getlang(a))))
        root.dl.append(a.get('href'))
        root.len += 1

if root.list:
    root.printsubs()
else:
    root.end()

root.actions()
