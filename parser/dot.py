#format python

"""
MoinMoin processor for dot.

This processor passes its input to dot (from AT&T's GraphViz package)
to render graph diagrams.

-------------------------------------------------------------------------------

Copyright (C) 2004, 2005  Alexandre Duret-Lutz <adl@gnu.org>
Copyright (C) 2005, 2007  P. Bauermeister <pascal DOT bauermeister AT gmail DOT com>

This module is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2, or (at your option)
any later version.

-------------------------------------------------------------------------------

Usage:

* Plain Dot features:

  {{{#!dot
    digraph G {
      node [style=filled, fillcolor=white]
      a -> b -> c -> d -> e -> a

      // a comment

      a [URL='http://some.where/a']   // link to an external URL
      b [URL='MoinMoinLink']          // link to a wiki absolute page
      c [URL='/Subpage']              // link to a wiki subpage
      d [URL='#anchor']               // link to an anchor in current page
      e [fillcolor=blue]
    }
  }}}

  WARNING: URL must be specified in separate []'s, e.g:
      ThisIsANode [shape=rectangle] [URL='someLink']

* Support for alternate filters (= layout engines):
    dot   - filter for drawing directed graphs
    neato - filter for drawing undirected graphs
    twopi - filter for radial layouts of graphs
    circo - filter for circular layout of graphs
    fdp   - filter for drawing undirected graphs

    At install-time, symlink to the filter name, e.g.: ln -s dot.py neato.py

* Extra MoinMoin-ish features:

  {{{#!dot OPTIONS
    digraph G {
      node [style=filled, fillcolor=white]
      a -> b -> c -> d -> e -> a

      [[Include(MoinMoinPage)]]       // include a whole wiki page content
      [[Include(MoinMoinPage,name)]]  // same, but just a named dot section
      [[Include(,name)]]              // include named dot sect of current page
      [[Set(varname,'value')]]        // assign a value to a variable
      [[Get(varname)]]                // expand a variable
    }
  }}}

  Options:
    * name=IDENTIFIER  name this dot section; used in conjunction with Include.

    * show=0|1         allow to hide a dot section; useful to define hidden
                         named section used as 'libraries' to be included;
                         default: 0  (i.e. show)

    * debug=0|1        when not 0,preceed the image by the expanded dot source;
                         default: 0  (i.e. debug off)

    * raw=0|1|2
                       when 1: the raw text passed to the parser is shown
                       after.
                       when 2: the complete parser block with delimiters
                       and bang path is shown after.

    * help[0|1|2]      when not 0, display 1:short or 2:full help in the page;
                         default: 0  (i.e. no help)

    * bgcolor=NAME     graph's bg color; for names, see
                         http://www.graphviz.org/doc/info/attrs.html#k:color
                         default: 'transparent'

    * attname=NAME[.png]
      attachment_name=NAME[.png]
                       the image will be copied to this named attachment, which
                       allows to have predictable attachment URLs.

The result will be an attached PNG, displayed at this point in the
document.  The AttachFile action must therefore be enabled.

If some node in the input contains a URL label, the processor will
generate a user-side image map. See above warning on specifying URLs.

GraphViz: http://www.research.att.com/sw/tools/graphviz/

Examples of use of this processor:
    * http://spot.lip6.fr/wiki/LtlTranslationAlgorithms (with image map)
    * http://spot.lip6.fr/wiki/HowToParseLtlFormulae (without image map)

-------------------------------------------------------------------------------

Installation:

  * copy this file into your parsers directory (something like
    /var/local/MY-WIKI/data/plugin/parser)

  * optionally, set the env var DOT_PATH to the directory where your dot
    program can be found. By default, dot is seeked in /usr/bin.
    E.g. if you have dot in /usr/local/bin, and you are using CGI:
    add to /var/local//MY-WIKI/cgi-bin/moin.cgi:
    import os
    os.environ['DOT_PATH'] = "/usr/local/bin"

-------------------------------------------------------------------------------

ChangeLog:

Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2009-01-09
  * Compatibility for MoinMoin 1.7 and above

Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2007-09-14:
  * Improved wiki_text -> html formatter

Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2007-09-11:
  * Added options: attachment_name
  * Get path to dot via environment var DOT_PATH (default /usr/bin)
  * GV_FILE_PATH is set via os.environ[] and no longer by prefixing commands
  
Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2006-12-27:
  * Added support for these filters:
    dot   - filter for drawing directed graphs (*as before*)
    neato - filter for drawing undirected graphs
    twopi - filter for radial layouts of graphs
    circo - filter for circular layout of graphs
    fdp   - filter for drawing undirected graphs

    At install-time, symlink to the filter name, e.g.: ln -s dot.py neato.py

    At run-time:
    * use the filter name, e.g. {{{#!neato ...}}}
    * some attributes may (not) apply, see
      http://www.graphviz.org/doc/info/attrs.html
    * map is still supported, use [URL='...'] (in separate []'s, see usage)
                                   
Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2006-01-18:
  * Use StringIO instead of cStringIO, for unicode compatibility
  * Supports using image attachements for shapefile  

Alexandre Duret-Lutz  <adl@gnu.org>  2005-03-23:
  * Rewrite as a parser for Moin 1.3.4.
    (I haven't tested any of the features Pascal added.  I hope they
    didn't broke in the transition.)

Pascal Bauermeister <pascal DOT bauermeister AT gmail DOT com> 2004-11-03:
  * Macros: Include/Set/Get
  * MoinMoin URLs
  * Can force image rebuild thanks to special attachment:
    delete.me.to.regenerate.

"""

# Parser's name
NAME = __name__.split(".")[-1]

Dependencies = []

import os, re, sha, shutil
import StringIO, string
from MoinMoin.action import AttachFile
from MoinMoin.Page import Page
from MoinMoin import wikiutil, config
from subprocess import Popen, PIPE


DOT_PATH = os.environ.get ("DOT_PATH", "/usr/bin")

###############################################################################

def quote (s): return '"%s"' % s


def escape(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def execute(cmd, stdin):
    try:
        p = Popen(cmd, shell=False, bufsize=0,
                  stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
    except OSError:
        raise RuntimeError(
            "Error executing command " \
                "(maybe '%s' is not installed on the system?) : %s" % (
                os.path.split(cmd[0])[-1], ' '.join(cmd)))

    stdout, stderr = p.communicate(stdin.encode("utf-8"))
    stdout = unicode(stdout, "utf-8")
    stderr = unicode(stderr, "utf-8")

    return stdout, stderr

###############################################################################

class Parser:

    extensions = ['.dot']

    def __init__(self, raw, request, **kw):
        # save call arguments for later use in format()
        self.raw = raw ##.encode('utf-8')
        self.request = request

        self.attrs, msg = wikiutil.parseAttributes(request,
                                                   kw.get('format_args', ''))

        # Some regexes that we will need
        p1_re = "(?P<p1>.*?)"
        p2_re = "(?P<p2>.*?)"
        end_re = "( *//.*)?"

        #   a shapefile
        self.sfi_re = re.compile(
            r'\[ *shapefile=(?P<quote>[\'"])(?P<shapefile>.+?)(?P=quote) *]',
            re.IGNORECASE)

        #   an URL
        self.url_re = re.compile(
            r'\[ *URL=(?P<quote>[\'"])(?P<url>.+?)(?P=quote) *]',
            re.IGNORECASE)

        #   non-wiki URLs
        self.notwiki_re = re.compile(
            r'[a-z0-9_]*:.*', re.IGNORECASE)

        #   include pseudo-macro
        self.inc_re = re.compile(
            r'\[\[ *Include *\( *%s( *, *%s)? *\) *\]\]%s' %
                         (p1_re, p2_re, end_re))
        #   set pseudo-macro
        self.set_re = re.compile(
            r'\[\[ *Set *\( *%s *, *(?P<quote>[\'"])%s(?P=quote) *\) *\]\]%s' %
            (p1_re, p2_re, end_re))

        #   get pseudo-macro
        self.get_re = re.compile(
            r'\[\[ *Get *\( *%s *\) *\]\]' % (p1_re))


    def _usage(self, full=False):

        """Return the interesting part of the module's doc"""

        if full: return __doc__

        lines = __doc__.splitlines()
        start = 0
        end = len(lines)
        for i in range(end):
            if lines[i].strip().lower() == "usage:":
                start = i
                break
        for i in range(start, end):
            if lines[i].startswith ('--'):
                end = i
                break
        return '\n'.join(lines[start:end])


    def _resolve_att(self, name, this_page):

        """For name in this form: [WikiPage/]Attachment.ext
        return the complete file path of the attachment. If WikiPage misses,
        take the current page"""

        if name.startswith("/"):
            # a wiki subpage
            name = this_page + name

        if "/" not in name:
            # an attachment in this page
            name = this_page + "/" + name

        pos = name.rfind("/")
        page, att = name[:pos], name[pos+1:]

        path =AttachFile.getAttachDir(self.request, page) + '/' + att
        return path


    def _resolve_link(self, url, this_page):

        """Return external URL, anchor, or wiki link"""

        if self.notwiki_re.match(url) or url.startswith("#"):
            # return url as-is
            return url
        elif url.startswith("/"):
            # a wiki subpage
            return "%s/%s%s" % (self.request.getScriptname(), this_page, url)
        else:
            # a wiki page
            return "%s/%s" % (self.request.getScriptname(), url)


    def _preprocess(self, formatter, lines, newlines, substs, attdir, recursions):

        """Resolve URLs and pseudo-macros (incl. includes) """

        self.images = []

        for line in lines:
            # Handle URLs to resolve Wiki links
            sline = line.strip()
            sfi_match = self.sfi_re.search(line)
            url_match = self.url_re.search(line)
            inc_match = self.inc_re.match(sline)
            set_match = self.set_re.match(sline)
            get_match = self.get_re.search(line)

            this_page = formatter.page.page_name

            if sfi_match:
                # Process shapefile; [OptionalWikiPage/]Attachment.ext
                name = sfi_match.group('shapefile')
                path = self._resolve_att(name, this_page)
                self.images.append((name,path))
                ext = path.split(".")[-1]
                imgpath = os.path.join(attdir, "__tmp_image_%d.%s" % (len(self.images), ext))
                line = line[:sfi_match.start()] \
                       + '[shapefile="%s"]' % imgpath \
                       + line[sfi_match.end():]
                newlines.append(line)
            elif url_match:
                # Process URL; handle both normal URLs and wiki names
                url = url_match.group('url')
                newurl = self._resolve_link(url, this_page)
                line = line[:url_match.start()] \
                       + '[URL="%s"]' % newurl \
                       + line[url_match.end():]
                newlines.append(line)
            elif inc_match:
                # Process [[Include(page[,ident])]]
                page = inc_match.group('p1')
                ident = inc_match.group('p2')
                # load page, search for named dot section, add it
                other_line = self._get_include(page, ident, this_page)
                newlines.extend(other_line)
            elif set_match:
                # Process [[Set(var,'value')]]
                var = set_match.group('p1')
                val = set_match.group('p2')
                substs[var] = val
            elif get_match:
                # Process [[Get(var)]]
                var = get_match.group('p1')
                val = substs.get(var, None)
                if val is None:
                    raise RuntimeError("Cannot resolve Variable '%s'" % var)
                line = line[:get_match.start()] + val + line[get_match.end():]
                newlines.append(line)
            else:
                # Process other lines
                newlines.append(line)
        return newlines


    def _get_include(self, page, ident, this_page):

        """Return the content of the given page; if ident is not empty,
        extract the content of an enclosed section:
        {{{#!dot ... name=ident ...
          ...content...
        }}}
        """

        lines = self._get_page_body(page, this_page)

        if not ident: return lines

        start_re = re.compile(r'{{{#!%s.* name=' % NAME)

        inside = False
        found =[]

        for line in lines:
            if not inside:
                f = start_re.search(line)
                if f:
                    name = line[f.end():].split()[0]
                    inside = name == ident
            else:
                pos = line.find('}}}')
                if pos >=0:
                    found.append(line[:pos])
                    inside = False
                else: found.append(line)

        if len(found)==0:
            raise RuntimeError("Identifier '%s' not found in page '%s'" %
                               (ident, page))

        return found


    def _get_page_body(self, page, this_page):

        """Return the content of a named page; accepts relative pages"""

        if page.startswith("/") or len(page)==0:
            page = this_page + page

        p = Page(self.request, page)
        if not p.exists ():
            raise RuntimeError("Page '%s' not found" % page)
        else:
            return p.get_raw_body().split('\n')


    def format(self, formatter):
        """The parser's entry point"""

        lines = self.raw.split('\n')
        text0 = lines

        # parse bangpath for arguments
        opt_show = 1
        opt_raw = 0
        opt_dbg  = False
        opt_name = None
        opt_attname = None
        opt_help = None
        need_map = False
        opt_bgcolor = "transparent"
        for (key, val) in self.attrs.items():
            val = val [1:-1]
            if   key == 'show':    opt_show = int(val)
            elif key == 'raw':     opt_raw  = int(val)
            elif key == 'debug':   opt_dbg  = int(val)
            elif key == 'name':    opt_name = val
            elif key == 'help':    opt_help = val
            elif key == 'map':     need_map = True
            elif key == 'bgcolor': opt_bgcolor = val
            elif key == 'background_color': opt_bgcolor = val
            elif key == 'attname': opt_attname = val
            elif key == 'attachment_name': opt_attname = val
            else:
                self.request.write(formatter.rawHTML("""
                <p><strong class="error">
                Error: processor %s: invalid argument: %s
                <pre>%s</pre></strong> </p>
                """ % (NAME, self.attrs, self._usage())))
                return

        # help ?
        if opt_help is not None and opt_help != '0':
            self.request.write(formatter.rawHTML("""
            <p>
            Processor %s usage:
            <pre>%s</pre></p>
            """ % (NAME, self._usage(opt_help == '2'))))
            return

        # don't show ?
        if not opt_show: return

        # useful
        substs = {}
        pagename = formatter.page.page_name

        attdir = AttachFile.getAttachDir(self.request, pagename, create=1) + '/'

        # default variables
        substs ['__PAGE__'] = pagename
        substs ['__NAME__'] = opt_name

        # preprocess lines
        newlines = []
        try:
            lines = self._preprocess(formatter, lines, newlines, substs, attdir, 0)
        except RuntimeError, str:
            self.request.write(formatter.rawHTML("""
            <p><strong class="error">
            Error: macro %s: %s
            </strong> </p>
            """ % (NAME, str) ))
            opt_dbg = True

        # debug ?  pre-print and exit
        if opt_dbg:
            self.request.write(formatter.rawHTML(
                "<pre>\n%s\n</pre>" % '\n'.join(lines)))

        # go !

        all = '\n'.join(lines).strip()
        name = 'autogenerated--dot-parser--' + NAME + '-' + \
               sha.new(all.encode('utf8')+DOT_PATH).hexdigest()
        pngname = name + '.png'
        dotname = name + '.map'
        pngpath = attdir + pngname
        mappath = attdir + dotname

        all_up = all.upper ()

        for each in "URL", "TOOLTIP", "HREF", "TITLE":
            if each+"=" in all_up: need_map = True
        
        dm2ri = attdir + "delete.me.to.regenerate.images"

        # delete autogenerated attachments if dm2ri attachment does not exist
        if not os.path.isfile(dm2ri):
            # create dm2ri attachment
            open(dm2ri,'w').close()
            # delete autogenerated attachments
            for root, dirs, files in os.walk(attdir, topdown=False):
                for name in files:
                    if name.startswith("autogenerated-"):
                        os.remove(os.path.join(root, name))

        want_png = not os.path.exists(pngpath)
        want_map = need_map and not os.path.exists(mappath)
        want_sfi = len(self.images) and (want_png or want_map)

        engine = NAME
        engine_path = os.path.join (DOT_PATH, engine)
        
        if want_sfi:
            i = 1
            for name, path in self.images:
                ext = path.split(".")[-1]
                dest = "%s__tmp_image_%d.%s" % (attdir, i, ext)
                try:
                    shutil.copyfile(path, dest)
                except IOError, e:
                    self.request.write(formatter.rawHTML("""
                    <p><strong class="error">
                    Error: macro %s: No such attachment: %s <br/> (%s)
                    </strong> </p>
                    """ % (NAME, name, escape(`e`)) ))
                    return

                i += 1

        if want_png:
            cmd = [engine_path,
                   '-Tpng',
                   '-Gbgcolor=' + opt_bgcolor,
                   '-o',
                   pngpath
                   ]

            stdout, stderr = execute(cmd, all)
            if stderr:
                RuntimeError(stderr)
            if opt_attname:
                if not opt_attname.lower ().endswith (".png"):
                    opt_attname += ".png"
                shutil.copyfile (pngpath, attdir + opt_attname)

        if want_map:
            #cmd = 'GV_FILE_PATH="'+attdir+'" ' + \
            #      engine + ' -Tcmap -o "' + mappath + '"'
            os.environ ['GV_FILE_PATH'] = attdir
            cmd = [engine_path, '-Tcmap', '-o', mappath]

            stdout, stderr = execute(cmd, all)
            if stderr:
                RuntimeError(stderr)

        if want_sfi:
            for root, dirs, files in os.walk(attdir, topdown=False):
                for name in files:
                    if name.startswith("__tmp_image_"):
                        os.remove(os.path.join(root, name))


        url = AttachFile.getAttachUrl(pagename, pngname, self.request)
        if not need_map:
            self.request.write(formatter.image(src = url))
        else:
            self.request.write(formatter.image(src = url,
                                          usemap = '#' + name,
                                          border = 0))
            self.request.write(formatter.rawHTML('<MAP name="' + name
                                                 + '\">\n'))
            import codecs
            p = codecs.open(mappath, "r", "utf-8")
            m = p.read()
            p.close()
            self.request.write(formatter.rawHTML(m + '</MAP>'))

        # raw output
        if opt_raw==1:
            html = u"<pre>%s</pre>\n" % escape(text0)
            self.request.write(formatter.rawHTML(html))
        elif opt_raw==2:
            html = u"<pre>{{{#!dot %s\n%s\n}}}</pre>\n" % (
                " ".join(["%s=%s" % (k,v) for k,v in self.attrs.items()
                          if k!="raw"]),
                escape("\n".join(text0))
                )
            self.request.write(formatter.rawHTML(html))
