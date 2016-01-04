#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'orlando'

import subprocess
import sys
import tempfile
import xml.etree.cElementTree as ET

"""Functions"""


def print_head(osm_file, size=5, tags=None, attribs=None, child_tags=None, less=True):
    """ Prints OSM elements that match specified conditions in a pretty format

    :param osm_file: File path to OSM XML file
    :param size: Integer size of head - Use -1 if all elements are desired
    :param tags: List with top level tags to print
    :param attribs: List with required attributes to print or None for no filter
    :param child_tags: List with required child tag keys to print
    :param less: If True it will use the UNIX utility 'less' for printing
    """
    tmp_file = None
    path = None
    if less:
        # HACK: We want to print with the less command, so
        # we'll create a temp file to dump the output and
        # later run less on it
        path = tempfile.mkstemp()[1]
        tmp_file = open(path, 'a')
        sys.stdout = tmp_file
    try:
        tag_count = 1
        for event, element in ET.iterparse(osm_file):
            if size != -1 and tag_count > size:
                break

            if tags and element.tag not in tags:
                continue

            element_log = 'Tag #{}: {}\n'.format(tag_count, element.tag)
            should_print_log = False

            element_log += '    Attributes:\n'
            for attrib, value in element.attrib.iteritems():
                if attribs is not None and attrib in attribs:
                    should_print_log = True
                element_log += u'        {}: {}\n'.format(attrib, value)

            element_log += '    Child tags:\n'
            for tag in element.iter("tag"):
                if child_tags is not None and tag.attrib['k'] in child_tags:
                    should_print_log = True
                element_log += u'        {}: {}\n'.format(tag.attrib['k'], tag.attrib['v'])

            if should_print_log:
                print element_log.encode('utf-8')
                tag_count += 1

        if less:
            # HACK: We have a temporal file and decided we want to use less to
            # print, so create a separate process to run less until EOF
            tmp_file.flush()
            p = subprocess.Popen(['less', path], stdin=subprocess.PIPE)
            p.communicate()
    finally:
        if less:
            tmp_file.close()
            sys.stdout = sys.__stdout__


def find_elements_with_tag_value(osm_file, tag_key, tag_value, should_print=True):
    """ Returns a list of XML elements with child tags that have a
    tag_value for the tag_key

    :param osm_file: File path to OSM XML file
    :param tag_key: String value of the tag key
    :param tag_value: String value of the tag value
    :return: List of Element objects with the desired tag value
    """
    elements = []
    for event, element in ET.iterparse(osm_file):
        if element.tag == "node" or element.tag == "way":
            for tag in element.iter("tag"):
                if tag.attrib['k'] == tag_key and tag.attrib['v'] == tag_value:
                    elements.append(element)
                    break
    if should_print:
        for element in elements:
            print pretty_element(element)
    return elements


def pretty_element(element):
    """ Pretty prints the data of an OSM XML element

    :param element: Element object with OSM format
    """
    pretty_str = u'Tag: {}\n'.format(element.tag)
    pretty_str += u'    Attributes:\n'
    for attrib, value in element.attrib.iteritems():
        pretty_str += u'        {}: {}\n'.format(attrib, value)
    pretty_str += u'    Child tags:\n'
    for tag in element.iter("tag"):
        pretty_str += u'        {}: {}\n'.format(tag.attrib['k'], tag.attrib['v'])
    return pretty_str


def osm_general_stats(osm_file):
    """ Constructs a dictionary with general statistics
    extracted after fully parsing a provided OSM XML file

    :param osm_file: File path to OSM XML file
    :return: Dict with with general stats
    """
    stats = {
        'element_types': {},
        'attributes': {},
        'tag_keys': {},
    }
    for event, element in ET.iterparse(osm_file, events=("start",)):
        # Element types
        if element.tag not in stats['element_types']:
            stats['element_types'][element.tag] = 0
        stats['element_types'][element.tag] += 1

        # Attributes
        for attrib in element.attrib:
            if attrib not in stats['attributes']:
                stats['attributes'][attrib] = 0
            stats['attributes'][attrib] += 1

        # Tag keys
        if element.tag == "tag":
            if element.attrib['k'] not in stats['tag_keys']:
                stats['tag_keys'][element.attrib['k']] = 0
            stats['tag_keys'][element.attrib['k']] += 1
    return stats
