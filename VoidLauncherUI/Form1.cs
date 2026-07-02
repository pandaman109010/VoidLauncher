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
    // holds the config data in the JSON file
    private RootConfig fullConfig; 

    // holds config data in JSON file
    private List<Personality> personalitiesList = new List<Personality>(); 

    // tracks personality being edited on screen
    private Personality currentPersonality;

        private string GetConfigFilePath()
        {
            // Gets the folder where the UI is currently running
            string exeDirectory = AppDomain.CurrentDomain.BaseDirectory;

            // 1. checks if the config file is right next to the UI
            string productionPath = Path.Combine(exeDirectory, "scripts", "config.json");
            if (File.Exists(productionPath))
            {
                return productionPath;
            }

            // 2. if not step up dir and chek for it each time
            DirectoryInfo dir = new DirectoryInfo(exeDirectory);
            while (dir != null)
            {
                string potentialPath = Path.Combine(dir.FullName, "scripts", "config.json");
                if (File.Exists(potentialPath))
                {
                    return potentialPath; 
                }
                dir = dir.Parent; // Move up one folder level each time
            }

            // Fallback default path if it can't find it anywhere
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

                    if (fullConfig != null && fullConfig.Personalities != null)
                    {
                        // fill the list inishaly
                        personalitiesList = fullConfig.Personalities;

                        // clear the list to avoid duplicates if reloading
                        all_personalatys.Items.Clear();
                        all_personalatys_auto.Items.Clear();
                        list_personalatys_visual.Items.Clear();
                        list_personalatys_sys.Items.Clear();

                        // Loop through your JSON array and add the names ("Study", "Gaming") into all ListBoxes
                        foreach (var personality in personalitiesList)
                        {
                            all_personalatys.Items.Add(personality.Name);
                            all_personalatys_auto.Items.Add(personality.Name);
                            list_personalatys_visual.Items.Add(personality.Name);
                            list_personalatys_sys.Items.Add(personality.Name);
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

        public ui()
        {
            InitializeComponent();
            LoadPersonalitiesFromJson();
            
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
        {  //opens file exploer to select an aplication
            OpenFileDialog openFileDialog = new OpenFileDialog();
            openFileDialog.Filter = "Applications (*.exe)|*.exe|All files (*.*)|*.*";
            openFileDialog.Title = "Select an Application for your personalaty";

            if (openFileDialog.ShowDialog() == DialogResult.OK)
            {
                // Automatically adds the aplication to the listbox
                list_aplications_personalaty.Items.Add(openFileDialog.FileName);
            }
        }

        private void remove_app_personalaty_Click(object sender, EventArgs e)
        {
            // Check if the user has actually selected an item in the list
            if (list_aplications_personalaty.SelectedIndex != -1)
            {
                // Remove the selected item from the ListBox
                list_aplications_personalaty.Items.RemoveAt(list_aplications_personalaty.SelectedIndex);
            }
            else
            {
                // Alert the user if they clicked remove without choosing an item
                MessageBox.Show("Please select an item from the list to remove.", "No Selection", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        private void remove_link_personalaty_Click(object sender, EventArgs e)
        {
            // Check if the user has actually selected an item in the list
            if (list_websites_personalaty.SelectedIndex != -1)
            {
                // Remove the selected item from the ListBox
                list_websites_personalaty.Items.RemoveAt(list_websites_personalaty.SelectedIndex);
            }
            else
            {
                // Optional: Alert the user if they clicked remove without choosing an item
                MessageBox.Show("Please select an item from the list to remove.", "No Selection", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        private void add_link_personalaty_Click(object sender, EventArgs e)
        {
            // 1. Grab the text from the text box and remove any accidental spaces at the beginning/end
                string url = personalaty_web_feald.Text.Trim();

                // 2. Make sure they actually typed something before clicking add
                if (string.IsNullOrEmpty(url))
                {
                    MessageBox.Show("Please enter a website URL first.", "Empty Field", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }

                // 3. Smart Formatting: If they typed "www.website.com", turn it into "https://www.website.com"
                // This makes sure it safely launches in their browser later on!
                if (!url.StartsWith("http://") && !url.StartsWith("https://"))
                {
                    url = "https://" + url;
                }

                // 4. Add the URL straight into the website ListBox
                list_websites_personalaty.Items.Add(url);

                // 5. Clear out the text box so it's instantly ready for the next link they want to type
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
            currentPersonality = personalitiesList[selectedIndex];

            // --- PANEL 1: PERSONALITIES VIEW ---
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

            // --- PANEL 2: AUTOMATION VIEW & SWITCHES ---
            // 1. App and Tab Checkboxes
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

            // 2. Trigger Shortcut TextBox
            trigger.Text = currentPersonality.TriggerShortcut ?? "";

            // 3. Virtual Desktop Checkbox & Virtual Desktop Name TextBox
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

            // --- PANEL 3: SYSTEM SETTINGS (PRE-WIRED FOR LATER) ---
            if (currentPersonality.SystemSettingsAutomation != null)
            {
                // chk_sys_automation_enabled.Checked = currentPersonality.SystemSettingsAutomation.Enabled;
                // num_volume_level.Value = currentPersonality.SystemSettingsAutomation.VolumeLevel;
                // chk_dnd_enabled.Checked = currentPersonality.SystemSettingsAutomation.DoNotDisturb;
            }

            if (currentPersonality.WallpaperSwitch != null)
            {
                // chk_wallpaper_enabled.Checked = currentPersonality.WallpaperSwitch.Enabled;
                // txt_wallpaper_path.Text = currentPersonality.WallpaperSwitch.WallpaperPath;
            }
        }

        private void save_pesonalatys_Click(object sender, EventArgs e)
        {
            SaveSettings(); //idk what is the right one and for some random reason this works so i leave it :D
        }

        private void save_pesonalatys_Click_1(object sender, EventArgs e)
        {
            SaveSettings(); //idk what is the right one and for some random reason this works so i leave it :D
        }

        // Separate reusable helper to write the FULL preserved config back to disk

        private void SaveSettings()
        {
            if (currentPersonality == null || fullConfig == null) return;

            // 1. Collect data from Personalities tab
            currentPersonality.AppsToLaunch.Paths = string.Join(", ", list_aplications_personalaty.Items.Cast<string>());
            currentPersonality.TabsToOpen.Urls = string.Join(", ", list_websites_personalaty.Items.Cast<string>());
            currentPersonality.Name = personalaty_name_feld.Text.Trim();
            currentPersonality.Enabled = enable_personalaty.Checked;

            if (currentPersonality.VirtualDesktopSwitch == null)
            {
                currentPersonality.VirtualDesktopSwitch = new VirtualDesktopSwitchClass { TargetDesktopName = "" };
            }
            currentPersonality.VirtualDesktopSwitch.Enabled = enable_Virtual_destop.Checked;

            if (currentPersonality.AppsToLaunch == null)
            {
                currentPersonality.AppsToLaunch = new AppsToLaunchClass();
            }
            currentPersonality.AppsToLaunch.Enabled = enable_apps.Checked;

            if (currentPersonality.TabsToOpen == null)
            {
                currentPersonality.TabsToOpen = new TabsToOpenClass();
            }
            currentPersonality.TabsToOpen.Enabled = enable_tabs.Checked;

            // 2. Collect data from Automation tab (Safety checks + templates ready for your controls)
            
            // === FIX 1: Save the shortcut key sequence from the correct text field ===
            currentPersonality.TriggerShortcut = trigger.Text.Trim();

            // === FIX 2: Save the virtual desktop target name from the correct text field ===
            currentPersonality.VirtualDesktopSwitch.TargetDesktopName = Virtual_destop_name.Text.Trim();

            if (currentPersonality.SystemSettingsAutomation == null)
            {
                currentPersonality.SystemSettingsAutomation = new SystemSettingsAutomationClass();
            }
            // UNCOMMENT THESE WHEN YOUR CONTROLS ARE READY:
            // currentPersonality.SystemSettingsAutomation.Enabled = chk_sys_automation_enabled.Checked;
            // currentPersonality.SystemSettingsAutomation.VolumeLevel = (int)num_volume_level.Value;
            // currentPersonality.SystemSettingsAutomation.DofNotDisturb = chk_dnd_enabled.Checked;

            if (currentPersonality.WallpaperSwitch == null)
            {
                currentPersonality.WallpaperSwitch = new WallpaperSwitchClass();
            }
            // UNCOMMENT THESE WHEN YOUR CONTROLS ARE READY:
            // currentPersonality.WallpaperSwitch.Enabled = chk_wallpaper_enabled.Checked;
            // currentPersonality.WallpaperSwitch.WallpaperPath = txt_wallpaper_path.Text.Trim();


            // 3. Update all visual listbox rows across all panels
            int selectedIndex = all_personalatys.SelectedIndex;
            if (selectedIndex != -1)
            {
                all_personalatys.Items[selectedIndex] = currentPersonality.Name;
                all_personalatys_auto.Items[selectedIndex] = currentPersonality.Name;
                list_personalatys_visual.Items[selectedIndex] = currentPersonality.Name;
                list_personalatys_sys.Items[selectedIndex] = currentPersonality.Name;
            }
            
            // 4. Save everything out to the single JSON file
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
                
                // Uses our clean new classes for consistent initialization defaults!
                SystemSettingsAutomation = new SystemSettingsAutomationClass
                {
                    Enabled = false,
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

            // 1. Double check they have an item highlighted
            if (selectedIndex == -1)
            {
                MessageBox.Show("Please select a personality from the list to delete.", "No Selection", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            // 2. Safety confirmation prompt
            var confirmResult = MessageBox.Show($"Are you sure you want to delete '{personalitiesList[selectedIndex].Name}'?", 
                                                 "Confirm Delete", MessageBoxButtons.YesNo, MessageBoxIcon.Question);
            
            if (confirmResult != DialogResult.Yes) return;

            // 3. Remove it from your local collections
            personalitiesList.RemoveAt(selectedIndex);
            all_personalatys.Items.RemoveAt(selectedIndex);
            all_personalatys_auto.Items.RemoveAt(selectedIndex);
            list_personalatys_visual.Items.RemoveAt(selectedIndex);
            list_personalatys_sys.Items.RemoveAt(selectedIndex);

            // 4. Update the JSON file right away to commit the deletion
            try
            {
                string updatedJson = JsonConvert.SerializeObject(fullConfig, Formatting.Indented);
                File.WriteAllText(GetConfigFilePath(), updatedJson);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Failed to sync file deletion: {ex.Message}", "Save Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }

            // 5. UI Cleanup: Select another profile if any remain, otherwise empty the screen
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
    
        //switch between setting panels
        private void SwitchSettingsView(Panel panelToShow)
        {
            if (panelToShow == null) return;

            // Snaps the selected panel to the top of the stack inside main_content_container
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
            //this is the trigger, it wont populate the names :(
        }

        private void checkBox2_CheckedChanged(object sender, EventArgs e)
        {
            //this is enable the virtual inverment
        }

        private void textBox2_TextChanged(object sender, EventArgs e)
        {
            //this is name the virtual inverment
        }

        private void tableLayoutPanel7_Paint(object sender, PaintEventArgs e)
        {

        }
    }
    public class RootConfig
    {
        [JsonProperty("global-settings")]
        public Dictionary<string, Dictionary<string, bool>> GlobalSettings { get; set; }

        [JsonProperty("personalities")]
        public List<Personality> Personalities { get; set; }

        // CATCH-ALL: Keeps ram-monitor, smart-suggestions, etc. completely safe
        [JsonExtensionData]
        public Dictionary<string, object> AdditionalData { get; set; }
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

        // NEW: Strong types for your Automation & Wallpaper settings!
        [JsonProperty("system-settings-automation")]
        public SystemSettingsAutomationClass SystemSettingsAutomation { get; set; }

        [JsonProperty("wallpaper-switch")]
        public WallpaperSwitchClass WallpaperSwitch { get; set; }

        [JsonExtensionData]
        public Dictionary<string, object> AdditionalData { get; set; }
    }

    // Class structure matching the automation JSON format
    public class SystemSettingsAutomationClass
    {
        [JsonProperty("enabled")]
        public bool Enabled { get; set; }

        [JsonProperty("volume-level")]
        public int VolumeLevel { get; set; }

        [JsonProperty("do-not-disturb")]
        public bool DoNotDisturb { get; set; }
    }

    // Class structure matching the wallpaper JSON format
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
