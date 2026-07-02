using System.Collections.Generic;
using Newtonsoft.Json;

namespace VoidLauncherUI
{
    public class RootConfig
    {
        [JsonProperty("global-settings")]
        public Dictionary<string, Dictionary<string, bool>> GlobalSettings { get; set; }

        [JsonProperty("personalities")]
        public List<Personality> Personalities { get; set; }

        [JsonProperty("feature-ram-monitor")]
        public Dictionary<string, object> FeatureRamMonitor { get; set; }

        [JsonProperty("feature-smart-suggestions")]
        public Dictionary<string, object> FeatureSmartSuggestions { get; set; }
    }

    public class Personality
    {
        [JsonProperty("name")]
        public string Name { get; set; }

        [JsonProperty("enabled")]
        public bool Enabled { get; set; }

        [JsonProperty("trigger-shortcut")]
        public string TriggerShortcut { get; set; }

        [JsonProperty("apps-to-launch")]
        public AppsToLaunchClass AppsToLaunch { get; set; }

        [JsonProperty("tabs-to-open")]
        public TabsToOpenClass TabsToOpen { get; set; }

        [JsonProperty("virtual-desktop-switch")]
        public VirtualDesktopSwitchClass VirtualDesktopSwitch { get; set; }

        [JsonProperty("system-settings-automation")]
        public SystemSettingsAutomationClass SystemSettingsAutomation { get; set; }

        [JsonProperty("wallpaper-switch")]
        public WallpaperSwitchClass WallpaperSwitch { get; set; }

        [JsonExtensionData]
        public Dictionary<string, object> AdditionalData { get; set; }
    }

    public class SystemSettingsAutomationClass
    {
        [JsonProperty("enabled")]
        public bool Enabled { get; set; }

        [JsonProperty("volume-level")]
        public int VolumeLevel { get; set; }

        [JsonProperty("do-not-disturb")]
        public bool DoNotDisturb { get; set; }
    }

    public class WallpaperSwitchClass
    {
        [JsonProperty("enabled")]
        public bool Enabled { get; set; }

        [JsonProperty("wallpaper-path")]
        public string WallpaperPath { get; set; }
    }

    public class VirtualDesktopSwitchClass
    {
        [JsonProperty("enabled")]
        public bool Enabled { get; set; }

        [JsonProperty("target-desktop-name")]
        public string TargetDesktopName { get; set; }
    }

    public class AppsToLaunchClass
    {
        [JsonProperty("enabled")]
        public bool Enabled { get; set; }

        [JsonProperty("paths")]
        public string Paths { get; set; }
    }

    public class TabsToOpenClass
    {
        [JsonProperty("enabled")]
        public bool Enabled { get; set; }

        [JsonProperty("urls")]
        public string Urls { get; set; }
    }
}