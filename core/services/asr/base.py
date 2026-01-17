from abc import ABC, abstractmethod


class ASRProvider(ABC):
    name: str

    @abstractmethod
    def transcribe(self, audio_path: str) -> dict:
        """
        Must return:
        {
            language,
            transcript_native,
            transcript_english
        }
        """
        pass
