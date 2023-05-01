# Copyright (C) 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Sample that implements gRPC client for Google Assistant API."""

import json
import logging
import os.path

import click
import grpc
import google.auth.transport.grpc
import google.auth.transport.requests
import google.oauth2.credentials
from emotions import emotions
from google.assistant.embedded.v1alpha2 import (
    embedded_assistant_pb2,
    embedded_assistant_pb2_grpc
)

from tenacity import retry, stop_after_attempt, retry_if_exception



try:
    import assistant_helpers
    import audio_helpers
    import device_helpers
except SystemError:
    import assistant_helpers
    import audio_helpers
    import device_helpers
    
#new imports
import multiprocessing
from servoMovementAndDisplay import default, init, listen, happy, sad, angry, fear, disgust, surprise
import threading

ASSISTANT_API_ENDPOINT = 'embeddedassistant.googleapis.com'
END_OF_UTTERANCE = embedded_assistant_pb2.AssistResponse.END_OF_UTTERANCE
DIALOG_FOLLOW_ON = embedded_assistant_pb2.DialogStateOut.DIALOG_FOLLOW_ON
CLOSE_MICROPHONE = embedded_assistant_pb2.DialogStateOut.CLOSE_MICROPHONE
DEFAULT_GRPC_DEADLINE = 60 * 3 + 5


first = True
current_emotion = 1
previous_emotion = 1


def animateServosAndDisplay(emotion):
    if emotion == 0: #default
        default()
    elif emotion == 1: #listen
        listen()
    elif emotion == 2: #happy
        happy()
    elif emotion == 3: #sad
        sad()
    elif emotion == 4:
        angry()
    elif emotion == 5:
        fear()
    elif emotion == 6:
        disgust()
    elif emotion == 7:
        surprise()

class Animation (threading.Thread):
    def __init__(self, startEmotion):
        init()
        threading.Thread.__init__(self)
        current_emotion = startEmotion
        previous_emotion = startEmotion
    
    
        
    def run(self):
        global first
        while True:
            if first:
                print("animating")
                previous_emotion = current_emotion
                first = False
                animateServosAndDisplay(current_emotion)
            else:
                if current_emotion != previous_emotion:
                    previous_emotion = current_emotion
                    animateServosAndDisplay(current_emotion)
                    print("animating")


def set_emotion(current_emotion, str):
        splits = str.split()
        for split in splits:
                for i in range(len(emotions)):
                        for j in range(len(emotions[i])):
                                if split.lower() == emotions[i][j]:
                                        return i
        return 1
    


class Assistant():
    def __init__(self,language_code,device_id,device_model_id):
        Animation(1).start()
        self.device_id=device_id
        self.device_model_id=device_model_id
        self.language_code=language_code
        self.api_endpoint = ASSISTANT_API_ENDPOINT
        self.credentials = os.path.join(click.get_app_dir('google-oauthlib-tool'),
                                   'credentials.json')
        # Setup logging.
        logging.basicConfig() # filename='assistant.log', level=logging.DEBUG if self.verbose else logging.INFO)
        self.logger = logging.getLogger("assistant")
        self.logger.setLevel(logging.DEBUG)

        # Load OAuth 2.0 credentials.
        try:
            with open(self.credentials, 'r') as f:
                self.credentials = google.oauth2.credentials.Credentials(token=None,
                                                                    **json.load(f))
                self.http_request = google.auth.transport.requests.Request()
                self.credentials.refresh(self.http_request)
        except Exception as e:
            logging.error('Error loading credentials: %s', e)
            logging.error('Run google-oauthlib-tool to initialize '
                          'new OAuth 2.0 credentials.')
            return

        # Create an authorized gRPC channel.
        self.grpc_channel = google.auth.transport.grpc.secure_authorized_channel(
            self.credentials, self.http_request, self.api_endpoint)
        logging.info('Connecting to %s', self.api_endpoint)
        
        self.audio_sample_rate = audio_helpers.DEFAULT_AUDIO_SAMPLE_RATE
        self.audio_sample_width = audio_helpers.DEFAULT_AUDIO_SAMPLE_WIDTH
        self.audio_iter_size = audio_helpers.DEFAULT_AUDIO_ITER_SIZE
        self.audio_block_size = audio_helpers.DEFAULT_AUDIO_DEVICE_BLOCK_SIZE
        self.audio_flush_size = audio_helpers.DEFAULT_AUDIO_DEVICE_FLUSH_SIZE
        self.grpc_deadline = DEFAULT_GRPC_DEADLINE

        # Create Google Assistant API gRPC client.
        self.assistant = embedded_assistant_pb2_grpc.EmbeddedAssistantStub(self.grpc_channel)

        # Stores an opaque blob provided in ConverseResponse that,
        # when provided in a follow-up ConverseRequest,
        # gives the Assistant a context marker within the current state
        # of the multi-Converse()-RPC "conversation".
        # This value, along with MicrophoneMode, supports a more natural
        # "conversation" with the Assistant.
        self.conversation_state_bytes = None

        # Stores the current volument percentage.
        # Note: No volume change is currently implemented in this sample
        self.volume_percentage = 50
    
    
    def assist(self):
        #global animate
        global current_emotion
        
        # Configure audio source and sink.
        self.audio_device = None
        self.audio_source = self.audio_device = (
            self.audio_device or audio_helpers.SoundDeviceStream(
                sample_rate=self.audio_sample_rate,
                sample_width=self.audio_sample_width,
                block_size=self.audio_block_size,
                flush_size=self.audio_flush_size
            )
        )

        self.audio_sink = self.audio_device = (
            self.audio_device or audio_helpers.SoundDeviceStream(
                sample_rate=self.audio_sample_rate,
                sample_width=self.audio_sample_width,
                block_size=self.audio_block_size,
                flush_size=self.audio_flush_size
            )
        )

        # Create conversation stream with the given audio source and sink.
        self.conversation_stream = audio_helpers.ConversationStream(
            source=self.audio_source,
            sink=self.audio_sink,
            iter_size=self.audio_iter_size,
            sample_width=self.audio_sample_width
        )
        restart = False
        continue_dialog = True
        try:
            while continue_dialog:
                continue_dialog = False
                self.conversation_stream.start_recording()
                self.logger.info('Recording audio request.')
                current_emotion = 1

                def iter_assist_requests():
                    for c in self.gen_assist_requests():
                        assistant_helpers.log_assist_request_without_audio(c)
                        yield c
                    self.conversation_stream.start_playback()
                
                final = ""
                lastFlag = 0
                # This generator yields AssistResponse proto messages
                # received from the gRPC Google Assistant API.
                for resp in self.assistant.Assist(iter_assist_requests(),
                                                    self.grpc_deadline):
                    assistant_helpers.log_assist_response_without_audio(resp)
                    if resp.event_type == END_OF_UTTERANCE:
                        self.logger.info('End of audio request detected')
                        self.conversation_stream.stop_recording()
                        lastFlag = 1
                    if resp.speech_results:
                        self.logger.info('Transcript of user request: "%s".',
                                         ' '.join(r.transcript
                                                  for r in resp.speech_results))
                        if lastFlag:
                            self.logger.info('Playing assistant response.')
                            lastFlag = 0
                            final = ' '.join(r.transcript for r in resp.speech_results)
                            current_emotion = set_emotion(current_emotion, final)
                            print("Emotion Detected: ", emotions[current_emotion][0])
                    if resp.dialog_state_out.supplemental_display_text:
                        display_text=resp.dialog_state_out.supplemental_display_text
                        self.logger.info('Response text:' + ''.join(display_text))
                    if len(resp.audio_out.audio_data) > 0:
                        self.conversation_stream.write(resp.audio_out.audio_data)
                    if resp.dialog_state_out.conversation_state:
                        self.conversation_state_bytes = resp.dialog_state_out.conversation_state
                        self.logger.info('Updating conversation state.')
                    if resp.dialog_state_out.volume_percentage != 0:
                        volume_percentage = resp.dialog_state_out.volume_percentage
                        self.logger.info('Volume should be set to %s%%', volume_percentage)
                        self.conversation_stream.volume_percentage = volume_percentage
                    if resp.dialog_state_out.microphone_mode == DIALOG_FOLLOW_ON:
                        continue_dialog = True
                        self.logger.info('Expecting follow-on query from user.')
                    elif resp.dialog_state_out.microphone_mode == CLOSE_MICROPHONE:
                        continue_dialog = False

                self.logger.info('Finished playing assistant response.')
                self.conversation_stream.stop_playback()
                current_emotion = 1
        except Exception as e:
            self._create_assistant()
            self.logger.exception('Skipping because of connection reset')
            restart = True
        try:
            self.conversation_stream.close()
            if restart:
                self.assist()
        except Exception:
            self.logger.error('Failed to close conversation_stream.')

    def _create_assistant(self):
        # Create gRPC channel
        grpc_channel = google.auth.transport.grpc.secure_authorized_channel(
            self.credentials, self.http_request, self.api_endpoint)

        self.logger.info('Connecting to %s', self.api_endpoint)
        # Create Google Assistant API gRPC client.
        self.assistant = embedded_assistant_pb2_grpc.EmbeddedAssistantStub(grpc_channel)

    def is_grpc_error_unavailable(e):
        is_grpc_error = isinstance(e, grpc.RpcError)
        if is_grpc_error and (e.code() == grpc.StatusCode.UNAVAILABLE):
            logging.error('grpc unavailable error: %s', e)
            return True
        return False

    @retry(reraise=True, stop=stop_after_attempt(3),
           retry=retry_if_exception(is_grpc_error_unavailable))
    
    # This generator yields ConverseRequest to send to the gRPC
    # Google Assistant API.
    def gen_assist_requests(self):
        """Yields: ConverseRequest messages to send to the API."""
        
        dialog_state_in = embedded_assistant_pb2.DialogStateIn(
                language_code=self.language_code,
                conversation_state=b''
            )
        if self.conversation_state_bytes:
            logging.debug('Sending converse_state: %s',
                          self.conversation_state_bytes)
            dialog_state_in.conversation_state = self.conversation_state_bytes
        config = embedded_assistant_pb2.AssistConfig(
            audio_in_config=embedded_assistant_pb2.AudioInConfig(
                encoding='LINEAR16',
                sample_rate_hertz=self.conversation_stream.sample_rate,
            ),
            audio_out_config=embedded_assistant_pb2.AudioOutConfig(
                encoding='LINEAR16',
                sample_rate_hertz=self.conversation_stream.sample_rate,
                volume_percentage=self.conversation_stream.volume_percentage,
            ),
            dialog_state_in=dialog_state_in,
            device_config=embedded_assistant_pb2.DeviceConfig(
                device_id=self.device_id,
                device_model_id=self.device_model_id,
            )
        )
        # The first ConverseRequest must contain the ConverseConfig
        # and no audio data.
        yield embedded_assistant_pb2.AssistRequest(config=config)
        for data in self.conversation_stream:
            # Subsequent requests need audio data, but not config.
            yield embedded_assistant_pb2.AssistRequest(audio_in=data)