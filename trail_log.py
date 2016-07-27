#!/usr/bin/env python
# CloudTrail => HipChat
import os
import requests
import logging
import json
import boto3
import urllib2
import urllib
import gzip
import geoip2.database
from geoip2.errors import AddressNotFoundError
from StringIO import StringIO

from ConfigParser import ConfigParser

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

config = ConfigParser()
config.read('config.cfg')
notify_url = config.get('hipchat', 'notify_url')
room_id = config.get('hipchat', 'room_id')


def post_message(msg, notify=False):
    logger.info(msg)
    color = "red" if notify else "green"
    req_body = {
        "from": "AWS Lambda",
        "message_format": "text",
        "message": msg,
        "color": color,
        "notify": 1 if notify else 0,
        "room_id": room_id
    }
    try:
        data = urllib.urlencode(req_body)
        ret = urllib2.urlopen(notify_url, data)
        logger.info(ret.getcode())
    except urllib2.URLError as e:
        logger.exception(e)


def lambda_handler(event, context):
    s3 = boto3.resource('s3')
    for record in event['Records']:
        logger.info(record)
        if 's3' not in record:
            continue
        bucket_name = record['s3']['bucket']['name']
        name = record['s3']['object']['key']
        tmp_file = os.path.join('/tmp', os.path.basename(name))
        s3.meta.client.download_file(
            bucket_name, name, tmp_file)
        json_data = StringIO()
        with gzip.open(tmp_file, 'rb') as fin:
            json_data.writelines(fin)
        json_data.seek(0)
        jobj = json.load(json_data)
        process_event(jobj)


def process_event(event):
    for rec in filter(
        lambda i: not i['eventName'].startswith(
            ('Describe', 'List', 'Get', 'CreateLogStream')), event['Records']):
        notify = False
        if 'sourceIPAddress' in rec:
            rec['sourceGeo'] = get_geoip2_info(rec['sourceIPAddress'])
        if rec['eventName'].startswith('Console'):
            notify = True
        post_message(
            gen_hipchat_msg(rec),
            notify,
        )


def gen_hipchat_msg(data={}, raw=False):
    if raw:
        return '{}'.format(json.dumps(data, indent=2))
    identity_type = data['userIdentity'].get('type')
    user = data['userIdentity'].get('arn', 'Root')
    if identity_type == 'IAMUser':
        user = data['userIdentity'].get('userName', 'N/A')
    location = data.get('sourceGeo', {}).get('city', None)
    if not location:
        location = data.get('sourceGeo', {}).get('country', None)
    ret_str = "{} from {}({})\nDo: {}\nId: {}\nTime: {}\nUserAgent: {}".format(
        user,
        data['sourceIPAddress'],
        location,
        data['eventName'],
        data['eventID'],
        data['eventTime'],
        data.get('userAgent', 'No UserAgent'),
    )
    return ret_str


def download_file(url, dst_path=None):
    import zlib
    r = requests.get(url, stream=True)
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    with open(dst_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(d.decompress(chunk))


def get_geoip2_info(ip_addr):
    mmdb = 'GeoLite2-City.mmdb'
    db_file = os.path.join('/tmp', mmdb)
    if not os.path.isfile(db_file):
        download_file('http://geolite.maxmind.com/download/geoip/'
                      'database/GeoLite2-City.mmdb.gz', db_file)
    if not os.path.isfile(db_file):
        return

    reader = geoip2.database.Reader(db_file, ['en'])
    try:
        response = reader.city(ip_addr)
        return {
            'continent': response.continent.name,
            'country': response.country.name,
            'subdivision': response.subdivisions.most_specific.name,
            'city': response.city.name,
            'postal_code': response.postal.code,
            'location': [
                response.location.latitude,
                response.location.longitude,
            ],
            'time_zone': response.location.time_zone,
        }
    except AddressNotFoundError:
        return {}
    except Exception as e:
        logger.exception(e)
        return {}


# for local testing
if __name__ == '__main__':
    with open('event.json', 'rb') as fin:
        jobj = json.load(fin)
        process_event(jobj)
