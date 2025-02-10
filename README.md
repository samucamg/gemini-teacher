# Assistente de Conversação em inglês com Gemini

Este é um assistente de prática de conversação em inglês baseado no Google Gemini AI, que pode reconhecer sua pronúncia em inglês em tempo real e fornecer feedback instantâneo e sugestões de correção.

## Características

-🎤 Reconhecimento de fala em tempo real
- 🤖 Avaliação de pronúncia com tecnologia de IA
- 📝 Correção gramatical
- 🔄 Prática de diálogo situacional
- 🎯 Orientação de pronúncia direcionada
- 💡 Troca de cena inteligente

## Requisitos do sistema

-Python 3.11+ (obrigatório)
-Equipamento de microfone
-Conexão de rede.

## Pré-dependências

Você precisa de uma chave de API Gemini, que é gratuita 4 milhões de vezes por dia, o que é suficiente para seu uso.

Acesse esta página [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) para gerá-lo.

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/nishuzumi/gemini-teacher.git
cd gemini-teacher
```

2. Crie e ative um ambiente virtual (recomendado):
```bash
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
# ou
.venv\Scripts\activate  # Windows
```

3. Instale as dependências:

Antes de instalar as dependências do Python, instale as seguintes dependências do sistema:

- Windows: Nenhuma instalação adicional necessária
- macOS: `brew install portaudio`
- Ubuntu/Debian: `sudo apt-get install portaudio19-dev python3-pyaudio`

```bash
pip install -r requirements.txt
```

## Uso

1. Configure o ambiente
Crie um novo arquivo `.env`, copie o conteúdo de `.env.example` para ele e modifique-o.

Se você precisar definir um proxy, preencha `HTTP_PROXY`, por exemplo `HTTP_PROXY=http://127.0.0.1:7890`

`GOOGLE_API_KEY` preencha a chave da API do Google Gemini
### Habilitar a função de voz
Este recurso é habilitado sob demanda. `ELEVENLABS_API_KEY` é a CHAVE de API para o recurso de voz.

Como obter:
- Abra o site [https://elevenlabs.io/](https://try.elevenlabs.io/2oulemau2lxk)
- Clique em Experimentar gratuitamente no canto superior direito para se registrar e ganhar 1.000 créditos grátis
- Vá para as configurações pessoais, gere uma chave de API e preencha-a

```bash
python starter.py
```

2. Fale frases em inglês de acordo com as instruções
3. Aguarde o feedback do assistente de IA
4. Melhore a pronúncia com base no feedback

## Instruções de interação

- 🎤 : Gravação
- ♻️ : Processando
- 🤖 : Feedback de IA

## Licença

MIT

## contribuir

Problemas e solicitações de pull são bem-vindos!
## Licença
