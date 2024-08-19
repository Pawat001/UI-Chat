from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, join_room, leave_room, emit
from datetime import datetime
import pytz  # For timezone handling

app = Flask(__name__)
socketio = SocketIO(app)

rooms = {}  # Track users in rooms
peers = {}  # Track peer connections

# Define the timezone for Thailand
thailand = pytz.timezone('Asia/Bangkok')

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login.html')
def login2():
    return render_template('login.html')

@app.route('/chat')
def chat():
    return render_template('index.html')

@app.route('/temp.html')
def temp():
    return render_template('temp.html')

@app.route('/rooms')
def get_rooms():
    return jsonify(list(rooms.keys()))

@socketio.on('join')
def handle_join(data):
    username = data['username']
    room = data['room']

    if room not in rooms:
        rooms[room] = []
    if username not in rooms[room]:
        rooms[room].append(username)

    peers[request.sid] = room
    join_room(room)
    timestamp = data.get('timestamp', datetime.now(thailand).strftime('%Y-%m-%d %H:%M:%S'))
    emit('status', {'message': f'{username} has joined the room.', 'timestamp': timestamp}, room=room)

    # Notify all users in the room of the new user
    emit('user-list', {'users': rooms[room]}, room=room)

@socketio.on('ready-for-video')
def handle_ready_for_video(data):
    room = data['room']
    username = data['username']
    peer_id = request.sid

    # Notify all users in the room about the new peer
    emit('peer-id', {'peerId': peer_id, 'username': username}, room=room, include_self=False)

@socketio.on('video-signal')
def handle_video_signal(data):
    signal = data['signal']
    peer_id = data['peerId']

    # Forward the video signal to the correct peer
    emit('video-signal', {'signal': signal, 'peerId': request.sid}, room=peer_id)

@socketio.on('send-message')
def handle_send_message(data):
    room = data['room']
    username = data['username']
    message = data['message']
    timestamp = datetime.now(thailand).strftime('%Y-%m-%d %H:%M:%S')

    emit('receive-message', {'username': username, 'message': message, 'timestamp': timestamp}, room=room)

@socketio.on('leave')
def handle_leave(data):
    username = data['username']
    room = data['room']

    if room in rooms and username in rooms[room]:
        leave_room(room)
        rooms[room].remove(username)
        del peers[request.sid]  # Remove peer from tracking
        if not rooms[room]:
            del rooms[room]
        timestamp = datetime.now(thailand).strftime('%Y-%m-%d %H:%M:%S')
        emit('status', {'message': f'{username} has left the room.', 'timestamp': timestamp}, room=room)

        # Notify remaining users in the room
        emit('user-list', {'users': rooms[room]}, room=room)

@socketio.on('stop-video')
def handle_stop_video(data):
    room = data['room']
    username = data['username']
    
    # Notify all users in the room that this user stopped the video
    emit('user-stopped-video', {'username': username}, room=room)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in peers:
        room = peers[sid]
        username = None

        for user, user_room in rooms.items():
            if sid == user:
                username = user
                rooms[user_room].remove(username)
                break

        leave_room(room)
        del peers[sid]

        if room in rooms and not rooms[room]:
            del rooms[room]

        timestamp = datetime.now(thailand).strftime('%Y-%m-%d %H:%M:%S')
        emit('status', {'message': f'{username} has disconnected.', 'timestamp': timestamp}, room=room)

        # Notify remaining users in the room
        emit('user-list', {'users': rooms[room]}, room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True)