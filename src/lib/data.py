#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'orlando'

import xml.etree.cElementTree as ET
import re
import codecs
import json

"""GLOBALS"""

# Compiled regular expressions
LOWER_REGEX = re.compile(r'^([a-z]|_)*$')
LOWER_COLON_REGEX = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
PROBLEMATIC_CHARS_REGEX = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

# Helper lists
JSON_CREATED_KEY_CHILDREN = ["version", "changeset", "timestamp", "user", "uid"]

""" Functions"""

def shape_element(element):
    """ Transforms the shape of the provided OSM XML element into a json structure.
    For more details about the format of an input element, you can visit
    https://wiki.openstreetmap.org/wiki/Elements.

    The transformation takes into consideration the following:

    - only the top level tags "node" and "way" are transformed
    - all attributes of "node" and "way" are turned into regular key/value pairs, except:
        - attributes in the JSON_CREATED_KEY_CHILDS are added under a key "created"
        - attributes for latitude and longitude are added to a "pos" array of floats,
          for use in geospacial indexing
    - if second level tag "k" value contains problematic characters as defined by
    PROBLEMATIC_CHARS_REGEX, it will be ignored
    - if second level tag "k" value starts with "addr:", it will added to a dictionary "address"
    - if second level tag "k" value does not start with "addr:", but contains ":", it will be
      processed same as any other tag.
    - if there is a second ":" that separates the type/direction of a street,
      the tag will be ignored, for example:

        <tag k="addr:housenumber" v="5158"/>
        <tag k="addr:street" v="North Lincoln Avenue"/>
        <tag k="addr:street:name" v="Lincoln"/>
        <tag k="addr:street:prefix" v="North"/>
        <tag k="addr:street:type" v="Avenue"/>
        <tag k="amenity" v="pharmacy"/>

        will be turned into:

        {
            ...
            "address": {
                "housenumber": 5158,
                "street": "North Lincoln Avenue"
            }
            "amenity": "pharmacy",
            ...
        }

    - for "way" specifically:

        <nd ref="305896090"/>
        <nd ref="1719825889"/>

        will be turned into:

        "node_refs": ["305896090", "1719825889"]

    Here is an example of a node transformation:

    {
        "id": "2406124091",
        "type: "node",
        "visible":"true",
        "created": {
                  "version":"2",
                  "changeset":"17206049",
                  "timestamp":"2013-08-03T16:43:42Z",
                  "user":"linuxUser16",
                  "uid":"1219059"
                },
        "pos": [41.9757030, -87.6921867],
        "address": {
                  "housenumber": "5157",
                  "postcode": "60625",
                  "street": "North Lincoln Ave"
                },
        "amenity": "restaurant",
        "cuisine": "mexican",
        "name": "La Cabana De Don Luis",
        "phone": "1 (773)-271-5176"
    }

    Note that function won't try to audit the data in any form, for that please check the
    functions in src/audit.py
    """
    node = {}
    if element.tag == "node" or element.tag == "way":
        # Defining type
        node["type"] = element.tag

        # Processing node/way attributes
        for attrib, value in element.attrib.iteritems():
            if attrib in JSON_CREATED_KEY_CHILDREN:
                if "created" not in node:
                    node["created"] = {}
                node["created"][attrib] = value
            elif attrib in ["lat", "lon"]:
                if "pos" not in node:
                    node["pos"] = [0, 0]
                index = 0 if attrib == "lat" else 1
                node["pos"][index] = float(value)
            else:
                node[attrib] = value

        # Processing second level tags
        for tag in element.findall('tag'):
            key = tag.attrib['k']
            value = tag.attrib['v']
            if re.search(PROBLEMATIC_CHARS_REGEX, key):
                continue
            key_split = key.split(':')
            if len(key_split) > 1 and key_split[0] == "addr":
                if key_split[1] == "street" and len(key_split) == 3:
                    continue
                if "address" not in node:
                    node["address"] = {}
                node["address"][key_split[1]] = value
            else:
                node[key] = value

        if element.tag == "way":
            node["node_refs"] = []
            for nd in element.findall('nd'):
                node["node_refs"].append(nd.attrib["ref"])

        return node
    else:
        return None


def process_map(file_in, pretty=False):
    """
    Generates a list of JSON structures for a subset of elements
    in the provided OSM XML file

    :param file_in: Filepath to OSM XML file
    :param pretty: If True, it will write the data into a file in a pretty format
    :param json_dir: Folder to the location of the
    :return: List of JSON structures
    """
    file_out = "{0}.json".format(file_in)
    data = []
    for _, element in ET.iterparse(file_in):
            el = shape_element(element)
            if el:
                data.append(el)
    with open(file_out, 'w') as json_f:
        if pretty:
            json.dump(data, json_f, indent=2)
        else:
            json.dump(data, json_f)
    return data
