# -*- coding: utf-8 -*-

# Copyright 2023 Google LLC
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

from websockets.legacy.client import WebSocketClientProtocol
from websockets_proxy import Proxy, proxy_connect
import asyncio
import base64
import json
import os
import sys
import pyaudio
from rich.console import Console
from rich.markdown import Markdown
from websockets.asyncio.client import connect
from websockets.asyncio.connection import Connection
from elevenlabs import ElevenLabs, play
import numpy as np
import dotenv

dotenv.load_dotenv()

# Configuração básica
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 16000
CHUNK_SIZE = 512

host = "generativelanguage.googleapis.com"
model = "gemini-2.0-flash-exp"
api_key = os.environ["GOOGLE_API_KEY"]
uri = f"wss://{host}/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={api_key}"

# Configurações de voz
pya = pyaudio.PyAudio()
voice_api_key = os.environ.get("ELEVENLABS_API_KEY")
voice_model = "eleven_flash_v2_5"
voice_voice_id = "nPczCjzI2devNBz1zQrb"

# Definições de tema e cena
THEMES = {
    "business": ["job interview", "business meeting", "presentation", "networking"],
    "travel": ["airport", "hotel", "restaurant", "sightseeing"],
    "daily life": ["shopping", "weather", "hobbies", "family"],
    "social": ["meeting friends", "party", "social media", "dating"],
}

class AudioLoop:
    def __init__(self):
        self.ws: WebSocketClientProtocol | Connection
        self.audio_out_queue = asyncio.Queue()
        self.running_step = 0
        self.paused = False
        self.current_theme = None
        self.current_scenario = None
        self.console = Console()
        self.voice_client = None
        
       # Inicializar o cliente de voz
        if voice_api_key:
            self.console.print("Ativar modo de voz", style="green")
            self.voice_client = ElevenLabs(api_key=voice_api_key)
        else:
            self.console.print("Modo de voz desativado, não consigo encontrar ELEVENLABS_API_KEY", style="red")

    def calculate_pronunciation_score(self, audio_data):
        """Calculando pontuações de pronúncia"""
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Recursos de áudio de computação
            energy = np.mean(np.abs(audio_array))
            zero_crossings = np.sum(np.abs(np.diff(np.signbit(audio_array))))
            
            # Normalizar e calcular a pontuação
            energy_score = min(100, energy / 1000)
            rhythm_score = min(100, zero_crossings / 100)
            
            # Pontuação final
            final_score = int(0.6 * energy_score + 0.4 * rhythm_score)
            return min(100, max(0, final_score))
        except Exception as e:
            self.console.print(f"Erro de cálculo de classificação: {e}", style="red")
            return 70  # Retorna a pontuação padrão em caso de erro

    async def startup(self):
     """Inicializar a conversa"""
     # Configurar configuração inicial
        setup_msg = {
            "setup": {
                "model": f"models/{model}",
                "generation_config": {"response_modalities": ["TEXT"]},
            }
        }
        await self.ws.send(json.dumps(setup_msg))
        await self.ws.recv()

        # Enviar prompt inicial
        initial_msg = {
            "client_content": {
                "turns": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": """Você é um professor de de inglês acostumado a ensinar pronúncia para brasileiros. Por favor, responda em português brasileiro e inglês, com inglês primeiro e português por último, separados por ---.
                                
                                
Your responsibilities are:
1. Help users correct grammar and pronunciation
2. Give pronunciation scores and detailed feedback
3. Understand and respond to control commands:
   - Pause when user says "Can I have a break"
   - Continue when user says "OK let's continue"
4. Provide practice sentences based on chosen themes and scenarios

Suas responsabilidades são:
1. Ajude os usuários a corrigir a gramática e a pronúncia
2. Dê classificações de pronúncia e feedback detalhado
3. Entenda e responda às instruções de controle do usuário:
 - Pausa quando o usuário diz "Posso fazer uma pausa"
 - Continue quando o usuário disser "OK, vamos continuar"
4. Forneça frases de prática com base em tópicos e cenários selecionados

First, ask which theme they want to practice (business, travel, daily life, social) in English.

Cada vez que o usuário termina uma frase, você precisa:
1. Identifique o que o usuário disse (Inglês)
2. Dê uma pontuação de pronúncia (0-100 pontos)
3. Explicação detalhada de problemas de pronúncia e gramática (em português e inglês)
4. Forneça sugestões de melhoria (em português e inglês)
5. Forneça frases de prática para o próximo cenário relevante (em português e inglês)

Por favor, mantenha sempre o seguinte formato:
[Conteúdo em inglês]
---
[Conteúdo Português]

Se você entendeu, por favor responda em português ou inglês. OK"""
                            }
                        ],
                    }
                ],
                "turn_complete": True,
            }
        }
        await self.ws.send(json.dumps(initial_msg))
        
        # Aguarde a resposta da IA OK
        current_response = []
        async for raw_response in self.ws:
            response = json.loads(raw_response)
            try:
                if "serverContent" in response:
                    parts = response["serverContent"].get("modelTurn", {}).get("parts", [])
                    for part in parts:
                        if "text" in part:
                            current_response.append(part["text"])
            except Exception:
                pass

            try:
                turn_complete = response["serverContent"]["turnComplete"]
                if turn_complete:
                    if "".join(current_response).startswith("OK"):
                        self.console.print("Inicialização concluída ✅", style="green")
                        return
            except KeyError:
                pass

    async def listen_audio(self):
        """Monitorar entrada de áudio"""
        mic_info = pya.get_default_input_device_info()
        stream = pya.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )

        self.console.print("🎤 Por favor, fale Inglês", style="yellow")

        while True:
            if self.paused:
                await asyncio.sleep(0.1)
                continue

            data = await asyncio.to_thread(stream.read, CHUNK_SIZE)
            if self.running_step > 1:
                continue

            # Detecção de volume
            audio_data = []
            for i in range(0, len(data), 2):
                sample = int.from_bytes(data[i:i+2], byteorder="little", signed=True)
                audio_data.append(abs(sample))
            volume = sum(audio_data) / len(audio_data)

            if volume > 200:
                if self.running_step == 0:
                    self.console.print("🎤 :", style="yellow", end="")
                    self.running_step += 1
                self.console.print("*", style="green", end="")
            await self.audio_out_queue.put(data)

    async def send_audio(self):
        """Enviar dados de áudio"""
        while True:
            if self.paused:
                await asyncio.sleep(0.1)
                continue

            chunk = await self.audio_out_queue.get()
            msg = {
                "realtime_input": {
                    "media_chunks": [
                        {
                            "data": base64.b64encode(chunk).decode(),
                            "mime_type": "audio/pcm",
                        }
                    ]
                }
            }
            await self.ws.send(json.dumps(msg))

    async def receive_audio(self):
        """Receber e processar respostas"""
        current_response = []
        async for raw_response in self.ws:
            if self.running_step == 1:
                self.console.print("\n♻️ Processamento：", end="")
                self.running_step += 1

            response = json.loads(raw_response)
            try:
                if "serverContent" in response:
                    parts = response["serverContent"].get("modelTurn", {}).get("parts", [])
                    for part in parts:
                        if "text" in part:
                            current_response.append(part["text"])
                            self.console.print("-", style="blue", end="")
            except Exception:
                pass

            try:
                turn_complete = response["serverContent"]["turnComplete"]
                if turn_complete and current_response:
                    text = "".join(current_response)
                    
                    # Verifique se é um comando de controle
                    if "can i have a break" in text.lower():
                        self.paused = True
                        self.console.print("\n⏸️ A sessão está pausada. Diga 'OK, vamos continuar', style="yellow")
                    elif "ok let's continue" in text.lower() and self.paused:
                        self.paused = False
                        self.console.print("\n▶️ Continuação da sessão", style="green")
                    
                   # Exibir a resposta
                    self.console.print("\n🤖 =============================================", style="yellow")
                    self.console.print(Markdown(text))
                    
                   # Reproduzir áudio
                    if self.voice_client and not self.paused:
                        try:
                            def play_audio():
                                # Conteúdo dividido em chinês e inglês
                                parts = text.split('---')
                                if len(parts) > 0:
                                    # Toque apenas a parte em inglês (a primeira parte)
                                    english_text = parts[0].strip()
                                    voice_stream = self.voice_client.text_to_speech.convert_as_stream(
                                        voice_id=voice_voice_id,
                                        text=english_text,
                                        model_id=voice_model,
                                    )
                                    play(voice_stream)

                            self.console.print("🙎 Som tocando........", style="yellow")
                            await asyncio.to_thread(play_audio)
                            self.console.print("🙎 Reprodução concluída", style="green")
                        except Exception as e:
                            self.console.print(f"Erro de reprodução de voz: {e}", style="red")

                    current_response = []
                    self.running_step = 0 if not self.paused else 2
            except KeyError:
                pass

    async def run(self):
        """Função principal em execução"""
        proxy = Proxy.from_url(os.environ["HTTP_PROXY"]) if os.environ.get("HTTP_PROXY") else None
        if proxy:
            self.console.print("Use um proxy", style="yellow")
        else:
            self.console.print("Sem proxy", style="yellow")

        async with (proxy_connect(uri, proxy=proxy) if proxy else connect(uri)) as ws:
            self.ws = ws
            self.console.print("Gemini Assistente de Fala Inglês", style="green", highlight=True)
            self.console.print("Make by twitter: @BoxMrChen", style="blue")
            self.console.print("============================================", style="yellow")
            
            await self.startup()

            async with asyncio.TaskGroup() as tg:
                tg.create_task(self.listen_audio())
                tg.create_task(self.send_audio())
                tg.create_task(self.receive_audio())

                def check_error(task):
                    if task.cancelled():
                        return
                    if task.exception():
                        print(f"Error: {task.exception()}")
                        sys.exit(1)

                for task in tg._tasks:
                    task.add_done_callback(check_error)

if __name__ == "__main__":
    main = AudioLoop()
    asyncio.run(main.run())
