from flask import Flask, request, jsonify
import requests
import os
import json


app = Flask(__name__)
SHORTCODE = 21585741
DEVAPI_URL = "http://devapi.globelabs.com.ph"
SMS_URL = DEVAPI_URL + "/smsmessaging/v1/outbound/" + \
    str(SHORTCODE) + "/requests"
LBS_URL = DEVAPI_URL + "/location/v1/queries/location"
FOURSQUARE_URL = "https://api.foursquare.com/v2/venues/search"
FOURSQUARE_CLIENT_ID = "SW0YVUUEGJZP1SZ5AMWZ12ULGNAQD2BHTK1LVHV2IYR0IUNT"
FOURSQUARE_CLIENT_SECRET = "RWEKVSEE2LMSTRAAVJZHNN4PFFNJZJF0DWNU1OZT3DB5TJOE"


users = {}


def parse_subscriber_number(raw_subscriber_number):
    return raw_subscriber_number[7:]


def send_message(subscriber_number, message, access_token=None):
    resp = requests.post(SMS_URL, data={
        "message": message,
        "address": subscriber_number,
        "access_token": access_token
    })
    return resp


def locate_user(subscriber_number, access_token=None):
    resp = requests.get(LBS_URL, data={
        "requestedAccuracy": 100,
        "access_token": access_token,
        "address": subscriber_number,
    })
    if resp.status_code != 200:
        return None

    data = json.loads(resp.text)

    return data['terminalLocationList']['terminalLocation']['currentLocation']


def foursquare_query(longitude, latitude, query, limit=5):
    data = {
        'query': query,
        'll': "%s,%s" % (latitude, longitude),
        'v': 20140806,
        'm': 'foursquare',
        'client_id': FOURSQUARE_CLIENT_ID,
        'client_secret': FOURSQUARE_CLIENT_SECRET,
        'limit': limit,
    }
    resp = requests.get(FOURSQUARE_URL, params=data)
    if resp.status_code != 200:
        return None

    data = resp.text.encode('utf-8').strip()
    return json.loads(data)


def parse_venues(venues):
    clean_venues = []
    for v in venues:
        print v
        clean_venues.append({
            'name': v['name'],
            'address': "%s, %s" % (v['location'].get('address', "No Address Info"),
                                   v['location'].get('city', "No City Info")),
        })
    return clean_venues


@app.route('/auth/globe/callback')
def auth_globe_callback():
    """Authentication callback for globe."""
    # TODO: Persist registered numbers.
    subscriber_number = request.args.get('subscriber_number')
    access_token = request.args.get('access_token')
    users[subscriber_number] = access_token
    return "Ok"


@app.route('/hooks/globe', methods=['POST'])
def hooks_globe():
    """This is triggered whenever a subscriber sends a request."""
    data = request.json
    message_data = data['inboundSMSMessageList']['inboundSMSMessage'][0]
    subscriber_number = message_data['senderAddress']

    # Return a response immidiately. We need to defer everything from this point
    # onwards.

    message = message_data['message']
    subscriber_number = parse_subscriber_number(subscriber_number)
    if not subscriber_number:
        return "Failed"

    access_token = users.get(subscriber_number, None)

    # Get location
    # location = locate_user(subscriber_number, access_token=access_token)
    location = {
        'longitude': '121.034961',
        'latitude': '14.504785',
    }

    query = message
    venues = foursquare_query(location['longitude'], location['latitude'], message)
    venues = venues['response']
    parsed_venues = parse_venues(venues['venues'])
    print parsed_venues

    message = ["%s - %s" % (v['name'], v['address']) for v in parsed_venues]
    message = '\n'.join(message)
    top_message = "Here are the top 5 results for '%s' near you.\n" % query
    message = top_message + message

    status = send_message(
        subscriber_number,
        message,
        access_token=access_token
    )
    return jsonify(json.loads(status.text))


if __name__ == '__main__':
    app.run(host=os.environ.get('HOST', '0.0.0.0'),
            port=int(os.environ.get('PORT', 3000)),
            debug=True)
