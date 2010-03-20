from lxml.html import fromstring, tostring
from urllib2 import urlopen
import os, re
import curses
import tempfile, zipfile

cim = '4400'
# if sys.argv[1]:
#     cim = sys.argv[1]
# else:
#     cim = raw_input('cim: ')
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
        self.list = []
        self.maxy, self.maxx = self.scr.getmaxyx()
        self.scr.clear()
        self.row = 0
        self.page = 0
        self.len = 0
        self.y = 0
        self.x = 0

    def printsubs(self):
        lrow = 0
        idx = self.page * self.maxy + self.row
        downl = self.page * self.maxy
        upl = (self.page + 1) * self.maxy

        for sub in self.list[downl:upl]:
            self.scr.addstr(self.y + lrow, self.x, sub)
            lrow += 1

        self.scr.addstr(self.y + self.row, self.x,
                self.list[idx], curses.A_STANDOUT)
        self.scr.refresh()

    def move(self, i):
        idx = self.page * self.maxy + self.row
        maxrow = self.len - self.page * self.maxy - 1

        if i >= 0 and i <= maxrow and i < self.maxy:
            self.scr.addstr(self.y + self.row, self.x, self.list[idx])
            self.row = i
            idx = self.page * self.maxy + self.row
            self.scr.addstr(self.y + self.row, self.x, self.list[idx],
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

class Root(Win):
    def __init__(self, scr):
        self.scr = scr
        self.list = []
        self.dl = []
        self.maxy, self.maxx = self.scr.getmaxyx()
        self.scr.clear()
        self.row = 0
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
        self.page = 0
        self.len = len(self.list)
        self.y = 1
        self.x = 1
        self.scr.erase()
        self.scr.box()
        self.scr.addstr(0, 3, 'download')

root = Root(scr)

for a in html.cssselect('a#menu'):
    if 'download.php' in a.get('href'):
        root.list.append(' - '.join((
            re.search('<br>(.+?)<\/td>', tostring(a.getparent())).group(1),
            a.getparent().getnext().getchildren()[0].attrib['alt'])))
        root.dl.append(a.get('href'))
        root.len += 1

root.printsubs()


def fetch():
    link = 'http://www.hosszupuskasub.com/' + root.dl[root.row]
    f = tempfile.NamedTemporaryFile()
    f.write(urlopen(link).read())
    zf = None
    files = []
    if re.search('\.zip$', root.dl[root.row]):
        zf = zipfile.ZipFile(f)
        files = zf.namelist()
    elif re.search('\.rar$', root.dl[root.row]):
        files = os.popen('unrar lb %s' % f.name).read().split('\n')
        files.pop()

    submaxx = submaxx = len(files) + 2
    if len(files)+2 > root.maxy:
        submaxx = root.maxy - 2
    dwin = SubWin(
            root.scr.subwin(submaxx, int(root.maxx * 0.85), 10, 2), files)
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
#         elif c in (ord('e'), curses.KEY_ENTER, 10):
#             fetch()
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
        if root.len - 1 < root.maxy:
            root.move(root.len - 1)
        elif root.len - 1 > (root.page+1) * root.maxy:
            root.move(root.maxy - 1)
        else:
            root.move(root.len-1 - root.page*root.maxy)
#     elif c in (ord('i'), ord('I')):
#         subscr = scr.subwin(5, 65, 10, 2)
#         subscr.addstr(1, 1, '; '.join(subs[row]), curses.A_STANDOUT)
#         subscr.box()
#         subscr.addstr(0, 3, 'info box')
#         subscr.getch()
#         subscr.erase()
#         printsubs()
#         scr.addstr(row, 0, subs[row][0], curses.A_STANDOUT)
    elif c in (ord('f'), curses.KEY_ENTER, 10):
        fetch()
    elif c in (ord('r'), ord('R')):
        scr.refresh()
