'''
Copyright (c) 2020 Cisco and/or its affiliates.

This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at

               https://developer.cisco.com/docs/licenses

All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
'''


from flask import Flask, request, redirect, url_for, render_template, jsonify
import requests
import xmltodict


# FILL IN VARIABLES HERE
username = '' # username to CMS
password = '' # password to CMS
cms_ips = [''] # list of IP address or DNS name of CMS(s)
port = '' # https port on CMS


# globally used vars
data = {}
call_correlator = None
all_calls = []
participants_inlobby = None


# flask app
app = Flask(__name__)


# get all currently active calls
def active_calls():
    global all_calls
    all_calls = []

    for url in cms_ips:
        cms_url = 'https://' + url + ':' + port + '/api/v1'

        calls = requests.get(cms_url + '/calls', auth=(username, password), verify=False)
        calls_text = xmltodict.parse(calls.content)

        if calls_text['calls']['@total'] != '0':
            list_calls = calls_text['calls']['call']
            if calls_text['calls']['@total'] != '1':
                for call in list_calls:
                    call = {
                        'name': call['name'],
                        'correlator': call['callCorrelator'],
                        'cms': [{
                            'instance': url,
                            'call_id': call['@id']
                        }]
                    }
                    all_calls.append(call)
            else:
                call = {
                    'name': list_calls['name'],
                    'correlator': list_calls['callCorrelator'],
                    'cms': [{
                        'instance': url,
                        'call_id': list_calls['@id']
                    }]
                }
                all_calls.append(call)

        else:
            call = {
                'name': '',
                'correlator': '',
                'cms': [{
                    'instance': '',
                    'call_id': ''
                }]
            }
            all_calls.append(call)


    for call1 in all_calls:
        for call2 in all_calls:
            if call1 != call2:
                if call1['correlator'] == call2['correlator']:
                    call1['cms'].append(call2['cms'][0])
                    all_calls.remove(call2)

    print(all_calls)
    data['calls'] = all_calls


# get all participants in the meeting, and identify whether they are waiting in the lobby or already in the call
def call_participants():

    global participants_inlobby
    participants_inlobby = []
    participants_inmeeting = []

    if call_correlator != None:
        for call in all_calls:
            if call['correlator'] == call_correlator:
                for cms in call['cms']:
                    cms_instance = cms['instance']
                    cms_url = 'https://' + cms_instance + ':' + port + '/api/v1'
                    call_id = cms['call_id']

                    # get all calllegs
                    calllegs = requests.get(cms_url + '/calls/' + call_id + '/calllegs', auth=(username, password), verify=False)
                    calllegs_text = xmltodict.parse(calllegs.content)
                    list_calllegs = calllegs_text['callLegs']['callLeg']
                    calllegs_list_call = []
                    if calllegs_text['callLegs']['@total'] != '1':
                        for callleg in list_calllegs:
                            callleg_dict = {
                                'callleg_id': callleg['@id'],
                                'cms_url': cms_url,
                                'call_id': call_id,
                                'name': callleg['name']
                            }
                            calllegs_list_call.append(callleg_dict)
                    else:
                        callleg_dict = {
                            'callleg_id': list_calllegs['@id'],
                            'cms_url': cms_url,
                            'call_id': call_id,
                            'name': list_calllegs['name']
                        }
                        calllegs_list_call.append(callleg_dict)


                    # get lobby status
                    for callleg in calllegs_list_call:
                        callleg_id = callleg['callleg_id']
                        get_lobby_status = requests.get(cms_url + '/calllegs/' + callleg_id, auth=(username, password), verify=False)
                        get_lobby_status_text = xmltodict.parse(get_lobby_status.content)
                        try:
                            if get_lobby_status_text['callLeg']['subType'] == 'distributionLink':
                                # delete entry from calllegs_list_call
                                calllegs_list_call = [item for item in calllegs_list_call if
                                                      item['name'] != get_lobby_status_text['callLeg']['name']]
                            else:
                                try:
                                    if get_lobby_status_text['callLeg']['status']['deactivated'] == 'true':
                                        callleg['lobby_status'] = 'waiting'
                                except:
                                    callleg['lobby_status'] = 'in_meeting'

                                if callleg['lobby_status'] == 'waiting':
                                    participants_inlobby.append(callleg)
                                else:
                                    participants_inmeeting.append(callleg)

                        except:
                            try:
                                if get_lobby_status_text['callLeg']['status']['deactivated'] == 'true':
                                    callleg['lobby_status'] = 'waiting'
                            except:
                                callleg['lobby_status'] = 'in_meeting'

                            if callleg['lobby_status'] == 'waiting':
                                participants_inlobby.append(callleg)
                            else:
                                participants_inmeeting.append(callleg)


    data['participants_inlobby'] = participants_inlobby
    data['participants_inmeeting'] = participants_inmeeting


# landing page
@app.route('/')
def start():
    return render_template('login.html')


# login page
@app.route('/login')
def login():
    # placeholder for authentication method, none implemented in this demo
    return redirect(url_for('.main'))


# main page listing all active calls
@app.route('/main')
def main():

    active_calls()

    return render_template('mainpage.html', calls=data['calls'], participants_inlobby=[], participants_inmeeting=[])


# page of a specific call, listing all participants in meeting and in lobby
@app.route('/call/<correlator>')
def call_users(correlator):

    global call_correlator
    call_correlator = correlator

    active_calls()
    call_participants()

    return render_template('mainpage.html', calls=data['calls'], participants_inlobby=data['participants_inlobby'], participants_inmeeting=data['participants_inmeeting'])


# called when user presses the "accept" button to move the selected participants from waiting in the lobby to being in the call
@app.route('/acceptParticipants', methods=['POST'])
def acceptParticipant():
    calllegs_participantsToChange = request.json['data']

    for selected_person in calllegs_participantsToChange:
        for person_waiting in participants_inlobby:
            if selected_person == person_waiting['name']:
                cms_url = person_waiting['cms_url']
                call_id = person_waiting['call_id']

                # get call participants
                call_participants = requests.get(cms_url + '/calls/' + call_id + '/participants',
                                                 auth=(username, password), verify=False)
                call_participants_text = xmltodict.parse(call_participants.content)
                list_call_participants = call_participants_text['participants']['participant']
                if call_participants_text['participants']['@total'] != '1':
                    for participant in list_call_participants:
                        if participant['name'] == selected_person:
                            requests.put(cms_url + '/participants/' + participant['@id'],
                                         headers={'Content-Type': 'application/x-www-form-urlencoded'},
                                         data='deactivated=false', auth=(username, password), verify=False)
                else:
                    requests.put(cms_url + '/participants/' + list_call_participants['@id'],
                                 headers={'Content-Type': 'application/x-www-form-urlencoded'},
                                 data='deactivated=false', auth=(username, password), verify=False)

    return jsonify({'success': True})


if __name__ == '__main__':
    app.run()
