import requests
import json
import os
import time
import html
from pprint import pprint
from bottle import Bottle, response, request as bottle_request

class GifGenerator:
    GIF_URL = "https://api.tenor.com/v1/random?q=%s&key=%s&limit=%s&media_filter=%s&locale=%s"    

    apikey = "K0MB08OYLEJN"
    lmt = 1
    media_filter = "minimal"
    locale = "de_DE"

    # get random results
    def get_random_gif(self, query):
        r = requests.get(
        self.GIF_URL % (query, self.apikey, self.lmt, self.media_filter, self.locale))
        return self.extract_gif(r)
 
    def extract_gif(self, request):
        if request.status_code == 200:
            gifs = json.loads(request.content)
            try:
                gif = gifs['results'][0]['url']
                print(gif)
                return gif
            except IndexError:
                print("No gif found")
                return None
        else:
            return None

class DataCollector:
    BOT_URL = None
    ERROR_MSG = "sorry, nix gefunden"
    # telegram-api parameters
    SEND_ANIMATION = 'sendAnimation'
    SEND_MESSAGE = 'sendMessage'
    DELETE_MESSAGE = 'deleteMessage'
    CHAT_ID = "chat_id"
    ANIMATION = 'animation'
    MESSAGE_ID = 'message_id'
    MESSAGE = 'message'
    CHAT = 'chat'
    ID = 'id'
    TEXT = 'text'

    def get_chat_id(self, data):
        chat_id = data[self.MESSAGE][self.CHAT][self.ID]
        return chat_id

    def get_message_id(self, data):
        message_id = data[self.MESSAGE][self.MESSAGE_ID]
        return message_id

    def get_message(self, data):
        message_text = data[self.MESSAGE][self.TEXT]
        print(self.sanitize_string(message_text))
        return self.sanitize_string(message_text)

    def sanitize_string(self, text):
        trim = text.strip()
        if trim[0] == '/':
            tmp = trim[1:]
            trim = tmp
        return html.escape(trim)    
    
    def has_current_message(self, data):
        if self.MESSAGE in data and not self.is_old_message(data[self.MESSAGE]):
            if self.TEXT in data[self.MESSAGE] and str(data[self.MESSAGE][self.TEXT]):
                return True
        return False

    def is_old_message(self, message):
        return int(message['date'] + 120) < int(time.time()) 


class TelegramBot(DataCollector, Bottle, GifGenerator):

    BOT_URL = 'https://api.telegram.org/bot742173952:AAHPWua9jFVLKk2eqaBb1eu7LNjAo4RrIng/'

    def __init__(self, *args, **kwargs):
        super(TelegramBot, self).__init__()
        self.route('/', callback=self.post_handler, method="POST")

    def prepare_data_for_answer(self, data):
        message = self.get_message(data)
        answer = self.get_random_gif(message)
        chat_id = self.get_chat_id(data)
        json_data = {
            self.CHAT_ID: chat_id,
            self.ANIMATION: answer,
        }
        return json_data

    def prepare_data_for_deleting(self, data):
        json_data = {
            self.CHAT_ID:self.get_chat_id(data),
            self.MESSAGE_ID: self.get_message_id(data),
        }
        return json_data

    def post_handler(self):
        data = bottle_request.json
        if self.has_current_message(data):
            answer_data = self.prepare_data_for_answer(data)
            delete_data = self.prepare_data_for_deleting(data)
            self.send_message(answer_data)
            self.delete_message(delete_data)
            return response

    def send_message(self, prepd_data):
        if prepd_data[self.ANIMATION] is not None:
            self.send_gif(prepd_data)
        else:
            self.send_no_gif_found(prepd_data)

    def send_gif(self, prepd_data):
        message_url = self.BOT_URL + self.SEND_ANIMATION
        requests.post(message_url, json=prepd_data)

    def send_no_gif_found(self, prepd_data):
        message_url = self.BOT_URL + self.SEND_MESSAGE
        requests.post(message_url, json={
        self.CHAT_ID: prepd_data[self.CHAT_ID],
        self.TEXT: self.ERROR_MSG,
        })
            
    def delete_message(self, delete_data):
        message_url = self.BOT_URL + self.DELETE_MESSAGE
        requests.post(message_url, json=delete_data)

class Ngrok_Connector(TelegramBot):

    url = "http://host.docker.internal:4040/api/tunnels/"

    def __init__(self, *args, **kwargs):
        super(Ngrok_Connector, self).__init__()

    def get_ngrok_url(self):
        connected = False
        while not connected:
            try:
                res = requests.get(self.url)
                connected = True
                return self.fetch_url(res)
            except  requests.exceptions.ConnectionError:
                print("Connection not available yet, trying again in 2s...")
                time.sleep(2)

    def fetch_url(self, res):
        res_unicode = res.content.decode("utf-8")
        res_json = json.loads(res_unicode)
        for i in res_json['tunnels']:
            if i['name'] == 'command_line':
                return i['public_url']

    def connect_server(self, bot_url):
        ngrok_url = self.get_ngrok_url()
        requests.get(bot_url + "setWebHook?url=%s" % ngrok_url)
    

if __name__ == '__main__':
    app = TelegramBot()
    connector = Ngrok_Connector()
    connector.connect_server(app.BOT_URL)
    app.run(host='0.0.0.0', port=8080, debug=True)