"""This module contains functions to write all accompanying files for the
dictionary, e.g. license or README."""

import os
import shutil
import sys
import textwrap
import xml.dom.minidom

class OutputError(Exception):
    pass


def reindent_xml(file_name):
    """Reindent an XML file with Python's minidom package. Please note that this
    will likely use a large amount of main memory."""
    try:
        tree = xml.dom.minidom.parse(file_name)
        with open(file_name, 'w', encoding='utf-8') as f:
            reindented = tree.toprettyxml(indent="  ")
            # avoid multiple empty lines, inserted by minidom
            f.write('\n'.join(l for l in reindented.split('\n') if l.strip()))
    except MemoryError:
        print("Unable to reindent file using Python's minidom module.")
        if shutil.which('xmllint'):
            print("Using xmllint for reindentation.")
            ret = os.system('xmllint --format {0} > {0}.tmp'.format(file_name))
            if ret:
                print("Aborting.")
                sys.exit(21)
            with open(file_name + '.tmp', encoding='utf-8') as infile:
                with open(file_name, 'w', encoding='utf-8') as out:
                    out.write(infile.read())
            os.remove(file_name + '.tmp')
        else:
            print('\n'.join(textwrap.wrap(("Please install xmllint as a fallback (this "
                "script will automatically use it) or use some other magic to "
                "increase the available main memory."), 78)))
            sys.exit(9)


