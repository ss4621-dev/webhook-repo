import os
from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = MongoClient(os.getenv("MONGO_URI"))
db = client.github_events
events = db.events

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/github_webhook', methods=['POST'])
def webhook():
    event = request.headers.get('X-GitHub-Event')
    payload = request.json

    #Push Event
    if event == 'push':
        author = payload['pusher']['name']
        branch = payload['ref'].split('/')[-1]
        timestamp = payload['head_commit']['timestamp']
        commit_id = payload['head_commit']['id']

        events.insert_one({
            'request_id': commit_id,
            'author': author,
            'action': 'PUSH',
            'from_branch': None,
            'to_branch': branch,
            'timestamp': datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ')
        })

    # Pull Request Events
    elif event == 'pull_request':
        pr = payload['pull_request']
        author = pr['user']['login']
        action = payload['action']
        timestamp = pr['updated_at']
        pr_id = str(pr['number'])

        # PR created
        if action == 'opened':
            events.insert_one({
                'request_id': pr_id,
                'author': author,
                'action': 'PULL_REQUEST',
                'from_branch': pr['head']['ref'],
                'to_branch': pr['base']['ref'],
                'timestamp': datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ')
            })

        # PR Merged
        elif action == 'closed' and pr['merged']:
            events.insert_one({
                'request_id': pr_id,
                'author': author,
                'action': 'MERGE',
                'from_branch': pr['head']['ref'],
                'to_branch': pr['base']['ref'],
                'timestamp': datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ')
            })

    return jsonify(status='success'), 200


@app.route('/events')
def get_events():
    latest_events = list(events.find().sort('timestamp', -1).limit(10))
    for event in latest_events:
        event['_id'] = str(event['_id']) # Convert ObjectId
        event['timestamp'] = event['timestamp'].isoformat() # Convert datetime
    return jsonify(latest_events)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)