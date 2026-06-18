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

                        // Loop through your JSON array and add the names ("Study", "Gaming") into the ListBox
                        foreach (var personality in personalitiesList)
                        {
                            all_personalatys.Items.Add(personality.Name);
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
            // 1. make sure the user actually selected a valid item index
            if (all_personalatys.SelectedIndex == -1) return;

            // 2. Point currentPersonality to the item they clicked on in the roster list
            currentPersonality = personalitiesList[all_personalatys.SelectedIndex];

            // 3. Clear out old application views
            list_aplications_personalaty.Items.Clear();

            // 4. Split the comma separated path string and drop them into the app list box
            string dynamicPaths = currentPersonality.AppsToLaunch.Paths;
            if (!string.IsNullOrEmpty(dynamicPaths))
            {
                list_aplications_personalaty.Items.AddRange(dynamicPaths.Split(new string[] { ", " }, StringSplitOptions.RemoveEmptyEntries));
            }

            // 5. Do the exact same thing for the web URLs list box
            list_websites_personalaty.Items.Clear();
            string dynamicUrls = currentPersonality.TabsToOpen.Urls;
            if (!string.IsNullOrEmpty(dynamicUrls))
            {
                list_websites_personalaty.Items.AddRange(dynamicUrls.Split(new string[] { ", " }, StringSplitOptions.RemoveEmptyEntries));
            }

            // 6. Load name and trigger shortcut into their text fields
            personalaty_name_feld.Text = currentPersonality.Name;
            Trigger_feald_personalaty.Text = currentPersonality.TriggerShortcut;

            // 7. Load checkbox states
            enable_personalaty.Checked = currentPersonality.Enabled;

            if (currentPersonality.VirtualDesktopSwitch != null)
            {
                personalaty_in_vtral_invirement.Checked = currentPersonality.VirtualDesktopSwitch.Enabled;
            }
            else
            {
                personalaty_in_vtral_invirement.Checked = false;
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

            // 1: Collect ALL data from the UI controls into the object
            currentPersonality.AppsToLaunch.Paths = string.Join(", ", list_aplications_personalaty.Items.Cast<string>());
            currentPersonality.TabsToOpen.Urls = string.Join(", ", list_websites_personalaty.Items.Cast<string>());
            currentPersonality.Name = personalaty_name_feld.Text.Trim();
            currentPersonality.TriggerShortcut = Trigger_feald_personalaty.Text.Trim();
            currentPersonality.Enabled = enable_personalaty.Checked;

            // Make sure the virtual desktop object exists before assigning to it
            if (currentPersonality.VirtualDesktopSwitch == null)
            {
                currentPersonality.VirtualDesktopSwitch = new VirtualDesktopSwitchClass { TargetDesktopName = "" };
            }
            currentPersonality.VirtualDesktopSwitch.Enabled = personalaty_in_vtral_invirement.Checked;

            // 2: Update the visual listbox text on the left 
            int selectedIndex = all_personalatys.SelectedIndex;
            if (selectedIndex != -1)
            {
                all_personalatys.Items[selectedIndex] = currentPersonality.Name;
            }
            
            // 3: Save everything out to the JSON file
            try
            {
                string updatedJson = JsonConvert.SerializeObject(fullConfig, Formatting.Indented);
                
                File.WriteAllText(GetConfigFilePath(), updatedJson);
                MessageBox.Show("All changes synchronized into JSON file successfully!", "Saved", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Failed writing files out: {ex.Message}", "Save Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void add_personalaty_Click(object sender, EventArgs e)
        {
           if (fullConfig == null || personalitiesList == null) return;

            // 1. Create a brand new personality template with defaults
            Personality newPersonality = new Personality
            {
                Name = "new personality",
                Enabled = true,
                TriggerShortcut = "ctrl+alt+n",
                AppsToLaunch = new AppsToLaunchClass 
                { 
                    Enabled = true, 
                    Paths = @"C:\Program Files\some-app.exe" 
                },
                TabsToOpen = new TabsToOpenClass 
                { 
                    Enabled = false, 
                    Urls = "https://www.google.com" 
                },
                VirtualDesktopSwitch = new VirtualDesktopSwitchClass 
                { 
                    Enabled = false, 
                    TargetDesktopName = "new-desktop" 
                },
                // inject these into AdditionalData so they write out to the JSON perfectly 
                // without needing explicit C# classes for them yet
                AdditionalData = new Dictionary<string, object>
                {
                    {
                        "system-settings-automation", new Dictionary<string, object>
                        {
                            { "enabled", false },
                            { "volume-level", 20 },
                            { "do-not-disturb", true }
                        }
                    },
                    {
                        "wallpaper-switch", new Dictionary<string, object>
                        {
                            { "enabled", true },
                            { "wallpaper-path", @"D:\backgrounds\interesting.jpg" }
                        }
                    }
                }
            };

            // 2. Push it into our configuration tracking arrays
            personalitiesList.Add(newPersonality);
            all_personalatys.Items.Add(newPersonality.Name);

            // 3. Force-select the new item (this automatically runs SelectedIndexChanged to load your new defaults on-screen)
            all_personalatys.SelectedIndex = all_personalatys.Items.Count - 1;

            // 4. Save the container state immediately to your config file
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
                Trigger_feald_personalaty.Clear();
                list_aplications_personalaty.Items.Clear();
                list_websites_personalaty.Items.Clear();
                enable_personalaty.Checked = false;
                personalaty_in_vtral_invirement.Checked = false;
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

        [JsonExtensionData]
        public Dictionary<string, object> AdditionalData { get; set; }
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
