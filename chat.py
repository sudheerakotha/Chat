import streamlit as st
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit
import threading

import streamlit.components.v1 as components

# Flask backend setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

rooms = {
    "public": set(),  # public rooms
    "private": {}     # private rooms: room_name -> set(users)
}
user_rooms = {}  # sid -> set(room_names)

@app.route('/')
def index():
    return "Chat backend running."

@socketio.on('join')
def handle_join(data):
    room = data['room']
    username = data['username']
    private = data.get('private', False)
    sid = request.sid

    if private:
        key = data.get('key')
        if room not in rooms['private']:
            rooms['private'][room] = set()
        # Simple key check (for demo)
        if key != "letmein":
            emit('error', {'msg': 'Invalid room key.'})
            return
        rooms['private'][room].add(username)
    else:
        rooms['public'].add(room)

    join_room(room)
    user_rooms.setdefault(sid, set()).add(room)
    emit('message', {'msg': f"{username} has joined {room}."}, room=room)

@socketio.on('leave')
def handle_leave(data):
    room = data['room']
    username = data['username']
    sid = request.sid
    leave_room(room)
    user_rooms.get(sid, set()).discard(room)
    emit('message', {'msg': f"{username} has left {room}."}, room=room)

@socketio.on('send_message')
def handle_message(data):
    room = data['room']
    username = data['username']
    msg = data['msg']
    emit('message', {'msg': f"{username}: {msg}"}, room=room)

def run_flask():
    socketio.run(app, port=5001)

# Start Flask backend in a thread
threading.Thread(target=run_flask, daemon=True).start()

# Streamlit frontend
st.title("Chat Application (Public & Private Rooms)")

st.markdown("""
- **Public rooms:** Join by name.
- **Private rooms:** Room key is `letmein`.
""")

username = st.text_input("Your name", key="username")
room = st.text_input("Room name", key="room")
private = st.checkbox("Private room?")
key = st.text_input("Room key (private only)", type="password") if private else ""

if st.button("Join Room"):
    st.session_state['joined'] = True

if st.session_state.get('joined'):
    # Socket.IO client via HTML/JS
    components.html(f"""
    <script src="https://cdn.socket.io/4.7.4/socket.io.min.js"></script>
    <div id="chat"></div>
    <input id="msg" autocomplete="off"/><button onclick="sendMsg()">Send</button>
    <script>
    var socket = io("http://localhost:5001");
    var room = "{room}";
    var username = "{username}";
    var privateRoom = {str(private).lower()};
    var key = "{key}";

    socket.on('connect', function() {{
        socket.emit('join', {{
            room: room,
            username: username,
            private: privateRoom,
            key: key
        }});
    }});

    socket.on('message', function(data) {{
        var chat = document.getElementById('chat');
        chat.innerHTML += "<div>" + data.msg + "</div>";
    }});

    socket.on('error', function(data) {{
        alert(data.msg);
    }});

    function sendMsg() {{
        var msg = document.getElementById('msg').value;
        socket.emit('send_message', {{
            room: room,
            username: username,
            msg: msg
        }});
        document.getElementById('msg').value = "";
    }}
    </script>
    """, height=400)
