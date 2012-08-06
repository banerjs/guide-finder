import os, sys
import math
import Image
import pycurl, urllib
from math import log10
from Image import ANTIALIAS
from datetime import time

from django.db import models, connection, transaction
from django.db.models import FileField
from django.forms import forms
from django.template.defaultfilters import filesizeformat
from django.utils.translation import ugettext_lazy as _
from django.utils import simplejson as json
from django.core.exceptions import ValidationError
from django.conf import settings

# Online Libraries and Snippets to help Django function

digits = lambda n: ((n==0) and 1) or int(log10(abs(n)))+1

def resize_image(path, size):
    try:
        im = Image.open(settings.MEDIA_ROOT + str(path))
    except:
        return False
    im.thumbnail(size, ANTIALIAS)
    im.save(settings.MEDIA_ROOT + str(path))
    return True

def containsOnly(str, set):
    """
    Function to check if the string has the set of characters only, and nothing else.
    """
    return not (False in [c in set for c in str])

class ContentTypeRestrictedFileField(FileField):
    """
    Same as FileField, but you can specify:
    * content_types - list containing allowed content_types. Example: ['application/pdf', 'image/jpeg']
    * max_upload_size - a number indicating the maximum file size allowed for upload.
    2.5MB - 2621440
    5MB - 5242880
    10MB - 10485760
    20MB - 20971520
    50MB - 5242880
    100MB 104857600
    250MB - 214958080
    500MB - 429916160
    """
    def __init__(self, *args, **kwargs):
        self.content_types = kwargs.pop("content_types")
        self.max_upload_size = kwargs.pop("max_upload_size")
        
        super(ContentTypeRestrictedFileField, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        data = super(ContentTypeRestrictedFileField, self).clean(*args, **kwargs)
        file = data.file
        try:
            content_type = file.content_type
            if content_type in self.content_types:
                if file._size > self.max_upload_size:
                    raise forms.ValidationError(_('Please keep filesize under %s. Current filesize %s') % (filesizeformat(self.max_upload_size), filesizeformat(file._size)))
                else:
                    raise forms.ValidationError(_('Filetype not supported.'))
        except AttributeError:
            pass
        return data

class GoogleLatLng:
    """
    Send an address to Google Geocoder API and get JSON output back.
    Parse to retrieve latitude and longitude.
    There is a 24-hour usage limit, currently this is 2500 requests
    but this could change in the future. Check Google's Terms of Use
    before employing this technique.
    """
    def __init__(self):
        self.lat = 1000.0
        self.lng = 1000.0
        self.results = ""
        self.type = None
        self.GEOCODE_URL = 'http://maps.googleapis.com/maps/api/geocode/json'

    def parseType(self, type):
        """
        A type=True implies a search for bodies of water
        """
        for r in self.results['results']:
            if ('natural_feature' in r['types']) == type:
                self.lat = r['geometry']['location']['lat']
                self.lng = r['geometry']['location']['lng']
                self.results = r
                self.type = type
                return True
        self.type = None
        return False

    def parseLocation(self):
        """
        WARNING: Only use if self.parseType returns True
        """
        r = []
        if self.type == None: return r
        elif not self.type:
            if self.results['types'][0] in ['locality', 'administrative_area_level_2', 'point_of_interest', 'street_address', 'route']:
                for a in self.results['address_components']:
                    if a['types'][0] in ['locality', 'administrative_area_level_2']:
                        r.append(a['long_name'])
                    elif a['types'][0] in ['administrative_area_level_1', 'country']:
                        r.append((a['long_name'], a['short_name']))
                    else:
                        pass
            return r
        else:
            for a in self.results['address_components']:
                if a['types'][0] in ['administrative_area_level_1', 'country']:
                    r.append((a['long_name'], a['short_name']))
                elif a['types'][0] == 'natural_feature':
                    r.append(a['long_name'])
                else:
                    pass
            return r

    def requestLatLngJSON(self, address, type=False, sensor='false', **kwargs):
        kwargs.update({ 'address':address, 'sensor':'false' })
        url = self.GEOCODE_URL + '?' + urllib.urlencode(kwargs)
        self.results = json.load(urllib.urlopen(url))
        if not self.results['results']:
            self.type = None
            return False
        else:
            return self.parseType(type)

#adapted from http://www.djangosnippets.org/snippets/494/
#using UN country and 3 char code list from http://unstats.un.org/unsd/methods/m49/m49alpha.htm
#correct as of 17th October 2008

COUNTRIES_THREE = (
        ('AFG', _('Afghanistan')),
        ('ALA', _('Aland Islands')),
        ('ALB', _('Albania')),
        ('DZA', _('Algeria')),
        ('ASM', _('American Samoa')),
        ('AND', _('Andorra')),
        ('AGO', _('Angola')),
        ('AIA', _('Anguilla')),
        ('ATG', _('Antigua and Barbuda')),
        ('ARG', _('Argentina')),
        ('ARM', _('Armenia')),
        ('ABW', _('Aruba')),
        ('AUS', _('Australia')),
        ('AUT', _('Austria')),
        ('AZE', _('Azerbaijan')),
        ('BHS', _('Bahamas')),
        ('BHR', _('Bahrain')),
        ('BGD', _('Bangladesh')),
        ('BRB', _('Barbados')),
        ('BLR', _('Belarus')),
        ('BEL', _('Belgium')),
        ('BLZ', _('Belize')),
        ('BEN', _('Benin')),
        ('BMU', _('Bermuda')),
        ('BTN', _('Bhutan')),
        ('BOL', _('Bolivia')),
        ('BIH', _('Bosnia and Herzegovina')),
        ('BWA', _('Botswana')),
        ('BRA', _('Brazil')),
        ('VGB', _('British Virgin Islands')),
        ('BRN', _('Brunei Darussalam')),
        ('BGR', _('Bulgaria')),
        ('BFA', _('Burkina Faso')),
        ('BDI', _('Burundi')),
        ('KHM', _('Cambodia')),
        ('CMR', _('Cameroon')),
        ('CAN', _('Canada')),
        ('CPV', _('Cape Verde')),
        ('CYM', _('Cayman Islands')),
        ('CAF', _('Central African Republic')),
        ('TCD', _('Chad')),
        ('CIL', _('Channel Islands')),
        ('CHL', _('Chile')),
        ('CHN', _('China')),
        ('HKG', _('China - Hong Kong')),
        ('MAC', _('China - Macao')),
        ('COL', _('Colombia')),
        ('COM', _('Comoros')),
        ('COG', _('Congo')),
        ('COK', _('Cook Islands')),
        ('CRI', _('Costa Rica')),
        ('CIV', _('Cote d\'Ivoire')),
        ('HRV', _('Croatia')),
        ('CUB', _('Cuba')),
        ('CYP', _('Cyprus')),
        ('CZE', _('Czech Republic')),
        ('PRK', _('Democratic People\'s Republic of Korea')),
        ('COD', _('Democratic Republic of the Congo')),
        ('DNK', _('Denmark')),
        ('DJI', _('Djibouti')),
        ('DMA', _('Dominica')),
        ('DOM', _('Dominican Republic')),
        ('ECU', _('Ecuador')),
        ('EGY', _('Egypt')),
        ('SLV', _('El Salvador')),
        ('GNQ', _('Equatorial Guinea')),
        ('ERI', _('Eritrea')),
        ('EST', _('Estonia')),
        ('ETH', _('Ethiopia')),
        ('FRO', _('Faeroe Islands')),
        ('FLK', _('Falkland Islands (Malvinas)')),
        ('FJI', _('Fiji')),
        ('FIN', _('Finland')),
        ('FRA', _('France')),
        ('GUF', _('French Guiana')),
        ('PYF', _('French Polynesia')),
        ('GAB', _('Gabon')),
        ('GMB', _('Gambia')),
        ('GEO', _('Georgia')),
        ('DEU', _('Germany')),
        ('GHA', _('Ghana')),
        ('GIB', _('Gibraltar')),
        ('GRC', _('Greece')),
        ('GRL', _('Greenland')),
        ('GRD', _('Grenada')),
        ('GLP', _('Guadeloupe')),
        ('GUM', _('Guam')),
        ('GTM', _('Guatemala')),
        ('GGY', _('Guernsey')),
        ('GIN', _('Guinea')),
        ('GNB', _('Guinea-Bissau')),
        ('GUY', _('Guyana')),
        ('HTI', _('Haiti')),
        ('VAT', _('Holy See (Vatican City)')),
        ('HND', _('Honduras')),
        ('HUN', _('Hungary')),
        ('ISL', _('Iceland')),
        ('IND', _('India')),
        ('IDN', _('Indonesia')),
        ('IRN', _('Iran')),
        ('IRQ', _('Iraq')),
        ('IRL', _('Ireland')),
        ('IMN', _('Isle of Man')),
        ('ISR', _('Israel')),
        ('ITA', _('Italy')),
        ('JAM', _('Jamaica')),
        ('JPN', _('Japan')),
        ('JEY', _('Jersey')),
        ('JOR', _('Jordan')),
        ('KAZ', _('Kazakhstan')),
        ('KEN', _('Kenya')),
        ('KIR', _('Kiribati')),
        ('KWT', _('Kuwait')),
        ('KGZ', _('Kyrgyzstan')),
        ('LAO', _('Lao People\'s Democratic Republic')),
        ('LVA', _('Latvia')),
        ('LBN', _('Lebanon')),
        ('LSO', _('Lesotho')),
        ('LBR', _('Liberia')),
        ('LBY', _('Libyan Arab Jamahiriya')),
        ('LIE', _('Liechtenstein')),
        ('LTU', _('Lithuania')),
        ('LUX', _('Luxembourg')),
        ('MKD', _('Macedonia')),
        ('MDG', _('Madagascar')),
        ('MWI', _('Malawi')),
        ('MYS', _('Malaysia')),
        ('MDV', _('Maldives')),
        ('MLI', _('Mali')),
        ('MLT', _('Malta')),
        ('MHL', _('Marshall Islands')),
        ('MTQ', _('Martinique')),
        ('MRT', _('Mauritania')),
        ('MUS', _('Mauritius')),
        ('MYT', _('Mayotte')),
        ('MEX', _('Mexico')),
        ('FSM', _('Micronesia, Federated States of')),
        ('MCO', _('Monaco')),
        ('MNG', _('Mongolia')),
        ('MNE', _('Montenegro')),
        ('MSR', _('Montserrat')),
        ('MAR', _('Morocco')),
        ('MOZ', _('Mozambique')),
        ('MMR', _('Myanmar')),
        ('NAM', _('Namibia')),
        ('NRU', _('Nauru')),
        ('NPL', _('Nepal')),
        ('NLD', _('Netherlands')),
        ('ANT', _('Netherlands Antilles')),
        ('NCL', _('New Caledonia')),
        ('NZL', _('New Zealand')),
        ('NIC', _('Nicaragua')),
        ('NER', _('Niger')),
        ('NGA', _('Nigeria')),
        ('NIU', _('Niue')),
        ('NFK', _('Norfolk Island')),
        ('MNP', _('Northern Mariana Islands')),
        ('NOR', _('Norway')),
        ('PSE', _('Occupied Palestinian Territory')),
        ('OMN', _('Oman')),
        ('PAK', _('Pakistan')),
        ('PLW', _('Palau')),
        ('PAN', _('Panama')),
        ('PNG', _('Papua New Guinea')),
        ('PRY', _('Paraguay')),
        ('PER', _('Peru')),
        ('PHL', _('Philippines')),
        ('PCN', _('Pitcairn')),
        ('POL', _('Poland')),
        ('PRT', _('Portugal')),
        ('PRI', _('Puerto Rico')),
        ('QAT', _('Qatar')),
        ('KOR', _('Republic of Korea')),
        ('MDA', _('Republic of Moldova')),
        ('REU', _('Reunion')),
        ('ROU', _('Romania')),
        ('RUS', _('Russian Federation')),
        ('RWA', _('Rwanda')),
        ('BLM', _('Saint-Barthelemy')),
        ('SHN', _('Saint Helena')),
        ('KNA', _('Saint Kitts and Nevis')),
        ('LCA', _('Saint Lucia')),
        ('MAF', _('Saint-Martin (French part)')),
        ('SPM', _('Saint Pierre and Miquelon')),
        ('VCT', _('Saint Vincent and the Grenadines')),
        ('WSM', _('Samoa')),
        ('SMR', _('San Marino')),
        ('STP', _('Sao Tome and Principe')),
        ('SAU', _('Saudi Arabia')),
        ('SEN', _('Senegal')),
        ('SRB', _('Serbia')),
        ('SYC', _('Seychelles')),
        ('SLE', _('Sierra Leone')),
        ('SGP', _('Singapore')),
        ('SVK', _('Slovakia')),
        ('SVN', _('Slovenia')),
        ('SLB', _('Solomon Islands')),
        ('SOM', _('Somalia')),
        ('ZAF', _('South Africa')),
        ('ESP', _('Spain')),
        ('LKA', _('Sri Lanka')),
        ('SDN', _('Sudan')),
        ('SUR', _('Suriname')),
        ('SJM', _('Svalbard and Jan Mayen Islands')),
        ('SWZ', _('Swaziland')),
        ('SWE', _('Sweden')),
        ('CHE', _('Switzerland')),
        ('SYR', _('Syrian Arab Republic')),
        ('TJK', _('Tajikistan')),
        ('THA', _('Thailand')),
        ('TLS', _('Timor-Leste')),
        ('TGO', _('Togo')),
        ('TKL', _('Tokelau')),
        ('TON', _('Tonga')),
        ('TTO', _('Trinidad and Tobago')),
        ('TUN', _('Tunisia')),
        ('TUR', _('Turkey')),
        ('TKM', _('Turkmenistan')),
        ('TCA', _('Turks and Caicos Islands')),
        ('TUV', _('Tuvalu')),
        ('UGA', _('Uganda')),
        ('UKR', _('Ukraine')),
        ('ARE', _('United Arab Emirates')),
        ('GBR', _('United Kingdom')),
        ('TZA', _('United Republic of Tanzania')),
        ('USA', _('United States of America')),
        ('VIR', _('United States Virgin Islands')),
        ('URY', _('Uruguay')),
        ('UZB', _('Uzbekistan')),
        ('VUT', _('Vanuatu')),
        ('VEN', _('Venezuela (Bolivarian Republic of)')),
        ('VNM', _('Viet Nam')),
        ('WLF', _('Wallis and Futuna Islands')),
        ('ESH', _('Western Sahara')),
        ('YEM', _('Yemen')),
        ('ZMB', _('Zambia')),
        ('ZWE', _('Zimbabwe')),
)

# ISO 3166-1 country names and codes adapted from http://opencountrycodes.appspot.com/python/
COUNTRIES_TWO = (
    ('GB', _('United Kingdom')),
    ('AF', _('Afghanistan')),
    ('AX', _('Aland Islands')),
    ('AL', _('Albania')),
    ('DZ', _('Algeria')),
    ('AS', _('American Samoa')),
    ('AD', _('Andorra')),
    ('AO', _('Angola')),
    ('AI', _('Anguilla')),
    ('AQ', _('Antarctica')),
    ('AG', _('Antigua and Barbuda')),
    ('AR', _('Argentina')),
    ('AM', _('Armenia')),
    ('AW', _('Aruba')),
    ('AU', _('Australia')),
    ('AT', _('Austria')),
    ('AZ', _('Azerbaijan')),
    ('BS', _('Bahamas')),
    ('BH', _('Bahrain')),
    ('BD', _('Bangladesh')),
    ('BB', _('Barbados')),
    ('BY', _('Belarus')),
    ('BE', _('Belgium')),
    ('BZ', _('Belize')),
    ('BJ', _('Benin')),
    ('BM', _('Bermuda')),
    ('BT', _('Bhutan')),
    ('BO', _('Bolivia')),
    ('BA', _('Bosnia and Herzegovina')),
    ('BW', _('Botswana')),
    ('BV', _('Bouvet Island')),
    ('BR', _('Brazil')),
    ('IO', _('British Indian Ocean Territory')),
    ('BN', _('Brunei Darussalam')),
    ('BG', _('Bulgaria')),
    ('BF', _('Burkina Faso')),
    ('BI', _('Burundi')),
    ('KH', _('Cambodia')),
    ('CM', _('Cameroon')),
    ('CA', _('Canada')),
    ('CV', _('Cape Verde')),
    ('KY', _('Cayman Islands')),
    ('CF', _('Central African Republic')),
    ('TD', _('Chad')),
    ('CL', _('Chile')),
    ('CN', _('China')),
    ('CX', _('Christmas Island')),
    ('CC', _('Cocos (Keeling) Islands')),
    ('CO', _('Colombia')),
    ('KM', _('Comoros')),
    ('CG', _('Congo')),
    ('CD', _('Congo, The Democratic Republic of the')),
    ('CK', _('Cook Islands')),
    ('CR', _('Costa Rica')),
    ('CI', _('Cote d\'Ivoire')),
    ('HR', _('Croatia')),
    ('CU', _('Cuba')),
    ('CY', _('Cyprus')),
    ('CZ', _('Czech Republic')),
    ('DK', _('Denmark')),
    ('DJ', _('Djibouti')),
    ('DM', _('Dominica')),
    ('DO', _('Dominican Republic')),
    ('EC', _('Ecuador')),
    ('EG', _('Egypt')),
    ('SV', _('El Salvador')),
    ('GQ', _('Equatorial Guinea')),
    ('ER', _('Eritrea')),
    ('EE', _('Estonia')),
    ('ET', _('Ethiopia')),
    ('FK', _('Falkland Islands (Malvinas)')),
    ('FO', _('Faroe Islands')),
    ('FJ', _('Fiji')),
    ('FI', _('Finland')),
    ('FR', _('France')),
    ('GF', _('French Guiana')),
    ('PF', _('French Polynesia')),
    ('TF', _('French Southern Territories')),
    ('GA', _('Gabon')),
    ('GM', _('Gambia')),
    ('GE', _('Georgia')),
    ('DE', _('Germany')),
    ('GH', _('Ghana')),
    ('GI', _('Gibraltar')),
    ('GR', _('Greece')),
    ('GL', _('Greenland')),
    ('GD', _('Grenada')),
    ('GP', _('Guadeloupe')),
    ('GU', _('Guam')),
    ('GT', _('Guatemala')),
    ('GG', _('Guernsey')),
    ('GN', _('Guinea')),
    ('GW', _('Guinea-Bissau')),
    ('GY', _('Guyana')),
    ('HT', _('Haiti')),
    ('HM', _('Heard Island and McDonald Islands')),
    ('VA', _('Holy See (Vatican City State)')),
    ('HN', _('Honduras')),
    ('HK', _('Hong Kong')),
    ('HU', _('Hungary')),
    ('IS', _('Iceland')),
    ('IN', _('India')),
    ('ID', _('Indonesia')),
    ('IR', _('Iran, Islamic Republic of')),
    ('IQ', _('Iraq')),
    ('IE', _('Ireland')),
    ('IM', _('Isle of Man')),
    ('IL', _('Israel')),
    ('IT', _('Italy')),
    ('JM', _('Jamaica')),
    ('JP', _('Japan')),
    ('JE', _('Jersey')),
    ('JO', _('Jordan')),
    ('KZ', _('Kazakhstan')),
    ('KE', _('Kenya')),
    ('KI', _('Kiribati')),
    ('KP', _('Korea, Democratic People\'s Republic of')),
    ('KR', _('Korea, Republic of')),
    ('KW', _('Kuwait')),
    ('KG', _('Kyrgyzstan')),
    ('LA', _('Lao People\'s Democratic Republic')),
    ('LV', _('Latvia')),
    ('LB', _('Lebanon')),
    ('LS', _('Lesotho')),
    ('LR', _('Liberia')),
    ('LY', _('Libyan Arab Jamahiriya')),
    ('LI', _('Liechtenstein')),
    ('LT', _('Lithuania')),
    ('LU', _('Luxembourg')),
    ('MO', _('Macao')),
    ('MK', _('Macedonia, The Former Yugoslav Republic of')),
    ('MG', _('Madagascar')),
    ('MW', _('Malawi')),
    ('MY', _('Malaysia')),
    ('MV', _('Maldives')),
    ('ML', _('Mali')),
    ('MT', _('Malta')),
    ('MH', _('Marshall Islands')),
    ('MQ', _('Martinique')),
    ('MR', _('Mauritania')),
    ('MU', _('Mauritius')),
    ('YT', _('Mayotte')),
    ('MX', _('Mexico')),
    ('FM', _('Micronesia, Federated States of')),
    ('MD', _('Moldova')),
    ('MC', _('Monaco')),
    ('MN', _('Mongolia')),
    ('ME', _('Montenegro')),
    ('MS', _('Montserrat')),
    ('MA', _('Morocco')),
    ('MZ', _('Mozambique')),
    ('MM', _('Myanmar')),
    ('NA', _('Namibia')),
    ('NR', _('Nauru')),
    ('NP', _('Nepal')),
    ('NL', _('Netherlands')),
    ('AN', _('Netherlands Antilles')),
    ('NC', _('New Caledonia')),
    ('NZ', _('New Zealand')),
    ('NI', _('Nicaragua')),
    ('NE', _('Niger')),
    ('NG', _('Nigeria')),
    ('NU', _('Niue')),
    ('NF', _('Norfolk Island')),
    ('MP', _('Northern Mariana Islands')),
    ('NO', _('Norway')),
    ('OM', _('Oman')),
    ('PK', _('Pakistan')),
    ('PW', _('Palau')),
    ('PS', _('Palestinian Territory, Occupied')),
    ('PA', _('Panama')),
    ('PG', _('Papua New Guinea')),
    ('PY', _('Paraguay')),
    ('PE', _('Peru')),
    ('PH', _('Philippines')),
    ('PN', _('Pitcairn')),
    ('PL', _('Poland')),
    ('PT', _('Portugal')),
    ('PR', _('Puerto Rico')),
    ('QA', _('Qatar')),
    ('RE', _('Reunion')),
    ('RO', _('Romania')),
    ('RU', _('Russian Federation')),
    ('RW', _('Rwanda')),
    ('BL', _('Saint Barthelemy')),
    ('SH', _('Saint Helena')),
    ('KN', _('Saint Kitts and Nevis')),
    ('LC', _('Saint Lucia')),
    ('MF', _('Saint Martin')),
    ('PM', _('Saint Pierre and Miquelon')),
    ('VC', _('Saint Vincent and the Grenadines')),
    ('WS', _('Samoa')),
    ('SM', _('San Marino')),
    ('ST', _('Sao Tome and Principe')),
    ('SA', _('Saudi Arabia')),
    ('SN', _('Senegal')),
    ('RS', _('Serbia')),
    ('SC', _('Seychelles')),
    ('SL', _('Sierra Leone')),
    ('SG', _('Singapore')),
    ('SK', _('Slovakia')),
    ('SI', _('Slovenia')),
    ('SB', _('Solomon Islands')),
    ('SO', _('Somalia')),
    ('ZA', _('South Africa')),
    ('GS', _('South Georgia and the South Sandwich Islands')),
    ('ES', _('Spain')),
    ('LK', _('Sri Lanka')),
    ('SD', _('Sudan')),
    ('SR', _('Suriname')),
    ('SJ', _('Svalbard and Jan Mayen')),
    ('SZ', _('Swaziland')),
    ('SE', _('Sweden')),
    ('CH', _('Switzerland')),
    ('SY', _('Syrian Arab Republic')),
    ('TW', _('Taiwan, Province of China')),
    ('TJ', _('Tajikistan')),
    ('TZ', _('Tanzania, United Republic of')),
    ('TH', _('Thailand')),
    ('TL', _('Timor-Leste')),
    ('TG', _('Togo')),
    ('TK', _('Tokelau')),
    ('TO', _('Tonga')),
    ('TT', _('Trinidad and Tobago')),
    ('TN', _('Tunisia')),
    ('TR', _('Turkey')),
    ('TM', _('Turkmenistan')),
    ('TC', _('Turks and Caicos Islands')),
    ('TV', _('Tuvalu')),
    ('UG', _('Uganda')),
    ('UA', _('Ukraine')),
    ('AE', _('United Arab Emirates')),
    ('US', _('United States')),
    ('UM', _('United States Minor Outlying Islands')),
    ('UY', _('Uruguay')),
    ('UZ', _('Uzbekistan')),
    ('VU', _('Vanuatu')),
    ('VE', _('Venezuela')),
    ('VN', _('Viet Nam')),
    ('VG', _('Virgin Islands, British')),
    ('VI', _('Virgin Islands, U.S.')),
    ('WF', _('Wallis and Futuna')),
    ('EH', _('Western Sahara')),
    ('YE', _('Yemen')),
    ('ZM', _('Zambia')),
    ('ZW', _('Zimbabwe')),
)
