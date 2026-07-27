using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.IO;          
using Newtonsoft.Json;    

namespace VoidLauncherUI
{
    public partial class ui : Form
    {
        // json config data
        private RootConfig fullConfig; 

        // list of all personalities
        private List<Personality> personalitiesList = new List<Personality>(); 

        // current active personality
        private Personality currentPersonality;

        public ui()
        {
            InitializeComponent();
            
            // force volume trackbar range so it doesn't crash on high volumes
            volume.Minimum = 0;
            volume.Maximum = 100;

            LoadPersonalitiesFromJson();
        }

        private string GetConfigFilePath()
        {
            // get current folder of the exe
            string exeDirectory = AppDomain.CurrentDomain.BaseDirectory;

            // check if json is right next to the exe first
            string productionPath = Path.Combine(exeDirectory, "scripts", "config.json");
            if (File.Exists(productionPath))
            {
                return productionPath;
            }

            // go up directories to find scripts/config.json
            DirectoryInfo dir = new DirectoryInfo(exeDirectory);
            while (dir != null)
            {
                string potentialPath = Path.Combine(dir.FullName, "scripts", "config.json");
                if (File.Exists(potentialPath))
                {
                    return potentialPath; 
                }
                dir = dir.Parent; 
            }

            // fallback if not found anywhere else
            return Path.Combine(exeDirectory, "scripts", "config.json");
        }

        private void LoadPersonalitiesFromJson()
        {
            try
            {
                string jsonPath = GetConfigFilePath();

                if (File.Exists(jsonPath))
                {
                    string jsonContent = File.ReadAllText(jsonPath);
                    fullConfig = JsonConvert.DeserializeObject<RootConfig>(jsonContent);

                    if (fullConfig != null)
                    {
                        // load global features
                        if (fullConfig.FeatureSmartSuggestions != null)
                        {
                            smart_suggestion.Checked = fullConfig.FeatureSmartSuggestions.Enabled;
                        }
                        if (fullConfig.FeatureRamMonitor != null)
                        {
                            Ram_mon.Checked = fullConfig.FeatureRamMonitor.Enabled;
                        }

                        if (fullConfig.Personalities != null)
                        {
                            // load personalities to list
                            personalitiesList = fullConfig.Personalities;

                            // clear listboxes so we don't get duplicates
                            all_personalatys.Items.Clear();
                            all_personalatys_auto.Items.Clear();
                            list_personalatys_visual.Items.Clear();
                            list_personalatys_sys.Items.Clear();

                            // add names to all listboxes
                            foreach (var personality in personalitiesList)
                            {
                                all_personalatys.Items.Add(personality.Name);
                                all_personalatys_auto.Items.Add(personality.Name);
                                list_personalatys_visual.Items.Add(personality.Name);
                                list_personalatys_sys.Items.Add(personality.Name);
                            }
                        }
                    }
                }
                else
                {
                    MessageBox.Show($"Could not locate config.json automatically at:\n{jsonPath}", "File Not Found", MessageBoxButtons.OK, MessageBoxIcon.Error);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error reading initialization file: {ex.Message}", "Load Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void panel1_Paint(object sender, PaintEventArgs e)
        {
        }

        private void personalaty_setings_Paint(object sender, PaintEventArgs e)
        {
        }

        private void flowLayoutPanel1_Paint(object sender, PaintEventArgs e)
        {
        }

        private void menu_personalaty_settings_Paint(object sender, PaintEventArgs e)
        {
        }

        private void textBox3_TextChanged(object sender, EventArgs e)
        {
        }

        private void add_app_personalaty_Click(object sender, EventArgs e)
        {  
            // open file dialog to choose an exe
            OpenFileDialog openFileDialog = new OpenFileDialog();
            openFileDialog.Filter = "Applications (*.exe)|*.exe|All files (*.*)|*.*";
            openFileDialog.Title = "Select an Application for your personality";

            if (openFileDialog.ShowDialog() == DialogResult.OK)
            {
                // add it to the apps list
                list_aplications_personalaty.Items.Add(openFileDialog.FileName);
            }
        }

        private void remove_app_personalaty_Click(object sender, EventArgs e)
        {
            // make sure something is selected
            if (list_aplications_personalaty.SelectedIndex != -1)
            {
                // remove selected application
                list_aplications_personalaty.Items.RemoveAt(list_aplications_personalaty.SelectedIndex);
            }
            else
            {
                // show warning if they didn't select anything
                MessageBox.Show("Please select an item from the list to remove.", "No Selection", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        private void remove_link_personalaty_Click(object sender, EventArgs e)
        {
            // make sure something is selected
            if (list_websites_personalaty.SelectedIndex != -1)
            {
                // remove selected website
                list_websites_personalaty.Items.RemoveAt(list_websites_personalaty.SelectedIndex);
            }
            else
            {
                // warning if nothing is selected
                MessageBox.Show("Please select an item from the list to remove.", "No Selection", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        private void add_link_personalaty_Click(object sender, EventArgs e)
        {
            // get url text and trim whitespace
            string url = personalaty_web_feald.Text.Trim();

            // error out if text field is empty
            if (string.IsNullOrEmpty(url))
            {
                MessageBox.Show("Please enter a website URL first.", "Empty Field", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            // add https prefix if missing
            if (!url.StartsWith("http://") && !url.StartsWith("https://"))
            {
                url = "https://" + url;
            }

            // add url to listbox
            list_websites_personalaty.Items.Add(url);

            // clear input field for next one
            personalaty_web_feald.Clear();
        }

        private void all_personalatys_SelectedIndexChanged(object sender, EventArgs e)
        {
            if (all_personalatys.SelectedIndex == -1) return;
            LoadPersonalityData(all_personalatys.SelectedIndex);
        }

        private void all_personalatys_auto_SelectedIndexChanged(object sender, EventArgs e)
        {
            if (all_personalatys_auto.SelectedIndex == -1) return;
            LoadPersonalityData(all_personalatys_auto.SelectedIndex);
        }

        private void LoadPersonalityData(int selectedIndex)
        {
            if (personalitiesList == null || selectedIndex < 0 || selectedIndex >= personalitiesList.Count) return;
            currentPersonality = personalitiesList[selectedIndex];

            // load personality panel info
            list_aplications_personalaty.Items.Clear();
            string dynamicPaths = currentPersonality.AppsToLaunch?.Paths;
            if (!string.IsNullOrEmpty(dynamicPaths))
            {
                list_aplications_personalaty.Items.AddRange(dynamicPaths.Split(new string[] { ", " }, StringSplitOptions.RemoveEmptyEntries));
            }

            list_websites_personalaty.Items.Clear();
            string dynamicUrls = currentPersonality.TabsToOpen?.Urls;
            if (!string.IsNullOrEmpty(dynamicUrls))
            {
                list_websites_personalaty.Items.AddRange(dynamicUrls.Split(new string[] { ", " }, StringSplitOptions.RemoveEmptyEntries));
            }

            personalaty_name_feld.Text = currentPersonality.Name;
            enable_personalaty.Checked = currentPersonality.Enabled;

            // load automation tab settings
            if (currentPersonality.AppsToLaunch != null)
            {
                enable_apps.Checked = currentPersonality.AppsToLaunch.Enabled;
            }
            else
            {
                enable_apps.Checked = false;
            }

            if (currentPersonality.TabsToOpen != null)
            {
                enable_tabs.Checked = currentPersonality.TabsToOpen.Enabled;
            }
            else
            {
                enable_tabs.Checked = false;
            }

            // update trigger hotkey
            trigger.Text = currentPersonality.TriggerShortcut ?? "";

            // update virtual desktop settings
            if (currentPersonality.VirtualDesktopSwitch != null)
            {
                enable_Virtual_destop.Checked = currentPersonality.VirtualDesktopSwitch.Enabled;
                Virtual_destop_name.Text = currentPersonality.VirtualDesktopSwitch.TargetDesktopName ?? "";
            }
            else
            {
                enable_Virtual_destop.Checked = false;
                Virtual_destop_name.Text = "";
            }

            // load system settings
            if (currentPersonality.SystemSettingsAutomation != null)
            {
                int volVal = currentPersonality.SystemSettingsAutomation.VolumeLevel;
                volume.Value = Math.Max(0, Math.Min(100, volVal));
                DnD.Checked = currentPersonality.SystemSettingsAutomation.DoNotDisturb;
            }
            else
            {
                volume.Value = 20;
                DnD.Checked = false;
            }

            // load wallpaper settings
            list_wallpapers.Items.Clear(); 

            if (currentPersonality.WallpaperSwitch != null)
            {
                enable_wallpaper.Checked = currentPersonality.WallpaperSwitch.Enabled;
                
                if (!string.IsNullOrEmpty(currentPersonality.WallpaperSwitch.WallpaperPath))
                {
                    list_wallpapers.Items.Add(currentPersonality.WallpaperSwitch.WallpaperPath);
                }
            }
            else
            {
                enable_wallpaper.Checked = false;
            }
        }

        private void save_pesonalatys_Click_1(object sender, EventArgs e)
        {
            SaveSettings(); 
        }

        private void SaveSettings()
        {
            if (currentPersonality == null || fullConfig == null) return;

            // save personality general settings
            if (currentPersonality.AppsToLaunch == null)
            {
                currentPersonality.AppsToLaunch = new AppsToLaunchClass();
            }
            currentPersonality.AppsToLaunch.Paths = string.Join(", ", list_aplications_personalaty.Items.Cast<string>());
            currentPersonality.AppsToLaunch.Enabled = enable_apps.Checked;

            if (currentPersonality.TabsToOpen == null)
            {
                currentPersonality.TabsToOpen = new TabsToOpenClass();
            }
            currentPersonality.TabsToOpen.Urls = string.Join(", ", list_websites_personalaty.Items.Cast<string>());
            currentPersonality.TabsToOpen.Enabled = enable_tabs.Checked;

            currentPersonality.Name = personalaty_name_feld.Text.Trim();
            currentPersonality.Enabled = enable_personalaty.Checked;

            // save automation tab settings
            if (currentPersonality.VirtualDesktopSwitch == null)
            {
                currentPersonality.VirtualDesktopSwitch = new VirtualDesktopSwitchClass { TargetDesktopName = "" };
            }
            currentPersonality.VirtualDesktopSwitch.Enabled = enable_Virtual_destop.Checked;
            currentPersonality.VirtualDesktopSwitch.TargetDesktopName = Virtual_destop_name.Text.Trim();

            currentPersonality.TriggerShortcut = trigger.Text.Trim();

            // save system settings
            if (currentPersonality.SystemSettingsAutomation == null)
            {
                currentPersonality.SystemSettingsAutomation = new SystemSettingsAutomationClass();
            }
            currentPersonality.SystemSettingsAutomation.DoNotDisturb = DnD.Checked;
            currentPersonality.SystemSettingsAutomation.VolumeLevel = volume.Value;

            // save global features
            if (fullConfig.FeatureSmartSuggestions == null)
            {
                fullConfig.FeatureSmartSuggestions = new FeatureSmartSuggestionsClass { ScanIntervalMinutes = 5 };
            }
            fullConfig.FeatureSmartSuggestions.Enabled = smart_suggestion.Checked;

            if (fullConfig.FeatureRamMonitor == null)
            {
                fullConfig.FeatureRamMonitor = new FeatureRamMonitorClass { MaxAllowedPercentage = 85 };
            }
            fullConfig.FeatureRamMonitor.Enabled = Ram_mon.Checked;

            // save wallpaper path
            if (currentPersonality.WallpaperSwitch == null)
            {
                currentPersonality.WallpaperSwitch = new WallpaperSwitchClass();
            }
            currentPersonality.WallpaperSwitch.Enabled = enable_wallpaper.Checked;

            if (list_wallpapers.Items.Count > 0)
            {
                currentPersonality.WallpaperSwitch.WallpaperPath = list_wallpapers.Items[0].ToString();
            }
            else
            {
                currentPersonality.WallpaperSwitch.WallpaperPath = "";
            }

            // sync updated personality name across all lists
            int selectedIndex = all_personalatys.SelectedIndex;
            if (selectedIndex != -1)
            {
                all_personalatys.Items[selectedIndex] = currentPersonality.Name;
                all_personalatys_auto.Items[selectedIndex] = currentPersonality.Name;
                list_personalatys_visual.Items[selectedIndex] = currentPersonality.Name;
                list_personalatys_sys.Items[selectedIndex] = currentPersonality.Name;
            }
            
            // write everything back to config.json
            try
            {
                string updatedJson = JsonConvert.SerializeObject(fullConfig, Formatting.Indented);
                File.WriteAllText(GetConfigFilePath(), updatedJson);
                MessageBox.Show("All changes across all menus saved successfully!", "Saved", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Failed writing files out: {ex.Message}", "Save Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void add_personalaty_Click(object sender, EventArgs e)
        {
            if (fullConfig == null || personalitiesList == null) return;

            Personality newPersonality = new Personality
            {
                Name = "new personality",
                Enabled = true,
                TriggerShortcut = "ctrl+alt+n",
                AppsToLaunch = new AppsToLaunchClass { Enabled = true, Paths = @"C:\Program Files\some-app.exe" },
                TabsToOpen = new TabsToOpenClass { Enabled = false, Urls = "https://www.google.com" },
                VirtualDesktopSwitch = new VirtualDesktopSwitchClass { Enabled = false, TargetDesktopName = "new-desktop" },
                SystemSettingsAutomation = new SystemSettingsAutomationClass
                {
                    Enabled = true, 
                    VolumeLevel = 20,
                    DoNotDisturb = true
                },
                WallpaperSwitch = new WallpaperSwitchClass
                {
                    Enabled = true,
                    WallpaperPath = @"D:\backgrounds\interesting.jpg"
                }
            };

            personalitiesList.Add(newPersonality);
            all_personalatys.Items.Add(newPersonality.Name);
            all_personalatys_auto.Items.Add(newPersonality.Name);
            list_personalatys_visual.Items.Add(newPersonality.Name);
            list_personalatys_sys.Items.Add(newPersonality.Name);

            all_personalatys.SelectedIndex = all_personalatys.Items.Count - 1;

            try
            {
                string updatedJson = JsonConvert.SerializeObject(fullConfig, Formatting.Indented);
                File.WriteAllText(GetConfigFilePath(), updatedJson);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Failed to save new personality: {ex.Message}", "Save Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void del_personalaty_Click(object sender, EventArgs e)
        {
            int selectedIndex = all_personalatys.SelectedIndex;

            if (selectedIndex == -1)
            {
                MessageBox.Show("Please select a personality from the list to delete.", "No Selection", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            var confirmResult = MessageBox.Show($"Are you sure you want to delete '{personalitiesList[selectedIndex].Name}'?", 
                                                 "Confirm Delete", MessageBoxButtons.YesNo, MessageBoxIcon.Question);
            
            if (confirmResult != DialogResult.Yes) return;

            personalitiesList.RemoveAt(selectedIndex);
            all_personalatys.Items.RemoveAt(selectedIndex);
            all_personalatys_auto.Items.RemoveAt(selectedIndex);
            list_personalatys_visual.Items.RemoveAt(selectedIndex);
            list_personalatys_sys.Items.RemoveAt(selectedIndex);

            try
            {
                string updatedJson = JsonConvert.SerializeObject(fullConfig, Formatting.Indented);
                File.WriteAllText(GetConfigFilePath(), updatedJson);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Failed to sync file deletion: {ex.Message}", "Save Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }

            if (all_personalatys.Items.Count > 0)
            {
                all_personalatys.SelectedIndex = Math.Min(selectedIndex, all_personalatys.Items.Count - 1);
            }
            else
            {
                currentPersonality = null;
                personalaty_name_feld.Clear();
                list_aplications_personalaty.Items.Clear();
                list_websites_personalaty.Items.Clear();
                enable_personalaty.Checked = false;
                enable_Virtual_destop.Checked = false;
            }
        }

        private void personalaty_button_Click(object sender, EventArgs e)
        {
            SwitchSettingsView(personalaty_settings);
        }

        private void auto_button_Click(object sender, EventArgs e)
        {
            SwitchSettingsView(automation_settings);
        }

        private void visual_button_Click(object sender, EventArgs e)
        {
            SwitchSettingsView(visual_settings);
        }

        private void sys_button_Click(object sender, EventArgs e)
        {
            SwitchSettingsView(sys_settings);
        }

        private void suport_button_Click(object sender, EventArgs e)
        {
            SwitchSettingsView(support_settings);
        }
    
        private void SwitchSettingsView(Panel panelToShow)
        {
            if (panelToShow == null) return;
            panelToShow.BringToFront();
        }

        private void tableLayoutPanel5_Paint(object sender, PaintEventArgs e)
        {
        }

        private void save_web_Click(object sender, EventArgs e)
        {
        }

        private void save_apps_Click(object sender, EventArgs e)
        {
        }

        private void list_personalatys_visual_SelectedIndexChanged(object sender, EventArgs e)
        {
            if (list_personalatys_visual.SelectedIndex == -1) return;
            LoadPersonalityData(list_personalatys_visual.SelectedIndex);
        }

        private void list_personalatys_sys_SelectedIndexChanged(object sender, EventArgs e)
        {
            if (list_personalatys_sys.SelectedIndex == -1) return;
            LoadPersonalityData(list_personalatys_sys.SelectedIndex);
        }

        private void enable_tabs_CheckedChanged(object sender, EventArgs e)
        {
        }

        private void checkBox1_CheckedChanged(object sender, EventArgs e)
        {
        }

        private void checkBox3_CheckedChanged(object sender, EventArgs e)
        {
        }

        private void enable_personalaty_CheckedChanged(object sender, EventArgs e)
        {
        }

        private void textBox3_TextChanged_1(object sender, EventArgs e)
        {
        }

        private void checkBox2_CheckedChanged(object sender, EventArgs e)
        {
        }

        private void textBox2_TextChanged(object sender, EventArgs e)
        {
        }

        private void tableLayoutPanel7_Paint(object sender, PaintEventArgs e)
        {
        }

        private void visual_settins_panel_Paint(object sender, PaintEventArgs e)
        {
        }

        private void label18_Click(object sender, EventArgs e)
        {
        }

        private void enable_wallpaper_CheckedChanged(object sender, EventArgs e)
        {
            if (currentPersonality == null) return;

            if (currentPersonality.WallpaperSwitch == null)
            {
                currentPersonality.WallpaperSwitch = new WallpaperSwitchClass();
            }
            currentPersonality.WallpaperSwitch.Enabled = enable_wallpaper.Checked;
        }

        private void add_wallpaper_Click(object sender, EventArgs e)
        {
            if (currentPersonality == null)
            {
                MessageBox.Show("Please select a personality first.", "No Selection", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            using (OpenFileDialog openFileDialog = new OpenFileDialog())
            {
                openFileDialog.Filter = "Image Files (*.jpg;*.jpeg;*.png;*.bmp)|*.jpg;*.jpeg;*.png;*.bmp|All files (*.*)|*.*";
                openFileDialog.Title = "Select a Background Wallpaper";

                if (openFileDialog.ShowDialog() == DialogResult.OK)
                {
                    if (currentPersonality.WallpaperSwitch == null)
                    {
                        currentPersonality.WallpaperSwitch = new WallpaperSwitchClass();
                    }
                    currentPersonality.WallpaperSwitch.WallpaperPath = openFileDialog.FileName;
                    
                    list_wallpapers.Items.Clear();
                    list_wallpapers.Items.Add(openFileDialog.FileName);
                    
                    MessageBox.Show($"Wallpaper path selected:\n{openFileDialog.FileName}\n\nDon't forget to click Save Changes!", "Path Set", MessageBoxButtons.OK, MessageBoxIcon.Information);
                }
            }
        }

        private void remove_wallpaper_Click(object sender, EventArgs e)
        {
            if (currentPersonality == null) return;

            if (currentPersonality.WallpaperSwitch != null)
            {
                currentPersonality.WallpaperSwitch.WallpaperPath = "";
                list_wallpapers.Items.Clear(); // clear listbox visually
                MessageBox.Show("Wallpaper path cleared. Click Save Changes to commit.", "Cleared", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
        }

        private void list_wallpapers_SelectedIndexChanged(object sender, EventArgs e)
        {
        }

        private void smart_suggestion_CheckedChanged(object sender, EventArgs e)
        {
        }

        private void Ram_mon_CheckedChanged(object sender, EventArgs e)
        {
        }

        private void volume_Scroll(object sender, EventArgs e)
        {
        }

        private void DnD_CheckedChanged(object sender, EventArgs e)
        {
        }

        private void ResetConfig_Click(object sender, EventArgs e)
        {
            // Prompt for confirmation to avoid accidental resets
            var confirmResult = MessageBox.Show(
                "Are you sure you want to reset your configuration to default?\nThis will overwrite your current settings.",
                "Confirm Reset",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Warning);

            if (confirmResult != DialogResult.Yes) return;

            try
            {
                // Standard default JSON structure matching your exact schema format
                string defaultJson = @"{
                ""global-settings"": {
                ""minimize-to-tray"": {
                  ""enabled"": true
                },
                ""run-at-startup"": {
                  ""enabled"": false
                }
                },
                ""personalities"": [
                {
                  ""name"": ""Study"",
                  ""enabled"": true,
                  ""trigger-shortcut"": ""ctrl+alt+s"",
                  ""apps-to-launch"": {
                    ""enabled"": true,
                    ""paths"": ""C:\\Program Files\\Code.exe, C:\\Program Files\\Anki\\anki.exe""
                  },
                  ""tabs-to-open"": {
                    ""enabled"": true,
                    ""urls"": ""https://github.com, https://trello.com""
                  },
                  ""virtual-desktop-switch"": {
                    ""enabled"": false,
                    ""target-desktop-name"": ""Study-Zone""
                  },
                  ""system-settings-automation"": {
                    ""enabled"": true,
                    ""volume-level"": 20,
                    ""do-not-disturb"": true
                  },
                  ""wallpaper-switch"": {
                    ""enabled"": true,
                    ""wallpaper-path"": ""D:\\backgrounds\\study.jpg""
                  }
                }
              ],
              ""feature-ram-monitor"": {
                ""enabled"": true,
                ""max-allowed-percentage"": 85
              },
              ""feature-smart-suggestions"": {
                ""enabled"": true,
                ""scan-interval-minutes"": 5
              }
            }";

                // Write the default JSON payload to config.json
                string filePath = GetConfigFilePath();
                System.IO.File.WriteAllText(filePath, defaultJson);

                // Refresh UI components immediately
                LoadPersonalitiesFromJson();

                // Select the new default personality in the UI list if present
                if (all_personalatys.Items.Count > 0)
                {
                    all_personalatys.SelectedIndex = 0;
                }

                MessageBox.Show("Configuration successfully reset to default settings!", "Reset Complete", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Failed to reset configuration: {ex.Message}", "Reset Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void OpenConfig_Click(object sender, EventArgs e)
        {
            try
            {
                string filePath = GetConfigFilePath();
                string directoryPath = System.IO.Path.GetDirectoryName(filePath);

                // Ensure directory exists
                if (!string.IsNullOrEmpty(directoryPath) && !System.IO.Directory.Exists(directoryPath))
                {
                    System.IO.Directory.CreateDirectory(directoryPath);
                }

                // If config.json exists, open folder and highlight the file directly
                if (System.IO.File.Exists(filePath))
                {
                    System.Diagnostics.Process.Start("explorer.exe", $"/select,\"{filePath}\"");
                }
                // If the file doesn't exist yet, open the containing directory
                else if (!string.IsNullOrEmpty(directoryPath) && System.IO.Directory.Exists(directoryPath))
                {
                    System.Diagnostics.Process.Start("explorer.exe", $"\"{directoryPath}\"");
                }
                else
                {
                    MessageBox.Show("Could not locate or create the configuration folder.", "Folder Not Found", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Unable to open configuration folder: {ex.Message}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }

    public class RootConfig
    {
        [JsonProperty("global-settings")]
        public Dictionary<string, Dictionary<string, bool>> GlobalSettings { get; set; }

        [JsonProperty("personalities")]
        public List<Personality> Personalities { get; set; }

        [JsonProperty("feature-ram-monitor")]
        public FeatureRamMonitorClass FeatureRamMonitor { get; set; }

        [JsonProperty("feature-smart-suggestions")]
        public FeatureSmartSuggestionsClass FeatureSmartSuggestions { get; set; }

        [JsonExtensionData]
        public Dictionary<string, object> AdditionalData { get; set; }
    }

    public class FeatureRamMonitorClass
    {
        [JsonProperty("enabled")]
        public bool Enabled { get; set; }

        [JsonProperty("max-allowed-percentage")]
        public int MaxAllowedPercentage { get; set; }
    }

    public class FeatureSmartSuggestionsClass
    {
        [JsonProperty("enabled")]
        public bool Enabled { get; set; }

        [JsonProperty("scan-interval-minutes")]
        public int ScanIntervalMinutes { get; set; }
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