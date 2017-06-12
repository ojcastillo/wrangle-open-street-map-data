#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'orlando'

import subprocess
import sys
import tempfile
import xml.etree.cElementTree as ET

from pymongo import MongoClient

"""Functions"""


def print_head(osm_file, size=5, tags=None, attribs=None,
               child_tags=None, less=True):
    """ Prints OSM elements that match specified conditions in a pretty format

    :param osm_file: File path to OSM XML file
    :param size: Integer size of head - Use -1 if all elements are desired
    :param tags: List with top level tags to print
    :param attribs: List with required attributes to print or
                    None for no filter
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
                element_log += u'        {}: {}\n'.format(
                    tag.attrib['k'], tag.attrib['v'])

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


def find_elements_with_tag_value(osm_file, tag_key, tag_value,
                                 should_print=True):
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
        pretty_str += u'        {}: {}\n'.format(
            tag.attrib['k'], tag.attrib['v'])
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


def get_db(db_name):
    """
    Returns an instance to a local Mongo database
    :param db_name: String identifier of the database
    :return: Mongo database
    """
    client = MongoClient('localhost:27017')
    db = client[db_name]
    return db


def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag

    Reference:
    http://stackoverflow.com/questions/3095434/inserting-newlines-in-xml-file-generated-via-xml-etree-elementtree-in-python
    """
    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def generate_submission_sample(map_path, sample_path):
    """
    Generates a sample version of a provided OSM map intended for submission
    to Udacity
    :param map_path: Path to OSM file for which the sample will be created
    :param sample_path: Path to where the OSM sample will be saved
    """
    with open(sample_path, 'wb') as output:
        output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        output.write('<osm>\n  ')

        # Write every 10th top level element
        for i, element in enumerate(get_element(map_path)):
            if i % 10 == 0:
                output.write(ET.tostring(element, encoding='utf-8'))

        output.write('</osm>')