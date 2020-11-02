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
cms_ip = '' # IP address or DNS name of CMS
port = '' # https port on CMS


# globally used vars
cms_url = 'https://' + cms_ip + ':' + port + '/api/v1'
data = {}
call_id = None
all_calls = []
call_participants_text = None


# flask app
app = Flask(__name__)


# get all currently active calls
def active_calls():
    global all_calls

    calls = requests.get(cms_url + '/calls', auth=(username, password), verify=False)
    calls_text = xmltodict.parse(calls.content)

    all_calls = []
    if calls_text['calls']['@total'] != '0':
        list_calls = calls_text['calls']['call']
        if calls_text['calls']['@total'] != '1':
            for call in list_calls:
                call = {
                    'id': call['@id'],
                    'name': call['name'],
                    'correlator': call['callCorrelator']
                }
                all_calls.append(call)
        else:
            call = {
                'id': list_calls['@id'],
                'name': list_calls['name'],
                'correlator': list_calls['callCorrelator']
            }
            all_calls.append(call)

    else:
        call = {
            'id': '',
            'name': '',
            'correlator': ''
        }
        all_calls.append(call)

    data['calls'] = all_calls


# get all participants in the meeting, and identify whether they are waiting in the lobby or already in the call
def call_participants():

    global call_participants_text

    if call_id != None:
        # get all calllegs
        calllegs = requests.get(cms_url + '/calls/' + call_id + '/calllegs', auth=(username, password), verify=False)
        calllegs_text = xmltodict.parse(calllegs.content)
        list_calllegs = calllegs_text['callLegs']['callLeg']
        calllegs_list_call = []
        updated_calllegs_list_call = []
        if calllegs_text['callLegs']['@total'] != '1':
            for callleg in list_calllegs:
                callleg_dict = {
                    'callleg_id': callleg['@id'],
                    'name': callleg['name']
                }
                calllegs_list_call.append(callleg_dict)
        else:
            callleg_dict = {
                'callleg_id': list_calllegs['@id'],
                'name': list_calllegs['name']
            }
            calllegs_list_call.append(callleg_dict)

        # get call participants
        call_participants = requests.get(cms_url + '/calls/' + call_id + '/participants',
                                                 auth=(username, password), verify=False)
        call_participants_text = xmltodict.parse(call_participants.content)
        list_call_participants = call_participants_text['participants']['participant']

        # get lobby status
        for callleg in calllegs_list_call:
            callleg_id = callleg['callleg_id']
            get_lobby_status = requests.get(cms_url + '/calllegs/' + callleg_id, auth=(username, password), verify=False)
            get_lobby_status_text = xmltodict.parse(get_lobby_status.content)
            try: # for redirected users connecting from a call bridge
                if get_lobby_status_text['callLeg']['subType'] == 'distributionLink':
                    # delete entry from calllegs_list_call
                    calllegs_list_call = [item for item in calllegs_list_call if item['name'] != get_lobby_status_text['callLeg']['name']]

                    # get url of remote CMS
                    updated_cms_url = 'https://' + get_lobby_status_text['callLeg']['remoteParty'] + ':' + port + '/api/v1'

                    # find the call correlator and get the right details from the remote CMS
                    for item in all_calls:
                        if item['id'] == call_id:
                            call_correlator = item['correlator']
                    updated_calls = requests.get(updated_cms_url + '/calls', auth=(username, password), verify=False)
                    updated_calls_text = xmltodict.parse(updated_calls.content)
                    updated_list_calls = updated_calls_text['calls']['call']
                    if updated_calls_text['calls']['@total'] != '1':
                        for item in updated_list_calls:
                            if item['callCorrelator'] == call_correlator:
                                updated_call_id = item['@id']
                    else:
                        updated_call_id = updated_list_calls['@id']

                    updated_calllegs = requests.get(updated_cms_url + '/calls/' + updated_call_id + '/calllegs', auth=(username, password),
                                            verify=False)
                    updated_calllegs_text = xmltodict.parse(updated_calllegs.content)
                    updated_list_calllegs = updated_calllegs_text['callLegs']['callLeg']


                    # repeat the process of getting the lobby status, now for the calllegs connected over the callbridge
                    try:
                        for participant in list_call_participants:
                            if updated_calllegs_text['callLegs']['@total'] != '1':
                                for callleg in updated_list_calllegs:
                                    if participant['@id'] == callleg['@id']:
                                            callleg_dict = {
                                                'callleg_id': callleg['@id'],
                                                'name': callleg['name']
                                            }
                                            updated_calllegs_list_call.append(callleg_dict)
                            else:
                                callleg_dict = {
                                    'callleg_id': updated_list_calllegs['@id'],
                                    'name': updated_list_calllegs['name']
                                }
                                updated_calllegs_list_call.append(callleg_dict)

                        for callleg in updated_calllegs_list_call:
                            callleg_id = callleg['callleg_id']
                            get_lobby_status = requests.get(updated_cms_url + '/calllegs/' + callleg_id,
                                                            auth=(username, password), verify=False)
                            get_lobby_status_text = xmltodict.parse(get_lobby_status.content)
                            try:
                                if get_lobby_status_text['callLeg']['status']['deactivated'] == 'true':
                                    callleg['lobby_status'] = 'waiting'
                            except:
                                callleg['lobby_status'] = 'in_meeting'
                    except:
                        pass

            except:
                try:
                    if get_lobby_status_text['callLeg']['status']['deactivated'] == 'true':
                        callleg['lobby_status'] = 'waiting'
                except:
                    callleg['lobby_status'] = 'in_meeting'

    # create a list of all participants in meeting and waiting in the lobby to parse to the HTML
    participants_inlobby = []
    participants_inmeeting = []

    for callleg in calllegs_list_call:
        if callleg['lobby_status'] == 'waiting':
            participants_inlobby.append(callleg)
        else:
            participants_inmeeting.append(callleg)


    for callleg in updated_calllegs_list_call:
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
@app.route('/call/<id>')
def call_users(id):

    global call_id
    call_id = id

    active_calls()
    call_participants()

    return render_template('mainpage.html', calls=data['calls'], participants_inlobby=data['participants_inlobby'], participants_inmeeting=data['participants_inmeeting'])


# called when user presses the "accept" button to move the selected participants from waiting in the lobby to being in the call
@app.route('/acceptParticipants', methods=['POST'])
def acceptParticipant():
    calllegs_participantsToChange = request.json['data']

    list_participants = call_participants_text['participants']['participant']
    if call_participants_text['participants']['@total'] != '1':
        for participant in list_participants:
            for callleg in calllegs_participantsToChange:
                if participant['name'] == callleg:
                    requests.put(cms_url + '/participants/' + participant['@id'],
                                 headers={'Content-Type': 'application/x-www-form-urlencoded'},
                                 data='deactivated=false', auth=(username, password), verify=False)
    else:
        requests.put(cms_url + '/participants/' + list_participants['@id'],
                     headers={'Content-Type': 'application/x-www-form-urlencoded'},
                     data='deactivated=false', auth=(username, password), verify=False)

    return jsonify({'success': True})


if __name__ == '__main__':
    app.run()