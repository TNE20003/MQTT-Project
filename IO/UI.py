"""Simple MQTT viewer. Run from the project root with: python -m IO.UI"""

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from queue import Empty, Queue
from threading import Thread
from uuid import uuid4

if __package__:
    from .MQTT_Server import MQTTServer
else:
    from MQTT_Server import MQTTServer


class MQTTUI:
    def __init__(self, root):
        self.root = root
        self.server = MQTTServer(client_id=f"MQTT_UI_{uuid4().hex[:8]}")
        self.connected = False
        self.connection_results = Queue()
        self.connection_thread = None
        self.closed = False

        root.title("MQTT Message Viewer")
        root.geometry("800x550")
        root.protocol("WM_DELETE_WINDOW", self.close)

        frame = ttk.Frame(root, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(5, weight=1)

        self.status = tk.StringVar(value="Disconnected")
        ttk.Label(frame, textvariable=self.status).grid(row=0, column=0, columnspan=2, sticky="w")
        self.connect_button = ttk.Button(frame, text="Connect", command=self.connect)
        self.connect_button.grid(row=0, column=2, padx=5)

        ttk.Label(frame, text="Subscribe topic").grid(row=1, column=0, sticky="w", pady=8)
        self.subscribe_topic = tk.StringVar(value="Robot/#")
        ttk.Entry(frame, textvariable=self.subscribe_topic).grid(row=1, column=1, sticky="ew", padx=8)
        self.subscribe_button = ttk.Button(frame, text="Subscribe", command=self.subscribe, state="disabled")
        self.subscribe_button.grid(row=1, column=2)

        ttk.Label(frame, text="Publish topic").grid(row=2, column=0, sticky="w")
        self.publish_topic = tk.StringVar(value="Robot/command")
        ttk.Entry(frame, textvariable=self.publish_topic).grid(row=2, column=1, sticky="ew", padx=8)
        self.publish_button = ttk.Button(frame, text="Publish", command=self.publish, state="disabled")
        self.publish_button.grid(row=2, column=2)

        ttk.Label(frame, text="Message").grid(row=3, column=0, sticky="w", pady=8)
        self.payload = tk.StringVar(value="query light_sensor")
        ttk.Entry(frame, textvariable=self.payload).grid(row=3, column=1, columnspan=2, sticky="ew", padx=8)
        ttk.Label(frame, text="Topics automatically use the {103218929}/ prefix. Subscribe supports + and #.").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=8
        )

        self.messages = ScrolledText(frame, state="disabled", wrap="word", height=18)
        self.messages.grid(row=5, column=0, columnspan=3, sticky="nsew")
        ttk.Button(frame, text="Clear log", command=self.clear_log).grid(row=6, column=2, pady=8)
        root.after(100, self.poll_messages)

    def log(self, message):
        self.messages.configure(state="normal")
        self.messages.insert("end", message + "\n")
        self.messages.see("end")
        self.messages.configure(state="disabled")

    def clear_log(self):
        self.messages.configure(state="normal")
        self.messages.delete("1.0", "end")
        self.messages.configure(state="disabled")

    def connect(self):
        self.connect_button.configure(state="disabled")
        self.status.set("Connecting...")
        self.connection_thread = Thread(target=self.connect_worker, daemon=True)
        self.connection_thread.start()

    def connect_worker(self):
        # Network connection happens off the UI thread to keep the window responsive.
        try:
            self.server.connect()
            self.connection_results.put(None)
        except Exception as error:
            self.connection_results.put(str(error))

    def subscribe(self):
        topic = self.subscribe_topic.get().strip()
        if not topic:
            self.log("Enter a subscription topic.")
            return
        try:
            self.server.subscribe(topic)
            self.log(f"SUBSCRIBE requested: {topic}")
        except Exception as error:
            self.log(f"Subscribe error: {error}")

    def publish(self):
        topic = self.publish_topic.get().strip()
        if not topic or '+' in topic or '#' in topic:
            self.log("Enter a publish topic without wildcard characters.")
            return
        try:
            payload = self.payload.get()
            self.server.publish(topic, payload)
            self.log(f"SEND requested [{topic}] {payload}")
        except Exception as error:
            self.log(f"Publish error: {error}")

    def poll_messages(self):
        try:
            error = self.connection_results.get_nowait()
        except Empty:
            pass
        else:
            if error is None:
                self.connected = True
                self.status.set(f"MQTT started: {self.server.mqtt_broker}")
                self.subscribe_button.configure(state="normal")
                self.publish_button.configure(state="normal")
                self.subscribe()
            else:
                self.status.set("Connection failed")
                self.log(f"Connection error: {error}")
                self.connect_button.configure(state="normal")

        # Limit each batch so a busy topic cannot freeze the window.
        for _ in range(100):
            try:
                topic, payload = self.server.read_message(timeout=0)
            except TimeoutError:
                break
            except UnicodeDecodeError:
                self.log("Received a non-UTF-8 payload; cannot display it as text.")
                continue
            self.log(f"RECEIVE [{topic}] {payload}")
        if not self.closed:
            self.root.after(100, self.poll_messages)

    def close(self):
        self.closed = True
        self.root.destroy()
        # Wait for any pending connection before stopping its network loop.
        if self.connection_thread is not None:
            self.connection_thread.join()
        self.server.disconnect()


if __name__ == "__main__":
    window = tk.Tk()
    MQTTUI(window)
    window.mainloop()
