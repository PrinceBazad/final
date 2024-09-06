from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase
from googletrans import Translator
from langdetect import detect

app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"
socketio = SocketIO(app, async_mode='eventlet')

trans = Translator()

rooms = {}

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        if code not in rooms:
            break

    return code

@app.route("/", methods=["GET", "POST"])
def homepage():
    session.clear()
    if request.method == "POST":
        return redirect(url_for("home"))
    return render_template("HOME1.HTML") 

@app.route("/home", methods=["GET", "POST"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        language = request.form.get("language")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)

        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": {}, "messages": []}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)

        session["room"] = room
        session["name"] = name
        session["language"] = language
        rooms[room]["members"][name] = language
        return redirect(url_for("room"))
    return render_template("home.html")  


@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))
    return render_template("room.html", code=room, messages=rooms[room]["messages"], number_of_member=len(rooms[room]["members"]))

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return
    
    original_message = data["data"]
    sender_name = session.get("name")
    sender_language = detect(original_message)
    
    translated_messages = {}

    for member_name, member_language in rooms[room]["members"].items():
        translated_text = trans.translate(original_message, src=sender_language, dest=member_language).text
        translated_messages[member_name] = translated_text

        send({
            "name": sender_name,
            "language": member_language,
            "message": translated_text
        }, to=room)
    
    rooms[room]["messages"].append({
        "name": sender_name,
        "original_message": original_message,
        "translations": translated_messages
    })

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    language = session.get("language")
    message = "has entered the room"
    
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    send({"name": name, "message": message, "language": language}, to=room)
    print(f"{name} joined room {room}")
    print(f"Number of members in the room: {len(rooms[room]['members'])}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    language = session.get("language")
    leave_room(room)
    message = "has left the room"

    if room in rooms:
        del rooms[room]["members"][name]
        if len(rooms[room]["members"]) == 0:
            del rooms[room]
    send({"name": name, "message": message, "language": language}, to=room)
    print(f"{name} has left the room {room}")

if __name__ == "__main__":
    socketio.run(app, debug=True)
