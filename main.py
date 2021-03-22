from flask import Flask, request, abort
from datetime import datetime
from threading import Thread
from pytz import timezone
import smtplib
import time
import json


class Statistics:
    def __init__(self):
        self.data = json.load(open('database.json'))
        self.TIMEZONE = timezone('Canada/Atlantic')

    def get_date(self):
        return str(datetime.now(self.TIMEZONE).strftime("%Y-%m-%d"))

    def get_current_time(self):
        return str(datetime.now(self.TIMEZONE).strftime("%H:%M:%S"))

    def get_time(self, t_time=None, fmt="%H:%M:%S"):
        if t_time is None:
            t_time = self.get_current_time()
        return datetime.strptime(t_time, fmt)

    def write_data(self):
        with open('database.json') as f:
            json.dump(self.data, f)
        return

    def reminder(self, reason, duration):
        today = self.data[self.get_date()]

        if self.last_reminder() > today['cooldown']:
            today['last_reminder'] = self.get_current_time()
            today['cooldown'] = duration
            self.push_notification(reason)
        return

    def complete_task(self, task):
        today = self.data[self.get_date()]
        if task == "brush_log":
            self.complete_task("wake_time")
            today[task].append(self.get_current_time())
        elif task == "shower":
            today[task] = True
        else:
            today[task] = self.get_current_time()
        self.write_data()
        return

    def push_notification(self, reason):
        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.ehlo()
            server.login("EMAIL", "PASSWORD")
            server.sendmail(
                "Notification",
                ["PHONE_NUMBER@msg.telus.com"],
                "To:PHONE_NUMBER@msg.telus.com\n{}".format(reason)
            )
            server.close()
            return True
        except Exception as e:
            return False, e

    def register_day(self):
        self.data[self.get_date()] = {
            "brush_log": [],
            "shower": False,
            "wake_time": None,
            "bed_time": None,
            "last_reminder": None,
            "cooldown": 0
        }
        self.write_data()
        return True

    def last_reminder(self):
        today = self.data[self.get_date()]
        return 0 if today['last_reminder'] is None else int(
            (self.get_time() -
             self.get_time(today['last_reminder'])).total_seconds()
        )

    def run(self):
        while True:
            if self.get_date() in self.data:
                self.register_day()
            today = self.data[self.get_date()]

            if today['wake_time'] is None:
                if int(self.get_current_time().split(':')[0]) >= 12:
                    self.reminder("Wake up!", 300)
            else:
                if len(today['brush_log']) == 0:
                    if (self.get_time() - self.get_time(today['wake_time'])).total_seconds() > 300:
                        self.reminder("Brush your teeth!", 1200)
                elif today['bed_time'] is not None:
                    if len(today['brush_log']) < 2:
                        self.reminder("Brush your  teeth!", 60)
            print(self.data)
            time.sleep(60)


app = Flask(__name__)
main_statistics = Statistics()


@app.route('/events', methods=['POST'])
def events():
    if request.method == 'POST':
        try:
            main_statistics.complete_task(request.json['event_type'])
            return 'sucess', 200
        except Exception as e:
            return f'invalid params {e}', 404
    else:
        abort(400)


@app.route('/')
def index():
    return main_statistics.data


if __name__ == '__main__':
    newThread = Thread(target=main_statistics.run)
    newThread.daemon = True
    newThread.start()
    app.run()
