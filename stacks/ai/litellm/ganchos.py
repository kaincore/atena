# Ganchos do LiteLLM do servidor Atena (carregados por litellm_settings.callbacks no config.yaml).
from litellm.integrations.custom_logger import CustomLogger


class Voz(CustomLogger):
    """O Hermes pede opus para a mensagem de voz, mas o Speaches só gera mp3, flac, wav ou pcm.
    No modelo "voz", troca o formato por mp3; o Hermes reconverte para Ogg/Opus com o ffmpeg."""

    async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        if call_type == "aspeech" and data.get("model") == "voz" and data.get("response_format") in ("opus", "aac"):
            data["response_format"] = "mp3"
        return data


voz = Voz()
