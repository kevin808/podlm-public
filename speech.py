#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# author：samge
# date：2024-06-29
# describe：Azure Speech Service TTS Implementation

import os
import azure.cognitiveservices.speech as speechsdk
import config
from datetime import datetime

def log(message):
    print(f"[{datetime.now().isoformat()}] {message}")

def text_to_speech(ssml) -> bytes:
    """Use Azure Speech Service and convert SSML to audio bytes."""
    log("Initializing text-to-speech conversion")

    speech_config = speechsdk.SpeechConfig(
        subscription=config.azure_speech_key,
        region=config.azure_speech_region,
    )

    audio_config = None  # enable in-memory audio stream
    log("Configuring speech synthesis format: RIFF 48KHz 16-bit mono PCM")
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff48Khz16BitMonoPcm
    )

    log("Creating speech synthesizer")
    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=audio_config
    )

    log("Starting SSML synthesis")
    result = speech_synthesizer.speak_ssml_async(ssml).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        audio_size = len(result.audio_data)
        log(f"Speech synthesis completed successfully. Generated {audio_size} bytes of audio data")
        return result.audio_data

    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        log(f"Speech synthesis canceled: {cancellation_details.reason}")

        if (
            cancellation_details.reason == speechsdk.CancellationReason.Error
            and cancellation_details.error_details
        ):
            log(f"Error details: {cancellation_details.error_details}")

        raise Exception(f"Error details: {cancellation_details.error_details}")

    log(f"Speech synthesis failed with unknown reason: {result.reason}")
    raise Exception(f"Unknown exit reason: {result.reason}")


def text_to_ssml(text, speaker_name, *, prosody_rate=None, temperature=1.0) -> str:
    """Convert plain text to SSML for a specific speaker.
    
    Args:
        text: The text to convert
        speaker_name: Name of the speaker (must be in config.azure_hd_voices)
        prosody_rate: Optional speech rate adjustment (e.g. '-10%')
        temperature: Voice temperature parameter (default: 1.0)
    
    Returns:
        str: SSML string
    """
    # Escape special XML characters
    text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
    
    # Get voice name from config
    voice_name = config.azure_hd_voices.get(speaker_name)
    if not voice_name:
        log(f"Warning: No voice configuration found for speaker {speaker_name}. Using default voice.")
        voice_name = "zh-CN-YunxiNeural"
    
    # Create SSML
    ssml = "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='zh-CN'>"
    
    # Add voice tag with optional temperature parameter
    voice_tag = f"<voice name='{voice_name}'"
    if temperature != 1.0:
        voice_tag += f" parameters='temperature={temperature}'"
    voice_tag += ">"
    
    ssml += voice_tag
    
    # Add prosody tag if rate is specified
    if prosody_rate:
        ssml += f"<prosody rate='{prosody_rate}'>{text}</prosody>"
    else:
        ssml += text
    
    ssml += "</voice></speak>"
    
    return ssml


def generate_audio_with_azure(text, speaker_name):
    """Generate audio using Azure Speech Service.
    
    Args:
        text: Text to synthesize
        speaker_name: Name of the speaker
        
    Returns:
        bytes: Audio data in WAV format
    """
    try:
        # Convert text to SSML
        ssml = text_to_ssml(
            text, 
            speaker_name, 
            prosody_rate=config.prosody_rate, 
            temperature=config.voice_temperature
        )
        
        # Convert SSML to speech
        audio_data = text_to_speech(ssml)
        
        return audio_data
    except Exception as e:
        log(f"Error generating audio with Azure: {str(e)}")
        return None


def legacy_tts_request(text, anchor_type):
    """Legacy TTS implementation using HTTP requests.
    Used as a fallback if Azure setup is not complete."""
    import requests
    
    url = config.get_tts_url(text, anchor_type)
    for _ in range(3):
        try:
            response = requests.get(url, timeout=120, headers=config.get_tts_headers())
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            log(f"Legacy TTS request failed: {str(e)}, retrying...")
    
    log("Legacy TTS request failed 3 times, giving up")
    return None
