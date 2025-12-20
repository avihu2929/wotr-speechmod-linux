using SpeechMod.Unity.Extensions;
using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
// Required for Process.Start
using UnityEngine;
using static System.Text.Encoding;

// We remove the DllImport and Interop using directives as they are no longer needed.

namespace SpeechMod.Unity;

// This new class replaces the WindowsVoiceUnity class functionality.
public class LinuxVoiceUnity : MonoBehaviour
{
    // The enum name must remain the same (WindowsVoiceStatus) if other parts of the mod 
    // rely on this exact name for status checking. We use the original enum name for maximum compatibility.
    public enum WindowsVoiceStatus { Uninitialized, Ready, Speaking, Terminated, Error }

    // ADDED: Command to execute the Linux TTS engine
// Change the constant back to the shell interpreter:
// CRITICAL FIX: The command must be a Windows executable guaranteed to be in the PATH.
    private const string TTS_COMMAND = "cmd.exe"; 
    private const string QUEUE_FILE_PATH = @"C:\tmp\speech_mod_queue.txt";

// The script path remains the same (Windows-formatted).
    private const string TTS_SCRIPT_PATH = @"C:\GOG Games\Pathfinder Kingmaker\Mods\PFKingmakerSpeechMod\run_spd_say.sh";
    private static LinuxVoiceUnity m_TheVoice;
    private static int m_CurrentWordCount;
    
    // Updated properties based on Linux external process model
    public static bool IsSpeaking { get; private set; } = false;
    public static WindowsVoiceStatus VoiceStatus { get; private set; } = WindowsVoiceStatus.Ready;

    // The original DLL functions are removed.
    // The mod must call LinuxVoiceUnity.Method instead of WindowsVoiceUnity.Method.

    private static void Init()
    {
        // No complex DLL initialization needed for external process
        VoiceStatus = WindowsVoiceStatus.Ready;
    }

    private static bool IsVoiceInitialized()
    {
        if (m_TheVoice != null)
            return true;

        Main.Logger.Critical("No voice initialized!");
        return false;
    }

    void Start()
    {
        m_CurrentWordCount = 0;
        if (m_TheVoice != null)
        {
            // If another instance exists, destroy this one.
            Destroy(gameObject);
        }
        else
        {
            m_TheVoice = this;
            // Initialize the voice on start
            Init();
        }
    }

    public static string[] GetAvailableVoices()
    {
        // Cannot easily query voices on Linux, returning placeholders
        return new string[] { "Linux System Default (spd-say)", "eSpeak" };
    }

    public static void Speak(string text, int length, float delay = 0f)
    {
        if (!IsVoiceInitialized() || string.IsNullOrWhiteSpace(text))
            return;

        if (Main.Settings!.InterruptPlaybackOnPlay && IsSpeaking)
            Stop();

        m_CurrentWordCount = length;
        
        if (delay <= 0f)
            ExecuteExternalSpeech(text);
        else
            // ExecuteLater is an extension method likely defined in SpeechMod.Unity.Extensions
            m_TheVoice.ExecuteLater(delay, () => ExecuteExternalSpeech(text));
        
    }

    private static void ExecuteExternalSpeech(string text)
    {
        try
        {
            IsSpeaking = true;
            // Execute spd-say non-blockingly: -t text (tells spd-say it's text), quoted text
           // Process.Start(TTS_COMMAND, $"-t text \"{text}\""); 
// Arguments passed to cmd.exe: "/c sh C:\path\to\script -t text 'text'"
            string sanitizedText = Regex.Replace(text, "<.*?>", string.Empty);
            
            // 2. Remove potential empty spaces created by tag removal
            sanitizedText = sanitizedText.Trim();
            
            // 3. Write the CLEANED text to the file.
            File.WriteAllText(QUEUE_FILE_PATH, sanitizedText + Environment.NewLine, Encoding.UTF8);


            Main.Logger.Log($"Wrote speech queue to: {QUEUE_FILE_PATH}");
            // Set a simple timeout to reset the speaking flag.
            // Assuming 10 chars per second plus a 1.0s buffer.
            float duration = text.Length * 0.1f + 1.0f; 
            m_TheVoice.ExecuteLater(duration, () => IsSpeaking = false);
        }
        catch (Exception ex)
        {
            Main.Logger.Error($"Failed to execute TTS command '{TTS_COMMAND}': {ex.Message}");
            IsSpeaking = false;
            VoiceStatus = WindowsVoiceStatus.Error;
        }
    }
    
    // --- Simplified/Placeholder Functions (Original Windows functionality is lost) ---

    public static string GetStatusMessage() => "Running on Linux via external process (spd-say).";

    // Word tracking functions are now placeholders
    public static int WordPosition => m_CurrentWordCount; 
    public static int WordCount => m_CurrentWordCount;
    public static int WordLength => 1; 

    public static float GetNormalizedProgress() => IsSpeaking ? 0.5f : 1.0f; // Placeholder value

    public static void Stop()
    {
        if (!IsVoiceInitialized() || !IsSpeaking)
            return;
        
        // Cannot reliably stop external spd-say process; we only stop tracking.
        IsSpeaking = false;
        ClearQueue();
    }

    public static void ClearQueue()
    {
        if (!IsVoiceInitialized())
            return;
        
        try
        {
            // CRITICAL FIX: Write an empty string to the file and clear it.
            // This is the C# mod's way of saying: "Stop and be quiet."
            File.WriteAllText(QUEUE_FILE_PATH, string.Empty, Encoding.UTF8); 
        
            Main.Logger.Log($"Wrote empty string to queue: {QUEUE_FILE_PATH}");
        }
        catch (Exception ex)
        {
            Main.Logger.Error($"Failed to clear queue (write empty string): {ex.Message}");
        }
    }

    void OnDestroy()
    {
        if (m_TheVoice != this)
            return;

        m_TheVoice = null;
    }
}