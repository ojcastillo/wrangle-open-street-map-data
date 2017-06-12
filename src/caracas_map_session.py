#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'orlando'

import codecs
import datetime
import re
import pprint
import src.lib.utils as utils
import xml.etree.cElementTree as ET

from collections import defaultdict

"""GLOBALS"""

ORIGINAL_OSM_MAP_FILE = 'resources/caracas_venezuela.osm'
CLEAN_OSM_MAP_FILE = 'resources/caracas_venezuela_clean.osm'

STREET_TYPE_REGEX = re.compile(r'^(?:\d+[ª.] +)?(\S+) +', re.IGNORECASE |
                               re.UNICODE)
POST_CODE_REGEX = re.compile(r'^\d{4}$')

EXPECTED_STREET_TYPES = ["Calle", "Avenida", "Bulevar", "Autopista", "Redoma",
                         "Carretera", "Acceso", "Entrada", "Transversal",
                         "Vereda", "Cota", "Esquina", "Troncal",
                         "Distribuidor", u"Vía".encode('utf-8'),
                         u"Túnel".encode('utf-8'),
                         u"Prolongación".encode('utf-8'),
                         u"Callejón".encode('utf-8')]

STREET_TYPES_CLEAN_MAPPING = {
    "Av. ": "Avenida ",
    "Av.": "Avenida ",
    "Av ": "Avenida ",
    "C.C. ": "Centro Comercial ",
    "CC ": "Centro Comercial ",
    "Km. ": u"Kilómetro ".encode('utf-8'),
    "Km ": u"Kilómetro ".encode('utf-8'),
    "Klm ": u"Kilómetro ".encode('utf-8'),
    "Urb. ": u"Urbanización ".encode('utf-8'),
    "Urb ": u"Urbanización ".encode('utf-8'),
    u"2ªTransversal ".encode('utf-8'): u"2ª Transversal ".encode('utf-8'),
    u"Vìa ".encode('utf-8'): u"Vía ".encode('utf-8'),
    u"Vía:".encode('utf-8'): u"Vía".encode('utf-8'),
    "Prolongacion ": u"Prolongación ".encode('utf-8'),
    "Carretera: ": "Carretera ",
    "carretera ": "Carretera ",
    "Autopista: ": "Autopista ",
    "calle ": "Calle ",
    "Bulevard ": "Bulevar ",
    "Bolevar ": "Bulevar ",
    "Boulevar ": "Bulevar ",
    "Boulevard ": "Bulevar ",
    "Distribuidor: ": "Distribuidor ",
    "Tunel ": u"Túnel ".encode('utf-8')
}

STREET_TYPES_CLEAN_ORDER = ["Av. ", "Av.", "Av ", "C.C. ", "CC ", "Km. ",
                            "Km ", "Klm ", "Urb. ", "Urb ",
                            u"2ªTransversal ".encode('utf-8'),
                            u"Vìa ".encode('utf-8'),
                            u"Vía:".encode('utf-8'),
                            "Prolongacion ", "Carretera: ", "carretera ",
                            "Autopista: ", "calle ", "Bulevard ",
                            "Bolevar ", "Boulevar ", "Boulevard ",
                            "Distribuidor: ", "Tunel "]

ATTRIBUTES_TYPE_MAP = {
    "lon": 'float',
    "lat": 'float',
    "timestamp": 'datetime'
}

ATTRIBUTES_CLEAN_KEY_MAPPING = {
    'addr:ful': 'addr:full',
    'addr:full\x7f': 'addr:full',
    '\x7faddr:full': 'addr:full'
}

ID_TO_TAG_DELETE_MAPPING = {
    "914310439": ["addr:postcode"]
}

CUSTOM_TAG_VALUES_MAPPING = {
    "addr:street": {
        "Los Chaguaramos": {
            "addr:postcode": '1060'
        },
        "Principal de la Haciendita": {
            "addr:postcode": '1000'
        },
    },
    "addr:full": {
        "Centro Comercial Santa Fe": {
            "addr:postcode": '1080'
        }
    },

}

"""FUNCTIONS"""

# Utilities


def write_stats(osm_file, save_path):
    stats = utils.osm_general_stats(osm_file)
    with open(save_path, 'w') as file_o:
        pprint.pprint(stats, file_o)


def print_elements_with_tag_value(osm_file, tag_value):
    elements = utils.find_elements_with_tag_value(
        osm_file, 'addr:street', tag_value)
    for element in elements:
        utils.pretty_element(element)


# Auditing

def audit_street_type(audit_dict, street_name):
    m = STREET_TYPE_REGEX.search(street_name)
    if m:
        street_type = m.group(1)
        if street_type.encode('utf-8') not in EXPECTED_STREET_TYPES:
            audit_dict['street_types'][street_type].add(street_name)


def audit_post_code(audit_dict, post_code):
    m = POST_CODE_REGEX.search(post_code)
    if not m:
        audit_dict['postcode_types'][post_code] += 1


def audit_city(audit_dict, tag_value):
    if tag_value != 'Caracas':
        audit_dict['city_types'][tag_value] += 1


def audit_country(audit_dict, tag_value):
    if tag_value != 'VE':
        audit_dict['country_types'][tag_value] += 1


def audit_state(audit_dict, tag_value):
    if tag_value != 'Distrito Capital':
        audit_dict['state_types'][tag_value] += 1


def audit_element(element, audit_dict):
    # Auditing attributes types
    for field, type_str in ATTRIBUTES_TYPE_MAP.iteritems():
        if field in element.attrib:
            try:
                if type_str == "float":
                    float(element.attrib[field])
                elif type_str == "datetime":
                    datetime.datetime.strptime(
                        element.attrib[field], "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                audit_dict[field + "_types"].add(element.attrib[field])

    # Auditing tags
    for tag in element.iter("tag"):
        tag_key = tag.attrib['k']
        tag_value = tag.attrib['v']
        if tag_key == "addr:street":
            audit_street_type(audit_dict, tag_value)
        elif tag_key == "addr:postcode":
            audit_post_code(audit_dict, tag_value)
        elif tag_key == "addr:city":
            audit_city(audit_dict, tag_value)
        elif tag_key == "addr:country":
            audit_country(audit_dict, tag_value)
        elif tag_key == "addr:state":
            audit_state(audit_dict, tag_value)


def audit(osm_file):
    osm_file = open(osm_file, "r")
    audit_dict = {
        "lon_types": set(),
        "lat_types": set(),
        "timestamp_types": set(),
        "street_types": defaultdict(set),
        "postcode_types": defaultdict(int),
        "city_types": defaultdict(int),
        "country_types": defaultdict(int),
        "state_types": defaultdict(int)
    }
    for event, element in ET.iterparse(osm_file):
        if element.tag == "node" or element.tag == "way":
            audit_element(element, audit_dict)
    return audit_dict


def save_audit(osm_file, save_path):
    audit_dict = audit(osm_file)
    with codecs.open(save_path, mode='w', encoding='utf-8') as file_o:
        for key, value in audit_dict.iteritems():
            file_o.write('Unrecognized {}: {}\n'.format(key, len(value)))
            if type(value) == set:
                for set_value in value:
                    file_o.write(u'\t{}\n'.format(set_value))
            else:
                for value_type, value in audit_dict[key].iteritems():
                    if type(value) == set:
                        file_o.write(u'\t{}\n'.format(value_type))
                        for value_member in value:
                            file_o.write(u'\t\t{}\n'.format(value_member))
                    else:
                        file_o.write(u'\t{}; {}\n'.format(value_type, value))
            file_o.write('\n')

# Cleaning


def clean_street_name(street_name):
    # Replace abbreviations with full street types
    street_name = street_name.encode('utf-8')
    for abbrv_type in STREET_TYPES_CLEAN_ORDER:
        full_type = STREET_TYPES_CLEAN_MAPPING[abbrv_type]
        if street_name.find(abbrv_type) != -1:
            street_name = street_name.replace(abbrv_type, full_type, 1)
    street_name = street_name.decode('utf-8')
    return street_name


def clean_city_value(city_value):
    if city_value.lower() == 'caracas':
        return 'Caracas'
    return city_value


def clean_element(element, clean_summary):
    # Create a map for child tags to make it easier cross reference tags
    child_tags_map = {}
    for tag in element.iter("tag"):
        child_tags_map[tag.attrib['k']] = tag

    # Extract map with child tags to delete
    child_tags_to_delete = []
    if element.attrib['id'] in ID_TO_TAG_DELETE_MAPPING:
        child_tags_to_delete = ID_TO_TAG_DELETE_MAPPING[element.attrib['id']]

    # Clean up child tags
    for tag_key, tag in child_tags_map.iteritems():
        tag_value = tag.attrib['v']
        if tag_key in child_tags_to_delete:
            element.remove(tag)
            summary_key = tag_key + "=" + tag_value
            clean_summary['deleted_tag_types'][summary_key] = 1
        else:
            if tag_key in CUSTOM_TAG_VALUES_MAPPING:
                # We allow the assignment of a custom value to a set of tags
                # if we match a substring of another tag value. For example, we
                # might want to force a postal code based on the address value.
                tag_mapping = CUSTOM_TAG_VALUES_MAPPING[tag_key]
                for sub_str, map_dict in tag_mapping.iteritems():
                    if sub_str in tag_value.encode('utf-8'):
                        for ref_key, custom_value in map_dict.iteritems():
                            if ref_key in child_tags_map:
                                ref_value = child_tags_map[ref_key].attrib['v']
                                if ref_value != custom_value:
                                    child_tags_map[ref_key].attrib[
                                        'v'] = custom_value
                                    summary_key = u"<{}={},{}={}>".format(
                                        tag_key, tag_value, ref_key,
                                        custom_value)
                                    clean_summary['custom_tag_values'][
                                        summary_key] += 1
                        break
            if tag_key == "addr:street":
                clean_value = clean_street_name(tag_value)
                if clean_value != tag_value:
                    tag.attrib['v'] = clean_value
                    clean_summary['updated_street_types'][
                        tag_value] = clean_value
            if tag_key == "addr:city":
                clean_value = clean_city_value(tag_value)
                if clean_value != tag_value:
                    tag.attrib['v'] = clean_value
                    clean_summary['updated_city_types'][
                        tag_value] = clean_value
            if tag_key in ATTRIBUTES_CLEAN_KEY_MAPPING:
                tag.attrib['k'] = ATTRIBUTES_CLEAN_KEY_MAPPING[tag_key]
                clean_summary['updated_attribute_types'][tag_key] += 1


def clean_up_map(original_osm=ORIGINAL_OSM_MAP_FILE,
                 clean_osm=CLEAN_OSM_MAP_FILE):
    # Get an iterable
    context = ET.iterparse(original_osm, events=("start", "end"))

    # Turn it into an iterator
    context = iter(context)

    # Get the root element
    event, root = context.next()

    # Clean
    clean_summary = {
        "updated_street_types": defaultdict(str),
        "updated_city_types": defaultdict(str),
        "updated_attribute_types": defaultdict(int),
        "deleted_tag_types": defaultdict(int),
        "custom_tag_values": defaultdict(int),
    }
    for event, element in context:
        if event == "end" and (element.tag == "node" or element.tag == "way"):
            clean_element(element, clean_summary)

    # Save
    tree = ET.ElementTree(root)
    tree.write(clean_osm, 'utf-8', True)

    return clean_summary


def generate_clean_summary(save_path, original_osm=ORIGINAL_OSM_MAP_FILE,
                           clean_osm=CLEAN_OSM_MAP_FILE):
    clean_summary = clean_up_map(original_osm, clean_osm)
    with codecs.open(save_path, mode='w', encoding='utf-8') as file_o:
        for key, value in clean_summary.iteritems():
            file_o.write('{}: {}\n'.format(key, len(value)))
            for field, change in value.iteritems():
                file_o.write(u'\t{}: {}\n'.format(field, change))
            file_o.write('\n')
