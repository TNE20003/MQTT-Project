"""Simple MQTT viewer. Run from the project root with: python -m IO.UI"""

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from queue import Empty, Queue
from threading import Thread
from uuid import uuid4
from time import monotonic, sleep
import paho.mqtt.client as mqtt

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
        self.subscriptions = set()

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
        self.subscribe_topic = tk.StringVar(value="")
        ttk.Entry(frame, textvariable=self.subscribe_topic).grid(row=1, column=1, sticky="ew", padx=8)
        self.subscribe_button = ttk.Button(frame, text="Subscribe", command=self.subscribe, state="disabled")
        self.subscribe_button.grid(row=1, column=2)
        self.unsubscribe_button = ttk.Button(frame, text="Unsubscribe all", command=self.unsubscribe_all, state="disabled")
        self.unsubscribe_button.grid(row=6, column=0, pady=8)

        ttk.Label(frame, text="Publish topic").grid(row=2, column=0, sticky="w")
        self.publish_topic = tk.StringVar(value="Robot/command")
        ttk.Entry(frame, textvariable=self.publish_topic).grid(row=2, column=1, sticky="ew", padx=8)
        self.publish_button = ttk.Button(frame, text="Publish", command=self.publish, state="disabled")
        self.publish_button.grid(row=2, column=2)

        ttk.Label(frame, text="Message").grid(row=3, column=0, sticky="w", pady=8)
        self.payload = tk.StringVar(value="get_sensor all")
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
            deadline = monotonic() + 10
            while not self.server.client.is_connected():
                if self.closed or monotonic() >= deadline:
                    raise TimeoutError("Broker did not confirm the connection. Check network access and credentials.")
                sleep(0.05)
            self.connection_results.put(None)
        except Exception as error:
            self.server.disconnect()
            self.connection_results.put(str(error))

    @staticmethod
    def relative_topic(topic):
        # Accept topics copied from the receive log without adding the prefix twice.
        return topic.strip().removeprefix("{103218929}/")

    def subscribe(self):
        topic = self.relative_topic(self.subscribe_topic.get())
        if not self.server.client.is_connected():
            self.log("Connect to the broker before subscribing.")
            return
        if not topic:
            self.log("Enter a subscription topic.")
            return
        try:
            self.server.subscribe(topic)
            self.subscriptions.add(topic)
            self.log(f"SUBSCRIBE requested: {topic}")
        except Exception as error:
            self.log(f"Subscribe error: {error}")

    def unsubscribe_all(self):
        for topic in list(self.subscriptions):
            try:
                result, _ = self.server.client.unsubscribe("{103218929}/" + topic)
                if result != mqtt.MQTT_ERR_SUCCESS:
                    raise RuntimeError(f"MQTT unsubscribe failed (code {result})")
                self.subscriptions.remove(topic)
            except Exception as error:
                self.log(f"Unsubscribe error for {topic}: {error}")
        if not self.subscriptions:
            self.log("No active subscriptions.")

    def publish(self):
        topic = self.relative_topic(self.publish_topic.get())
        if not self.server.client.is_connected():
            self.log("Connect to the broker before publishing.")
            return
        if not topic or '+' in topic or '#' in topic:
            self.log("Enter a publish topic without wildcard characters.")
            return
        try:
            payload = self.payload.get()
            result = self.server.publish(topic, payload)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(f"MQTT publish failed (code {result.rc})")
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
                self.status.set(f"Connected: {self.server.mqtt_broker}")
                self.subscribe_button.configure(state="normal")
                self.publish_button.configure(state="normal")
                self.unsubscribe_button.configure(state="normal")
            else:
                self.status.set("Connection failed")
                self.log(f"Connection error: {error}")
                self.connect_button.configure(state="normal")

        if self.connected and not self.server.client.is_connected():
            self.connected = False
            self.status.set("Connection lost; restart the UI to reconnect")
            self.subscribe_button.configure(state="disabled")
            self.publish_button.configure(state="disabled")
            self.unsubscribe_button.configure(state="disabled")
            self.log("Connection lost. Commands cannot be sent.")

        # Limit each batch so a busy topic cannot freeze the window.
        for _ in range(100):
            try:
                topic, payload = self.server.read_message(timeout=0)
            except TimeoutError:
                break
            except UnicodeDecodeError:
                self.log("Received a non-UTF-8 payload; cannot display it as text.")
                continue
            # Ignore queued messages from subscriptions that were just removed.
            if any(mqtt.topic_matches_sub("{103218929}/" + sub, topic) for sub in self.subscriptions):
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
