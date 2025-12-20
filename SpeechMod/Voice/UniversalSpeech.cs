using SpeechMod.Unity;
using SpeechMod.Voice; // Added this using directive for VoiceType
using System;
using System.Collections.Generic;

namespace SpeechMod.Voice;

// This class acts as the safe, universal implementation of ISpeech
// for all platforms where the original WindowsSpeech would fail.
public class UniversalSpeech : ISpeech 
{
    // The constructor is empty and guaranteed not to fail at runtime.
    public UniversalSpeech() 
    {
    }

    // --- Delegate all method calls directly to the working Linux component ---

    // Method used by Main.cs for basic speaking
    public void Speak(string text, int length, float delay) => LinuxVoiceUnity.Speak(text, length, delay);

    // Get voices delegates to the component
    public string[] GetAvailableVoices() => LinuxVoiceUnity.GetAvailableVoices();
    
    // Status delegates to the component
    public string GetStatusMessage() => LinuxVoiceUnity.GetStatusMessage();

    // Stop delegates to the component
    public void Stop() => LinuxVoiceUnity.Stop();

    // Clear queue delegates to the component
    public void ClearQueue() => LinuxVoiceUnity.ClearQueue();
    
    // --- Implement remaining ISpeech methods by delegating to the simplest Speak method ---
    
    // This method needs to check the static status of the component
    public bool IsSpeaking() => LinuxVoiceUnity.IsSpeaking; 

    // Speak methods must be implemented; we use the LinuxVoiceUnity.Speak(string text, int length, float delay)
    // Since we don't know the intended length/word count for these specific calls, we will pass a placeholder (1).
    public void Speak(string text, float delay = 0) => LinuxVoiceUnity.Speak(text, 1, delay);

    public void SpeakPreview(string text, VoiceType voiceType) => LinuxVoiceUnity.Speak(text, 1);

    public void SpeakDialog(string text, float delay = 0) => LinuxVoiceUnity.Speak(text, 1, delay);

    public void SpeakAs(string text, VoiceType type, float delay = 0) => LinuxVoiceUnity.Speak(text, 1, delay);

    // Note: If you encounter an error "Cannot resolve symbol 'VoiceType'", you may need to add the correct
    // using statement for the VoiceType enum, which is likely: 
    // using SpeechMod.Voice; 
    // (I have added this to the top of the code block).
}